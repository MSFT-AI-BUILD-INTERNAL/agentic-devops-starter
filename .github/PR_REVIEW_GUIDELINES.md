# PR Review Guidelines - SpecKit Driven Development

This document outlines the automated PR review process for the agentic-devops-starter project. All PRs are automatically reviewed for compliance with SpecKit-driven development practices and project constitution requirements.

## Overview

The automated PR review system checks PRs for:

1. **SpecKit-Driven Development** - Proper planning and documentation artifacts
2. **Test Coverage** - Adequate testing for code changes (when applicable)
3. **Code Quality** - Adherence to coding standards and type safety
4. **Documentation** - Proper documentation and inline comments
5. **Constitution Compliance** - Alignment with project constitution requirements

## Review Criteria

### 1. SpecKit-Driven Development ✅

All feature PRs should follow the SpecKit workflow:

#### Required
- **spec.md** - Feature specification document in `specs/<feature-id>/`
  - Must include: Overview, User Stories, Technical Requirements, Success Metrics
  - Should clearly define what is being built and why

#### Recommended
- **plan.md** - Implementation plan in `specs/<feature-id>/`
  - Should include: Technical architecture, component design, testing strategy
  - Provides detailed implementation roadmap

- **tasks.md** - Task breakdown in `specs/<feature-id>/`
  - Should include: Checklist of all tasks, dependencies, completion status
  - Enables tracking and parallel work coordination

**Example Structure:**
```
specs/
└── 001-feature-name/
    ├── spec.md      ✅ Required
    ├── plan.md      📋 Recommended
    └── tasks.md     📋 Recommended
```

### 2. Test Coverage 🧪

#### When Tests are Required
- New features with business logic
- Bug fixes that prevent regressions
- Changes to existing functionality
- API endpoint additions or modifications

#### When Tests May Not Be Required
- Documentation-only changes
- Configuration updates
- Simple refactoring without logic changes

#### Test Requirements
- Tests should be in `app/tests/` directory
- Follow naming convention: `test_*.py`
- Use pytest framework
- Aim for meaningful coverage of critical paths

**Example:**
```python
# app/tests/test_feature.py
def test_feature_basic_functionality():
    """Test that the feature works as expected"""
    # Arrange
    feature = MyFeature()
    
    # Act
    result = feature.process()
    
    # Assert
    assert result is not None
```

### 3. Code Quality 🔍

All code changes must pass quality checks:

#### Ruff Linting (Required)
- Code must pass `ruff check` with no violations
- Configuration in `app/pyproject.toml`
- Run locally: `ruff check app/src/`

#### Type Checking (Recommended)
- Code should pass `mypy` type checking
- All functions should have type hints
- Configuration in `app/pyproject.toml`
- Run locally: `mypy app/src/`

#### Code Style
- Follow PEP 8 style guidelines
- Use meaningful variable names
- Keep functions focused and small
- Add docstrings to public functions

### 4. Documentation 📚

#### README Updates
- Update `app/README.md` for new features
- Include usage examples
- Document configuration options
- Explain architectural decisions

#### Inline Documentation
- Add docstrings to classes and public methods
- Use clear, descriptive comments for complex logic
- Document parameters and return values
- Include type hints

**Example:**
```python
def process_message(message: str, context: dict[str, Any]) -> str:
    """
    Process a user message and generate a response.
    
    Args:
        message: The user's input message
        context: Additional context for message processing
        
    Returns:
        The generated response string
        
    Raises:
        ValueError: If message is empty or invalid
    """
    # Implementation
```

### 5. Constitution Compliance 📜

All code must comply with the project constitution:

#### Required Elements
- **Python ≥3.12** - Specified in `app/pyproject.toml`
- **Type Safety** - Use Pydantic models and type hints
- **Agent Framework** - Use microsoft-agent-framework for agents
- **Structured Logging** - Include correlation IDs for traceability
- **Project Structure** - Application code in `app/` directory

#### Validation
The automated review checks for:
- Python version requirement in pyproject.toml
- Presence of Pydantic in dependencies
- microsoft-agent-framework dependency
- Logging utilities for observability
- Proper directory structure

## Running Reviews Locally

### Automated Script
```bash
# Run the full PR review locally
python .github/scripts/pr_reviewer.py
```

### Individual Checks
```bash
# Check code quality
cd app
ruff check src/
mypy src/

# Run tests
pytest tests/ -v

# Check structure
ls specs/*/spec.md
```

## GitHub Actions Workflow

The PR review runs automatically on:
- Pull request opened
- Pull request synchronized (new commits)
- Pull request reopened
- Pull request marked ready for review

