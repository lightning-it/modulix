# Wunderbox governed execution binding

`root-of-trust-policy.json` is the public, environment-neutral Recorder-v3
action contract for one Wunderbox Root-of-Trust build. Its top-level schema is
exact: it declares the policy identity, required repositories and collections,
the collection-to-repository mapping, target contract, projection-contract
descriptor and action matrix. It no longer contains signing configuration or
environment-specific topology. The projection descriptor contains only the
authorized inventory repository, a canonical relative path and an exact
SHA-256. The recorder loads the corresponding private contract exclusively
from the authorized read-only inventory snapshot, validates its closed schema,
requires its target and controller to match the signed manifest and rechecks
the exact bytes before every projection use. Policy action paths and contract
projection paths must match exactly.

The policy path, policy digest, manifest
signer, runtime-attestation signer and approval authority are pinned by the
root/admin-owned controller trust descriptor at
`/Library/Application Support/Lightning IT/Governed Ansible/controller-trust.json`;
an adapter caller cannot replace them.

The adapter executes only the fixed root-owned launcher at
`/Library/Application Support/Lightning IT/Governed Ansible/bin/governed-ansible-exec`.
That launcher must enter the root-owned, digest-pinned installed recorder with
the pinned absolute Python interpreter in isolated safe-path mode. The same
descriptor pins the Podman client, a root-owned local Unix socket by
device/inode, owner, group and mode, the normalized stable backend identity,
and a root-brokered append-only replay client and store ID. It also pins a
root-brokered process supervisor that owns every execution domain and must kill
escaped descendants as well as close inherited pipes at timeout. Volatile counters,
capacity and uptime from `podman info` are deliberately not identity fields. A
root-owned acceptance receipt must prove controller readback, a negative replay
test, bounded output and an escaped-descendant termination test. Until those external
anchors are installed and independently accepted, the adapter fails closed.

Each action fixes its record prefix, gate, impact, playbook or projection mode,
timeout, output bound, extra-variable contract and evidence prerequisites. Every
callback artifact that may be persisted has an exact schema which types every
projected field and binds target identity fields to the signed manifest. The
adapter `scripts/wbx-governed-exec.py` exposes no policy, allowed-signers,
target, inventory, playbook, gate, impact or arbitrary command option.

The WBX-G0 inventory projection uses payload schema version 3. In addition to
target, controller, identity and lifecycle, it carries the fully resolved,
secret-free effective-access contract: TCP 22/1905/2222 by function, mode and
source, matching provider and host-firewall semantics, Tang TCP/80 sources and
empty legacy aggregate lists. It also binds ADR-WBX-016 and WBX-EV-032: the
Installimage IPv4-only flag, CIS GRUB disable mode, IPv4-only Netplan render,
empty IPv6 sources/destinations and DNS AAAA set, active provider filtering,
no IPv6 provider rule and the assigned-but-unconfigured Hetzner `/64`. The
record also binds the exact absolute
snapshot `ansible-nav` path and its SHA-256; a consumer must compare both
against independently supplied pins and must not accept a matching suffix.

`gate-manifest.template.json` and the renderer use manifest schema version 2.
The runtime section binds only digest-pinned toolbox and run-EE images plus the
absolute path, SHA-256 and detached signature path of the separate runtime
attestation. That signed attestation records the source commits and measured
installed collection trees. Collection metadata stated only by the manifest is
not accepted as runtime provenance.

Both signed runtime-attestation roles also bind the effective Ansible loader:
only the two system collection roots are allowed and Python `sys.path`
collection scanning is disabled. Runtime probes read this effective loader
configuration inside the toolbox and run-EE before and after execution.

A real engagement manifest is created outside Git in an owner-only directory.
It binds the exact target/controller identity, all six frozen repository
commits, runtime attestation, gate states and one exact authorization entry for
every action. Unselected and blocked actions remain `NOT_APPROVED`. A selected
action additionally needs a time-bounded outer authorization and a separate,
cryptographically signed Foundational execution approval. The execution
approval binds the exact recorder execution ID, repository commits, target,
controller, action, policy, runtime and outer approval. Before Ansible starts,
the recorder must claim it through the descriptor-pinned root-brokered,
append-only replay store; the caller-controlled evidence directory is never an
authorization store.

