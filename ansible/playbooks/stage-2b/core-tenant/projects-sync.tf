resource "gitlab_project" "dc_projects_bfarm_fdz_helm_demoapp" {
    name = "demoapp"
    namespace_id = gitlab_group.helm.id
    visibility_level = "internal"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/helm/demoapp.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_helm_image_mirror_sets" {
    name = "image-mirror-sets"
    namespace_id = gitlab_group.helm.id
    visibility_level = "internal"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/helm/image-mirror-sets.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_ansible_roles_terragrunt" {
    name = "terragrunt"
    namespace_id = gitlab_group.ansible_roles.id
    visibility_level = "internal"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/ansible-roles/terragrunt.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_ansible_roles_artifactory" {
    name = "artifactory"
    namespace_id = gitlab_group.ansible_roles.id
    visibility_level = "internal"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/ansible-roles/artifactory.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_helm_ibm_storage_fusion_operator" {
    name = "ibm-storage-fusion-operator"
    namespace_id = gitlab_group.helm.id
    visibility_level = "internal"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/helm/ibm-storage-fusion-operator.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_helm_ibm_storage_fusion_instance" {
    name = "ibm-storage-fusion-instance"
    namespace_id = gitlab_group.helm.id
    visibility_level = "internal"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/helm/ibm-storage-fusion-instance.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_helm_openshift_ingressoperatorpatch" {
    name = "openshift-ingressOperatorPatch"
    namespace_id = gitlab_group.helm.id
    visibility_level = "internal"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/helm/openshift-ingressoperatorpatch.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_ansible_roles_gitlab_sync" {
    name = "gitlab-sync"
    namespace_id = gitlab_group.ansible_roles.id
    visibility_level = "internal"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/ansible-roles/gitlab-sync.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_ansible_inventories_vintdevkub005_fdz_internal" {
    name = "vintdevkub005.fdz.internal"
    namespace_id = gitlab_group.ansible_inventories.id
    visibility_level = "private"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/ansible-inventories/vintdevkub005.fdz.internal.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_ansible_inventories_vintdevkub004_fdz_internal" {
    name = "vintdevkub004.fdz.internal"
    namespace_id = gitlab_group.ansible_inventories.id
    visibility_level = "private"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/ansible-inventories/vintdevkub004.fdz.internal.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_ansible_inventories_vintdevkub003_fdz_internal" {
    name = "vintdevkub003.fdz.internal"
    namespace_id = gitlab_group.ansible_inventories.id
    visibility_level = "private"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/ansible-inventories/vintdevkub003.fdz.internal.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_ansible_inventories_vdmzprdkub021_fdz_internal" {
    name = "vdmzprdkub021.fdz.internal"
    namespace_id = gitlab_group.ansible_inventories.id
    visibility_level = "private"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/ansible-inventories/vdmzprdkub021.fdz.internal.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_ansible_inventories_vdmzprekub020_fdz_internal" {
    name = "vdmzprekub020.fdz.internal"
    namespace_id = gitlab_group.ansible_inventories.id
    visibility_level = "private"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/ansible-inventories/vdmzprekub020.fdz.internal.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_ansible_inventories_vdmzqaskub019_fdz_internal" {
    name = "vdmzqaskub019.fdz.internal"
    namespace_id = gitlab_group.ansible_inventories.id
    visibility_level = "private"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/ansible-inventories/vdmzqaskub019.fdz.internal.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_terraform_gitlab_ee" {
    name = "gitlab-ee"
    namespace_id = gitlab_group.terraform.id
    visibility_level = "internal"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/terraform/gitlab-ee.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_helm_gitlab_runner_instance" {
    name = "gitlab-runner-instance"
    namespace_id = gitlab_group.helm.id
    visibility_level = "internal"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/helm/gitlab-runner-instance.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_helm_gitlab_runner_operator" {
    name = "gitlab-runner-operator"
    namespace_id = gitlab_group.helm.id
    visibility_level = "internal"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/helm/gitlab-runner-operator.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_helm_openshift_cert_manager_cluster_issuer_lets_encrypt" {
    name = "openshift-cert-manager-cluster-issuer-lets-encrypt"
    namespace_id = gitlab_group.helm.id
    visibility_level = "internal"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/helm/openshift-cert-manager-cluster-issuer-lets-encrypt.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_ansible_inventories_de01_core_corp_l_it_io" {
    name = "de01.core.corp.l-it.io"
    namespace_id = gitlab_group.ansible_inventories.id
    visibility_level = "internal"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/ansible-inventories/de01.core.corp.l-it.io.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_ansible_roles_os_rhel_desktop" {
    name = "os_rhel_desktop"
    namespace_id = gitlab_group.ansible_roles.id
    visibility_level = "internal"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/ansible-roles/os_rhel_desktop.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_cluster_configs" {
    name = "cluster-configs "
    namespace_id = gitlab_group.bfarm_fdz.id
    visibility_level = "internal"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/cluster-configs.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_ansible_inventories_vintdevkub002_fdz_internal" {
    name = "vintdevkub002.fdz.internal"
    namespace_id = gitlab_group.ansible_inventories.id
    visibility_level = "private"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/ansible-inventories/vintdevkub002.fdz.internal.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_ansible_inventories_sapdi01_core_corp_l_it_io" {
    name = "sapdi01.core.corp.l-it.io"
    namespace_id = gitlab_group.ansible_inventories.id
    visibility_level = "internal"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/ansible-inventories/sapdi01.core.corp.l-it.io.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_ansible_roles_dnsmasq" {
    name = "dnsmasq"
    namespace_id = gitlab_group.ansible_roles.id
    visibility_level = "internal"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/ansible-roles/dnsmasq.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_helm_vault_instance" {
    name = "vault-instance"
    namespace_id = gitlab_group.helm.id
    visibility_level = "internal"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/helm/vault-instance.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_helm_vault_operator" {
    name = "vault-operator"
    namespace_id = gitlab_group.helm.id
    visibility_level = "internal"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/helm/vault-operator.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_ansible_roles_chrony" {
    name = "chrony"
    namespace_id = gitlab_group.ansible_roles.id
    visibility_level = "internal"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/ansible-roles/chrony.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_helm_openshift_cert_manager_cluster_issuer" {
    name = "openshift-cert-manager-cluster-issuer"
    namespace_id = gitlab_group.helm.id
    visibility_level = "internal"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/helm/openshift-cert-manager-cluster-issuer.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_helm_artifactory_preparation" {
    name = "artifactory-preparation"
    namespace_id = gitlab_group.helm.id
    visibility_level = "internal"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/helm/artifactory-preparation.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_helm_artifactory" {
    name = "artifactory"
    namespace_id = gitlab_group.helm.id
    visibility_level = "internal"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/helm/artifactory.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_helm_cloudnativepg_instance" {
    name = "cloudnativepg-instance"
    namespace_id = gitlab_group.helm.id
    visibility_level = "internal"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/helm/cloudnativepg-instance.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_helm_cloudnativepg_operator" {
    name = "cloudnativepg-operator"
    namespace_id = gitlab_group.helm.id
    visibility_level = "internal"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/helm/cloudnativepg-operator.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_helm_package_registry" {
    name = "package-registry"
    namespace_id = gitlab_group.helm.id
    visibility_level = "internal"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/helm/package-registry.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_ansible_inventories_dg01_test_corp_l_it_io" {
    name = "dg01.test.corp.l-it.io"
    namespace_id = gitlab_group.ansible_inventories.id
    visibility_level = "internal"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/ansible-inventories/dg01.test.corp.l-it.io.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_container_images_rhel9_nodejs_20" {
    name = "rhel9-nodejs-20"
    namespace_id = gitlab_group.container_images.id
    visibility_level = "internal"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/container-images/rhel9-nodejs-20.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_container_images_ansible_builder_rhel9" {
    name = "ansible-builder-rhel9"
    namespace_id = gitlab_group.container_images.id
    visibility_level = "internal"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/container-images/ansible-builder-rhel9.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_ansible_inventories_vdmzdevkub018_fdz_internal" {
    name = "vdmzdevkub018.fdz.internal"
    namespace_id = gitlab_group.ansible_inventories.id
    visibility_level = "private"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/ansible-inventories/vdmzdevkub018.fdz.internal.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_helm_ibm_marketplace" {
    name = "ibm-marketplace"
    namespace_id = gitlab_group.helm.id
    visibility_level = "internal"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/helm/ibm-marketplace.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_argocd_ibm_storage_fusion_services" {
    name = "ibm-storage-fusion-services"
    namespace_id = gitlab_group.argocd.id
    visibility_level = "internal"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/argocd/ibm-storage-fusion-services.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_helm_sapdi_registry" {
    name = "sapdi-registry"
    namespace_id = gitlab_group.helm.id
    visibility_level = "internal"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/helm/sapdi-registry.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_helm_sapdi_observer" {
    name = "sapdi-observer"
    namespace_id = gitlab_group.helm.id
    visibility_level = "internal"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/helm/sapdi-observer.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_helm_sapdi_node_configurator" {
    name = "sapdi-node-configurator"
    namespace_id = gitlab_group.helm.id
    visibility_level = "internal"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/helm/sapdi-node-configurator.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_argocd_loki" {
    name = "loki"
    namespace_id = gitlab_group.argocd.id
    visibility_level = "internal"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/argocd/loki.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_ansible_inventories_vcomprdkub001_fdz_internal" {
    name = "vcomprdkub001.fdz.internal"
    namespace_id = gitlab_group.ansible_inventories.id
    visibility_level = "private"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/ansible-inventories/vcomprdkub001.fdz.internal.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_helm_ocp_oauth_htpasswd" {
    name = "ocp-oauth-htpasswd"
    namespace_id = gitlab_group.helm.id
    visibility_level = "internal"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/helm/ocp-oauth-htpasswd.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_argocd_rhbk_instance" {
    name = "rhbk-instance"
    namespace_id = gitlab_group.argocd.id
    visibility_level = "internal"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/argocd/rhbk-instance.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_argocd_ibm_storage_fusion" {
    name = "old_ibm_storage_fusion"
    namespace_id = gitlab_group.argocd.id
    visibility_level = "internal"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/argocd/ibm-storage-fusion.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_helm_rhbk_instance" {
    name = "rhbk-instance"
    namespace_id = gitlab_group.helm.id
    visibility_level = "internal"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/helm/rhbk-instance.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_ansible_inventories_fd01_prod_corp_l_it_io" {
    name = "fd01.prod.corp.l-it.io"
    namespace_id = gitlab_group.ansible_inventories.id
    visibility_level = "internal"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/ansible-inventories/fd01.prod.corp.l-it.io.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_argocd_ibm_spectrum_protect_plus" {
    name = "ibm-spectrum-protect-plus"
    namespace_id = gitlab_group.argocd.id
    visibility_level = "internal"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/argocd/ibm-spectrum-protect-plus.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_helm_openshift_cert_manager_operator" {
    name = "openshift-cert-manager-operator"
    namespace_id = gitlab_group.helm.id
    visibility_level = "internal"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/helm/openshift-cert-manager-operator.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_argocd_cert_manager_operator" {
    name = "cert-manager-operator"
    namespace_id = gitlab_group.argocd.id
    visibility_level = "internal"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/argocd/cert-manager-operator.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_argocd_crunchy_postgres" {
    name = "crunchy-postgres"
    namespace_id = gitlab_group.argocd.id
    visibility_level = "internal"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/argocd/crunchy-postgres.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_helm_crunchy_postgres_operator" {
    name = "crunchy-postgres-operator"
    namespace_id = gitlab_group.helm.id
    visibility_level = "internal"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/helm/crunchy-postgres-operator.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_helm_helper_status_checker" {
    name = "helper-status-checker"
    namespace_id = gitlab_group.helm.id
    visibility_level = "internal"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/helm/helper-status-checker.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_helm_helper_operator" {
    name = "helper-operator"
    namespace_id = gitlab_group.helm.id
    visibility_level = "internal"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/helm/helper-operator.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_helm_rhbk_operator" {
    name = "rhbk-operator"
    namespace_id = gitlab_group.helm.id
    visibility_level = "internal"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/helm/rhbk-operator.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_argocd_ocp4_compliance" {
    name = "ocp4-compliance"
    namespace_id = gitlab_group.argocd.id
    visibility_level = "internal"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/argocd/ocp4-compliance.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_argocd_vault_helm_community" {
    name = "vault-helm-community"
    namespace_id = gitlab_group.argocd.id
    visibility_level = "internal"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/argocd/vault-helm-community.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_argocd_xray" {
    name = "xray"
    namespace_id = gitlab_group.argocd.id
    visibility_level = "internal"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/argocd/xray.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_argocd_grafana" {
    name = "grafana"
    namespace_id = gitlab_group.argocd.id
    visibility_level = "internal"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/argocd/grafana.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_argocd_rhbk_operator" {
    name = "rhbk-operator"
    namespace_id = gitlab_group.argocd.id
    visibility_level = "internal"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/argocd/rhbk-operator.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_argocd_ocp_oauth_htpasswd" {
    name = "ocp-oauth-htpasswd"
    namespace_id = gitlab_group.argocd.id
    visibility_level = "internal"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/argocd/ocp-oauth-htpasswd.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_ansible_roles_gitops" {
    name = "gitops"
    namespace_id = gitlab_group.ansible_roles.id
    visibility_level = "internal"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/ansible-roles/gitops.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_terraform_artifactory_repos_users" {
    name = "artifactory_repos_users"
    namespace_id = gitlab_group.terraform.id
    visibility_level = "internal"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/terraform/artifactory_repos_users.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_terraform_gitlab_infra" {
    name = "gitlab-infra"
    namespace_id = gitlab_group.terraform.id
    visibility_level = "internal"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/terraform/gitlab-infra.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_ansible_roles_haproxy" {
    name = "haproxy"
    namespace_id = gitlab_group.ansible_roles.id
    visibility_level = "internal"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/ansible-roles/haproxy.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_helm_gitlab_ee" {
    name = "gitlab-ee"
    namespace_id = gitlab_group.helm.id
    visibility_level = "internal"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/helm/gitlab-ee.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_ansible_roles_certmanager" {
    name = "certmanager"
    namespace_id = gitlab_group.ansible_roles.id
    visibility_level = "internal"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/ansible-roles/certmanager.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_ansible_roles_user_management_fdz" {
    name = "user-management-fdz"
    namespace_id = gitlab_group.ansible_roles.id
    visibility_level = "internal"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/ansible-roles/user-management-fdz.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_ansible_roles_os_rhel_base_fdz" {
    name = "os-rhel-base-fdz"
    namespace_id = gitlab_group.ansible_roles.id
    visibility_level = "internal"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/ansible-roles/os-rhel-base-fdz.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_ansible_inventories_fdz_internal" {
    name = "fdz.internal"
    namespace_id = gitlab_group.ansible_inventories.id
    visibility_level = "internal"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/ansible-inventories/fdz.internal.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_ansible_inventories_vdmzprdkub025_fdz_internal" {
    name = "vdmzprdkub025.fdz.internal"
    namespace_id = gitlab_group.ansible_inventories.id
    visibility_level = "internal"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/ansible-inventories/vdmzprdkub025.fdz.internal.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_ansible_inventories_vdmzdevkub026_fdz_internal" {
    name = "vdmzdevkub026.fdz.internal"
    namespace_id = gitlab_group.ansible_inventories.id
    visibility_level = "internal"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/ansible-inventories/vdmzdevkub026.fdz.internal.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_argocd_prometheus_operator" {
    name = "prometheus-operator"
    namespace_id = gitlab_group.argocd.id
    visibility_level = "internal"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/argocd/prometheus-operator.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_ansible_inventories_jd01_test_corp_l_it_io" {
    name = "jd01.test.corp.l-it.io"
    namespace_id = gitlab_group.ansible_inventories.id
    visibility_level = "internal"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/ansible-inventories/jd01.test.corp.l-it.io.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_helm_gitlab_operator" {
    name = "gitlab-operator"
    namespace_id = gitlab_group.helm.id
    visibility_level = "internal"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/helm/gitlab-operator.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_ansible_inventories_fm01_prod_corp_l_it_io" {
    name = "fm01.prod.corp.l-it.io"
    namespace_id = gitlab_group.ansible_inventories.id
    visibility_level = "internal"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/ansible-inventories/fm01.prod.corp.l-it.io.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_ansible_inventories_tk01_dev_corp_l_it_io" {
    name = "tk01.dev.corp.l-it.io"
    namespace_id = gitlab_group.ansible_inventories.id
    visibility_level = "internal"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/ansible-inventories/tk01.dev.corp.l-it.io.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_argocd_app_of_apps" {
    name = "app-of-apps"
    namespace_id = gitlab_group.argocd.id
    visibility_level = "internal"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/argocd/app-of-apps.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_ansible_inventories_nightly01_dev_corp_l_it_io" {
    name = "nightly01.dev.corp.l-it.io"
    namespace_id = gitlab_group.ansible_inventories.id
    visibility_level = "internal"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/ansible-inventories/nightly01.dev.corp.l-it.io.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_ansible_roles_ocp_gitlab" {
    name = "ocp-gitlab"
    namespace_id = gitlab_group.ansible_roles.id
    visibility_level = "internal"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/ansible-roles/ocp_gitlab.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_ansible_roles_rhsso" {
    name = "rhsso"
    namespace_id = gitlab_group.ansible_roles.id
    visibility_level = "internal"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/ansible-roles/rhsso.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_ansible_roles_os_windows_server_base" {
    name = "os-windows_server-base"
    namespace_id = gitlab_group.ansible_roles.id
    visibility_level = "internal"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/ansible-roles/os-windows_server-base.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_ansible_roles_gitlab_runner_omnibus" {
    name = "gitlab-runner-omnibus"
    namespace_id = gitlab_group.ansible_roles.id
    visibility_level = "internal"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/ansible-roles/gitlab-runner-omnibus.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_ansible_roles_os_rhel_base" {
    name = "os-rhel-base"
    namespace_id = gitlab_group.ansible_roles.id
    visibility_level = "internal"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/ansible-roles/os-rhel-base.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_ansible_inventories_mgmt01_core_corp_l_it_io" {
    name = "mgmt01.core.corp.l-it.io"
    namespace_id = gitlab_group.ansible_inventories.id
    visibility_level = "internal"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/ansible-inventories/mgmt01.core.corp.l-it.io.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_ansible_roles_active_directory" {
    name = "active-directory"
    namespace_id = gitlab_group.ansible_roles.id
    visibility_level = "internal"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/ansible-roles/active-directory.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_ansible_roles_gitlab_omnibus" {
    name = "gitlab-omnibus"
    namespace_id = gitlab_group.ansible_roles.id
    visibility_level = "internal"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/ansible-roles/gitlab-omnibus.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_ansible_roles_squid" {
    name = "squid"
    namespace_id = gitlab_group.ansible_roles.id
    visibility_level = "internal"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/ansible-roles/squid.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_ansible_roles_ocp_local_user" {
    name = "ocp-local-user"
    namespace_id = gitlab_group.ansible_roles.id
    visibility_level = "private"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/ansible-roles/ocp-local-user.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_ansible_roles_manage_vcenter" {
    name = "manage-vcenter"
    namespace_id = gitlab_group.ansible_roles.id
    visibility_level = "internal"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/ansible-roles/manage-vcenter.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_ansible_inventories_core_corp_l_it_io" {
    name = "core.corp.l-it.io"
    namespace_id = gitlab_group.ansible_inventories.id
    visibility_level = "internal"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/ansible-inventories/core.corp.l-it.io.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_ansible_roles_redfish" {
    name = "redfish"
    namespace_id = gitlab_group.ansible_roles.id
    visibility_level = "internal"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/ansible-roles/redfish.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_ansible_roles_argocd" {
    name = "argocd"
    namespace_id = gitlab_group.ansible_roles.id
    visibility_level = "private"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/ansible-roles/argocd.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_ansible_roles_infra_nodes" {
    name = "infra-nodes"
    namespace_id = gitlab_group.ansible_roles.id
    visibility_level = "private"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/ansible-roles/infra-nodes.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_ansible_roles_manage_esxi" {
    name = "manage-esxi"
    namespace_id = gitlab_group.ansible_roles.id
    visibility_level = "internal"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/ansible-roles/manage-esxi.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_ansible_playbooks_infra" {
    name = "infra"
    namespace_id = gitlab_group.ansible_playbooks.id
    visibility_level = "internal"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/ansible-playbooks/infra.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_ansible_roles_odf" {
    name = "odf"
    namespace_id = gitlab_group.ansible_roles.id
    visibility_level = "private"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/ansible-roles/odf.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_ansible_inventories_jd01_bechtle_poc_corp_l_it_io" {
    name = "jd01.bechtle.poc.corp.l-it.io"
    namespace_id = gitlab_group.ansible_inventories.id
    visibility_level = "internal"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/ansible-inventories/jd01.bechtle.poc.corp.l-it.io.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_ansible_inventories_tk01_bechtle_poc_corp_l_it_io" {
    name = "tk01.bechtle.poc.corp.l-it.io"
    namespace_id = gitlab_group.ansible_inventories.id
    visibility_level = "private"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/ansible-inventories/tk01.bechtle.poc.corp.l-it.io.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_ansible_inventories_default_inventory" {
    name = "default-inventory"
    namespace_id = gitlab_group.ansible_inventories.id
    visibility_level = "internal"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/ansible-inventories/default-inventory.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_ansible_inventories_fm01_bechtle_poc_corp_l_it_io" {
    name = "fm01.bechtle.poc.corp.l-it.io"
    namespace_id = gitlab_group.ansible_inventories.id
    visibility_level = "internal"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/ansible-inventories/fm01.bechtle.poc.corp.l-it.io.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_ansible_playbooks_ocp4" {
    name = "ocp4"
    namespace_id = gitlab_group.ansible_playbooks.id
    visibility_level = "internal"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/ansible-playbooks/ocp4.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_ansible_roles_bastion_prepare" {
    name = "bastion-prepare"
    namespace_id = gitlab_group.ansible_roles.id
    visibility_level = "private"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/ansible-roles/bastion-prepare.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_ansible_roles_jfrog_artifactory" {
    name = "jfrog-artifactory"
    namespace_id = gitlab_group.ansible_roles.id
    visibility_level = "private"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/ansible-roles/jfrog-artifactory.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_ansible_roles_vmware_vsphere" {
    name = "vmware-vsphere"
    namespace_id = gitlab_group.ansible_roles.id
    visibility_level = "internal"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/ansible-roles/vmware-vsphere.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_ansible_roles_nginx" {
    name = "nginx"
    namespace_id = gitlab_group.ansible_roles.id
    visibility_level = "internal"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/ansible-roles/nginx.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_ansible_roles_user_management" {
    name = "user-management"
    namespace_id = gitlab_group.ansible_roles.id
    visibility_level = "internal"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/ansible-roles/user-management.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_ansible_roles_sshd" {
    name = "sshd"
    namespace_id = gitlab_group.ansible_roles.id
    visibility_level = "internal"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/ansible-roles/sshd.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_ansible_roles_ocp4_vsphere_upi" {
    name = "ocp4-vsphere-upi"
    namespace_id = gitlab_group.ansible_roles.id
    visibility_level = "internal"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/ansible-roles/ocp4-vsphere-upi.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_ci_templates_release_process" {
    name = "release-process"
    namespace_id = gitlab_group.ci_templates.id
    visibility_level = "internal"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/ci-templates/release-process.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
resource "gitlab_project" "dc_projects_bfarm_fdz_container_images_ansible_ee" {
    name = "ansible-ee"
    namespace_id = gitlab_group.container_images.id
    visibility_level = "internal"
    import_url = "https://gitlab.bechtlab.de/dc-projects/bfarm-fdz/container-images/ansible-ee.git"
    mirror = true
    import_url_username = var.git_import_user
    import_url_password = var.git_import_pass
    mirror_overwrites_diverged_branches = true
    mirror_trigger_builds = true
    depends_on = [gitlab_application_settings.app-settings]
}
