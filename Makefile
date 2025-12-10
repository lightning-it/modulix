.PHONY: lint test test-ansible deploy-keycloak

WUNDER ?= ./scripts/wunder-devtools-ee.sh

lint:
	$(WUNDER) sh -c "pip install -q pre-commit && pre-commit run --all-files"

test: test-ansible

test-ansible:
	$(WUNDER) ./scripts/test-ansible.sh

# Lightweight connectivity check for the Keycloak inventory.
# Adjust the inventory and playbook paths as needed for real deployments.
deploy-keycloak:
	$(WUNDER) ansible-playbook \
		-i ansible/inventories/poc/hosts.yml \
		ansible/playbooks/keycloak.yml
