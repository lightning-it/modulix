---
title: ModuLix
layout: default
---

# ModuLix

_Modular Infrastructure Platform for Secure, Automated IT._

ModuLix is Lightning IT’s modular infrastructure toolkit.  
The goal: reusable, standardized building blocks for modern Linux and Kubernetes infrastructures – from the first PoC environment to a hardened enterprise platform.

ModuLix is not a single product, but a **component library** with clearly defined blueprints and editions (for example Enterprise Bronze/Gold/Platinum). Every ModuLix installation is:

- documented,
- automated,
- and aligned with ISO 27001 / BSI Grundschutz / NIS2.

---

## Why ModuLix?

Most infrastructures grow “organically”:

- differently configured Linux servers
- ad-hoc installed platform products (Satellite, OpenShift, Ansible, Keycloak, Vault, …)
- barely any consistent hardening or operations documentation
- every new environment feels like a small project

**ModuLix fixes this by:**

- breaking infrastructure down into **clear components**,
- defining **editions** (e.g. Enterprise Bronze/Gold) composed from those components,
- describing each environment via **blueprints** (e.g. “Enterprise Silver – Green Blueprint v1.0.0”),
- mapping the full lifecycle via **Infrastructure-as-Code & GitOps**.

---

## Core Principles

1. **Components instead of Snowflake Servers**  
   Each technical piece (e.g. a Keycloak cluster, a GitLab platform, an OpenShift PoC) is a **ModuLix component** with:
   - a clear description
   - defined inputs/outputs
   - concrete automation (Ansible/Terraform/Helm)

2. **Editions and Blueprints**  
   ModuLix aggregates components into **editions** (e.g. Enterprise Bronze/Gold/Platinum) and makes them concrete via **blueprints**:
   - Edition = which components are included?
   - Blueprint = **how** they are wired (zones, clusters, VRFs, integrations, security).

3. **Security & Compliance by Design**  
   All building blocks are designed with:
   - ISO 27001 / BSI Grundschutz / NIS2 in mind,
   - hardening baselines (SCAP, CIS),
   - clear zone separation (e.g. COM/DMZ/INT/ISO),
   - zero-trust principles for remote access.

4. **Automation First**  
   Every component is:
   - provisioned via **Ansible/Terraform/Helm**,
   - versioned in Git,
   - reproducible via CI/CD and GitOps (e.g. Molecule for Ansible, `terraform test` for modules).

---

## Architecture Overview

At a high level, ModuLix consists of:

- **ModuLix Component Library**  
  A collection of technical building blocks (e.g. Satellite stack, Keycloak stack, GitLab common tenant, Vault, monitoring, logging, storage, …).

- **ModuLix Editions**  
  Curated bundles, e.g.:
  - _Enterprise Bronze_ – minimal platform (central config, logging, basic monitoring)
  - _Enterprise Gold/Platinum_ – increasingly complete platforms (OpenShift, GitLab, Keycloak, Vault, ACM/ACS, …)

- **Blueprints**  
  Edition-specific implementations, such as:
  - `midx-silver-standard-green-v1.0.0`
  - define zone layout, cluster count, integrations, security settings, operational processes.

- **Dev & Test Environments**  
  - `dev.l-it.io` as a playground for nightly builds and demos,
  - deep integration into GitHub Actions (nightly tests, Molecule, Terraform tests),
  - self-hosted runners that test against real stacks.

---

## Example Components

Some typical ModuLix components (examples):

- **Compute & Platform**
  - OpenShift clusters
  - Virtualization stacks (e.g. OpenShift Virtualization)
  - Satellite / RHEL lifecycle

- **Identity & Access**
  - Keycloak / Red Hat Build of Keycloak clusters
  - LDAP/AD integration
  - SSO for platforms

- **Developer Tooling**
  - GitLab platform (common tenant + DR instances)
  - Container registries
  - CI/CD pipelines for infra code

- **Security & Secrets**
  - Vault cluster with role-based access patterns
  - Central PKI / issuing CAs
  - Policy enforcement

- **Observability**
  - Monitoring stack (e.g. Prometheus, Alertmanager, Grafana)
  - Logging stack (e.g. Loki/EFK)
  - Metrics and dashboards for platforms and components

---

## Editions & Use Cases

**ModuLix Enterprise Bronze**

- Entry-level edition, minimal scope:
  - basic Linux/RHEL baseline
  - base monitoring/logging
  - simple CI/CD pipelines for infra code
- Goal: quickly create a small but clean environment for pilots.

**ModuLix Enterprise Gold/Platinum** (examples)

- Larger, zone-separated infrastructures:
  - COM/DMZ/INT/ISO zones
  - multi-cluster OpenShift
  - GitLab as central delivery platform
  - Keycloak/LDAP/Vault integration
- Goal: full-featured, auditable platforms ready for enterprise workloads.

---

## Development & Operations Model

### Code-First

- All components live in Git repos (e.g. `ansible-collection-…`, `terraform-…`, `container-…`).
- Standardized:
  - CI workflows (lint, Molecule, Terraform tests),
  - release pipelines (Semantic Release),
  - devtools containers (like `wunder-devtools-ee`).

### GitOps & Nightly

- Self-hosted runners execute:
  - nightly tests (Molecule scenarios, Terraform integration tests),
  - deployments into dev/nightly environments.
- GitHub provides full visibility:
  - nightly build status,
  - which components/blueprints are stable,
  - which are ready for demos or production.

### Demo & Product Experience

- Demos are standardized under domains like `*.demo.dev.l-it.io` (or equivalent):
  - based on reproducible blueprints,
  - ideal for showcasing concrete platform scenarios to customers or stakeholders.

---

## Roadmap & Next Steps

ModuLix is built to grow with you:

- more components (e.g. MicroShift, edge scenarios, additional security tools),
- new blueprints for specific industries (e.g. public sector, regulated environments),
- tighter integration with Lightning IT Control Platform (LCP), including:
  - framework mappings (ISO/BSI/NIS2/DORA),
  - automated controls,
  - reports and evidence collection.

---

## Contact & Contribution

ModuLix lives from clear building blocks, solid documentation, and real-world automation.

If you want to:

- contribute your own components,
- experiment with new blueprints,
- or roll out ModuLix in a concrete customer environment,

reach out to us or open an issue / discussion in the repo.

```text
Lightning IT – ModuLix
The modular infrastructure platform for secure, automated delivery.
