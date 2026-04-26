# Phase 2.12 – Cloud Architecture and Deployment

> **Status**: Deferred to v2. Version 1 of GDPR AI runs entirely on the user's local machine. This document plans the cloud architecture for when GDPR AI is hosted and serves external users.

## 1. Overview

Version 1 requires no hosting. The CLI runs locally, ChromaDB is embedded, and the only network call is to the Anthropic API.

Version 2 introduces a hosted component — a FastAPI service exposing the `/v1/analyse` endpoint and a Next.js frontend. This document describes the planned cloud architecture, deployment model, and operational considerations.

---

## 2. Design Goals

### 2.1 Primary Goals

* EU data residency (legal requirement for a GDPR-focused tool serving EU users)
* Low monthly fixed cost (under 20 EUR / month for a small beta)
* Simple operational footprint (one container, one volume, one database)
* Room to scale to hundreds of queries per day without re-architecture

### 2.2 Non-Goals for v2

* Auto-scaling across multiple regions
* High availability with hot failover
* Kubernetes-level orchestration complexity

---

## 3. Hosting Options Considered

### 3.1 Hetzner Cloud (Recommended for v2)

**Pros**

* EU data centres (Falkenstein, Nuremberg, Helsinki)
* Lowest cost per resource unit in the market
* Simple UI and API
* Good fit for a solo-maintained service

**Cons**

* Less managed tooling than AWS / GCP
* Requires self-management of OS updates and basic security

**Monthly cost estimate**: 5-15 EUR for a CX22 or CX32 instance

### 3.2 AWS Fargate

**Pros**

* Managed container orchestration
* Familiar ecosystem for most developers
* EU regions available (Frankfurt, Ireland)
* Elastic scaling

**Cons**

* Higher baseline cost than Hetzner
* More moving parts (ECS, ECR, VPC, ALB, etc.)
* Harder to predict monthly bill

**Monthly cost estimate**: 30-60 EUR for equivalent capacity

### 3.3 Railway or Fly.io

**Pros**

* Simple deploy experience
* Attractive for solo developers
* EU regions available

**Cons**

* Smaller vendor lock-in concern
* Less control over networking

**Monthly cost estimate**: 10-30 EUR

### 3.4 Self-Hosted on a Home Server

**Pros**

* No hosting cost
* Full control

**Cons**

* Availability depends on home network
* Not appropriate for external users

Considered only if v2 is an internal demo.

---

## 4. Recommended v2 Architecture

### 4.1 Topology

```
┌────────────────────────────────────────────────────┐
│  Cloudflare (CDN, DNS, WAF, rate limiting at edge) │
└──────────────────────┬─────────────────────────────┘
                       │
                       ▼
┌────────────────────────────────────────────────────┐
│  Hetzner Cloud VPS (Falkenstein, DE)               │
│                                                    │
│  ┌──────────────────────────────────────────────┐  │
│  │  Docker Compose                              │  │
│  │                                              │  │
│  │  ┌────────────┐    ┌──────────────────┐      │  │
│  │  │  Next.js   │◄──►│    FastAPI       │      │  │
│  │  │  (static)  │    │   (GDPR AI core) │      │  │
│  │  └────────────┘    └────────┬─────────┘      │  │
│  │                             │                │  │
│  │  ┌──────────────────────────┴──────────┐     │  │
│  │  │                                     │     │  │
│  │  │  ChromaDB (embedded in FastAPI)     │     │  │
│  │  │  SQLite (volume-mounted)            │     │  │
│  │  │  bge-m3 model (volume-mounted)      │     │  │
│  │  │                                     │     │  │
│  │  └─────────────────────────────────────┘     │  │
│  └──────────────────────────────────────────────┘  │
└──────────────────────┬─────────────────────────────┘
                       │
                       │ HTTPS outbound
                       ▼
              ┌──────────────────┐
              │  Anthropic API   │
              └──────────────────┘
```

### 4.2 Why This Shape

* One VPS keeps cost, complexity, and operations minimal
* Docker Compose is sufficient for a single-server deployment
* Cloudflare in front provides free DNS, HTTPS, caching, and basic DDoS protection
* Embedded ChromaDB and SQLite eliminate separate database services

---

## 5. Deployment Pipeline (v2 Plan)

### 5.1 Continuous Integration

GitHub Actions workflow:

