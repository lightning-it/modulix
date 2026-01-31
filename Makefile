# Makefile for local CI-like workflows around ModuLix / Keycloak

# Path to your devtools wrapper
WUNDER_DEVTOOLS := ./scripts/container-ee-wunder-devtools-ubi9.sh

# Ansible paths
ANSIBLE_PLAYBOOK   := ansible/playbooks/keycloak.yml
# Default to nightly inventory; override with ANSIBLE_INVENTORY=... (e.g. demo) on the CLI
ANSIBLE_INVENTORY ?= ansible/inventories/nightly/hosts.yml

.PHONY: help lint lint-yaml ssh-setup configure-keycloak deploy-keycloak ci

help:
	@echo "ModuLix Makefile"
	@echo
	@echo "Targets:"
	@echo "  lint             Run YAML lint on inventories, group_vars and playbooks via wunder-devtools"
	@echo "  lint-yaml        Run yamllint on ansible/group_vars, ansible/inventories, ansible/playbooks"
	@echo "  configure-keycloak  Run lint and then configure Keycloak via keycloak_config role (default: nightly)"
	@echo "  ssh-setup        Write SSH keys from env to ~/.ssh (for future SSH-based roles)"
	@echo "  ci               Run lint and (optionally) other CI-like checks"
	@echo
	@echo "Environment:"
	@echo "  ANSIBLE_INVENTORY   Inventory file to use (default: $(ANSIBLE_INVENTORY))"
	@echo "                       e.g. ansible/inventories/demo/hosts.yml"
	@echo "  SSH_PRIVATE_KEY     Private key for Ansible SSH (used by ssh-setup / future roles)"
	@echo "  SSH_KNOWN_HOSTS     Known hosts content (used by ssh-setup / future roles)"

# ---------------------------------------------------------------------------
# Linting
# ---------------------------------------------------------------------------

lint: lint-yaml ## Run all lint checks (YAML only)

lint-yaml: ## YAML lint via wunder-devtools (ansible directories)
	$(WUNDER_DEVTOOLS) yamllint ansible/group_vars ansible/inventories ansible/playbooks

# ---------------------------------------------------------------------------
# SSH Setup (for SSH-based roles, e.g. Satellite later)
# ---------------------------------------------------------------------------

ssh-setup: ## Write SSH keys from env to ~/.ssh
	@test -n "$$SSH_PRIVATE_KEY" || (echo "ERROR: SSH_PRIVATE_KEY is not set"; exit 1)
	@test -n "$$SSH_KNOWN_HOSTS" || (echo "ERROR: SSH_KNOWN_HOSTS is not set"; exit 1)
	@install -m 700 -d $$HOME/.ssh
	@printf '%s\n' "$$SSH_PRIVATE_KEY" > $$HOME/.ssh/id_rsa
	@chmod 600 $$HOME/.ssh/id_rsa
	@printf '%s\n' "$$SSH_KNOWN_HOSTS" > $$HOME/.ssh/known_hosts

# ---------------------------------------------------------------------------
# Configure Keycloak (nightly by default)
# ---------------------------------------------------------------------------

configure-keycloak: lint ## Run lint + configure Keycloak via keycloak_config role
	@echo ">>> Configuring Keycloak via $(ANSIBLE_PLAYBOOK) against inventory $(ANSIBLE_INVENTORY)"
	$(WUNDER_DEVTOOLS) sh -c ' \
	  ansible-galaxy collection install \
	    git+https://github.com/lightning-it/ansible-collection-supplementary.git,ro/role-keycloak && \
	  ansible-playbook -i $(ANSIBLE_INVENTORY) $(ANSIBLE_PLAYBOOK) \
	'

# ---------------------------------------------------------------------------
# CI wrapper
# ---------------------------------------------------------------------------

ci: lint ## CI-like entrypoint (extend as needed)
	@echo "CI checks finished (lint). Add more steps to 'ci' if needed."
