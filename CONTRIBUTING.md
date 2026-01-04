# Contributing to GhostStorm

Thank you for your interest in contributing to GhostStorm!

## Development Setup

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager
- Node.js 18+ (for web dashboard)
- Docker (optional, for containerized development)

### Quick Start

```bash
# Clone the repository
git clone https://github.com/devbyteai/ghoststorm.git
cd ghoststorm

# Install dependencies
uv sync --all-extras --dev

# Install pre-commit hooks
uv run pre-commit install

# Run tests
make test

# Start development server
make dev
```

## Code Style

We use strict code formatting and linting:

- **Ruff** for linting and formatting
- **MyPy** for type checking
- **Pre-commit** hooks for automated checks

```bash
# Format code
make format

# Run linter
make lint

# Run type checker
make typecheck
```

## Testing

```bash
# Run all tests
make test

# Run with coverage
make test-cov

# Run specific test file
uv run pytest tests/unit/test_example.py -v
```

### Test Structure

```
tests/
├── unit/           # Unit tests
├── integration/    # Integration tests
├── e2e/           # End-to-end tests
└── conftest.py    # Shared fixtures
```

## Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Ensure tests pass (`make test`)
5. Ensure linting passes (`make lint`)
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

### PR Guidelines

- Follow the PR template
- Keep changes focused and atomic
- Include tests for new functionality
- Update documentation as needed
- Ensure CI passes

## Commit Messages

Use conventional commits:

- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation
- `style:` Formatting
- `refactor:` Code restructuring
- `test:` Tests
- `chore:` Maintenance

## Architecture

See [docs/architecture.md](docs/architecture.md) for system design.

## Questions?

- Open a [Discussion](https://github.com/devbyteai/ghoststorm/discussions)
- Check existing [Issues](https://github.com/devbyteai/ghoststorm/issues)

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
