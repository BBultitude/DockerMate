"""
DockerMate - Network Manager Service (Sprint 4)
================================================

Service layer for Docker network lifecycle management with hardware-aware
subnet sizing, IPAM validation, and oversized-network detection.

Key responsibilities
---------------------
* CRUD against the Docker daemon (via the SDK) and mirror state into the
  ``networks`` DB table for the UI.
* Validate CIDR input: well-formed, non-overlapping with existing networks,
  and within the limit set by the hardware profile.
* Recommend subnet sizes based on the detected hardware tier so that
  resource-constrained hosts (e.g. Raspberry Pi) are not given a /16 by
  accident.
* Flag networks whose prefix length is much smaller than the number of
  containers actually using them ("oversized").

Usage
-----
    from backend.services.network_manager import NetworkManager

    manager = NetworkManager()
    networks = manager.list_networks()
    manager.create_network(name='app-net', driver='bridge', subnet='172.20.0.0/24')
    manager.delete_network('abc123...')
"""

import ipaddress
import logging
from typing import Any, Dict, List, Optional

from backend.models.database import SessionLocal
from backend.models.host_config import HostConfig
from backend.models.network import Network
from backend.models.container import Container
from backend.models.ip_reservation import IPReservation
from backend.utils.docker_client import get_docker_client

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Hardware-aware subnet recommendations
# ---------------------------------------------------------------------------
# Maps HostConfig.profile_name → (small_prefix, large_prefix)
# "small" = snug fit for up to ~max_containers / 3
# "large" = comfortable headroom for the full container limit
_PROFILE_SUBNETS: Dict[str, Dict[str, str]] = {
    'RASPBERRY_PI': {'small': '/28', 'large': '/27'},   # 14 / 30 hosts
    'LOW_END':      {'small': '/27', 'large': '/26'},   # 30 / 62 hosts
    'MEDIUM_SERVER':{'small': '/26', 'large': '/25'},   # 62 / 126 hosts
    'HIGH_END':     {'small': '/25', 'large': '/24'},   # 126 / 254 hosts
    'ENTERPRISE':   {'small': '/24', 'large': '/23'},   # 254 / 510 hosts
}

# Base addresses we cycle through when auto-picking a subnet
_BASE_OCTETS = ['172.20', '172.21', '172.22', '172.23',
                '10.10',  '10.11',  '10.12',  '10.13']


def _prefix_to_host_count(prefix: int) -> int:
    """Number of usable host addresses in a /<prefix> network."""
    return max(0, 2 ** (32 - prefix) - 2)


def _is_oversized(subnet: str, container_count: int) -> bool:
    """
    A network is "oversized" when the usable host count is more than 4x the
    number of containers currently attached (and at least 10 hosts are wasted).

    Networks with zero containers are never flagged — they are "unused", not
    "oversized".  The 4x ratio only becomes meaningful once at least one
    container is attached.

    /16 networks (65534 usable) are always flagged when they have at least one
    container, because even 4x would require 16 000+ containers to clear the
    bar — that threshold is meaningless in a home-lab context.  The hard
    trigger is: prefix ≤ 16 AND container_count ≥ 1.
    """
    if container_count == 0:
        return False
    try:
        prefix = ipaddress.ip_network(subnet, strict=False).prefixlen
        hosts = _prefix_to_host_count(prefix)
        # Always flag /16 and larger when any container is present
        if prefix <= 16:
            return True
        return hosts > max(container_count * 4, 10)
    except (ValueError, TypeError):
        return False


def _build_cli_create(name: str, driver: str, subnet: Optional[str], gateway: Optional[str]) -> str:
    """Reconstruct the equivalent ``docker network create`` CLI command."""
    parts = ['docker network create']
    if driver and driver != 'bridge':
        parts.append(f'--driver {driver}')
    if subnet:
        parts.append(f'--subnet {subnet}')
    if gateway:
        parts.append(f'--gateway {gateway}')
    parts.append(name)
    return ' '.join(parts)


