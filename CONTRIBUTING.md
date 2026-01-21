# Contributing to DockerMate

First off, thank you for considering contributing to DockerMate! It's people like you that make DockerMate a great tool for the home lab community.

## 🎯 Our Philosophy

DockerMate is **100% focused on home labs**. We intentionally avoid enterprise features that add complexity most users don't need. Please keep this in mind when proposing features.

### What We're Building
- ✅ Simple, powerful tools for home lab enthusiasts
- ✅ Educational features (CLI display, tooltips)
- ✅ Hardware-aware optimizations
- ✅ Single-user focused features
- ✅ Offline-first design

### What We're NOT Building
- ❌ Enterprise authentication (LDAP, SAML, OAuth)
- ❌ Multi-user management
- ❌ Role-based access control
- ❌ Audit compliance features
- ❌ Cloud dependencies
- ❌ Multi-tenancy

**Want these features?** Feel free to fork! See [Enterprise Fork Guidelines](#enterprise-fork-guidelines).

---

## 🚀 Quick Start

### 1. Fork & Clone

```bash
# Fork on GitHub, then:
git clone https://github.com/YOUR_USERNAME/DockerMate.git
cd DockerMate
```

### 2. Set Up Development Environment

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install
```

### 3. Create Feature Branch

```bash
git checkout -b feature/amazing-feature
```

---

## 📝 Code Style

### Python Style Guide

We follow [PEP 8](https://pep8.org/) with these additions:

```python
# Use Black formatter (required)
black backend/ frontend/ tests/

# Use type hints (required)
def calculate_size(max_containers: int, ips_per_container: int = 1) -> dict:
    """
    Calculate recommended network size
    
    Args:
        max_containers: Maximum containers hardware supports
        ips_per_container: IPs needed per container (default: 1)
    
    Returns:
        Dictionary with recommended CIDR and calculation details
        
    Examples:
        >>> calculate_size(15, 1)
        {'recommended_cidr': '/27', 'ips_needed': 15}
    """
    pass

# Comment liberally (Design Principle #3)
# All code must be understandable by someone learning
# Comments should explain WHY, not WHAT

# Error handling everywhere (Design Principle #4)
try:
    result = risky_operation()
except SpecificError as e:
    logger.error(f"Failed to do X: {e}")
    # Provide path to recovery
    return fallback_result()
```

### JavaScript Style Guide

```javascript
// Use Alpine.js for reactivity
// Use vanilla JS for utilities
// Comment all non-obvious code

// Good example:
function calculateIPRange(cidr) {
    // Parse CIDR notation (e.g., "192.168.1.0/24")
    const [network, prefix] = cidr.split('/');
    
    // Calculate usable IPs (total - network - broadcast)
    const totalIPs = Math.pow(2, 32 - parseInt(prefix));
    const usableIPs = totalIPs - 2;
    
    return {
        network: network,
        usable: usableIPs,
        // Verification: Can test with `ipcalc` command
        verification: `ipcalc ${cidr}`
    };
}
```

### Testing Requirements

```python
# Every function needs tests
# Include verification commands in test docstrings

def test_network_size_calculation():
    """
    Test hardware-aware network sizing
    
    Verification:
        $ python -m pytest tests/unit/test_network_manager.py::test_network_size_calculation -v
    """
    result = NetworkSizeCalculator.calculate_size(
        max_containers=15,
        ips_per_container=1,
        buffer_percent=20
    )
    
    # Test recommended size
    assert result['recommended_cidr'] == '/27'
    
    # Test calculation accuracy
    assert result['ips_needed'] == 15
    assert result['ips_with_buffer'] == 18
    
    # Test for oversized prevention
    assert result['safe_options']
    assert result['unsafe_options']
```

---

## 🔍 Development Workflow

### 1. Write Code

Follow our design principles:
1. **KISS** - Keep it simple
2. **Hardware-Aware** - Respect resource limits
3. **Educational** - Add CLI equivalents
4. **Progressive Disclosure** - Hide complexity
5. **Safety First** - Prevent destructive actions

### 2. Write Tests

```bash
# Unit tests
python -m pytest tests/unit/ -v

# Integration tests
bash tests/integration/test_container_lifecycle.sh

# Coverage report
pytest --cov=backend tests/
```

### 3. Run Linters

```bash
# Format code
black backend/ frontend/ tests/

# Type checking
mypy backend/

# Linting
flake8 backend/
pylint backend/

# Pre-commit hooks (runs automatically on commit)
pre-commit run --all-files
```

### 4. Update Documentation

```python
# Update docstrings
def new_feature(param: str) -> dict:
    """
    Brief description
    
    Detailed explanation of what this does and why.
    
    Args:
        param: Description of parameter
    
    Returns:
        Description of return value
        
    Examples:
        >>> new_feature("test")
        {'result': 'success'}
        
    Verification:
        $ python -c "from module import new_feature; print(new_feature('test'))"
    """
```

Update relevant markdown files:
- `README.md` - User-facing changes
- `DESIGN.md` - Architecture changes
- `docs/` - Feature documentation

### 5. Commit Changes

```bash
# Use conventional commits
git commit -m "feat: add network topology visualization"
git commit -m "fix: resolve container name validation bug"
git commit -m "docs: update installation instructions"
git commit -m "test: add integration tests for updates"

# Commit message format:
# <type>: <description>
#
# Types:
# feat: New feature
# fix: Bug fix
# docs: Documentation only
# style: Code style changes
# refactor: Code restructuring
# test: Adding tests
# chore: Maintenance tasks
```

### 6. Push & Create PR

```bash
git push origin feature/amazing-feature
```

Then create a Pull Request on GitHub with:
- Clear description of changes
- Reference to related issues
- Screenshots (if UI changes)
- Testing instructions

---

## 🧪 Testing Guidelines

### Unit Tests

```python
# tests/unit/test_example.py

import pytest
from backend.managers.network_manager import NetworkSizeCalculator

class TestNetworkSizing:
    """Test network size calculations"""
    
    def test_raspberry_pi_sizing(self):
        """
        Test that Raspberry Pi gets appropriate network sizes
        
        Raspberry Pi: 15 container limit
        Expected: /27 (30 IPs) for 1 IP per container
        """
        result = NetworkSizeCalculator.calculate_size(
            max_containers=15,
            ips_per_container=1
        )
        assert result['recommended_cidr'] == '/27'
    
    def test_oversized_detection(self):
        """Test oversized network warning"""
        result = NetworkSizeCalculator.validate_subnet_choice(
            cidr='/16',
            max_containers=15,
            profile={'profile_name': 'RASPBERRY_PI'}
        )
        assert result['requires_confirmation'] == True
        assert result['performance_score'] <= 3
```

### Integration Tests

```bash
#!/bin/bash
# tests/integration/test_network_creation.sh

# Test network creation workflow

echo "Testing network creation..."

# 1. Create network
response=$(curl -s -X POST http://localhost:5000/api/networks \
  -H "Content-Type: application/json" \
  -d '{
    "name": "test-network",
    "subnet": "172.30.0.0/26",
    "gateway": "172.30.0.1"
  }')

network_id=$(echo $response | jq -r '.id')

# 2. Verify Docker network created
docker network inspect test-network >/dev/null 2>&1 || exit 1

# 3. Create container on network
docker run -d --name test-container --network test-network nginx:latest

# 4. Verify IP assigned
container_ip=$(docker inspect test-container --format '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}')
[[ "$container_ip" =~ ^172\.30\.0\. ]] || exit 1

# 5. Cleanup
docker rm -f test-container
docker network rm test-network

echo "✅ Network creation test passed"
```

---

## 🎯 Feature Guidelines

### Before Starting

1. **Check existing issues** - Is someone else working on this?
2. **Open a discussion** - Propose the feature first
3. **Wait for feedback** - Make sure it aligns with our goals
4. **Get approval** - Avoid wasted effort

### Good Feature Examples

✅ **Good**: "Add ability to export containers as systemd services"
- Aligns with home lab use case
- Useful for many users
- Reasonable complexity
- Educational component possible

✅ **Good**: "Add Raspberry Pi hardware detection"
- Hardware-aware (core principle)
- Solves real problem
- Clear implementation path

✅ **Good**: "Add container dependency visualization"
- Helps users understand their setup
- Educational
- Visual aid

### Bad Feature Examples

❌ **Bad**: "Add LDAP authentication"
- Enterprise feature
- Not home lab focused
- Adds complexity
- Fork material

❌ **Bad**: "Add multi-user management with RBAC"
- Enterprise feature
- Violates single-user principle
- Fork material

❌ **Bad**: "Add cloud sync to AWS S3"
- Requires cloud dependency
- Violates offline-first principle
- Most users don't need it

---

## 📋 Pull Request Process

### 1. Pre-PR Checklist

- [ ] Code follows style guide
- [ ] All tests pass
- [ ] New tests added for new features
- [ ] Documentation updated
- [ ] Comments added for complex code
- [ ] Commit messages follow convention
- [ ] No merge conflicts

### 2. PR Description Template

```markdown
## Description
Brief description of changes

## Related Issue
Fixes #123

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
How was this tested?
- [ ] Unit tests
- [ ] Integration tests
- [ ] Manual testing

## Screenshots (if applicable)

## Checklist
- [ ] Code follows style guide
- [ ] Self-review completed
- [ ] Comments added
- [ ] Documentation updated
- [ ] Tests pass
- [ ] No new warnings
```

### 3. Review Process

1. **Automated Checks**: CI/CD runs tests and linters
2. **Code Review**: Maintainers review code
3. **Feedback**: Address any comments
4. **Approval**: Get approval from maintainer
5. **Merge**: We'll merge when ready

---

## 🏆 Recognition

Contributors are recognized in:
- README.md contributors section
- Release notes
- About page in application
- Annual contributor spotlight

---

## 💬 Communication

### Discussion Channels

- **GitHub Discussions**: General questions and ideas
- **GitHub Issues**: Bug reports and feature requests
- **Pull Requests**: Code review and technical discussion

### Response Times

- **Bug reports**: Within 48 hours
- **Feature proposals**: Within 1 week
- **Pull requests**: Within 1 week
- **Security issues**: Within 24 hours

---

## 📜 Code of Conduct

### Our Pledge

We are committed to providing a welcoming and inspiring community for all.

### Our Standards

**Positive behavior:**
- Using welcoming language
- Being respectful of differing viewpoints
- Accepting constructive criticism
- Focusing on what's best for the community
- Showing empathy towards others

**Unacceptable behavior:**
- Trolling or insulting comments
- Public or private harassment
- Publishing others' private information
- Other unprofessional conduct

### Enforcement

Violations can be reported by opening an issue on [GitHub](https://github.com/BBultitude/DockerMate/issues) with the `[CODE OF CONDUCT]` prefix. All complaints will be reviewed and investigated.

---

## ❓ Questions?

- 💬 [GitHub Discussions](https://github.com/BBultitude/DockerMate/discussions)
- 🐛 [Issue Tracker](https://github.com/BBultitude/DockerMate/issues)
- 📖 [Design Document](https://github.com/BBultitude/DockerMate/blob/main/DESIGN.md)

---

**Thank you for contributing to DockerMate! 🐳**