# Wunderbox Agent Notes

## Secret Storage Rule

- Never commit secret values, tokens, passwords, private keys, activation codes, or decrypted Vault output.
- When HC Vault is configured for the Wunderbox runbook, generated credentials must be read from HC Vault first, generated only when missing, written back to HC Vault, and then consumed by the application from Vault-backed Ansible variables.
- When HC Vault is not configured, required credentials must be supplied from Ansible Vault encrypted inventory variables. Do not add new plaintext generated-secret fallbacks.
- Tasks that read, generate, write, template, or compare secret material must use `no_log: true`.
- For `wunderbox02.prd.dmz.corp.l-it.io`, the HC Vault KV v2 mount is `stage-2c`. Store the generated application secrets at these exact paths, or provide the listed variables from Ansible Vault when HC Vault is not in use:

| Component | HC Vault path under `stage-2c` | Ansible Vault variables / keys |
|---|---|---|
| MinIO root | `wunderbox02.prd.dmz.corp.l-it.io/minio/root` | `minio_deploy_root_user`, `minio_deploy_root_password` / `root_user`, `root_password` |
| MinIO Vault bucket | `wunderbox02.prd.dmz.corp.l-it.io/minio/vault-bucket` | `minio_config_vault_bucket_access_key_effective`, `minio_config_vault_bucket_secret_key_effective` / `access_key`, `secret_key` |
| Forgejo | `wunderbox02.prd.dmz.corp.l-it.io/forgejo/secrets` | `forgejo_deploy_db_password`, `forgejo_deploy_admin_password`, `forgejo_deploy_admin_user` |
| Forgejo PostgreSQL | `wunderbox02.prd.dmz.corp.l-it.io/postgres/forgejo-postgres` | `postgres_deploy_db_password` / `postgres_deploy_db_password` |
| Keycloak | `wunderbox02.prd.dmz.corp.l-it.io/keycloak/secrets` | `keycloak_deploy_db_password`, `keycloak_deploy_admin_password`, `keycloak_deploy_admin_user` |
| Keycloak PostgreSQL | `wunderbox02.prd.dmz.corp.l-it.io/postgres/keycloak-postgres` | `postgres_deploy_db_password` / `postgres_deploy_db_password` |
| Nessus | `wunderbox02.prd.dmz.corp.l-it.io/nessus/admin` | `nessus_deploy_admin_user`, `nessus_deploy_admin_password` |
| Nexus admin | `wunderbox02.prd.dmz.corp.l-it.io/nexus/admin` | `nexus_target_admin_password` / `password` |
| Nexus AppRole KV | `wunderbox02.prd.dmz.corp.l-it.io/nexus/approle-kv` | `nexus_vault_kv_role_id`, `nexus_vault_kv_secret_id` / `role_id`, `secret_id` |
| Nexus AppRole PKI | `wunderbox02.prd.dmz.corp.l-it.io/nexus/approle-pki` | `nexus_vault_pki_role_id`, `nexus_vault_pki_secret_id` / `role_id`, `secret_id` |
| Grafana | `wunderbox02.prd.dmz.corp.l-it.io/grafana/admin` | `grafana_deploy_admin_user`, `grafana_deploy_admin_password` / `password` |
| Checkmk | `wunderbox02.prd.dmz.corp.l-it.io/checkmk/admin` | `checkmk_deploy_admin_user`, `checkmk_deploy_admin_password` / `password` |
