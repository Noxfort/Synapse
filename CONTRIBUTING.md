# Contributing to SYNAPSE_CORE

Thank you for your interest in contributing to the SYNAPSE Intelligent Perception Platform! We are building the future of urban mobility, and community contributions are essential to scale our AI-driven approach to traffic management.

## Getting Started

1. **Fork and Clone**: Fork the repository and clone it to your local machine.
2. **Setup Virtual Environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```
3. **Install Pre-commit Hooks** (if applicable) to ensure your code complies with our formatting standards before committing.

## Development Workflow

1. Create a feature branch (`git checkout -b feature/your-feature-name`).
2. Make your changes.
3. Run local tests:
   ```bash
   pytest tests/
   ```
4. Commit your changes using descriptive commit messages.
5. Push to your branch and open a Pull Request (PR) against the `main` branch.

## Code Style

- We strictly adhere to **PEP 8** for Python code.
- Enforce SOLID principles. Subsystems must be decoupled.
- All new neural architectures must inherit from `src.agents.base_agent.BaseAgent`.

## Reporting Bugs

Please use the provided GitHub Issue Templates. For security-related issues, DO NOT open a public issue. Refer to `SECURITY.md`.