1. Lint with Ruff
2. Type-check with mypy
3. Run unit tests
4. Run integration tests (mocked LLM)
5. Build Docker image
6. Push to container registry (GitHub Container Registry)

### 5.2 Continuous Deployment

On merge to `main`:

1. CI completes successfully
2. Deploy step SSHes to Hetzner VPS
3. Pulls new container image
4. Runs `docker compose up -d` with new image
5. Health check verifies service is responsive

### 5.3 Zero-Downtime Strategy (v2)

For v2 simplicity, brief downtime (a few seconds) during deploys is acceptable. If zero-downtime becomes important, switch to blue-green via two compose stacks behind Cloudflare.

---

## 6. Secret Management

### 6.1 v2 Approach

* `ANTHROPIC_API_KEY` stored as a Docker Compose environment variable, loaded from a `.env` file on the server
* `.env` is deployed via secure copy and never committed to Git
* GitHub Actions deploys use SSH keys stored in GitHub Secrets

### 6.2 Upgrade Path

If the service grows, migrate to a managed secret store (HashiCorp Vault, AWS Secrets Manager, or Doppler).

---

## 7. Backup and Recovery

### 7.1 What Needs Backing Up

* SQLite query log (user queries, feedback)
* User accounts (if added)
* ChromaDB is regeneratable from source scrapers; lower priority

### 7.2 Backup Strategy

Daily cron job:

* Snapshot SQLite file to encrypted off-server location (S3 or Backblaze B2)
* Retention: 30 daily snapshots, 12 monthly snapshots

### 7.3 Recovery Plan

In case of server loss:

* Provision a new Hetzner VPS
* Restore `.env` and SQLite snapshot
* Pull Docker image, run compose
* Re-run knowledge base indexing (takes ~1 hour)

Expected Recovery Time Objective: 2 hours

---

## 8. Monitoring and Alerting (v2)

### 8.1 What to Monitor

* API health endpoint (external ping every 60 seconds)
* Error rate per endpoint
* P95 latency
* Disk usage on VPS
* Anthropic API cost accumulation

### 8.2 Alerting Channels

* Email for non-urgent alerts
* Telegram or Discord bot for urgent alerts (5xx error surge, disk >80% full, daily cost exceeding threshold)

### 8.3 Dashboards

Simple Grafana instance running alongside FastAPI, reading from Prometheus scraped metrics.

---

## 9. Cost Model (v2 Estimates)

### 9.1 Fixed Monthly Costs

| Item | Cost |
|------|------|
| Hetzner VPS (CX22) | ~5 EUR |
| Cloudflare (free tier) | 0 EUR |
| Backups (B2 or S3) | <1 EUR |
| Domain name | ~1 EUR |
| **Fixed total** | **~7 EUR/month** |

### 9.2 Variable Costs

Anthropic API at 10 queries per day: ~3 EUR/month.
At 100 queries per day: ~30 EUR/month.

### 9.3 Upper-Bound Scenario

Even serving 500 queries per day, total cost stays around 150-200 EUR / month — well within hobby-project bounds.

---

## 10. Security Considerations

### 10.1 Network Security

* Only ports 80 (redirect to 443) and 443 open
* SSH restricted to specific IPs via Hetzner firewall
* Internal services communicate over Docker network, not exposed to host

### 10.2 Application Security

* Rate limiting at Cloudflare edge and in FastAPI
* Input validation via Pydantic
* CORS restricted to known origins
* HTTPS enforced end-to-end

### 10.3 Data Security

* Database encrypted at rest (LUKS on disk, if needed)
* Backups encrypted in transit and at rest
* API keys rotated quarterly

---

## 11. GDPR Compliance of the Hosted Service Itself

When GDPR AI becomes a hosted service, the service itself must comply with GDPR.

* Privacy policy drafted and published
* Data processing agreement with Anthropic reviewed
* Users informed about what is logged
* Data subject request process defined (access, deletion)
* DPIA conducted for the service

This is managed as a project task in the v2 roadmap.

---

## 12. Summary

The v2 cloud architecture is deliberately modest: one VPS in an EU data centre, Docker Compose, Cloudflare in front, embedded data stores. This keeps fixed monthly costs in single-digit euros while supporting a small beta and the ability to scale to hundreds of daily queries without re-architecting.

More complex deployment topologies (multi-region, Kubernetes, managed services) are deferred until real usage justifies the additional operational overhead.

---

## v2 Note

Remains deferred. v2 runs entirely locally. Cloud deployment is v3+ scope.