The controller SSH contract binds one exact private-key digest and one
dedicated `known_hosts` digest. The recorder seals only those two files into
its private runtime tree, verifies them again at each phase boundary and passes
both expected digests through the outer wrapper and Navigator. Every staging
copy is checked before and after copying, and strict host-key checking plus
`IdentitiesOnly` is forced; the full SSH directory and agent are not accepted
as substitutes.

Signed approvals used by an Ansible consumer are a separate trust event. The
manifest contains only `consumer_approval_contracts[variable]` with the exact
operation, target and consumer binding. The corresponding signed transport is
supplied only through that action's owner-only extra-vars input. It uses a
different nonce and replay identity from the recorder execution approval. The
recorder verifies and claims every consumer approval through the pinned root
broker immediately before payload execution and then independently reads each
claim back through the broker. Local markers and consumer-only assertions are
not accepted as authorization evidence.

Run the renderer to produce the complete non-approved skeleton:

```bash
python3 scripts/render-wbx-gate-manifest-template.py
```

`controller-trust.template.json`, `runtime-attestation.template.json` and
`execution-anchor-acceptance.template.json` define the other exact external
contracts. They are deliberately non-accepted placeholders and must be
installed under root ownership, read back and independently accepted before
their digests are copied into the live descriptor or manifest.

The renderer adds exactly the evidence and authorization fields required by
each policy action. It gives every action a distinct placeholder execution ID
and nonce so reuse is visible, but it never signs or approves anything. The
output remains non-executable because `manifest_status` is `TEMPLATE`, safety
hold is enabled and every signature is an explicit replacement marker. Replace
all placeholders, independently review the resulting bytes and sign that exact
manifest according to the fixed controller trust descriptor.

The pinned Ansible toolbox and execution environment are Linux runtimes. They
cannot use the macOS 1Password Desktop CLI integration. A socket-only or
partially mounted bridge would leave an unverified trust transition. Therefore
the following seven actions remain fail-closed:

- `recovery_metadata_plan`
- `prepare_installimage_plan`
- `installimage_plan`
- `prepare_installimage_apply`
- `installimage_apply`
- `first_encrypted_boot`
- `bootstrap_unlock`

Six of these actions depend on the Desktop-integrated preparation or unlock
path and use
`blocked_missing_desktop_integrated_onepassword_controller_runtime`.
`installimage_apply` instead requires a dedicated secret-safe orchestrator and
uses
`dedicated_secret_safe_onepassword_installimage_orchestrator_missing`. The
actions remain in the policy as reviewed interface contracts, and the recorder
rejects them before gate, authorization or process evaluation. Syntax actions
remain available because they neither consume the Desktop session nor mutate an
external target.

The blockers may be removed only after independent review of a dedicated macOS
adapter which uses the authenticated Desktop integration without exposing
secrets to the Linux execution environment, or a separately signed bootstrap
phase whose output is a secret-free, integrity-bound Linux input. The
installimage consumer must resolve the exact pinned Password item without
returning the secret to an Ansible variable, fact, callback, file or command
argument.

`ansible/runbooks/00-common/controller/10-onepassword-runtime.yml` implements
the plan-first controller preparation for that separate bootstrap phase. It
copies one digest-pinned CLI into an inventory-selected root-owned path,
installs only the public approval signer document and creates the private
controller-owned consumer replay directory. It targets `localhost`, requires
one explicit inventory target as context and performs mutations only for the
explicit `apply` action. The runbook never authenticates to 1Password and never
reads, creates or transports an item. A successful run therefore prepares the
boundary but does not by itself clear any blocked action or advance a gate;
independent readback and acceptance remain mandatory.

Retries never reuse an execution ID, execution approval, consumer approval or
nonce. Increment the attempt from `001` to `002` and retain the earlier
Started/Result records, including interrupted or failed attempts. Recorder
outputs remain Candidate Evidence until independently reviewed and externally
anchored; they never advance a gate by themselves.
