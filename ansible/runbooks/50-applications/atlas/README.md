# LIT Atlas Runbook

LIT Atlas is the Lightning IT Observability Platform. It is a curated,
single-stack appliance for infrastructure monitoring, metrics, logs, alerting,
dashboards, classic syslog ingestion, and host/service checks.

Atlas deploys one supported stack:

- Grafana
- Prometheus
- Loki
- Alloy
- Alertmanager
- rsyslog
- Checkmk

Atlas is not Wunderbox. LIT Wunderbox is the Infrastructure Platform. It
provides infrastructure services. LIT Atlas observes infrastructure. Atlas does
not provide DNS, DHCP, registry, mirror, PXE, or general infrastructure
bootstrap services; those belong to Wunderbox.

Product positioning:

- LIT ModuLix = Automation Content
- LIT AIO = Automation Runtime
- LIT Wunderbox = Infrastructure Platform
- LIT Atlas = Observability Platform

## Deliberate Exclusions

Atlas intentionally does not include OpenTelemetry Collector, Tempo, or Mimir.
The supported appliance stack keeps collection, metrics, logs, alerting, and
dashboards in one small Podman/systemd-managed footprint without Kubernetes,
OpenShift, or kubectl.

## Run

```bash
ansible-playbook -i inventory.yml \
  ansible/runbooks/50-applications/atlas/10-deploy.yml
```

The playbook targets the `atlas` inventory group.

## Runbooks

- `06-storage-evidence.yml`: collect read-only block, mount, swap, LVM, RAID,
  and SMART discovery for one exactly limited Atlas host.
- `05-prepare.yml`: create Atlas directories, prepare Ubuntu, configure Podman,
  and optionally apply firewall policy.
- `07-preflight.yml`: validate Atlas inventory shape and runtime readiness.
- `10-deploy.yml`: deploy the full Atlas observability appliance.
- `20-ops.yml`: inspect Atlas runtime status.

## Required Inventory

At minimum, define an `atlas` host or group:

```yaml
all:
  children:
    atlas:
      hosts:
        atlas01.example.invalid:
```

Common Atlas variables:

```yaml
lit_atlas_enabled: true
lit_atlas_domain: example.invalid
lit_atlas_data_dir: /opt/lit/atlas
lit_atlas_bind_address: 127.0.0.1

services:
  atlas:
    grafana: enabled
    prometheus: enabled
    loki: enabled
    alloy: enabled
    alertmanager: enabled
    rsyslog: enabled
    checkmk: enabled
```

Component credentials and production alert receivers must come from inventory,
HC Vault, or Ansible Vault. Do not store plaintext secrets in the runbook.

## Default Ports

| Service | Port |
|---|---:|
| Grafana | `3000/tcp` |
| Prometheus | `9090/tcp` |
| Alertmanager | `9093/tcp` |
| Loki | `3100/tcp` |
| Alloy | `12345/tcp` |
| rsyslog | `514/tcp`, `514/udp` |
| Checkmk | `5000/tcp` |

By default services bind to `127.0.0.1`. Set `lit_atlas_bind_address` and
enable `lit_atlas_firewall_enabled` only when services should be reachable from
outside the host or an external gateway.

## Backup-Relevant Directories

The default appliance layout is:

- `/opt/lit/atlas/config/`
- `/opt/lit/atlas/data/`
- `/opt/lit/atlas/quadlet/`
- `/opt/lit/atlas/backup/`

Back up `config`, `data`, and any external Vault-backed secrets required by the
Grafana and Checkmk roles.
