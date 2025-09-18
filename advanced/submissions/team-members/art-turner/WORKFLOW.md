# 🔄 Development Workflow & CI/CD

This document outlines the complete development workflow, branching strategy, and CI/CD pipeline for the Powercast API project.

## 📋 Table of Contents

- [Branching Strategy](#-branching-strategy)
- [Development Workflow](#-development-workflow)
- [CI/CD Pipeline](#️-cicd-pipeline)
- [Branch Protection Rules](#-branch-protection-rules)
- [Release Process](#-release-process)
- [Hotfix Process](#-hotfix-process)

## 🌳 Branching Strategy

We use a **Git Flow**-inspired branching model with the following branches:

### Main Branches

- **`main`** 🏆
  - **Purpose**: Production-ready code
  - **Protection**: ✅ Protected, requires PR + CI checks
  - **Deployment**: 🚀 Auto-deploys to production
  - **Merges from**: `develop` (via PR), `hotfix/*` (via PR)

- **`develop`** 🔧
  - **Purpose**: Integration branch for features
  - **Protection**: ✅ Protected, requires PR + CI checks
  - **Deployment**: 🧪 Auto-deploys to staging
  - **Merges from**: `feature/*`, `bugfix/*`

### Supporting Branches

- **`feature/*`** ✨
  - **Purpose**: New feature development
  - **Lifetime**: Temporary
  - **Naming**: `feature/add-metrics-endpoint`, `feature/user-authentication`
  - **Merges to**: `develop`

- **`bugfix/*`** 🐛
  - **Purpose**: Bug fixes for develop
  - **Lifetime**: Temporary
  - **Naming**: `bugfix/fix-validation-error`, `bugfix/memory-leak`
  - **Merges to**: `develop`

- **`hotfix/*`** 🚨
  - **Purpose**: Emergency production fixes
  - **Lifetime**: Temporary
  - **Naming**: `hotfix/security-patch`, `hotfix/critical-bug`
  - **Merges to**: `main` AND `develop`

## 🚀 Development Workflow

### 1. Feature Development

```bash
# 1. Start from develop
git checkout develop
git pull origin develop

# 2. Create feature branch
git checkout -b feature/your-feature-name

# 3. Develop your feature
# ... make changes, commit regularly ...

# 4. Keep up to date with develop
git fetch origin
git rebase origin/develop

# 5. Push and create PR
git push origin feature/your-feature-name
# Open PR: feature/your-feature-name → develop
```

### 2. Code Review Process

1. **Self-Review** ✅
   - Run tests locally: `pytest tests/`
   - Check code style: `black --check app_core tests/`
   - Review your own changes

2. **Create Pull Request** 📝
   - Use the PR template
   - Fill out all sections
   - Add appropriate labels
   - Request reviewers

3. **CI Checks** 🤖
   - Tests must pass
   - Security scans must pass
   - Docker build must succeed
   - Code coverage maintained

4. **Code Review** 👥
   - At least 1 approval required
   - Address all feedback
   - Resolve conversations

5. **Merge** 🎉
   - Use "Squash and merge" for features
   - Use "Merge commit" for releases

### 3. Testing Workflow

```bash
# Run full test suite
pytest tests/ --cov=app_core --cov-report=term-missing

# Run specific test categories
pytest tests/test_health.py -v
pytest tests/test_predict_shape.py -v

# Test Docker build locally
docker build -t powercast-test .
docker run -p 8000:8000 -e PORT=8000 powercast-test

# Manual API testing
curl http://localhost:8000/health
curl http://localhost:8000/ready
curl http://localhost:8000/dummy-data
```

## 🤖 CI/CD Pipeline

Our CI/CD pipeline runs on **GitHub Actions** and includes multiple stages:

### Pipeline Stages

#### 1. **Test Stage** 🧪
- **Triggers**: Push to any branch, PR to main/develop
- **Actions**:
  - Install dependencies
  - Run linting (flake8)
  - Run tests with coverage (pytest)
  - Upload coverage to Codecov

#### 2. **Security Stage** 🔒
- **Triggers**: Push to any branch, PR to main/develop
- **Actions**:
  - Security scanning (bandit)
  - Dependency vulnerability check (safety)
  - Generate security reports

#### 3. **Docker Stage** 🐳
- **Triggers**: Push to main or develop
- **Actions**:
  - Build Docker image
  - Test container health endpoints
  - Push to Docker Hub (main only)

#### 4. **Deploy Stage** 🚀
- **Staging**: Automatic on develop branch
- **Production**: Automatic on main branch
- **Actions**:
  - Deploy to cloud provider (Railway/Render)
  - Run smoke tests
  - Notify team

### Environment Variables for CI

Required secrets in GitHub repository settings:

```bash
# Docker Hub (for image publishing)
DOCKER_USERNAME=your-docker-username
DOCKER_PASSWORD=your-docker-token

# Deployment (optional)
RAILWAY_TOKEN=your-railway-token
RENDER_API_KEY=your-render-key
```

### Pipeline Configuration

```yaml
# .github/workflows/ci.yml
name: CI/CD Pipeline
on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  test:        # Run tests and linting
  security:    # Security scanning
  docker:      # Build and test Docker image
  deploy-staging:    # Deploy to staging (develop)
  deploy-production: # Deploy to production (main)
```

## 🛡️ Branch Protection Rules

### Main Branch Protection

**Required for `main` branch:**

- ✅ Require pull request reviews before merging
  - Required approving reviews: 1
  - Dismiss stale reviews when new commits are pushed
  - Require review from code owners

- ✅ Require status checks to pass before merging
  - Require branches to be up to date before merging
  - Required status checks:
    - `test (3.10.12)`
    - `security`
    - `docker`

- ✅ Require conversation resolution before merging
- ✅ Require signed commits (recommended)
- ✅ Restrict pushes that create files larger than 100MB
- ✅ Restrict force pushes
- ✅ Restrict deletions

### Develop Branch Protection

**Required for `develop` branch:**

- ✅ Require pull request reviews before merging
  - Required approving reviews: 1

- ✅ Require status checks to pass before merging
  - Required status checks:
    - `test (3.10.12)`
    - `security`

- ✅ Require conversation resolution before merging
- ✅ Restrict force pushes

### Setting Up Protection Rules

```bash
# Using GitHub CLI
gh api repos/:owner/:repo/branches/main/protection \
  --method PUT \
  --field required_status_checks='{"strict":true,"contexts":["test (3.10.12)","security","docker"]}' \
  --field enforce_admins=true \
  --field required_pull_request_reviews='{"required_approving_review_count":1,"dismiss_stale_reviews":true}' \
  --field restrictions=null
```

## 📦 Release Process

### Regular Release (develop → main)

1. **Prepare Release** 📋
   ```bash
   # Create release branch from develop
   git checkout develop
   git pull origin develop
   git checkout -b release/v1.2.0

   # Update version numbers, changelog, etc.
   # ... make final adjustments ...

   git commit -m "chore: prepare release v1.2.0"
   git push origin release/v1.2.0
   ```

2. **Create Release PR** 📝
   - Open PR: `release/v1.2.0` → `main`
   - Fill out release notes
   - Tag reviewers
   - Ensure all CI checks pass

3. **Deploy & Tag** 🏷️
   ```bash
   # After merge to main
   git checkout main
   git pull origin main
   git tag -a v1.2.0 -m "Release version 1.2.0"
   git push origin v1.2.0
   ```

4. **Merge Back** 🔄
   ```bash
   # Merge main back to develop
   git checkout develop
   git merge main
   git push origin develop
   ```

### Version Numbering

We use **Semantic Versioning** (SemVer):

- **Major** (X.0.0): Breaking changes
- **Minor** (1.X.0): New features, backward compatible
- **Patch** (1.1.X): Bug fixes, backward compatible

Examples:
- `v1.0.0` → `v1.1.0`: Added new API endpoint
- `v1.1.0` → `v1.1.1`: Fixed prediction bug
- `v1.1.1` → `v2.0.0`: Changed API response format

## 🚨 Hotfix Process

For **critical production issues** that can't wait for the next release:

### 1. Create Hotfix Branch
```bash
# Start from main (production)
git checkout main
git pull origin main
git checkout -b hotfix/fix-critical-security-issue
```

### 2. Implement Fix
```bash
# Make minimal changes to fix the issue
# ... implement fix ...
git commit -m "fix: resolve critical security vulnerability"
```

### 3. Test Thoroughly
```bash
# Run full test suite
pytest tests/

# Test Docker build
docker build -t powercast-hotfix .
docker run -p 8000:8000 powercast-hotfix

# Manual testing of the fix
```

### 4. Deploy via PR
```bash
# Push hotfix branch
git push origin hotfix/fix-critical-security-issue

# Create PR to main
# - Mark as hotfix
# - Explain urgency
# - Get expedited review
```

### 5. Merge and Deploy
```bash
# After merge to main, tag immediately
git checkout main
git pull origin main
git tag -a v1.1.2 -m "Hotfix: security vulnerability"
git push origin v1.1.2

# Merge back to develop
git checkout develop
git merge main
git push origin develop
```

## 📊 Monitoring & Metrics

### CI/CD Metrics to Track

- **Build Success Rate**: % of successful builds
- **Test Coverage**: Code coverage percentage
- **Deployment Frequency**: How often we deploy
- **Lead Time**: Time from commit to production
- **Mean Time to Recovery**: Time to fix production issues

### Alerts & Notifications

- **Slack/Teams**: Build failures, deployment status
- **Email**: Security vulnerabilities, dependency updates
- **GitHub**: PR reviews, CI status updates

## 🔍 Troubleshooting

### Common CI Issues

**Tests failing locally but passing in CI:**
- Check Python version differences
- Verify environment variable setup
- Check file path differences (Windows vs. Linux)

**Docker build failing:**
- Check .dockerignore excludes
- Verify all required files are copied
- Check base image availability

**Security scan failures:**
- Update vulnerable dependencies
- Review bandit findings
- Check safety database updates

### Getting Help

1. **Check CI logs** in GitHub Actions
2. **Review failing tests** locally
3. **Ask in team chat** for CI/CD issues
4. **Create issue** for persistent problems

---

## 🎯 Quick Reference

### Essential Commands

```bash
# Start new feature
git checkout develop && git pull && git checkout -b feature/my-feature

# Run tests
pytest tests/ --cov=app_core

# Format code
black app_core tests/

# Security check
bandit -r app_core

# Build Docker
docker build -t powercast-api .

# Test deployment
uvicorn app_core.main:app --port 8000
```

### Key Files

- **`.github/workflows/ci.yml`**: CI/CD pipeline
- **`.github/pull_request_template.md`**: PR template
- **`CONTRIBUTING.md`**: Development guidelines
- **`requirements-dev.txt`**: Development dependencies
- **`pytest.ini`**: Test configuration

This workflow ensures **reliable, secure, and fast delivery** of Powercast API updates! 🚀