class NetworkManager:
    """Manages Docker networks and their database mirror."""

    def __init__(self):
        self.db = SessionLocal()

    def close(self):
        if self.db:
            self.db.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    # ------------------------------------------------------------------
    # List
    # ------------------------------------------------------------------

    def list_networks(self) -> List[Dict[str, Any]]:
        """
        Return all Docker networks enriched with DB metadata and live
        container counts.  Docker's default networks (bridge, host, none)
        are included but marked as unmanaged.
        """
        client = get_docker_client()
        docker_nets = client.networks.list()

        # Build a quick lookup of DB-managed network IDs
        db_networks = {n.network_id: n for n in self.db.query(Network).all()}

        results = []
        for net in docker_nets:
            # Reload each network so that the Containers dict is populated;
            # the list endpoint may omit it in some Docker versions.
            try:
                net.reload()
            except Exception:
                pass

            net_id = net.id
            db_net = db_networks.get(net_id)

            # Pull IPAM config from Docker attrs
            ipam_config = net.attrs.get('IPAM', {}).get('Config', [])
            subnet = ipam_config[0].get('Subnet') if ipam_config else None
            gateway = ipam_config[0].get('Gateway') if ipam_config else None

            # Count containers attached to this network
            container_count = len(net.attrs.get('Containers', {}))

            is_default = net.name in ('bridge', 'host', 'none')

            # Driver — some Docker versions return null for built-in networks
            driver = net.attrs.get('Driver') or 'unknown'
            if driver == 'unknown' and net.name in ('bridge', 'host', 'none'):
                driver = net.name

            entry: Dict[str, Any] = {
                'network_id': net_id,
                'name': net.name,
                'driver': driver,
                'subnet': subnet,
                'gateway': gateway,
                'container_count': container_count,
                'managed': db_net.managed if db_net else False,
                'purpose': db_net.purpose if db_net else None,
                'oversized': (
                    False if is_default
                    else _is_oversized(subnet, container_count) if subnet
                    else False
                ),
                'docker_cli_create': _build_cli_create(net.name, driver, subnet, gateway) if not is_default else None,
            }
            results.append(entry)

        # Sync: persist any newly discovered networks into the DB
        self._sync_discovered_networks(docker_nets)

        return results

    # ------------------------------------------------------------------
    # Get single network
    # ------------------------------------------------------------------

    def get_network(self, network_id: str) -> Optional[Dict[str, Any]]:
        """Full details for one network including connected containers."""
        client = get_docker_client()
        try:
            net = client.networks.get(network_id)
            net.reload()   # populate Containers dict (may be omitted by list)
        except Exception:
            return None

        ipam_config = net.attrs.get('IPAM', {}).get('Config', [])
        subnet = ipam_config[0].get('Subnet') if ipam_config else None
        gateway = ipam_config[0].get('Gateway') if ipam_config else None

        db_net = self.db.query(Network).filter_by(network_id=network_id).first()

        # Cross-reference with DB to tag managed vs external containers
        managed_ids = {c.container_id for c in self.db.query(Container).all()}

        containers_raw = net.attrs.get('Containers', {})

        # Fallback: Docker's Containers dict is unreliable for host/none
        # networks.  Use the network filter on containers instead.
        if not containers_raw:
            try:
                for c in client.containers.list(all=True, filters={'network': [net.id]}):
                    c.reload()
                    for _, net_info in c.attrs.get('NetworkSettings', {}).get('Networks', {}).items():
                        if net_info.get('NetworkID') == net.id:
                            containers_raw[c.id] = {
                                'Name': c.attrs.get('Name', ''),
                                'IPv4Address': net_info.get('IPAddress', ''),
                                'IPv6Address': net_info.get('IPv6Address', ''),
                            }
                            break
            except Exception:
                pass

        containers = []
        for cid, cinfo in containers_raw.items():
            containers.append({
                'container_id': cid,
                'name': cinfo.get('Name', '').lstrip('/'),
                'ipv4_address': cinfo.get('IPv4Address', ''),
                'ipv6_address': cinfo.get('IPv6Address', ''),
                'managed': cid in managed_ids,
            })

        container_count = len(containers)

        is_default = net.name in ('bridge', 'host', 'none')

        # Driver — some Docker versions return null for built-in networks
        driver = net.attrs.get('Driver') or 'unknown'
        if driver == 'unknown' and net.name in ('bridge', 'host', 'none'):
            driver = net.name

        return {
            'network_id': net.id,
            'name': net.name,
            'driver': driver,
            'subnet': subnet,
            'gateway': gateway,
            'ip_range': ipam_config[0].get('IPRange') if ipam_config else None,
            'container_count': container_count,
            'containers': containers,
            'managed': db_net.managed if db_net else False,
            'purpose': db_net.purpose if db_net else None,
            'oversized': (
                False if is_default
                else _is_oversized(subnet, container_count) if subnet
                else False
            ),
            'options': net.attrs.get('Options', {}),
            'docker_cli_create': _build_cli_create(net.name, driver, subnet, gateway) if not is_default else None,
        }

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    def create_network(
        self,
        name: str,
        driver: str = 'bridge',
        subnet: Optional[str] = None,
        gateway: Optional[str] = None,
        ip_range: Optional[str] = None,
        purpose: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a Docker network and persist it to the DB.

        Validates the name and subnet before hitting the daemon.  Returns
        a success dict with the new network_id or an error dict.
        """
        client = get_docker_client()

        # --- name validation ---
        if not name or not name.strip():
            return {'success': False, 'error': 'Network name is required'}
        name = name.strip()

        # Check for duplicate name
        existing = self.db.query(Network).filter_by(name=name).first()
        if existing:
            return {'success': False, 'error': f"A network named '{name}' already exists"}

        # --- subnet validation ---
        if subnet:
            validation = self.validate_subnet(subnet)
            if not validation['valid']:
                return {'success': False, 'error': validation['reason']}

        # --- build IPAM config for Docker SDK ---
        ipam_config = None
        if subnet:
            import docker.types as dtypes
            ipam_pool = dtypes.IPAMPool(
                subnet=subnet,
                gateway=gateway,
                iprange=ip_range,
            )
            ipam_config = dtypes.IPAMConfig(pool_configs=[ipam_pool])

        # --- create via Docker daemon ---
        try:
            docker_net = client.networks.create(
                name=name,
                driver=driver,
                ipam=ipam_config,
            )
        except Exception as e:
            return {'success': False, 'error': f'Docker error: {str(e)}'}

        # Reload from Docker to pick up auto-assigned gateway/subnet
        docker_net.reload()
        ipam_cfg = docker_net.attrs.get('IPAM', {}).get('Config', [])
        actual_subnet = ipam_cfg[0].get('Subnet') if ipam_cfg else subnet
        actual_gateway = ipam_cfg[0].get('Gateway') if ipam_cfg else gateway

        # --- persist to DB ---
        db_network = Network(
            network_id=docker_net.id,
            name=name,
            driver=driver,
            subnet=actual_subnet,
            gateway=actual_gateway,
            ip_range=ip_range,
            purpose=purpose,
            managed=True,
        )
        self.db.add(db_network)
        self.db.commit()

        logger.info(f"Created network '{name}' ({docker_net.id[:12]})")

        return {
            'success': True,
            'network_id': docker_net.id,
            'name': name,
            'subnet': actual_subnet,
            'gateway': actual_gateway,
        }

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    def delete_network(self, network_id: str) -> Dict[str, Any]:
        """
        Remove a Docker network.  Refuses to delete networks that still have
        containers attached or that are Docker-managed defaults.
        """
        client = get_docker_client()

        # Fetch live network info
        try:
            net = client.networks.get(network_id)
        except Exception:
            return {'success': False, 'error': 'Network not found'}

        # Safety: refuse to delete default Docker networks
        if net.name in ('bridge', 'host', 'none'):
            return {'success': False, 'error': f"Cannot delete default Docker network '{net.name}'"}

        # Safety: refuse if containers are still attached
        if net.attrs.get('Containers'):
            count = len(net.attrs['Containers'])
            return {
                'success': False,
                'error': f"Network has {count} container(s) attached. Disconnect them first."
            }

        # Remove from Docker
        try:
            net.remove()
        except Exception as e:
            return {'success': False, 'error': f'Docker error: {str(e)}'}

        # Remove from DB
        db_net = self.db.query(Network).filter_by(network_id=network_id).first()
        if db_net:
            self.db.delete(db_net)
            self.db.commit()

        logger.info(f"Deleted network '{net.name}' ({network_id[:12]})")
        return {'success': True, 'name': net.name}

    # ------------------------------------------------------------------
    # Subnet validation
    # ------------------------------------------------------------------

    def validate_subnet(self, subnet: str) -> Dict[str, Any]:
        """
        Check that *subnet* is a valid CIDR block, does not overlap with
        any existing Docker network, and respects the hardware profile limit.

        Returns ``{'valid': True}`` or ``{'valid': False, 'reason': '...'}``.
        """
        # Parse
        try:
            network = ipaddress.ip_network(subnet, strict=False)
        except (ValueError, TypeError):
            return {'valid': False, 'reason': f"'{subnet}' is not a valid CIDR notation"}

        # Minimum /30 (2 hosts)
        if network.prefixlen > 30:
            return {'valid': False, 'reason': 'Subnet must be at least /30 (2 usable hosts)'}

        # Hardware-profile upper bound
        config = HostConfig.get_or_create(self.db)
        limit = config.network_size_limit or '/16'
        try:
            max_prefix = int(limit.replace('/', ''))
        except (ValueError, AttributeError):
            max_prefix = 16
        if network.prefixlen < max_prefix:
            return {
                'valid': False,
                'reason': (
                    f"Subnet is larger than the /{max_prefix} limit "
                    f"allowed by your {config.profile_name} hardware profile"
                )
            }

        # Overlap check against live Docker networks
        client = get_docker_client()
        for existing_net in client.networks.list():
            ipam = existing_net.attrs.get('IPAM', {}).get('Config', [])
            if not ipam:
                continue
            existing_subnet_str = ipam[0].get('Subnet')
            if not existing_subnet_str:
                continue
            try:
                existing_net_obj = ipaddress.ip_network(existing_subnet_str, strict=False)
                if network.overlaps(existing_net_obj):
                    return {
                        'valid': False,
                        'reason': (
                            f"Subnet overlaps with existing network "
                            f"'{existing_net.name}' ({existing_subnet_str})"
                        )
                    }
            except ValueError:
                continue

        return {'valid': True}

    # ------------------------------------------------------------------
    # Subnet recommendations (hardware-aware)
    # ------------------------------------------------------------------

    def recommend_subnets(self) -> Dict[str, Any]:
        """
        Return a small/large subnet recommendation based on the detected
        hardware profile, plus a free base address that does not collide with
        existing networks.
        """
        config = HostConfig.get_or_create(self.db)
        profile = config.profile_name or 'MEDIUM_SERVER'

        rec = _PROFILE_SUBNETS.get(profile, _PROFILE_SUBNETS['MEDIUM_SERVER'])

        # Find a non-overlapping base address
        client = get_docker_client()
        existing_subnets = []
        for net in client.networks.list():
            ipam = net.attrs.get('IPAM', {}).get('Config', [])
            if ipam and ipam[0].get('Subnet'):
                try:
                    existing_subnets.append(
                        ipaddress.ip_network(ipam[0]['Subnet'], strict=False)
                    )
                except ValueError:
                    pass

        free_base = None
        for base in _BASE_OCTETS:
            candidate = ipaddress.ip_network(f'{base}.0.0/16', strict=False)
            if not any(candidate.overlaps(e) for e in existing_subnets):
                free_base = base
                break

        if not free_base:
            free_base = '172.20'  # fallback; validation will catch collisions

        small_prefix = rec['small'].replace('/', '')
        large_prefix = rec['large'].replace('/', '')

        return {
            'profile': profile,
            'small': f'{free_base}.0.0{rec["small"]}',
            'large': f'{free_base}.0.0{rec["large"]}',
            'small_hosts': _prefix_to_host_count(int(small_prefix)),
            'large_hosts': _prefix_to_host_count(int(large_prefix)),
        }

    # ------------------------------------------------------------------
    # IP Reservations
    # ------------------------------------------------------------------

    def get_ip_allocations(self, network_id: str) -> Optional[Dict[str, Any]]:
        """
        Return a full IP-allocation snapshot for a single network.

        The response includes:
        - Subnet geometry (usable range, gateway, totals)
        - A list of assigned IPs pulled live from Docker
        - A list of reserved IPs/ranges from the database
        - Derived free-IP count

        Returns None if the network does not exist or has no subnet.
        """
        client = get_docker_client()
        try:
            net = client.networks.get(network_id)
        except Exception:
            return None

        ipam_config = net.attrs.get('IPAM', {}).get('Config', [])
        if not ipam_config or not ipam_config[0].get('Subnet'):
            return None

        subnet_str = ipam_config[0]['Subnet']
        gateway_str = ipam_config[0].get('Gateway', '')

        try:
            network_obj = ipaddress.ip_network(subnet_str, strict=False)
        except ValueError:
            return None

        usable = list(network_obj.hosts())  # excludes network + broadcast addresses
        if not usable:
            return None

        # --- assigned IPs (live from Docker) ---
        assigned_map: Dict[str, str] = {}  # ip -> container_name
        for cid, cinfo in net.attrs.get('Containers', {}).items():
            ip = cinfo.get('IPv4Address', '').split('/')[0]  # strip /prefix if present
            if ip:
                assigned_map[ip] = cinfo.get('Name', '').lstrip('/')

        # --- reserved IPs (from DB) ---
        db_net = self.db.query(Network).filter_by(network_id=network_id).first()
        reservations: List[Dict[str, Any]] = []
        reserved_ips: set = set()
        if db_net:
            rows = (
                self.db.query(IPReservation)
                .filter_by(network_id=db_net.id)
                .order_by(IPReservation.range_name, IPReservation.ip_address)
                .all()
            )
            # Group by range_name for the response
            ranges: Dict[str, Dict[str, Any]] = {}
            for row in rows:
                reserved_ips.add(row.ip_address)
                key = row.range_name or '__single__'
                if key not in ranges:
                    ranges[key] = {
                        'range_name': row.range_name,
                        'description': row.description,
                        'ips': [],
                    }
                ranges[key]['ips'].append(row.ip_address)
            reservations = list(ranges.values())

        # --- compute free and utilisation ---
        # "assignable" = subnet hosts minus the two locked addresses:
        #   • broadcast  — never allocatable (hosts() already drops it, but we
        #                  strip it explicitly so the intent is clear)
        #   • gateway    — owned by Docker / the host; shown separately in the UI
        # "used" = containers + reservations only; gateway and broadcast do NOT count.
        usable_set = {str(ip) for ip in usable}
        locked = {str(network_obj.broadcast_address)}
        if gateway_str:
            locked.add(gateway_str)
        assignable = usable_set - locked

        # Sorted assignable list gives us the true first/last boundaries
        assignable_sorted = sorted(assignable, key=lambda ip: ipaddress.ip_address(ip))

        user_used = set(assigned_map.keys()) | reserved_ips   # containers + reservations
        free_ips = assignable - user_used
        utilisation = round(len(user_used) / len(assignable) * 100, 1) if assignable else 0

        return {
            'network_id': network_id,
            'name': net.name,
            'subnet': subnet_str,
            'network_address': str(network_obj.network_address),
            'broadcast_address': str(network_obj.broadcast_address),
            'first_usable': assignable_sorted[0] if assignable_sorted else '',
            'last_usable': assignable_sorted[-1] if assignable_sorted else '',
            'total_usable': len(assignable),
            'gateway': gateway_str,
            'assigned': [
                {'ip': ip, 'container': name}
                for ip, name in sorted(assigned_map.items())
            ],
            'assigned_count': len(assigned_map),
            'reserved': reservations,
            'reserved_count': len(reserved_ips),
            'free_count': len(free_ips),
            'utilisation_pct': utilisation,
        }

    def reserve_ip_range(
        self,
        network_id: str,
        range_name: str,
        start_ip: str,
        end_ip: str,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a named reservation block covering [start_ip … end_ip] on the
        network identified by its Docker hex *network_id*.

        Validates that:
        - The network exists in the DB and has a subnet
        - Both IPs are within the subnet's usable range
        - start <= end
        - No IP in the range is already reserved
        """
        db_net = self.db.query(Network).filter_by(network_id=network_id).first()
        if not db_net or not db_net.subnet:
            return {'success': False, 'error': 'Network not found or has no subnet'}

        if not range_name or not range_name.strip():
            return {'success': False, 'error': 'Range name is required'}
        range_name = range_name.strip()

        # Parse and validate IPs
        try:
            start = ipaddress.ip_address(start_ip)
            end = ipaddress.ip_address(end_ip)
            net_obj = ipaddress.ip_network(db_net.subnet, strict=False)
        except ValueError as e:
            return {'success': False, 'error': f'Invalid IP address: {e}'}

        if start > end:
            return {'success': False, 'error': 'Start IP must be ≤ end IP'}

        usable = set(net_obj.hosts())
        # Walk the range and collect IPs
        candidate_ips: List[str] = []
        current = start
        while current <= end:
            if current not in usable:
                return {
                    'success': False,
                    'error': f'{current} is outside the usable range of {db_net.subnet}'
                }
            candidate_ips.append(str(current))
            current += 1

        if not candidate_ips:
            return {'success': False, 'error': 'No IPs in the specified range'}

        # Collision check against existing reservations
        existing = {
            r.ip_address for r in
            self.db.query(IPReservation).filter_by(network_id=db_net.id).all()
        }
        collisions = existing & set(candidate_ips)
        if collisions:
            return {
                'success': False,
                'error': f'IP(s) already reserved: {", ".join(sorted(collisions))}'
            }

        # Insert rows
        for ip in candidate_ips:
            self.db.add(IPReservation(
                network_id=db_net.id,
                ip_address=ip,
                range_name=range_name,
                description=description,
            ))
        self.db.commit()

        logger.info(
            f"Reserved {len(candidate_ips)} IPs as '{range_name}' "
            f"on network '{db_net.name}'"
        )
        return {
            'success': True,
            'range_name': range_name,
            'ips_reserved': candidate_ips,
            'count': len(candidate_ips),
        }

    def delete_reservation(self, network_id: str, range_name: str) -> Dict[str, Any]:
        """
        Remove all IP reservations matching *range_name* on the given network.
        """
        db_net = self.db.query(Network).filter_by(network_id=network_id).first()
        if not db_net:
            return {'success': False, 'error': 'Network not found'}

        rows = (
            self.db.query(IPReservation)
            .filter_by(network_id=db_net.id, range_name=range_name)
            .all()
        )
        if not rows:
            return {'success': False, 'error': f"No reservation named '{range_name}' found"}

        count = len(rows)
        for row in rows:
            self.db.delete(row)
        self.db.commit()

        logger.info(f"Deleted reservation '{range_name}' ({count} IPs) from '{db_net.name}'")
        return {'success': True, 'range_name': range_name, 'ips_released': count}

    # ------------------------------------------------------------------
    # Connect / disconnect containers
    # ------------------------------------------------------------------

    def connect_container(self, network_id: str, container_id: str) -> Dict[str, Any]:
        """Attach an existing container to a network."""
        client = get_docker_client()
        try:
            net = client.networks.get(network_id)
        except Exception:
            return {'success': False, 'error': 'Network not found'}

        if net.name in ('bridge', 'host', 'none'):
            return {'success': False, 'error': f"Use Docker directly to connect to default network '{net.name}'"}

        try:
            container = client.containers.get(container_id)
        except Exception:
            return {'success': False, 'error': 'Container not found'}

        try:
            net.connect(container)
        except Exception as e:
            return {'success': False, 'error': f'Docker error: {e}'}

        logger.info(f"Connected '{container.name.lstrip('/')}' to '{net.name}'")
        return {'success': True, 'container_name': container.name.lstrip('/')}

    def disconnect_container(self, network_id: str, container_id: str) -> Dict[str, Any]:
        """Detach a container from a network."""
        client = get_docker_client()
        try:
            net = client.networks.get(network_id)
        except Exception:
            return {'success': False, 'error': 'Network not found'}

        try:
            container = client.containers.get(container_id)
        except Exception:
            return {'success': False, 'error': 'Container not found'}

        try:
            net.disconnect(container)
        except Exception as e:
            return {'success': False, 'error': f'Docker error: {e}'}

        logger.info(f"Disconnected '{container.name.lstrip('/')}' from '{net.name}'")
        return {'success': True, 'container_name': container.name.lstrip('/')}

    # ------------------------------------------------------------------
    # Adopt / Release (FEAT-017)
    # ------------------------------------------------------------------

    def adopt_network(self, network_id: str) -> Dict[str, Any]:
        """
        Adopt an unmanaged network — flip managed → True.

        Metadata-only: no change is made to the Docker network itself.
        After adoption the network participates in all DockerMate
        management features (purpose field, oversized warnings, etc.).
        """
        net = self.db.query(Network).filter(Network.network_id == network_id).first()
        if not net:
            return {'success': False, 'error': 'Network not found'}
        if net.name in ('bridge', 'host', 'none'):
            return {'success': False, 'error': 'Default networks cannot be adopted'}
        if net.managed:
            return {'success': False, 'error': 'Network is already managed'}

        net.managed = True
        self.db.commit()
        logger.info(f"Network '{net.name}' adopted")
        return {'success': True, 'message': f"Network '{net.name}' adopted"}

    def release_network(self, network_id: str) -> Dict[str, Any]:
        """
        Release a managed network — flip managed → False.

        Metadata-only: the Docker network continues to exist and
        function.  The DB row is kept (so IP reservations etc. are
        preserved) but the network reverts to "unmanaged" state in
        the UI.
        """
        net = self.db.query(Network).filter(Network.network_id == network_id).first()
        if not net:
            return {'success': False, 'error': 'Network not found'}
        if net.name in ('bridge', 'host', 'none'):
            return {'success': False, 'error': 'Default networks cannot be released'}
        if not net.managed:
            return {'success': False, 'error': 'Network is not currently managed'}

        net.managed = False
        self.db.commit()
        logger.info(f"Network '{net.name}' released")
        return {'success': True, 'message': f"Network '{net.name}' released"}

    # ------------------------------------------------------------------
    # Documentation generation
    # ------------------------------------------------------------------

    def generate_docs(self) -> str:
        """
        Assemble a Markdown report covering every network on the host:
        metadata, connected containers, IP reservation blocks, and
        utilisation stats where a subnet is available.

        The output is plain Markdown — copy-paste ready.
        """
        from datetime import datetime, timezone

        networks = self.list_networks()
        lines: List[str] = []
        lines.append('# DockerMate — Network Documentation')
        lines.append(f'Generated: {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}')
        lines.append('')

        for net in networks:
            net_id = net['network_id']
            name = net['name']
            tags = []
            if net.get('managed'):
                tags.append('Managed')
            if name in ('bridge', 'host', 'none'):
                tags.append('Default')
            if net.get('oversized'):
                tags.append('Oversized')
            tag_str = f" [{', '.join(tags)}]" if tags else ''

            lines.append('---')
            lines.append('')
            lines.append(f'## {name}{tag_str}')
            lines.append('')
            lines.append(f'- **Driver:** {net.get("driver", "unknown")}')
            if net.get('subnet'):
                lines.append(f'- **Subnet:** {net["subnet"]}')
            if net.get('gateway'):
                lines.append(f'- **Gateway:** {net["gateway"]}')
            if net.get('purpose'):
                lines.append(f'- **Purpose:** {net["purpose"]}')
            lines.append(f'- **Containers:** {net.get("container_count", 0)}')
            if net.get('docker_cli_create'):
                lines.append(f'- **Create command:** `{net["docker_cli_create"]}`')
            lines.append('')

            # --- full detail (containers + IP stats) via get_network ---
            detail = self.get_network(net_id)
            if detail and detail.get('containers'):
                lines.append('### Connected Containers')
                lines.append('')
                lines.append('| Container | IP Address |')
                lines.append('|-----------|------------|')
                for c in detail['containers']:
                    lines.append(f'| `{c["name"]}` | `{c.get("ipv4_address", "—")}` |')
                lines.append('')

            # --- IP allocation stats (only if subnet exists) ---
            if net.get('subnet'):
                alloc = self.get_ip_allocations(net_id)
                if alloc:
                    lines.append('### IP Allocation')
                    lines.append('')
                    lines.append(f'| Metric | Value |')
                    lines.append(f'|--------|-------|')
                    lines.append(f'| Usable range | `{alloc["first_usable"]}` – `{alloc["last_usable"]}` |')
                    lines.append(f'| Total usable | {alloc["total_usable"]} |')
                    lines.append(f'| Assigned | {alloc["assigned_count"]} |')
                    lines.append(f'| Reserved | {alloc["reserved_count"]} |')
                    lines.append(f'| Free | {alloc["free_count"]} |')
                    lines.append(f'| Utilisation | {alloc["utilisation_pct"]}% |')
                    lines.append('')

                    if alloc.get('reserved'):
                        lines.append('### Reserved Ranges')
                        lines.append('')
                        lines.append('| Range Name | IPs | Description |')
                        lines.append('|------------|-----|-------------|')
                        for res in alloc['reserved']:
                            ip_display = (
                                res['ips'][0] if len(res['ips']) == 1
                                else f'{res["ips"][0]} – {res["ips"][-1]}'
                            )
                            lines.append(
                                f'| {res.get("range_name") or "Single"} '
                                f'| `{ip_display}` ({len(res["ips"])}) '
                                f'| {res.get("description") or "—"} |'
                            )
                        lines.append('')

        return '\n'.join(lines)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _sync_discovered_networks(self, docker_nets) -> None:
        """
        Persist any Docker networks we haven't seen before into the DB as
        unmanaged entries so the UI can reference them.
        """
        known_ids = {n.network_id for n in self.db.query(Network).all()}

        for net in docker_nets:
            if net.id in known_ids:
                continue
            # Skip internal Docker networks
            if net.name in ('bridge', 'host', 'none'):
                continue

            ipam = net.attrs.get('IPAM', {}).get('Config', [])
            subnet = ipam[0].get('Subnet') if ipam else None
            gateway = ipam[0].get('Gateway') if ipam else None

            db_net = Network(
                network_id=net.id,
                name=net.name,
                driver=net.attrs.get('Driver', 'bridge'),
                subnet=subnet,
                gateway=gateway,
                managed=False,
            )
            self.db.add(db_net)

        try:
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            logger.warning(f"Network sync commit failed (likely duplicate): {e}")
