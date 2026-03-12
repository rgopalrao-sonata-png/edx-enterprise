# Action Items for ENT-11238 Developer

## Pre-Merge Checklist

### 🔴 CRITICAL - Must Fix Before Merge

- [ ] **Fix Import Error** in `enterprise/api_client/braze_client.py` line 9
  ```python
  # Change:
  from braze.constants import BrazeAPIEndpoints
  # To:
  from enterprise.constants import BrazeAPIEndpoints
  ```
  **Why:** Current import will cause runtime failure

- [ ] **Remove Feature Branch** from `.github/workflows/ci.yml` line 5
  ```yaml
  # Change:
  branches: [master,ENT-11238-invite-delete-admin]
  # To:
  branches: [master]
  ```
  **Why:** CI should not trigger on temporary feature branches

- [ ] **Fix CHANGELOG** formatting in `CHANGELOG.rst` line 26
  ```
  # Change:
  * feat:Implement soft delete for admins
  # To:
  * feat: Implement soft delete for admins
  ```
  **Why:** Consistency with changelog format

### 🟡 RECOMMENDED - Should Fix

- [ ] **Clarify Email Duplication** in `enterprise/api_client/braze_client.py` lines 93-96
  - Either remove duplicate email setting
  - OR add comment explaining why both are needed
  - See FIXES_ENT-11238.md for options

- [ ] **Verify Version Number** consistency
  - `enterprise/__init__.py` shows: `6.6.6`
  - `CHANGELOG.rst` shows: `6.6.7` as latest
  - Confirm which is correct and update accordingly

### ✅ Testing Checklist

Before requesting final review:

- [ ] Run quality checks: `tox -e quality`
- [ ] Run test suite: `tox -e django52-celery53`
- [ ] Verify all tests pass
- [ ] Test in staging environment:
  - [ ] Send test admin invite email
  - [ ] Verify Braze integration works
  - [ ] Test pending admin deletion
  - [ ] Test active admin deletion
  - [ ] Verify soft delete behavior
  - [ ] Test permission checks

### 📋 Documentation Checklist

- [ ] Review CODE_REVIEW_ENT-11238.md
- [ ] Apply fixes from FIXES_ENT-11238.md
- [ ] Update PR description if needed
- [ ] Add any additional comments/documentation

### 🚀 Ready to Merge

Once all items above are complete:

- [ ] All critical issues fixed
- [ ] All tests passing
- [ ] Manual testing complete
- [ ] Staging environment verified
- [ ] Documentation updated
- [ ] PR approved by reviewers
- [ ] Merge conflicts resolved (if any)

---

## Quick Commands

```bash
# Switch to the recommended branch
git checkout ENT-11238-invite-delete-admin

# Apply the critical fixes
# (see FIXES_ENT-11238.md for exact changes)

# Run quality checks
tox -e quality

# Run tests
tox -e django52-celery53

# Check for any issues
git status
git diff

# Commit fixes
git add .
git commit -m "fix: address code review feedback from ENT-11238 review"
git push origin ENT-11238-invite-delete-admin
```

---

## Questions?

Refer to:
- **REVIEW_SUMMARY.md** - High-level overview
- **CODE_REVIEW_ENT-11238.md** - Detailed analysis
- **FIXES_ENT-11238.md** - Specific code changes needed

---

## Notes

- **Recommended Branch:** ENT-11238-invite-delete-admin (more recent)
- **Security Status:** ✅ No vulnerabilities found (CodeQL passed)
- **Test Coverage:** ✅ Excellent
- **Overall Status:** Ready to merge after critical fixes
