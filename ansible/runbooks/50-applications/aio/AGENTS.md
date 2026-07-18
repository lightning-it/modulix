# AIO Agent Notes

## Secret Storage Rule

- Never commit secret values, tokens, passwords, private keys, activation codes, or decrypted Vault output.
- When HC Vault is configured for the AIO runbook, generated credentials must be read from HC Vault first, generated only when missing, written back to HC Vault, and then consumed by the application from Vault-backed Ansible variables.
- When HC Vault is not configured, required credentials must be supplied from Ansible Vault encrypted inventory variables. Do not add new plaintext generated-secret fallbacks.
- Tasks that read, generate, write, template, or compare secret material must use `no_log: true`.
- For `aio01.prd.dmz.corp.l-it.io`, the HC Vault KV v2 mount is `stage-2c`. Store the generated application secrets at this exact path, or provide the listed variables from Ansible Vault when HC Vault is not in use:

| Component | HC Vault path under `stage-2c` | Ansible Vault variables / keys |
|---|---|---|
| Semaphore app and managed PostgreSQL | `aio01.prd.dmz.corp.l-it.io/semaphore/admin` | `semaphore_deploy_admin_login`, `semaphore_deploy_admin_password`, `semaphore_deploy_admin_name`, `semaphore_deploy_admin_email`, `semaphore_deploy_db_password`, `semaphore_deploy_access_key_encryption` / `semaphore_deploy_admin_login`, `semaphore_deploy_admin_password`, `semaphore_deploy_admin_name`, `semaphore_deploy_admin_email`, `semaphore_deploy_db_password`, `semaphore_deploy_access_key_encryption` |
