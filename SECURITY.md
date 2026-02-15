# Security Policy

ModuLix is used to describe and orchestrate infrastructure building blocks
(e.g. RHEL, Satellite, OpenShift, Keycloak) at a product and blueprint level.
Because these definitions can influence how infrastructure is deployed and
operated, we treat security-relevant reports seriously.

This document describes which versions of this **ModuLix repository** are
supported with security updates and how to report a vulnerability.

> **Note:** The actual automation implementations (e.g. Ansible Collections,
> Terraform modules, container images) live in separate repositories and have
> their own lifecycle and security handling. This policy only covers this
> repository.

---

## Supported Versions

ModuLix follows semantic versioning (`MAJOR.MINOR.PATCH`). In practice for
this repo:

- **MAJOR** – breaking structural changes to how ModuLix is organized
- **MINOR** – new products, blueprints, inventories, or orchestration logic
- **PATCH** – bug fixes and security-related corrections

We currently provide security fixes for:

| Version range | Status                                |
| ------------- | ------------------------------------- |
| `main` branch | ✅ actively supported (security + bugfixes) |
| latest tagged release (0.x) | ✅ best-effort security fixes         |
| older tags / branches      | ❌ no guaranteed security updates     |

If you are consuming ModuLix content from an older tag or branch, we strongly
recommend upgrading to the latest version from `main` or the most recent tag
before requesting security fixes.

---

## Reporting a Vulnerability

If you believe you have found a security-relevant issue in this repository,
for example:

- a blueprint or inventory that leads to insecure defaults,
- documentation that encourages unsafe configuration,
- or orchestration logic that accidentally weakens security controls,

please **do not** open a public issue or pull request.

Instead:

1. Prepare a short report including:
   - a description of the issue and potential impact,
   - which file(s), page(s), or blueprint(s) are affected,
   - steps to reproduce or understand the risk, if applicable,
   - any relevant logs, configs, or screenshots (redacted as needed).

2. Send your report to:

   - 📧 **security@l-it.io** (preferred), or  
   - your existing Lightning IT contact with the subject:  
     `ModuLix Security Report`

3. You will receive an acknowledgement within **3 business days**.  
   We will then:
   - triage the issue (severity, affected versions),
   - inform you whether we can reproduce or confirm it,
   - discuss remediation options and timelines if confirmed.

If the vulnerability is confirmed, we will:

- prepare and review a fix in a private branch,
- ship a patch or minor release depending on impact,
- reference the fix in the changelog and/or release notes,
- optionally credit you by name or pseudonym if you wish.

If the report is determined to be a false positive or out of scope, we will
still reply with an explanation.

---

## Scope

This security policy covers:

- the **content of this repository**, including:
  - ModuLix product inventory,
  - environment inventories (e.g. nightly, demo),
  - group variables and blueprints,
  - orchestration playbooks and documentation in this repo.

It does **not** cover:

- automation implementation repositories such as:
  - Ansible Collections (e.g. `lightning_it.supplementary`),
  - Terraform modules,
  - devtools containers,
- upstream products (RHEL, Satellite, OpenShift, Keycloak, Vault, GitLab, etc.),
  which have their own vendor security processes.

Security or vulnerability reports related to implementation repositories should
be filed via the security process of those specific repositories (for example,
their own `SECURITY.md` or instructions).
