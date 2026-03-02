# edx-enterprise PR Submission Guide

**Complete Checklist for Code Quality & CI/CD Success**

---

## Table of Contents

1. [Code Implementation Standards](#1-code-implementation-standards)
2. [Test Coverage Requirements](#2-test-coverage-requirements)
3. [Code Quality Checks](#3-code-quality-checks)
4. [Common Quality Issues](#4-common-quality-issues)
5. [Settings Configuration](#5-settings-configuration)
6. [Git Best Practices](#6-git-best-practices)
7. [Changelog & Versioning](#7-changelog--versioning)
8. [Pre-Push Validation](#8-pre-push-validation)
9. [CI/CD Pipeline](#9-cicd-pipeline)
10. [Common Gotchas](#10-common-gotchas)
11. [PR Submission Checklist](#11-pr-submission-checklist)
12. [Quick Command Reference](#12-quick-command-reference)

---

## 1. Code Implementation Standards

### ✅ Django/DRF Best Practices

- **Docstrings**: Add Google-style docstrings to all functions, classes, and methods
  ```python
  def invite_admins(self, request, **kwargs):
      """
      Invite new admins to an Enterprise Customer.
      
      Args:
          request: DRF request object
          **kwargs: Must contain 'enterprise_customer_uuid'
          
      Returns:
          Response: List of invite statuses
          
      Raises:
          ValidationError: If email format is invalid
      """
  ```

- **Constants**: Extract magic strings/numbers to `enterprise/constants.py`
  ```python
  # ❌ Bad
  if status == "invited":
  
  # ✅ Good
  class AdminInviteStatus:
      INVITED = "invited"
  
  if status == AdminInviteStatus.INVITED:
  ```

- **Transaction Safety**: Use `@transaction.atomic` for data mutations
  ```python
  from django.db import transaction
  
  @transaction.atomic
  def create_pending_invites(enterprise_customer, emails):
      # Database operations here
  ```

- **Query Optimization**: Prevent N+1 queries
  ```python
  # ❌ Bad - Causes N+1 queries
  for admin in admins:
      print(admin.user.email)
  
  # ✅ Good - Single query
  admins = EnterpriseCustomerAdmin.objects.select_related('user').all()
  ```

- **Error Handling**: Proper exception handling with logging
  ```python
  try:
      result = external_api_call()
  except BrazeClientError as exc:
      LOGGER.exception("Braze API error")
      raise
  ```

- **Settings Access**: Use `getattr()` for configuration
  ```python
  # ✅ Good
  api_key = getattr(settings, 'ENTERPRISE_BRAZE_API_KEY', None)
  
  # ❌ Bad - Hardcoded
  api_key = "1e7bc695-eab1-46cf-afcd-212c0c213ec5"
  ```

- **Permission Protection**: Add decorators to endpoints
  ```python
  @permission_required(
      ENTERPRISE_CUSTOMER_PROVISIONING_ADMIN_ACCESS_PERMISSION,
      fn=lambda request, *args, **kwargs: kwargs.get('enterprise_customer_uuid'),
  )
  @action(detail=False, methods=["post"])
  def invite_admins(self, request, **kwargs):
      # endpoint logic
  ```

---

## 2. Test Coverage Requirements

### ✅ Comprehensive Test Writing

**Target**: Minimum 90% code coverage

**Test Types Required**:

1. **Happy Path Scenarios**
   ```python
   def test_invite_admins_success(self):
       """Test successful admin invitation"""
       response = self.client.post(url, data={'emails': ['test@example.com']})
       assert response.status_code == 200
   ```

2. **Error Cases**
   ```python
   def test_invite_admins_invalid_email(self):
       """Test invitation with invalid email format"""
       response = self.client.post(url, data={'emails': ['invalid-email']})
       assert response.status_code == 400
   ```

3. **Edge Cases**
   ```python
   def test_invite_admins_empty_list(self):
       """Test invitation with empty email list"""
       response = self.client.post(url, data={'emails': []})
       assert response.status_code == 400
   ```

4. **Permission Checks**
   ```python
   def test_invite_admins_no_permission(self):
       """Test invitation without proper permissions"""
       self.user.is_staff = False
       response = self.client.post(url, data={'emails': ['test@example.com']})
       assert response.status_code == 403
   ```

### ✅ Mocking Best Practices

```python
# Mock external API calls
@mock.patch('enterprise.api_client.braze_client.BrazeAPIClient')
def test_send_invite_email(self, mock_braze):
    mock_braze.return_value.send_campaign_message.return_value = True
    # test logic

# Mock Celery task retry
@mock.patch.object(task, 'retry', side_effect=task.MaxRetriesExceededError())
def test_task_max_retries(self, mock_retry):
    # test logic
```

### ✅ Run Tests Locally

```bash
# Run specific test file
pytest tests/test_enterprise/api/test_views.py -v

# Run with coverage
pytest --cov=enterprise --cov-report=html

# Run specific test
pytest tests/test_enterprise/api/test_views.py::TestClass::test_method -v
```

---

## 3. Code Quality Checks

### ✅ Run Quality Checks Before Every Commit

```bash
# Run all quality checks
make quality

# This runs:
# - pylint (code quality)
# - pycodestyle (PEP8 compliance)
# - pydocstyle (docstring style)
# - isort (import ordering)
```

### ✅ Individual Quality Tools

```bash
# 1. Pylint - Find code quality issues
pylint enterprise/path/to/file.py

# 2. Pycodestyle - Check PEP8 compliance
pycodestyle enterprise/path/to/file.py

# 3. Isort - Check import ordering
isort --check-only enterprise/path/to/file.py

# Auto-fix import ordering
isort enterprise/path/to/file.py

# 4. Check specific issues
pylint --disable=all --enable=trailing-whitespace,unused-import file.py
```

---

## 4. Common Quality Issues

### ❌ Issues to Avoid

| Error Code | Issue | Fix |
|------------|-------|-----|
| **C0303** | Trailing whitespace | Remove spaces at end of lines |
| **W0611** | Unused import | Remove the import statement |
| **E302** | Missing 2 blank lines | Add blank lines before function/class |
| **E305** | Missing 2 blank lines after end of function/class | Add blank lines |
| **E301** | Missing 1 blank line | Add blank line |
| **E501** | Line too long (>120 chars) | Break into multiple lines |
| **E231** | Missing whitespace after ',' | Add space after comma |
| **W293** | Blank line contains whitespace | Remove whitespace from blank lines |

### ✅ Import Ordering (isort)

**Correct Order**: stdlib → third-party → django → local

```python
# ✅ Correct
import os
import sys

import requests
from celery import shared_task

from django.conf import settings
from django.db import models

from enterprise.models import EnterpriseCustomer
from enterprise.constants import AdminInviteStatus
```

**Import Formatting**:
- ≤2 items: Single line
- ≥3 items: Multi-line

```python
# ✅ Good - 2 items on one line
from enterprise.constants import STATUS_A, STATUS_B

# ✅ Good - 3+ items multi-line
from enterprise.models import (
    EnterpriseCustomer,
    EnterpriseCustomerAdmin,
    PendingEnterpriseCustomerAdmin,
)
```

### ✅ Common Fixes

```python
# Trailing whitespace - Remove spaces at line end
def my_function():  # ❌ (has trailing spaces)
def my_function():# ✅

# Unused imports - Remove completely
from django.test import override_settings  # ❌ if not used
# ✅ Delete the line

# Line too long
very_long_line = "This is a very long string that exceeds 120 characters and needs to be broken"  # ❌

# ✅ Break it up
very_long_line = (
    "This is a very long string that exceeds 120 characters "
    "and needs to be broken"
)
```

---

## 5. Settings Configuration

### ✅ Test Settings

Add to `enterprise/settings/test.py`:

```python
# Braze configuration for tests
ENTERPRISE_BRAZE_API_KEY = 'test-api-key'
EDX_BRAZE_API_SERVER = 'test-api-server'
BRAZE_ENTERPRISE_ADMIN_INVITE_EMAIL_CAMPAIGN_ID = 'test-campaign-id'
```

### ✅ Production Usage

In your code, always use `getattr()`:

```python
from django.conf import settings

# ✅ Good - Safe with defaults
api_key = getattr(settings, 'ENTERPRISE_BRAZE_API_KEY', None)
api_url = getattr(settings, 'EDX_BRAZE_API_SERVER', None)

# ❌ Bad - Hardcoded
api_key = "1e7bc695-eab1-46cf-afcd-212c0c213ec5"
```

### ⚠️ Security Warning

**NEVER commit:**
- Real API keys
- Passwords
- Secret tokens
- Production URLs

Use environment variables for production deployment.

---

## 6. Git Best Practices

### ✅ Check Modified Files

```bash
# See what you've changed
git status

# Compare with master
git diff --name-status master...HEAD

# See file changes in detail
git diff master...HEAD -- path/to/file.py
```

### ✅ Ensure Only Relevant Files

**Remove unrelated changes**:
- ❌ CI configuration files (unless specifically needed)
- ❌ Version bumps in `__init__.py`
- ❌ Unrelated test modifications
- ❌ Dependency updates in `requirements/*.txt`
- ❌ CHANGELOG.rst (unless releasing)

**Typical feature PR**: 10-20 files maximum

### ✅ Squash Commits

```bash
# 1. Reset to master (keeps changes staged)
git reset --soft master

# 2. Stage ONLY relevant files
git add enterprise/api/utils.py
git add enterprise/api/v1/serializers.py
# ... add other relevant files

# 3. Create ONE clean commit
git commit -m "feat: add enterprise admin invite endpoint with Braze integration"
```

### ✅ Commit Message Format

Follow **Conventional Commits**:

```bash
# Check recent commit messages for pattern
git log master --oneline -20

# Format: <type>: <description>
# Types: feat, fix, chore, build, docs, refactor, test

# Examples:
git commit -m "feat: add enterprise admin invite endpoint with Braze integration"
git commit -m "fix: resolve N+1 query issue in admin list endpoint"
git commit -m "chore: upgrade python dependencies"
git commit -m "docs: update API documentation for invite endpoint"
```

### ✅ Force Push Safely

```bash
# Use --force-with-lease (safer than --force)
git push --force-with-lease origin BRANCH-NAME

# This checks that no one else has pushed to the branch
```

---

## 7. Changelog & Versioning

### ✅ Changelog Updates

**Only update if you're releasing a version.**

```rst
# CHANGELOG.rst
Unreleased
----------
* feat: add enterprise admin invite endpoint with Braze integration

[6.6.5] - 2026-03-01
---------------------
* feat: add enterprise admin invite endpoint with Braze integration
```

### ❌ DO NOT Manually Bump Version

```python
# enterprise/__init__.py
# ❌ DO NOT manually change this
__version__ = "6.6.5"

# Let maintainers handle versioning
```

---

## 8. Pre-Push Validation

### ✅ Pre-Push Script

Save this as `pre_push_checks.sh`:

```bash
#!/bin/bash
set -e

echo "=========================================="
echo "🔍 Pre-Push Quality Checks"
echo "=========================================="

# 1. Quality checks
echo ""
echo "1️⃣  Running make quality..."
if make quality; then
    echo "✅ Quality checks passed"
else
    echo "❌ Quality checks failed"
    exit 1
fi

# 2. Run tests
echo ""
echo "2️⃣  Running tests..."
if pytest tests/test_enterprise/ -v --tb=short; then
    echo "✅ Tests passed"
else
    echo "❌ Tests failed"
    exit 1
fi

# 3. Check for debugging code
echo ""
echo "3️⃣  Checking for debugging code..."
if git diff master | grep -E "(import pdb|breakpoint\(\)|print\(|console\.log)"; then
    echo "⚠️  Warning: Found potential debugging code"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo "✅ No debugging code found"
fi

# 4. Check file count
echo ""
echo "4️⃣  Verifying file count..."
FILE_COUNT=$(git diff --name-only master...HEAD | wc -l)
echo "   Modified files: $FILE_COUNT"
if [ $FILE_COUNT -gt 30 ]; then
    echo "⚠️  Warning: Large number of files modified"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# 5. Verify single commit
echo ""
echo "5️⃣  Checking commits..."
COMMIT_COUNT=$(git log --oneline master..HEAD | wc -l)
echo "   Commits ahead of master: $COMMIT_COUNT"
if [ $COMMIT_COUNT -ne 1 ]; then
    echo "⚠️  Warning: Multiple commits detected"
    echo "   Consider squashing to 1 commit for cleaner history"
fi

echo ""
echo "=========================================="
echo "✅ All checks passed! Ready to push."
echo "=========================================="
```

**Usage**:
```bash
chmod +x pre_push_checks.sh
./pre_push_checks.sh
```

---

## 9. CI/CD Pipeline

### ✅ GitHub Actions Tests

Your code will be tested against:

| Environment | Description |
|-------------|-------------|
| **Python 3.11** | Python version compatibility |
| **Python 3.12** | Latest Python support |
| **Django 5.2** | Django framework version |
| **Celery 5.3** | Async task processing |

### ✅ Tox Environments

```bash
# Test locally like CI does
tox -e quality          # Code quality checks
tox -e docs             # Documentation build
tox -e django52-celery53  # Django + Celery tests
tox -e pii_check        # PII annotation check
```

### ✅ CI Workflow Stages

1. **quality**: pylint, pycodestyle, isort, pydocstyle
2. **docs**: Sphinx documentation build
3. **django52-celery53**: Unit tests + coverage
4. **pii_check**: Verify PII annotations

---

## 10. Common Gotchas

### ⚠️ Frequent Mistakes

| Issue | Wrong | Correct |
|-------|-------|---------|
| **Import Order** | Random ordering | stdlib → third-party → django → local |
| **Import Format** | Multi-line for 2 items | Single-line for ≤2, multi-line for ≥3 |
| **Blank Lines** | Inconsistent spacing | 2 lines between top-level functions/classes |
| **Logger Usage** | `LOGGER.error(exc_info=True)` | `LOGGER.exception()` |
| **Celery Retry** | Not mocking retry mechanism | Mock `task.request.retries`, `task.retry()` |
| **Settings** | Hardcoded values | `getattr(settings, 'NAME', default)` |
| **Permissions** | Getting UUID from `request.data` | Get from `kwargs['uuid']` |
| **Test Settings** | Different names than production | Must match exactly |

### ⚠️ Files NOT to Modify

Unless specifically needed for your feature:
- ❌ `.github/workflows/ci.yml`
- ❌ `enterprise/__init__.py` (version)
- ❌ `requirements/*.txt` (dependencies)
- ❌ `CHANGELOG.rst` (unless releasing)
- ❌ Unrelated test files
- ❌ `docker-compose.yml`
- ❌ `Makefile`

---

## 11. PR Submission Checklist

### ✅ Before Creating Pull Request

- [ ] All tests pass locally
- [ ] `make quality` passes with 0 errors
- [ ] Only relevant files committed (typically 10-20 files)
- [ ] Single clean commit with conventional commit message
- [ ] No hardcoded credentials/API keys/secrets
- [ ] No commented-out code (unless documented why)
- [ ] All functions have proper docstrings
- [ ] Permission decorators added to protected endpoints
- [ ] Database queries optimized (no N+1)
- [ ] Error handling with proper logging
- [ ] Branch is up-to-date with master
- [ ] Force-pushed to remote with `--force-with-lease`

### ✅ PR Description Template

```markdown
## Description
Brief description of what this PR does.

## Type of Change
- [ ] New feature
- [ ] Bug fix
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing completed

## Checklist
- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Tests pass locally
- [ ] Documentation updated (if needed)

## Related Issues
Closes #ISSUE_NUMBER
```

---

## 12. Quick Command Reference

### Daily Workflow

```bash
# Code quality
make quality                              # Run all quality checks
pytest tests/test_enterprise/ -v          # Run all tests
pytest --cov=enterprise --cov-report=html # Run with coverage

# Git operations
git status                                # See current changes
git diff --name-status master...HEAD      # Compare with master
git log --oneline -10                     # View recent commits

# Fix quality issues
isort .                                   # Fix import ordering
pycodestyle --show-source file.py         # See PEP8 errors with context
pylint file.py                            # See all pylint errors

# Clean commit workflow
git reset --soft master                   # Squash all commits
git add <files>                           # Stage relevant files only
git status                                # Verify staged files
git commit -m "feat: description"         # Create one clean commit
git push --force-with-lease origin BRANCH # Push safely

# Debug settings
python manage.py shell
>>> from django.conf import settings
>>> settings.YOUR_SETTING_NAME
>>> exit()

# Docker/LMS operations
docker-compose logs -f lms                # Follow LMS logs
docker-compose logs --tail=100 lms        # Last 100 log lines
docker-compose exec lms bash              # SSH into LMS container
docker-compose restart lms                # Restart LMS service
```

### Troubleshooting

```bash
# Quality check failed
make quality 2>&1 | tee quality_output.txt  # Save output to file
tail -50 quality_output.txt                  # View last 50 lines

# Tests failed
pytest tests/test_file.py -v --tb=short     # Short traceback
pytest tests/test_file.py -v --pdb          # Debug on failure

# Import errors
isort --check-only --diff .                 # See what would change
isort .                                     # Auto-fix all files

# Find specific issues
grep -r "import pdb" .                      # Find debugging code
grep -r "TODO" enterprise/                  # Find TODO comments
git diff master | grep "^+"                 # See all additions
```

---

## Document Version

**Version**: 1.0  
**Created**: March 2026  
**For**: edx-enterprise development team

---

## Additional Resources

- **edx-enterprise Repository**: https://github.com/openedx/edx-enterprise
- **Contributing Guide**: https://github.com/openedx/edx-enterprise/blob/master/CONTRIBUTING.rst
- **Open edX Documentation**: https://docs.openedx.org/
- **Django REST Framework**: https://www.django-rest-framework.org/
- **Conventional Commits**: https://www.conventionalcommits.org/

---

**Remember**: Clean code, comprehensive tests, and attention to detail make for successful PRs! 🚀
