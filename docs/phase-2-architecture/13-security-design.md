# Phase 2.13 – Security Design

## 1. Overview

GDPR AI handles sensitive input — scenarios that may describe real-world data protection incidents — and integrates with a paid external API. Security is a first-class concern across all design phases.

This document defines the security posture for v1 (local CLI) and sets direction for v2 (hosted service).

---

## 2. Threat Model

### 2.1 Assets

| Asset | Sensitivity | Impact if compromised |
|-------|-------------|----------------------|
| Anthropic API key | High | Credit theft, service abuse |
| User scenarios | Medium-High | Privacy leak if scenarios contain real data |
| Query logs (SQLite) | Medium | Privacy leak if scenarios contain real data |
| Knowledge base | Low | Regeneratable from public sources |
| Source code | Low | Public repo, MIT licensed |

### 2.2 Threat Actors

| Actor | Motivation | Likelihood (v1) |
|-------|------------|------------------|
| Credential-stealing bots (scanning public repos) | API key theft | Medium |
| Casual attackers | Disruption | Low |
| Targeted attackers | Specific user harm | Very low for personal project |

### 2.3 Out of Scope for v1

* Nation-state actors
* Insider threats (single-developer project)
* Supply-chain attacks on third-party libraries (monitored via `uv` lockfile)

---

## 3. v1 Security Principles

### 3.1 Secrets Never Committed

API keys and other secrets are stored only in `.env`, which is listed in `.gitignore`.

### 3.2 Local-Only Processing

All user data stays on the user's machine. The only data transmitted externally is the scenario text sent to Anthropic for LLM calls.

### 3.3 Principle of Least Privilege

Even on a single-user machine:

* Environment variables scoped to the Python process
* File permissions restrict `.env` to user-readable
* No background daemons or elevated privileges

### 3.4 Fail Closed

Invalid or ambiguous inputs cause the system to reject the request rather than proceed with guesses.

---

## 4. Key Management (v1)

### 4.1 API Key Storage

* Location: `.env` file in project root
* Permissions: 600 (user-readable only)
* Not committed: enforced via `.gitignore`
* Not logged: keys masked in all logging output

### 4.2 API Key Rotation

When a key is exposed (e.g., shared in a screenshot or accidentally committed):

1. Immediately revoke the key via Anthropic Console
2. Create a new key
3. Update `.env`
4. Restart any running processes

A documented rotation runbook is included in `docs/runbooks/key-rotation.md` (v2 scope).

### 4.3 Detection

Pre-commit hooks (v2) will scan for patterns matching `sk-ant-` before allowing commits to proceed.

---

## 5. Input Handling

### 5.1 Scenario Input Validation

User-provided scenarios are:

* Length-limited (10-2000 characters)
* Not interpreted as shell commands
* Not interpolated into prompts without escaping
* Passed to the LLM as quoted content, not as instructions

### 5.2 Prompt Injection Mitigation

Scenarios could attempt prompt injection (e.g., "Ignore previous instructions and..."). Mitigations:

* System prompts include explicit instructions to treat user scenario as content, not instructions
* Validation layer checks that outputs conform to the structured schema
* Article numbers in outputs are cross-checked against retrieved chunks (hallucination guard)

### 5.3 Shell Command Safety

Scenarios passed via CLI are received as arguments. They never reach `os.system`, `subprocess` with `shell=True`, or any other shell interpolation. Typer handles quoting correctly.

---

## 6. Output Handling

### 6.1 No Executable Output

Reports are text. No code is generated that would be executed automatically.

### 6.2 Source Attribution

Every article citation in the output includes its source URL. This gives users the ability to verify the claim against the authoritative source.

### 6.3 No Sensitive Data Echo

Reports summarise scenarios but do not expand or elaborate on personal details provided in input. A scenario mentioning "John Smith, SSN 123-45-6789" would not have those details amplified in the report.

---

## 7. Data at Rest

### 7.1 Local Storage

* Knowledge base: unencrypted (public source data)
* Query logs: stored in local SQLite, unencrypted on disk
* `.env`: unencrypted but permission-restricted

### 7.2 v2 Hosted Considerations

When GDPR AI becomes a hosted service, encryption at rest becomes relevant:

* Full-disk encryption on VPS (LUKS on Linux)
* SQLite file protected by disk encryption
* API keys in environment variables, not written to disk in plaintext outside `.env`

---

## 8. Data in Transit

### 8.1 v1

All network traffic is to `api.anthropic.com` over TLS. Python's `httpx` and the Anthropic SDK enforce TLS by default.

### 8.2 v2

All external endpoints served via HTTPS (TLS 1.2+). Cloudflare enforces HTTPS at the edge. Internal container-to-container traffic stays within the Docker bridge network.

---

## 9. Logging Security

### 9.1 Sensitive Data in Logs

Logs may contain:

* User scenarios (potentially sensitive)
* Retrieved chunks (public legal text, not sensitive)
* Timing and cost data (not sensitive)

### 9.2 Redaction Rules