### Workflow Steps
1. **Checkout code** - Get the PR branch
2. **Setup environment** - Install Python 3.12 and dependencies
3. **Check SpecKit artifacts** - Verify spec.md, plan.md, tasks.md exist
4. **Run tests** - Execute test suite and verify results
5. **Code quality** - Run ruff and mypy checks
6. **Documentation** - Check for README and docstrings
7. **Constitution** - Validate constitutional requirements
8. **Generate report** - Post review summary as PR comment

### Review Results

The automated review will post a comment on your PR with results:

#### ✅ Approved
All required checks passed. The PR is ready for human review.

#### ⚠️ Changes Requested
Some checks failed. Address the issues marked with ❌ or ⚠️ and push updates.

#### Review Comment Format
```markdown
## 🤖 Automated PR Review - SpecKit Compliance

**Overall Status:** ✅ APPROVED

### 📋 SpecKit-Driven Development
✅ spec.md found - Feature specification exists
✅ plan.md found - Implementation plan exists
✅ tasks.md found - Task breakdown exists

### 🧪 Test Coverage
✅ Tests found - 3 test files present
✅ Tests passed - All tests passing

### 🔍 Code Quality
✅ Ruff linting passed - No style violations
✅ Type checking passed - No type errors

### 📚 Documentation
✅ README.md present with 120 lines
✅ Good inline documentation - 45 docstrings found

### 📜 Constitution Compliance
✅ Application code in app/ directory
✅ Python >=3.12 requirement specified
✅ Pydantic used for type safety
✅ microsoft-agent-framework dependency present
```

## Best Practices

### For Feature Development
1. **Start with SpecKit** - Create spec.md before coding
2. **Plan thoroughly** - Document your approach in plan.md
3. **Break down work** - Create actionable tasks in tasks.md
4. **Test as you go** - Write tests alongside implementation
5. **Document continuously** - Keep README and docstrings updated

### For Bug Fixes
1. **Reference issue** - Link to the issue being fixed
2. **Add regression test** - Prevent the bug from recurring
3. **Document root cause** - Explain what was wrong in PR description
4. **Update docs** - If behavior changes, update documentation

### For Refactoring
1. **Explain why** - Justify the refactoring in PR description
2. **Maintain tests** - Ensure existing tests still pass
3. **No behavior changes** - Keep functionality identical
4. **Document patterns** - Update docs if patterns change

## Common Issues and Solutions

### ❌ "No spec.md found"
**Solution:** Create a feature specification in `specs/<feature-id>/spec.md`

### ❌ "Ruff linting found issues"
**Solution:** Run `ruff check --fix app/src/` to auto-fix issues

### ⚠️ "Some tests failed"
**Solution:** Run tests locally with `pytest tests/ -v` and fix failures

### ⚠️ "README.md minimal"
**Solution:** Expand README with usage examples and explanations

### ⚠️ "Python version requirement unclear"
**Solution:** Add `requires-python = ">=3.12"` to pyproject.toml

## Requesting Human Review

After addressing automated review feedback:

1. **Push updates** - Commit and push your changes
2. **Wait for re-review** - The automated review will run again
3. **Request reviewers** - Assign human reviewers when checks pass
4. **Address feedback** - Respond to human reviewer comments
5. **Merge** - Merge when approved by both automation and humans

## Workflow Configuration

The automated review workflow is defined in:
- **Workflow:** `.github/workflows/pr-review.yml`
- **Script:** `.github/scripts/pr_reviewer.py`
- **Documentation:** This file

To customize the review process, modify these files and submit a PR.

## Getting Help

If you have questions about the PR review process:

1. **Read this guide** - Most answers are here
2. **Check examples** - Look at merged PRs for reference
3. **Ask in PR** - Comment on your PR with questions
4. **Review constitution** - See `.specify/memory/constitution.md`

## Review Checklist

Use this checklist when preparing a PR:

- [ ] Created spec.md for the feature (if applicable)
- [ ] Created plan.md with implementation details (recommended)
- [ ] Created tasks.md with task breakdown (recommended)
- [ ] Added or updated tests for changes
- [ ] All tests passing locally
- [ ] Ruff linting passes (`ruff check app/src/`)
- [ ] Type checking passes (`mypy app/src/`)
- [ ] Updated app/README.md with relevant changes
- [ ] Added docstrings to new functions/classes
- [ ] Verified Python ≥3.12 requirement in pyproject.toml
- [ ] Used Pydantic for data validation
- [ ] Added structured logging with correlation IDs
- [ ] All code in app/ directory
- [ ] PR description explains what and why
- [ ] Linked to related issues

---

**Version:** 1.0.0  
**Last Updated:** 2026-01-13  
**Maintained By:** DevOps Team
