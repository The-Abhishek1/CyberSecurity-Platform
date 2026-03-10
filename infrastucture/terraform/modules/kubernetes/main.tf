# infrastructure/terraform/modules/kubernetes/main.tf

resource "azurerm_kubernetes_cluster" "aks" {
  name                = var.cluster_name
  location            = var.location
  resource_group_name = var.resource_group_name
  dns_prefix          = var.dns_prefix
  
  kubernetes_version = var.kubernetes_version
  
  default_node_pool {
    name       = "default"
    node_count = var.default_node_count
    vm_size    = var.default_node_size
    
    enable_auto_scaling = var.enable_auto_scaling
    min_count          = var.min_node_count
    max_count          = var.max_node_count
    
    node_labels = {
      "role" = "system"
    }
    
    node_taints = []
  }
  
  identity {
    type = "SystemAssigned"
  }
  
  network_profile {
    network_plugin = "azure"
    network_policy = "calico"
    dns_service_ip = "10.0.0.10"
    service_cidr   = "10.0.0.0/16"
  }
  
  oms_agent {
    log_analytics_workspace_id = var.log_analytics_workspace_id
  }
  
  azure_active_directory_role_based_access_control {
    managed            = true
    azure_rbac_enabled = true
  }
  
  ingress_application_gateway {
    gateway_id = var.app_gateway_id
  }
  
  key_vault_secrets_provider {
    secret_rotation_enabled = true
  }
  
  tags = var.tags
}

resource "azurerm_kubernetes_cluster_node_pool" "worker" {
  name                  = "worker"
  kubernetes_cluster_id = azurerm_kubernetes_cluster.aks.id
  vm_size              = var.worker_node_size
  node_count           = var.worker_node_count
  
  enable_auto_scaling = true
  min_count          = var.worker_min_count
  max_count          = var.worker_max_count
  
  node_labels = {
    "role" = "worker"
    "node-type" = "compute"
  }
  
  node_taints = []
  
  tags = var.tags
}

# Outputs
output "cluster_id" {
  value = azurerm_kubernetes_cluster.aks.id
}

output "cluster_name" {
  value = azurerm_kubernetes_cluster.aks.name
}

output "kube_config" {
  value     = azurerm_kubernetes_cluster.aks.kube_config_raw
  sensitive = true
}