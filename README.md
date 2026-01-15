# agentic-devops-starter
MVP for Agentic DevOps Starter (Compass)

## Overview

This repository provides a starter template for building agentic DevOps workflows with AI-powered automation. The project follows SpecKit-driven development methodology and includes automated PR review processes to ensure code quality and compliance.

## Features

- **SpecKit-Driven Development**: Structured approach to feature planning and implementation
- **Automated PR Reviews**: GitHub Actions workflow for automated code review
- **Constitution-Based Governance**: Enforced coding standards and architectural principles
- **Agent Framework Integration**: Built-in support for microsoft-agent-framework
- **Type-Safe Python**: Python 3.12+ with Pydantic validation

## Project Structure

```
.
├── .github/
│   ├── workflows/
│   │   ├── ci.yml              # Continuous integration
│   │   ├── deploy.yml          # Deployment workflow
│   │   └── pr-review.yml       # Automated PR review
│   ├── scripts/
│   │   └── pr_reviewer.py      # PR review automation script
│   └── PR_REVIEW_GUIDELINES.md # PR review documentation
├── .specify/
│   ├── memory/
│   │   └── constitution.md     # Project constitution
│   └── templates/              # SpecKit templates
├── app/
│   ├── src/                    # Application source code
│   ├── tests/                  # Test suite
│   ├── main.py                 # Main entry point
│   └── README.md               # Application documentation
├── specs/                      # Feature specifications
│   └── 001-agent-framework/    # Example spec
└── README.md                   # This file
```

## Getting Started

### Prerequisites

- Python ≥3.12
- uv package manager
- Git

### Installation

1. Clone the repository:
```bash
git clone https://github.com/MSFT-AI-BUILD-INTERNAL/agentic-devops-starter.git
cd agentic-devops-starter
```

2. Set up the Python environment:
```bash
cd app
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -r requirements.txt
```

3. Run the example application:
```bash
python main.py
```

### Running Tests

```bash
cd app
pytest tests/ -v
```

### Code Quality Checks

```bash
# Linting
ruff check src/

# Type checking
mypy src/
```

## Development Workflow

This project follows SpecKit-driven development. For detailed guidelines, see:

- **[PR Review Guidelines](.github/PR_REVIEW_GUIDELINES.md)** - Automated PR review process
- **[Constitution](.specify/memory/constitution.md)** - Project governance and standards
- **[Agent Framework Example](app/README.md)** - Application documentation

### Creating a New Feature

1. **Create Specification**: Define your feature in `specs/<feature-id>/spec.md`
2. **Plan Implementation**: Document your approach in `specs/<feature-id>/plan.md`
3. **Break Down Tasks**: Create actionable tasks in `specs/<feature-id>/tasks.md`
4. **Implement**: Write code in `app/src/`
5. **Add Tests**: Create tests in `app/tests/`
6. **Document**: Update README and add docstrings
7. **Submit PR**: Create a pull request for review

### PR Review Process

All pull requests are automatically reviewed for:

1. **SpecKit Compliance** - Presence of spec.md, plan.md, tasks.md
2. **Test Coverage** - Adequate testing for code changes
3. **Code Quality** - Ruff linting and mypy type checking
4. **Documentation** - README updates and inline documentation
5. **Constitution Compliance** - Adherence to project standards

The automated review will post a comment on your PR with detailed feedback. Address any issues marked with ❌ or ⚠️ before requesting human review.

## Project Constitution

The project follows a strict constitution that mandates:

- **Python-First Backend**: Python ≥3.12 for all backend services
- **Agent-Centric Architecture**: microsoft-agent-framework as core orchestration
- **Type Safety**: Type hints and Pydantic validation throughout
- **Response Quality**: LLM response validation and guardrails
- **Observability**: Structured logging with correlation IDs
- **Project Structure**: Application code in `app/`, infrastructure in `infra/`

See [.specify/memory/constitution.md](.specify/memory/constitution.md) for complete details.

## Contributing

We welcome contributions! Please follow these steps:

1. Fork the repository
2. Create a feature branch
3. Follow SpecKit-driven development process
4. Ensure all tests pass
5. Submit a pull request
6. Address automated review feedback
7. Wait for human reviewer approval

See [PR Review Guidelines](.github/PR_REVIEW_GUIDELINES.md) for detailed contribution requirements.

## Automated Reviews

This repository includes automated PR review workflows that check:

- ✅ SpecKit artifacts (spec.md, plan.md, tasks.md)
- ✅ Test coverage and test results
- ✅ Code quality (ruff, mypy)
- ✅ Documentation completeness
- ✅ Constitution compliance

The automated review provides immediate feedback on PRs and helps maintain code quality standards.

## License

See [LICENSE](LICENSE) file for details.

## Support

For questions or issues:

1. Check the [PR Review Guidelines](.github/PR_REVIEW_GUIDELINES.md)
2. Review the [Constitution](.specify/memory/constitution.md)
3. Open an issue on GitHub
4. Contact the DevOps team

---

**Version**: 1.0.0  
**Last Updated**: 2026-01-13
