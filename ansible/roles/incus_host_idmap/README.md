# Incus host ID map

`incus_host_idmap` reconciles the subordinate UID and GID allocation consumed
by the root-run Incus daemon. It restarts Incus only when either allocation
changes, before later Incus roles create instances.

The defaults follow the Incus-recommended root allocation. Override the values
from environment-owned inventory when the host already reserves overlapping
ranges for another user-namespace runtime.

```yaml
incus_host_idmap_enabled: true
incus_host_idmap_owner: root
incus_host_idmap_start: 1000000
incus_host_idmap_count: 1000000000
```
