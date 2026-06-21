# AAP Agent Notes

## Secret Storage Rule

- Never commit secret values, tokens, passwords, private keys, activation codes, or decrypted Vault output.
- When HC Vault is configured for the AAP runbook, generated credentials must be read from HC Vault first, generated only when missing, written back to HC Vault, and then consumed by the application from Vault-backed Ansible variables.
- When HC Vault is not configured, required credentials must be supplied from Ansible Vault encrypted inventory variables. Do not add new plaintext generated-secret fallbacks.
- Tasks that read, generate, write, template, or compare secret material must use `no_log: true`.
- For `aap04.prd.dmz.corp.l-it.io`, the HC Vault KV v2 mount is `stage-2c`. Store the generated application secrets at these exact paths, or provide the listed variables from Ansible Vault when HC Vault is not in use:

| Component | HC Vault path under `stage-2c` | Ansible Vault variables / keys |
|---|---|---|
| AAP admin passwords | `aap04.prd.dmz.corp.l-it.io/aap/deploy/admin_passwords` | `aap_gateway_admin_password_input`, `aap_controller_admin_password_input`, `aap_hub_admin_password_input`, `aap_eda_admin_password_input`, `aap_postgresql_admin_password_input`, `aap_breakglass_password_input` / `gateway_admin_password`, `controller_admin_password`, `hub_admin_password`, `eda_admin_password`, `postgresql_admin_password`, `breakglass_password` |
| AAP deploy defaults | `defaults` | `rh_offline_token` / `rh_offline_token`, `offline_token`, `token`, `RH_AUTOMATION_HUB_TOKEN` |
| AAP TLS PKI AppRole | `aap04.prd.dmz.corp.l-it.io/aap/approle-pki` | `aap_deploy_tls_vault_pki_role_id`, `aap_deploy_tls_vault_pki_secret_id` / `role_id`, `secret_id` |
