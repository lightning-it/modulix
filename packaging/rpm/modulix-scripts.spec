%global modulix_version %{?_modulix_version:%{_modulix_version}}%{!?_modulix_version:0.1.0}
%global modulix_release %{?_modulix_release:%{_modulix_release}}%{!?_modulix_release:1}

Name:           modulix-scripts
Version:        %{modulix_version}
Release:        %{modulix_release}%{?dist}
Summary:        ModuLix helper scripts for toolbox workflows
License:        GPL-2.0-only
URL:            https://github.com/lightning-it/modulix
Source0:        modulix-%{version}.tar.gz
BuildArch:      noarch

Requires:       bash
Requires:       git

%description
Command-line helper scripts from the ModuLix repository packaged for
RHEL-compatible systems.

The scripts are installed under /opt/modulix and exposed via wrapper commands
in %{_bindir}.

%prep
%autosetup -n modulix-%{version}

%build
# Nothing to build for script-only packaging.

%install
rm -rf %{buildroot}

install -d %{buildroot}/opt/modulix
cp -a scripts %{buildroot}/opt/modulix/
install -d %{buildroot}/opt/modulix/ansible
cp -a ansible/scripts %{buildroot}/opt/modulix/ansible/

# Ensure script payload is executable.
find %{buildroot}/opt/modulix -type f -name '*.sh' -exec chmod 0755 {} \;
chmod 0755 %{buildroot}/opt/modulix/scripts/git/pre-commit-devtools
chmod 0755 %{buildroot}/opt/modulix/ansible/scripts/ansible-nav
chmod 0755 %{buildroot}/opt/modulix/ansible/scripts/ansible-nav-local
chmod 0755 %{buildroot}/opt/modulix/ansible/scripts/install-local-collections

install -d %{buildroot}%{_bindir}

cat > %{buildroot}%{_bindir}/ansible-nav <<'EOF'
#!/usr/bin/env bash
exec /opt/modulix/ansible/scripts/ansible-nav "$@"
EOF

cat > %{buildroot}%{_bindir}/ansible-nav-local <<'EOF'
#!/usr/bin/env bash
exec /opt/modulix/ansible/scripts/ansible-nav-local "$@"
EOF

cat > %{buildroot}%{_bindir}/install-local-collections <<'EOF'
#!/usr/bin/env bash
exec /opt/modulix/ansible/scripts/install-local-collections "$@"
EOF

cat > %{buildroot}%{_bindir}/test-ansible.sh <<'EOF'
#!/usr/bin/env bash
exec /opt/modulix/scripts/test-ansible.sh "$@"
EOF

cat > %{buildroot}%{_bindir}/wunder-devtools-ee.sh <<'EOF'
#!/usr/bin/env bash
exec /opt/modulix/scripts/wunder-devtools-ee.sh "$@"
EOF

cat > %{buildroot}%{_bindir}/pre-commit-devtools <<'EOF'
#!/usr/bin/env bash
exec /opt/modulix/scripts/git/pre-commit-devtools "$@"
EOF

cat > %{buildroot}%{_bindir}/clone-all.sh <<'EOF'
#!/usr/bin/env bash
exec /opt/modulix/scripts/github/clone-all.sh "$@"
EOF

chmod 0755 \
  %{buildroot}%{_bindir}/ansible-nav \
  %{buildroot}%{_bindir}/ansible-nav-local \
  %{buildroot}%{_bindir}/install-local-collections \
  %{buildroot}%{_bindir}/test-ansible.sh \
  %{buildroot}%{_bindir}/wunder-devtools-ee.sh \
  %{buildroot}%{_bindir}/pre-commit-devtools \
  %{buildroot}%{_bindir}/clone-all.sh

%files
%license LICENSE
%doc README.md scripts/README.md
%{_bindir}/ansible-nav
%{_bindir}/ansible-nav-local
%{_bindir}/install-local-collections
%{_bindir}/test-ansible.sh
%{_bindir}/wunder-devtools-ee.sh
%{_bindir}/pre-commit-devtools
%{_bindir}/clone-all.sh
/opt/modulix

%changelog
* Thu Feb 19 2026 Lightning IT <opensource@l-it.io> - %{version}-%{release}
- Initial RPM packaging for ModuLix scripts.
