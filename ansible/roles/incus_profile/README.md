# Incus profile

`incus_profile` reconciles inventory-owned Incus profiles without requiring a
newer unreleased `lit.ubuntu` collection. It creates missing profiles and edits
only profiles whose description, configuration, or devices differ.

```yaml
incus_profile_items:
  - name: rhel9
    project: default
    description: RHEL installation defaults
    config:
      limits.cpu: "4"
    devices:
      root:
        type: disk
        path: /
        pool: default
```