* API keys masked in logs (`sk-ant-***<last-4>`)
* Optionally, scenarios can be redacted in logs if the user sets `LOG_SCENARIOS=false` in `.env` (v2 feature)

### 9.3 Log Retention (v1)

Local SQLite logs retained indefinitely unless the user explicitly clears them:

```
gdpr-check logs clear
```

### 9.4 Log Retention (v2)

Hosted service:

* Application logs: 30 days
* Query logs in SQLite: 90 days unless user opts into longer retention
* Backups: 30 days daily, 12 months monthly

---

## 10. Third-Party Dependencies

### 10.1 Dependency Review

Every dependency in `pyproject.toml` is reviewed for:

* Active maintenance
* License compatibility (MIT, Apache-2.0, BSD)
* Known vulnerabilities (via `pip-audit` in v2 CI)

### 10.2 Lockfile Integrity

`uv.lock` is committed and provides deterministic installs. Hash checking prevents tampered packages from being installed.

### 10.3 Supply Chain

* Models are downloaded from Hugging Face (BAAI/bge-m3) over HTTPS
* Python packages from PyPI over HTTPS
* No binary dependencies from untrusted sources

---

## 11. Anthropic API Usage

### 11.1 Data Sent

Per query, the following is sent to Anthropic:

* The user's scenario (for extraction)
* The scenario + entities (for classification)
* The scenario + retrieved chunks (for reasoning)

### 11.2 What Is Not Sent

* Any user identity information (there isn't any in v1)
* Previous queries from the same session
* API keys of other services

### 11.3 Data Retention at Anthropic

Subject to Anthropic's data usage policies. Users are informed in the README that scenarios are transmitted to Anthropic and advised to review Anthropic's terms before entering sensitive data.

---

## 12. Privacy by Design

### 12.1 Collection Minimisation

The system collects only what is necessary:

* No user account
* No telemetry
* No analytics
* No cookies (v1 CLI has no browser interface)

### 12.2 Local-First Data

All non-Anthropic data stays on the user's machine.

### 12.3 Transparent Processing

Users can inspect query logs at any time via SQLite or future dashboard. Every retrieval returns a chunk set the user could inspect.

---

## 13. Incident Response

### 13.1 v1 Scenarios

* API key exposed in screenshot → rotate immediately
* API key committed to Git → rotate + force-push + contact Anthropic if credits were consumed
* Dependency CVE disclosed → update dependency, rebuild lockfile

### 13.2 v2 Scenarios

* Suspected data breach → incident response plan documented separately
* Service abuse → rate limiting, potential IP block at Cloudflare
* LLM hallucination causing harmful output → review prompts, add gold-set scenario, fix

---

## 14. Compliance Considerations

### 14.1 GDPR Compliance of the Tool Itself

* v1 (local CLI): minimal compliance burden; user processes their own data on their own machine
* v2 (hosted): full GDPR compliance required — privacy policy, DPIA, lawful basis for processing, data subject rights

### 14.2 License Compliance

* GDPRhub CC BY-NC-SA 4.0: enforced through non-commercial project stance and attribution in outputs
* Code MIT license: standard
* Third-party libraries: tracked and respected

---

## 15. Security Testing

### 15.1 v1 Manual Checks

* Verify `.env` is gitignored: `git check-ignore -v .env`
* Verify no API keys in tracked files: `grep -r 'sk-ant-' .`
* Verify scenarios cannot escape to shell: manual test with adversarial inputs

### 15.2 v2 Automated Checks

* Pre-commit hook scanning for secret patterns
* CI dependency vulnerability scanning
* CI static analysis (Bandit or similar)
* External penetration test before public launch

---

## 16. Summary

GDPR AI's security posture is proportionate to its scope. Version 1 is a local CLI processing public legal knowledge and user-provided scenarios, with only the Anthropic API as an external dependency. Core protections — key management, input validation, hallucination guards, local-only storage — are in place from day one.

Version 2 introduces hosting and user accounts, which expand the threat surface. The v2 security plan includes encryption at rest, rate limiting, automated dependency scanning, and compliance with GDPR for the hosted service itself.

---

## v2 Security Considerations (local API and persistence)

* **SQLite file permissions** — the database file SHOULD be created with restrictive permissions (for example `chmod 600`) so other OS users on the same machine cannot read project or analysis content.
* **Language-model API payload** — requests contain **system descriptions** and **retrieved legal text**, not production databases of data subjects; users SHOULD avoid pasting real individuals' data into descriptions.
* **Generated documents** — stored **locally** only (SQLite and optional markdown export paths); no v2 requirement for remote object storage.
* **Authentication** — v2 local deployment has **no** mandatory API authentication (single-user trust boundary). **Authentication and multi-tenant isolation** are v3+ scope when a hosted frontend exists.
* **Prompt injection** — system descriptions and scenarios MUST be treated as **untrusted content**; system prompts and schema validation mitigate instruction hijacking; compliance outputs MUST remain citation-grounded where legal claims are made.
* **Rate limiting** — API layer SHOULD enforce local rate limits to prevent accidental **runaway** reasoning-engine cost (tight client loops, buggy scripts).