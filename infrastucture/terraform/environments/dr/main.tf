# infrastructure/terraform/environments/dr/main.tf

terraform {
  backend "azurerm" {
    resource_group_name  = "terraform-state-dr-rg"
    storage_account_name = "terraformstatedrsa"
    container_name       = "tfstate"
    key                 = "dr/terraform.tfstate"
  }
}

provider "azurerm" {
  features {}
  subscription_id = var.dr_subscription_id
  tenant_id       = var.tenant_id
}

module "dr_networking" {
  source = "../../modules/networking"
  
  environment = "dr"
  location    = var.dr_location
  vnet_cidr   = "10.128.0.0/9"  # Different CIDR from primary
  
  subnets = {
    "aks" = "10.128.0.0/16"
    "database" = "10.129.0.0/16"
    "cache" = "10.130.0.0/16"
  }
  
  tags = {
    Environment = "dr"
    ManagedBy   = "Terraform"
    DRFor       = "production"
  }
}

module "dr_database" {
  source = "../../modules/database"
  
  environment         = "dr"
  resource_group_name = module.dr_networking.resource_group_name
  subnet_id          = module.dr_networking.subnet_ids["database"]
  
  postgres_config = {
    sku_name   = "GP_Standard_D4s_v3"
    storage_mb = 1024000
    db_version = "13"
    
    backup_retention_days = 7
    geo_redundant_backup_enabled = false
    
    # Configure as replica of production
    create_mode = "Replica"
    source_server_id = var.prod_postgres_id
  }
  
  redis_config = {
    capacity    = 1
    family      = "P"
    sku_name    = "Premium"
    
    redis_version = "6"
    
    # Configure as replica
    replica_of = var.prod_redis_primary_connection_string
  }
  
  tags = module.dr_networking.tags
}

module "dr_kubernetes" {
  source = "../../modules/kubernetes"
  
  cluster_name        = "security-orchestrator-dr"
  location            = module.dr_networking.location
  resource_group_name = module.dr_networking.resource_group_name
  dns_prefix         = "security-dr"
  
  kubernetes_version = var.dr_kubernetes_version
  
  default_node_count = 2
  min_node_count     = 2
  max_node_count     = 5
  
  worker_node_size   = "Standard_D8s_v3"
  worker_node_count  = 3
  worker_min_count   = 3
  worker_max_count   = 10
  
  tags = module.dr_networking.tags
}

# Outputs for failover
output "dr_kube_config" {
  value     = module.dr_kubernetes.kube_config
  sensitive = true
}

output "dr_database_connection" {
  value = module.dr_database.connection_string
  sensitive = true
}