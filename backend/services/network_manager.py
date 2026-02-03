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
    """
    try:
        prefix = ipaddress.ip_network(subnet, strict=False).prefixlen
        hosts = _prefix_to_host_count(prefix)
        return hosts > max(container_count * 4, 10)
    except (ValueError, TypeError):
        return False


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
            net_id = net.id
            db_net = db_networks.get(net_id)

            # Pull IPAM config from Docker attrs
            ipam_config = net.attrs.get('IPAM', {}).get('Config', [])
            subnet = ipam_config[0].get('Subnet') if ipam_config else None
            gateway = ipam_config[0].get('Gateway') if ipam_config else None

            # Count containers attached to this network
            container_count = len(net.attrs.get('Containers', {}))

            is_default = net.name in ('bridge', 'host', 'none')

            entry: Dict[str, Any] = {
                'network_id': net_id,
                'name': net.name,
                'driver': net.attrs.get('Driver', 'unknown'),
                'subnet': subnet,
                'gateway': gateway,
                'container_count': container_count,
                'managed': db_net is not None,
                'purpose': db_net.purpose if db_net else None,
                'oversized': (
                    False if is_default
                    else _is_oversized(subnet, container_count) if subnet
                    else False
                ),
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
        except Exception:
            return None

        ipam_config = net.attrs.get('IPAM', {}).get('Config', [])
        subnet = ipam_config[0].get('Subnet') if ipam_config else None
        gateway = ipam_config[0].get('Gateway') if ipam_config else None

        db_net = self.db.query(Network).filter_by(network_id=network_id).first()

        containers = []
        for cid, cinfo in net.attrs.get('Containers', {}).items():
            containers.append({
                'container_id': cid,
                'name': cinfo.get('Name', '').lstrip('/'),
                'ipv4_address': cinfo.get('IPv4Address', ''),
                'ipv6_address': cinfo.get('IPv6Address', ''),
            })

        container_count = len(containers)

        is_default = net.name in ('bridge', 'host', 'none')

        return {
            'network_id': net.id,
            'name': net.name,
            'driver': net.attrs.get('Driver', 'unknown'),
            'subnet': subnet,
            'gateway': gateway,
            'ip_range': ipam_config[0].get('IPRange') if ipam_config else None,
            'container_count': container_count,
            'containers': containers,
            'managed': db_net is not None,
            'purpose': db_net.purpose if db_net else None,
            'oversized': (
                False if is_default
                else _is_oversized(subnet, container_count) if subnet
                else False
            ),
            'options': net.attrs.get('Options', {}),
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

        # Safety: refuse to delete default Docker networks or DockerMate's own
        if net.name in ('bridge', 'host', 'none'):
            return {'success': False, 'error': f"Cannot delete default Docker network '{net.name}'"}
        if 'dockermate' in net.name.lower():
            return {'success': False, 'error': f"Cannot delete DockerMate's internal network '{net.name}'"}

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
