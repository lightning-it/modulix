# aap_poc_inputs

Generates new installer-safe alphanumeric random AAP passwords and a placeholder PoC offline token only
when an explicitly approved encrypted output does not already exist. The role
immediately encrypts the owner-only YAML file with `ansible-vault` and creates
an empty public-registry authentication contract. It never rotates an existing
Vault file.
