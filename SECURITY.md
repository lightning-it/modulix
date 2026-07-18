# Security Policy

<<<<<<< HEAD
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
=======
Lightning IT builds and maintains software, automation, and reference
implementations to help customers deliver secure, policy-driven IT services
(e.g. infrastructure building blocks, DevSecOps tooling, blueprints, and
platform integrations). Because our repositories can influence how systems are
deployed, configured, and operated, we treat security-relevant reports
seriously.

This document describes which versions of this **Lightning IT repository** are
supported with security updates and how to report a vulnerability.

> **Note:** Lightning IT maintains multiple repositories (e.g. Ansible
> Collections, Terraform modules, container images, templates, documentation).
> Each repository may have its own lifecycle and release cadence, but the same
> reporting and disclosure principles apply across all Lightning IT projects.
>>>>>>> origin/develop

---

## Supported Versions

<<<<<<< HEAD
ModuLix follows semantic versioning (`MAJOR.MINOR.PATCH`). In practice for
this repo:

- **MAJOR** – breaking structural changes to how ModuLix is organized
- **MINOR** – new products, blueprints, inventories, or orchestration logic
=======
Lightning IT repositories generally follow semantic versioning
(`MAJOR.MINOR.PATCH`) where applicable:

- **MAJOR** – breaking changes (interfaces, structures, behavior)
- **MINOR** – new features or non-breaking improvements
>>>>>>> origin/develop
- **PATCH** – bug fixes and security-related corrections

We currently provide security fixes for:

<<<<<<< HEAD
| Version range | Status                                |
| ------------- | ------------------------------------- |
| `main` branch | ✅ actively supported (security + bugfixes) |
| latest tagged release (0.x) | ✅ best-effort security fixes         |
| older tags / branches      | ❌ no guaranteed security updates     |

If you are consuming ModuLix content from an older tag or branch, we strongly
recommend upgrading to the latest version from `main` or the most recent tag
before requesting security fixes.
=======
| Version range | Status |
| --- | --- |
| `main` (or default) branch | ✅ actively supported (security + bugfixes) |
| latest tagged release | ✅ supported (security fixes as needed) |
| older tags / branches | ❌ no guaranteed security updates |

If you are using an older tag or branch, we strongly recommend upgrading to
the latest version from the default branch or the most recent tag before
requesting security fixes.
>>>>>>> origin/develop

---

## Reporting a Vulnerability

<<<<<<< HEAD
If you believe you have found a security-relevant issue in this repository,
for example:

- a blueprint or inventory that leads to insecure defaults,
- documentation that encourages unsafe configuration,
- or orchestration logic that accidentally weakens security controls,
=======
If you believe you have found a security issue in this repository, for example:

- insecure defaults in automation, templates, or code,
- documentation that encourages unsafe configuration,
- misconfigurations that could weaken security controls,
- leaked credentials, tokens, or sensitive information,
- dependency or supply-chain concerns,
>>>>>>> origin/develop

please **do not** open a public issue or pull request.

Instead:

1. Prepare a short report including:
   - a description of the issue and potential impact,
<<<<<<< HEAD
   - which file(s), page(s), or blueprint(s) are affected,
   - steps to reproduce or understand the risk, if applicable,
   - any relevant logs, configs, or screenshots (redacted as needed).

2. Send your report to:

   - 📧 **security@l-it.io** (preferred), or  
   - your existing Lightning IT contact with the subject:  
     `ModuLix Security Report`
=======
   - which files/components are affected,
   - steps to reproduce (if applicable),
   - any relevant logs/config snippets (redacted as needed).

2. Send your report to:

   - 📧 **security@l-it.io** (preferred), or
   - your existing Lightning IT contact with the subject:
     `Security Report`
>>>>>>> origin/develop

3. You will receive an acknowledgement within **3 business days**.

We will then:
- triage the issue (severity, impact, affected versions),
- confirm whether we can reproduce it,
- propose remediation options and an appropriate timeline.

If the vulnerability is confirmed, we will:

<<<<<<< HEAD
- prepare and review a fix in a private branch,
- ship a patch or minor release depending on impact,
- reference the fix in the changelog and/or release notes,
=======
- prepare and review a fix (often in a private branch),
- ship a patch or minor release depending on impact,
- document the fix in release notes and/or a changelog where appropriate,
>>>>>>> origin/develop
- optionally credit you by name or pseudonym if you wish.

If the report is determined to be a false positive or out of scope, we will
still reply with an explanation.

---

## Scope

This security policy covers:

<<<<<<< HEAD
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
=======
- the **content of this repository**, including (as applicable):
  - source code,
  - automation definitions (e.g. playbooks, roles, pipelines),
  - container build definitions,
  - templates, configuration, and documentation shipped with the repository.

It does **not** cover:

- upstream products and dependencies (e.g. RHEL, OpenShift, Kubernetes,
  Keycloak, Vault, GitLab, etc.), which follow their own vendor security
  processes.

However, if you discover a vulnerability in a third-party component that is
**introduced or made exploitable** by Lightning IT configuration, packaging,
or guidance, please report it via the process above so we can assess impact and
publish mitigations.

---

## Coordinated Disclosure

We follow responsible, coordinated disclosure principles. Please allow us a
reasonable timeframe to investigate and remediate issues before public
disclosure. If you have a disclosure deadline, include it in your report so we
can coordinate appropriately.
>>>>>>> origin/develop
