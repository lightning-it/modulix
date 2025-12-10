# Security Policy

ModuLix is used to describe and orchestrate enterprise automation building blocks
at a product and blueprint level.
Because these definitions may influence how infrastructure is operated and
secured, we take security-related issues seriously.

This document explains which versions of the **ModuLix repository itself** are
supported with security updates, and how to report a vulnerability.

> **Note:**  
> The actual automation implementations (e.g. Ansible Collections, Terraform
> modules) live in separate repositories. Those have their own lifecycle and
> security handling policies.

## Supported Versions

ModuLix follows semantic versioning (`MAJOR.MINOR.PATCH`). In practice:

- **MAJOR** – breaking structural changes in how ModuLix is organized
- **MINOR** – new components, blueprints, documentation and orchestration logic
- **PATCH** – bug fixes and security-related corrections

Security fixes for this repository are only guaranteed for recent **minor**
versions.

| Version        | Supported                        |
| -------------- | -------------------------------- |
| 0.3.x          | ✅ actively supported (security + bugfixes) |
| 0.2.x          | ⚠️ best-effort, critical security issues only |
| < 0.2          | ❌ no longer supported           |

> While ModuLix is still < 1.0.0, structure and content may evolve more
> frequently. Once we reach 1.0.0, we will document a stricter support window.

If you are working with an older ModuLix version, we strongly recommend
upgrading to the latest `0.3.x` (or higher) before requesting security fixes.

## Reporting a Vulnerability

If you believe you have found a security-relevant issue in:

- the way ModuLix describes components, blueprints or integration flows, or
- documentation that could mislead users into deploying insecure configurations,

please **do not** open a public issue or pull request.

Instead:

1. Prepare a short report including:
   - a description of the issue and potential impact,
   - which file(s), page(s) or blueprint(s) are affected,
   - steps to reproduce or understand the risk, if applicable,
   - any relevant logs, configs or screenshots (redacted as needed).

2. Send your report to:

   - 📧 **security@l-it.io** (preferred), or  
   - your existing Lightning IT contact with the subject `ModuLix Security Report`.

3. You will receive an acknowledgement within **3 business days**.  
   We will then:
   - triage the issue (severity, affected versions),
   - inform you whether we can reproduce or confirm it,
   - discuss remediation options and timelines if confirmed.

If the vulnerability is confirmed, we will:

- prepare and review a fix in a private branch,
- ship a patch/minor release depending on impact,
- mention the fix in the changelog and/or release notes,
- credit you by name or pseudonym, if you wish.

If the report is determined to be a false positive or out of scope, we will
still reply with an explanation.

## Scope

This security policy covers:

- the **content of this repository**:
  - ModuLix product inventory,
  - blueprints and orchestration logic described here,
  - documentation and example flows contained in this repo.

It does **not** cover:

- implementation repositories such as:
  - Ansible Collections,
  - Terraform modules,
  - container images or other code hosted in separate repos,
- upstream products (RHEL, Satellite, OpenShift, Keycloak, Vault, GitLab, etc.),
  which have their own vendor security processes.

Security or vulnerability reports related to implementation repositories
should be filed via the security process of those specific repos
(e.g. their own `SECURITY.md` or instructions).
