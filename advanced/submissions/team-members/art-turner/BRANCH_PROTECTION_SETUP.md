# 🛡️ GitHub Branch Protection Setup Guide

This guide provides step-by-step instructions for setting up branch protection rules to ensure code quality and prevent accidental changes to production code.

## 🎯 Overview

Branch protection rules enforce:
- **Code review requirements** before merging
- **CI/CD checks** must pass before merging
- **Conversation resolution** before merging
- **Prevention of force pushes** and deletions
- **Administrator compliance** with the same rules

## 📋 Prerequisites

Before setting up branch protection, ensure:

1. ✅ **Repository permissions**: You must be a repository admin or owner
2. ✅ **CI/CD setup**: GitHub Actions workflow is configured (`.github/workflows/ci.yml`)
3. ✅ **Branch exists**: The `develop` branch has been created and pushed
4. ✅ **Initial commit**: At least one commit exists on each branch to be protected

## 🔧 Setting Up Branch Protection

### Option 1: GitHub Web Interface (Recommended)

#### Step 1: Navigate to Branch Protection Settings

1. Go to your repository on GitHub
2. Click **Settings** tab
3. Click **Branches** in the left sidebar
4. Click **Add rule** button

#### Step 2: Configure Main Branch Protection

**Branch name pattern**: `main`

**Protect matching branches** - Enable all options:

✅ **Restrict pushes that create files larger than 100MB**

✅ **Require a pull request before merging**
- Required approving reviews: `1`
- ✅ Dismiss stale pull request approvals when new commits are pushed
- ✅ Require review from code owners (if CODEOWNERS file exists)

✅ **Require status checks to pass before merging**
- ✅ Require branches to be up to date before merging
- **Required status checks** (add these individually):
  - `test (3.10.12)`
  - `security`
  - `docker`

✅ **Require conversation resolution before merging**

✅ **Require signed commits** (recommended)

✅ **Require linear history** (optional, enforces rebase/squash)

✅ **Restrict pushes that create files larger than 100MB**

**Do not allow bypassing the above settings**
- ✅ Include administrators

#### Step 3: Configure Develop Branch Protection

**Branch name pattern**: `develop`

**Protect matching branches** - Enable these options:

✅ **Require a pull request before merging**
- Required approving reviews: `1`
- ✅ Dismiss stale pull request approvals when new commits are pushed

✅ **Require status checks to pass before merging**
- ✅ Require branches to be up to date before merging
- **Required status checks**:
  - `test (3.10.12)`
  - `security`

✅ **Require conversation resolution before merging**

✅ **Restrict pushes that create files larger than 100MB**

**Do not allow bypassing the above settings**
- ✅ Include administrators

### Option 2: GitHub CLI

If you prefer command-line setup:

```bash
# Install GitHub CLI if not already installed
# https://cli.github.com/

# Login to GitHub
gh auth login

# Set up main branch protection
gh api repos/:owner/:repo/branches/main/protection \
  --method PUT \
  --field required_status_checks='{"strict":true,"contexts":["test (3.10.12)","security","docker"]}' \
  --field enforce_admins=true \
  --field required_pull_request_reviews='{"required_approving_review_count":1,"dismiss_stale_reviews":true}' \
  --field restrictions=null \
  --field required_conversation_resolution=true

# Set up develop branch protection
gh api repos/:owner/:repo/branches/develop/protection \
  --method PUT \
  --field required_status_checks='{"strict":true,"contexts":["test (3.10.12)","security"]}' \
  --field enforce_admins=true \
  --field required_pull_request_reviews='{"required_approving_review_count":1,"dismiss_stale_reviews":true}' \
  --field restrictions=null \
  --field required_conversation_resolution=true
```

### Option 3: Repository Settings via API

For automation or bulk setup:

```bash
# Main branch protection
curl -X PUT \
  -H "Authorization: token YOUR_GITHUB_TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  https://api.github.com/repos/OWNER/REPO/branches/main/protection \
  -d '{
    "required_status_checks": {
      "strict": true,
      "contexts": ["test (3.10.12)", "security", "docker"]
    },
    "enforce_admins": true,
    "required_pull_request_reviews": {
      "required_approving_review_count": 1,
      "dismiss_stale_reviews": true
    },
    "restrictions": null,
    "required_conversation_resolution": true
  }'
```

## 🔍 Verification

After setting up protection rules, verify they work:

### Test 1: Direct Push Prevention

```bash
# This should be blocked
git checkout main
echo "test" >> README.md
git commit -am "test: direct push to main"
git push origin main
# Expected: Error - branch is protected
```

