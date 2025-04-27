# Contributing to VAST

Thank you for your interest in contributing to the Vulnerable Agricultural Sensor Testbed (VAST)! This document provides guidelines and instructions for contributing to this security-focused educational project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Security Considerations](#security-considerations)
- [Getting Started](#getting-started)
- [Development Environment](#development-environment)
- [Contribution Workflow](#contribution-workflow)
- [Pull Request Guidelines](#pull-request-guidelines)
- [Coding Standards](#coding-standards)
- [Documentation Guidelines](#documentation-guidelines)
- [Testing Requirements](#testing-requirements)
- [Special Considerations](#special-considerations)

## Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment for everyone. We expect all contributors to:

- Use welcoming and inclusive language
- Respect differing viewpoints and experiences
- Accept constructive criticism gracefully
- Focus on what is best for the community and project
- Show empathy towards other community members

## Security Considerations

VAST is a **deliberately vulnerable framework** for educational purposes. When contributing:

1. **Balance Security and Education**: Vulnerabilities should be realistic, educational, and well-documented but not unnecessarily dangerous.

2. **Document All Vulnerabilities**: Any intentional vulnerabilities must be thoroughly documented in both code comments and supplementary documentation.

3. **Consider Attack Surface**: When adding new components, consider how they might unintentionally expand the attack surface beyond the educational purpose.

4. **Responsible Implementation**: Implement vulnerabilities in a way that enables learning but avoids unnecessary harm if misused.

5. **Never Add Backdoors**: Do not introduce undocumented vulnerabilities or backdoors.

## Getting Started

To contribute to VAST:

1. Fork the repository
2. Clone your fork locally
3. Set up the development environment
4. Make your changes
5. Test your changes
6. Submit a pull request

## Development Environment

### Prerequisites

- Docker and Docker Compose
- Python 3.8 or higher
- Git

### Setup

```bash
# Clone your fork
git clone https://github.com/YOUR-USERNAME/vast.git
cd vast

# Add the original repository as upstream
git remote add upstream https://github.com/EmilPasca/vast.git

# Install development dependencies
pip install -r requirements-dev.txt

# Build and start the containers
docker-compose -f main.docker-compose.yaml up -d
```

## Contribution Workflow

1. **Create a Branch**: Create a branch with a descriptive name related to your contribution
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make Changes**: Make your changes in small, logical commits with clear messages

3. **Stay Updated**: Regularly pull changes from upstream
   ```bash
   git pull upstream main
   ```

4. **Test Your Changes**: Ensure all tests pass and add new tests for new functionality

5. **Document Your Changes**: Update documentation to reflect your changes

## Pull Request Guidelines

When submitting a pull request:

1. **Describe Your Changes**: Provide a clear description of what your PR accomplishes
2. **Reference Issues**: Reference any related issues using GitHub's #issue_number syntax
3. **Explain Security Implications**: For changes to vulnerabilities, explain the educational purpose
4. **Include Documentation**: Update relevant documentation in supplementary-materials/
5. **Ensure CI Passes**: All automated checks should pass

## Coding Standards

- Follow PEP 8 for Python code
- Use meaningful variable and function names
- Comment complex logic or security-related code
- Add docstrings to all functions and classes
- Keep functions focused on a single responsibility
- For Docker files, follow Docker's best practices

## Documentation Guidelines

- Update relevant supplementary materials when changing functionality
- Document all deliberate vulnerabilities thoroughly
- Include examples of how to interact with new features
- Add comments explaining security weaknesses in code
- Update any affected diagrams or architecture documentation

## Testing Requirements

- Add tests for new features
- Ensure existing tests continue to pass
- Include security tests for new components
- Test in both default and custom configurations
- Verify Docker containers start correctly

## Special Considerations

### Adding New Vulnerabilities

When adding new vulnerabilities:

1. **Educational Value**: The vulnerability should have clear educational value for agricultural IoT security
2. **Documentation**: Create detailed documentation in the supplementary-materials directory
3. **Isolation**: Ensure the vulnerability doesn't compromise the host system unintentionally
4. **Realistic Scenario**: The vulnerability should represent a realistic scenario in agricultural IoT
5. **Controllable**: Users should be able to enable/disable the vulnerability

### Adding New Sensors

When adding new sensor types:

1. **Agricultural Relevance**: New sensors should be relevant to agricultural applications
2. **Consistent APIs**: Follow the established API patterns
3. **Fault Simulation**: Implement all four fault types (stuck, drift, spike, dropout)
4. **Monitoring Integration**: Ensure Prometheus/Grafana integration

### Modifying Existing Documentation

When updating documentation:

1. **Consistency**: Maintain consistent style with existing documentation
2. **Cross-References**: Update cross-references if changing document structure
3. **Paper Alignment**: Ensure documentation remains aligned with the published paper
4. **Code Examples**: Verify any code examples actually work

## Acknowledgments

Contributors will be acknowledged in the project README. If your contribution is substantial, you may also be acknowledged in related academic publications.

---

Thank you for contributing to VAST and helping improve agricultural IoT security education and research!