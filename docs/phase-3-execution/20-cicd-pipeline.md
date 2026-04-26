# Phase 3.20 – CI/CD Pipeline Design

> **Status**: Deferred to v2. Version 1 is tested and deployed manually by the solo developer. This document plans the automated CI/CD pipeline for v2.

## 1. Overview

Version 1 of GDPR AI runs on the developer's laptop and is "deployed" by running `git pull`. There is no automated testing or deployment.

Version 2 introduces a hosted service, at which point automated CI/CD becomes valuable for quality assurance and faster iteration.

---

## 2. Goals

### 2.1 Primary Goals

* Catch regressions before they reach `main`
* Automatic deployment on merges to `main`
* Fast feedback for pull request authors (under 3 minutes typical)
* Minimal cost (free tier where possible)

### 2.2 Non-Goals for v2

* Blue-green deployments with zero downtime
* Canary releases
* Automated performance benchmarking
* Multi-environment pipelines (staging, pre-prod, prod)

---

## 3. Platform: GitHub Actions

GitHub Actions is chosen because:

* Repo is on GitHub; zero additional infrastructure
* Free tier sufficient for a small project (2000 minutes/month)
* Strong ecosystem of reusable actions
* Simple YAML configuration

Alternatives briefly considered:

* **CircleCI**: more features, more complex, separate billing
* **GitLab CI**: requires moving the repo
* **Jenkins**: too heavy for a small project

---

## 4. Pipeline Overview

```
┌────────────────────────────────────────────────────────────┐
│                      Pull Request                          │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  1. Lint (Ruff)                                            │
│  2. Type check (mypy)                                      │
│  3. Unit tests (pytest)                                    │
│  4. Integration tests (pytest with mocked LLM)             │
│  5. Coverage report                                        │
│  6. Secret scanning (gitleaks)                             │
│  7. Dependency vulnerability scan (pip-audit)              │
│                                                            │
└────────────────────────────────────────────────────────────┘
                           │
                           ▼
               ┌─────────────────────┐
               │  Merge to main      │
               └──────────┬──────────┘
                          │
                          ▼
┌────────────────────────────────────────────────────────────┐
│                      Main Branch                           │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  1. All PR checks re-run                                   │
│  2. Build Docker image                                     │
│  3. Push to GitHub Container Registry                      │
│  4. Deploy to Hetzner VPS via SSH                          │
│  5. Health check post-deploy                               │
│  6. Notify (email on failure)                              │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

---

## 5. PR Pipeline Specification

### 5.1 Trigger

On any push to a branch with an open PR targeting `develop` or `main`.

### 5.2 Jobs

#### 5.2.1 Setup

* Checkout code
* Set up Python 3.11 via uv
* Install dependencies with cached uv cache
* Total setup time target: under 30 seconds

#### 5.2.2 Lint

```yaml
- name: Ruff lint
  run: uv run ruff check .

- name: Ruff format
  run: uv run ruff format --check .
```

Failure: block merge.

#### 5.2.3 Type Check

```yaml
- name: mypy
  run: uv run mypy src/gdpr_ai
```

Failure: block merge.

#### 5.2.4 Unit and Integration Tests

```yaml
- name: Run tests
  run: uv run pytest tests/ --cov=src/gdpr_ai --cov-report=xml
```

Failure: block merge. Uses mocked LLM responses from `tests/fixtures/`.

#### 5.2.5 Coverage Report

```yaml
- name: Upload coverage
  uses: codecov/codecov-action@v3
```

Informational only; does not block merge.

#### 5.2.6 Secret Scanning

```yaml
- name: Gitleaks
  uses: gitleaks/gitleaks-action@v2
```

Scans the diff for API keys, passwords, tokens. Failure: block merge.

#### 5.2.7 Dependency Vulnerability Scan

```yaml
- name: pip-audit
  run: uv run pip-audit
```

Informational; produces a summary comment on the PR. Critical CVEs block merge.

### 5.3 Target Duration

Full PR pipeline: under 3 minutes on cache hit, under 5 minutes on cache miss.

---

## 6. Main Pipeline Specification

### 6.1 Trigger

On push to `main` (i.e., after PR merge).

### 6.2 Jobs

#### 6.2.1 All PR Checks

Re-run all PR jobs for belt-and-braces verification.

#### 6.2.2 Build Docker Image

```yaml
- name: Build Docker image
  run: docker build -t ghcr.io/prathamesh0009/gdpr-ai:${{ github.sha }} .