### Test 2: PR Requirements

```bash
# This should work
git checkout develop
git checkout -b test/branch-protection
echo "test" >> README.md
git commit -am "test: branch protection verification"
git push origin test/branch-protection

# Open PR via GitHub web interface
# Verify that:
# - CI checks run automatically
# - Merge button is disabled until checks pass
# - Review is required before merge
```

### Test 3: Status Check Requirements

1. Create a PR with failing tests
2. Verify merge is blocked until tests pass
3. Fix tests and verify merge becomes available

## 📚 Status Checks Reference

### Required for Main Branch

| Check Name | Description | Source |
|------------|-------------|---------|
| `test (3.10.12)` | Python tests with coverage | GitHub Actions CI |
| `security` | Security scanning (bandit, safety) | GitHub Actions CI |
| `docker` | Docker build and health tests | GitHub Actions CI |

### Required for Develop Branch

| Check Name | Description | Source |
|------------|-------------|---------|
| `test (3.10.12)` | Python tests with coverage | GitHub Actions CI |
| `security` | Security scanning | GitHub Actions CI |

## 🚨 Troubleshooting

### Issue: Status checks not appearing

**Cause**: GitHub needs to see the checks run at least once

**Solution**:
```bash
# Push a commit to trigger CI
git checkout develop
git commit --allow-empty -m "trigger: initial CI run"
git push origin develop
```

### Issue: "Required status check is not available"

**Cause**: Check name doesn't match workflow job name

**Solution**: Check the exact names in your CI workflow:
```yaml
# In .github/workflows/ci.yml
jobs:
  test:  # This creates check "test (3.10.12)"
  security:  # This creates check "security"
  docker:  # This creates check "docker"
```

### Issue: Administrators can still push directly

**Cause**: "Include administrators" is not enabled

**Solution**:
1. Go to branch protection settings
2. Check "Do not allow bypassing the above settings"
3. Check "Include administrators"

### Issue: Old commits bypass protection

**Cause**: Protection was added after commits were made

**Solution**: This is expected behavior. Protection only applies to new commits.

## 📖 Best Practices

### 1. Gradual Rollout

Start with develop branch protection, then add main branch protection once team is comfortable.

### 2. Team Training

Ensure all team members understand:
- How to create feature branches
- PR creation and review process
- How to fix failing CI checks

### 3. Documentation

Keep this documentation updated as you add new status checks or change requirements.

### 4. Regular Review

Periodically review protection settings to ensure they still meet your team's needs.

## 🎯 Next Steps

After setting up branch protection:

1. ✅ **Train team members** on the new workflow
2. ✅ **Update documentation** with any project-specific requirements
3. ✅ **Test the process** with a small feature branch
4. ✅ **Monitor** the first few PRs to ensure smooth adoption
5. ✅ **Refine rules** based on team feedback

## 📞 Getting Help

If you encounter issues:

1. **Check GitHub Status**: https://www.githubstatus.com/
2. **Review GitHub Docs**: https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/defining-the-mergeability-of-pull-requests/about-protected-branches
3. **GitHub Support**: For repository-specific issues
4. **Team Discussion**: Use GitHub Discussions for team questions

---

## ✅ Checklist

Use this checklist to ensure proper setup:

### Repository Setup
- [ ] Repository is created and accessible
- [ ] CI/CD workflow (`.github/workflows/ci.yml`) is committed
- [ ] `main` and `develop` branches exist
- [ ] At least one commit exists on each branch

### Main Branch Protection
- [ ] Branch protection rule created for `main`
- [ ] Require pull request reviews (1 reviewer minimum)
- [ ] Dismiss stale reviews enabled
- [ ] Required status checks: `test (3.10.12)`, `security`, `docker`
- [ ] Require branches to be up to date
- [ ] Require conversation resolution
- [ ] Include administrators in restrictions
- [ ] Restrict force pushes

### Develop Branch Protection
- [ ] Branch protection rule created for `develop`
- [ ] Require pull request reviews (1 reviewer minimum)
- [ ] Required status checks: `test (3.10.12)`, `security`
- [ ] Require conversation resolution
- [ ] Include administrators in restrictions

### Verification
- [ ] Direct push to main blocked
- [ ] Direct push to develop blocked
- [ ] PR creation works from feature branches
- [ ] CI checks run automatically on PRs
- [ ] Merge blocked until checks pass and review approved
- [ ] Team members can successfully follow the workflow

**🎉 Congratulations! Your repository now has robust protection against accidental changes and ensures code quality through automated checks and peer review.**