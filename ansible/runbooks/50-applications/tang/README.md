# Tang Runbooks

`10-deploy.yml` deploys and validates the inventory-enabled Tang service, then
persists its public signing thumbprint through the declared Vault contract
using a compare-and-set write. Existing, different trust material is never
silently replaced.

The current implementation supports Ubuntu 24.04 through
`lit.ubuntu.tang_deploy`. Firewall and DNS policy remain external
prerequisites.

## Trust lifecycle

1. Deploy Tang on the single inventory-selected endpoint.
2. Review the signing thumbprint returned by `lit.ubuntu.tang_deploy` through a
   trusted channel.
3. Persist the public thumbprint in the declared HashiCorp Vault KV v2 record.
4. Back up and escrow each client LUKS header before adding a Clevis keyslot.
5. Bind the exact Tang URL and pinned thumbprint.
6. Run `30-operating-systems/ubuntu/24/19-tang-reboot-acceptance.yml` for one
   separately confirmed non-Tang client.

The reboot acceptance downloads the live advertisement, calculates its
verification-key thumbprints with the JOSE tooling installed alongside
Clevis, and requires the live key, Vault pin, and LUKS binding to agree before
reboot. It then proves a new boot returned on managed OpenSSH and that the
Dropbear recovery listener is closed.

Tang advertisement and thumbprints are public trust material; the private
Tang database is not. Never copy `/var/db/tang` into inventory, logs, or the
controller workspace. Key rotation requires a reviewed overlap plan and new
client bindings before an old signing key is retired.

## Failure and recovery

- A deployment or CAS failure leaves the previous Vault trust document
  authoritative. Resolve the failure and rerun; do not force an overwrite.
- A live-advertisement mismatch blocks reboot. Investigate DNS, routing, and
  Tang key rotation before changing any client keyslot.
- A reboot timeout is a failed automatic-unlock acceptance. Recover with the
  independently escrowed passphrase through Dropbear, then repair the binding
  without weakening the pinned trust check.
