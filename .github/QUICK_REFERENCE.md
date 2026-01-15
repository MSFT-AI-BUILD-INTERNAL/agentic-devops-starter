# Quick Reference - PR Review Automation

## For PR Authors

### Before Submitting a PR

Run the automated review locally:
```bash
python .github/scripts/pr_reviewer.py
```

### Required for All PRs

1. **spec.md** (Required) - Create in `specs/<feature-id>/spec.md`
2. **Tests** (If applicable) - Add to `app/tests/test_*.py`
3. **Clean Code** - Pass `ruff check app/src/`
4. **Documentation** - Update `app/README.md` and add docstrings

### Review Response Flow

1. Submit PR → Automated review runs
2. Review comment posted with ✅ or ⚠️ status
3. If ⚠️, address issues and push updates
4. Automated review re-runs on new commits
5. When ✅, request human reviewer

## For Reviewers

### What Gets Checked

The automated review validates:

- ✅ SpecKit artifacts exist (spec.md required)
- ✅ Tests present and passing (if applicable)
- ✅ Ruff linting passes
- ✅ Type hints present (mypy warnings only)
- ✅ Documentation updated
- ✅ Constitution requirements met

### Review Outcomes

**✅ APPROVED** - All required checks passed, ready for human review

**⚠️ CHANGES REQUESTED** - Issues found, author needs to address:
- ❌ = Must fix (blocking)
- ⚠️ = Should fix (recommended)
- ℹ️ = Informational only

### Human Review Focus

After automated checks pass, review for:

1. **Business Logic** - Does it solve the right problem?
2. **Architecture** - Does it fit the system design?
3. **Security** - Are there security implications?
4. **Performance** - Are there performance concerns?
5. **Maintainability** - Is it clear and maintainable?

## Common Issues

### "No spec.md found"
```bash
# Create spec.md in specs directory
mkdir -p specs/002-my-feature
cat > specs/002-my-feature/spec.md << EOF
# Feature Specification: My Feature

## Overview
[Description of the feature]

## User Stories
[User stories with acceptance criteria]
EOF
```

### "Ruff linting found issues"
```bash
# Auto-fix linting issues
cd app
ruff check src/ --fix
```

### "Tests failed"
```bash
# Run tests locally to debug
cd app
pytest tests/ -v
```

### "README.md minimal"
```bash
# Expand README with usage examples
cd app
# Edit README.md to add:
# - Feature description
# - Usage examples
# - Configuration options
```

## Workflow Files

- **Workflow**: `.github/workflows/pr-review.yml` - GitHub Actions workflow
- **Script**: `.github/scripts/pr_reviewer.py` - Python review script
- **Guidelines**: `.github/PR_REVIEW_GUIDELINES.md` - Full documentation
- **Constitution**: `.specify/memory/constitution.md` - Project standards

## Manual Commands

```bash
# Run full review locally
python .github/scripts/pr_reviewer.py

# Check code quality only
cd app
ruff check src/
mypy src/

# Run tests only
cd app
pytest tests/ -v

# Check for SpecKit artifacts
find specs -name "spec.md"
find specs -name "plan.md"
find specs -name "tasks.md"
```

## Tips

- ✨ Create spec.md before starting to code
- ✨ Run local review before pushing
- ✨ Add tests as you implement features
- ✨ Write clear commit messages
- ✨ Keep PRs focused and small
- ✨ Respond to review comments promptly
- ✨ Use draft PRs for work in progress

## Getting Help

1. Read [PR_REVIEW_GUIDELINES.md](.github/PR_REVIEW_GUIDELINES.md)
2. Check [constitution.md](.specify/memory/constitution.md)
3. Look at merged PRs for examples
4. Ask questions in PR comments
5. Contact DevOps team

---

**Quick Links:**
- [Full Guidelines](.github/PR_REVIEW_GUIDELINES.md)
- [Project Constitution](.specify/memory/constitution.md)
- [Example Feature Spec](specs/001-agent-framework/spec.md)