- name: Tag as latest
  run: docker tag ghcr.io/prathamesh0009/gdpr-ai:${{ github.sha }} ghcr.io/prathamesh0009/gdpr-ai:latest
```

#### 6.2.3 Push to Registry

```yaml
- name: Log in to GHCR
  run: echo ${{ secrets.GHCR_TOKEN }} | docker login ghcr.io -u prathamesh0009 --password-stdin

- name: Push image
  run: |
    docker push ghcr.io/prathamesh0009/gdpr-ai:${{ github.sha }}
    docker push ghcr.io/prathamesh0009/gdpr-ai:latest
```

#### 6.2.4 Deploy to VPS

```yaml
- name: Deploy via SSH
  uses: appleboy/ssh-action@master
  with:
    host: ${{ secrets.VPS_HOST }}
    username: ${{ secrets.VPS_USER }}
    key: ${{ secrets.VPS_SSH_KEY }}
    script: |
      cd /opt/gdpr-ai
      docker compose pull
      docker compose up -d
```

#### 6.2.5 Post-Deploy Health Check

```yaml
- name: Wait for health
  run: |
    for i in {1..30}; do
      if curl -sf https://gdpr-ai.example.com/v1/health; then
        exit 0
      fi
      sleep 2
    done
    exit 1
```

Failure: deployment considered broken; alert sent.

#### 6.2.6 Notification

On failure: email to the maintainer.

On success: no notification (reduces noise).

---

## 7. Secret Management

### 7.1 GitHub Secrets Used

| Secret | Purpose |
|--------|---------|
| `GHCR_TOKEN` | Push Docker images to registry |
| `VPS_HOST` | SSH target hostname |
| `VPS_USER` | SSH username |
| `VPS_SSH_KEY` | SSH private key |
| `ANTHROPIC_API_KEY` | For evaluation runs (not for normal CI) |

### 7.2 Never in Secrets

* Production `.env` contents (those live on the VPS)
* Database credentials (none in v2 architecture)

---

## 8. Dependency Caching

### 8.1 uv Cache

```yaml
- name: Cache uv
  uses: actions/cache@v4
  with:
    path: ~/.cache/uv
    key: ${{ runner.os }}-uv-${{ hashFiles('uv.lock') }}
    restore-keys: |
      ${{ runner.os }}-uv-
```

### 8.2 Docker Layer Cache

```yaml
- uses: docker/setup-buildx-action@v3
- name: Build with cache
  uses: docker/build-push-action@v5
  with:
    cache-from: type=gha
    cache-to: type=gha,mode=max
```

---

## 9. Rollback Strategy

### 9.1 Mechanism

If a deployment breaks production:

```bash
ssh vps
cd /opt/gdpr-ai
docker compose pull gdpr-ai:<previous-sha>
docker compose up -d
```

The previous image remains in the registry for at least 30 days.

### 9.2 Automated Rollback (v3)

For v2, rollback is manual. For v3, consider automated rollback when the post-deploy health check fails.

---

## 10. Evaluation Runs in CI

### 10.1 Scheduled Evaluation

Nightly cron workflow runs the full gold-set evaluation against the deployed service.

```yaml
on:
  schedule:
    - cron: '0 3 * * *'  # 03:00 UTC daily
```

### 10.2 Regression Detection

If F1 drops more than 5% below the last baseline, the workflow fails and emails the maintainer.

### 10.3 Cost

One gold-set run: approximately 0.50 EUR. Daily: 15 EUR/month. Acceptable for a maintained project.

---

## 11. Branch Protection Rules

### 11.1 `main` Branch

* Direct pushes disabled
* Require PR review (self-review acceptable for solo project, but ensures deliberate merge)
* Require all checks to pass
* Require up-to-date branch before merge

### 11.2 `develop` Branch

* Direct pushes disabled
* Require all checks to pass
* No review required (solo workflow)

---

## 12. Summary

The v2 CI/CD pipeline uses GitHub Actions for PR validation and main-branch deployment. Fast, free, and simple. Dependency caching keeps PR feedback under 3 minutes. Gitleaks prevents secrets from sneaking in. Deployment is a straightforward SSH-based Docker Compose update to a single Hetzner VPS.

More sophisticated delivery patterns (blue-green, canary, multi-region) are deferred until the project's scale justifies the complexity.

---

## v2 Note

Remains deferred. Local development relies on **manual** test runs (`pytest`, evaluation harness). Full **CI/CD** automation is **v3+** scope, alongside any hosted deployment.