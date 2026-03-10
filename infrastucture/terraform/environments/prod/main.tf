# infrastructure/terraform/environments/prod/main.tf

terraform {
  backend "azurerm" {
    resource_group_name  = "terraform-state-rg"
    storage_account_name = "terraformstatesa"
    container_name       = "tfstate"
    key                 = "prod/terraform.tfstate"
  }
}

provider "azurerm" {
  features {
    key_vault {
      purge_soft_delete_on_destroy = false
      recover_soft_deleted_key_vaults = true
    }
  }
}

module "networking" {
  source = "../../modules/networking"
  
  environment = "prod"
  vnet_cidr   = "10.0.0.0/8"
  
  subnets = {
    "aks" = "10.1.0.0/16"
    "database" = "10.2.0.0/16"
    "cache" = "10.3.0.0/16"
    "queue" = "10.4.0.0/16"
    "monitoring" = "10.5.0.0/16"
  }
  
  tags = {
    Environment = "production"
    ManagedBy   = "Terraform"
    CostCenter  = "Security"
  }
}

module "database" {
  source = "../../modules/database"
  
  environment         = "prod"
  resource_group_name = module.networking.resource_group_name
  subnet_id          = module.networking.subnet_ids["database"]
  
  postgres_config = {
    sku_name   = "GP_Standard_D4s_v3"
    storage_mb = 1024000
    db_version = "13"
    
    backup_retention_days = 35
    geo_redundant_backup_enabled = true
    
    high_availability = {
      mode = "ZoneRedundant"
    }
    
    replica_count = 2
  }
  
  redis_config = {
    capacity    = 3
    family      = "P"
    sku_name    = "Premium"
    shard_count = 3
    
    redis_version = "6"
    
    patch_schedule = [
      {
        day_of_week    = "Sunday"
        start_hour_utc = 2
      }
    ]
  }
  
  tags = module.networking.tags
}

module "kubernetes" {
  source = "../../modules/kubernetes"
  
  cluster_name          = "security-orchestrator-prod"
  location              = module.networking.location
  resource_group_name   = module.networking.resource_group_name
  dns_prefix           = "security-prod"
  
  kubernetes_version   = "1.28"
  
  default_node_count   = 3
  min_node_count       = 3
  max_node_count       = 10
  
  worker_node_size     = "Standard_D8s_v3"
  worker_node_count    = 10
  worker_min_count     = 5
  worker_max_count     = 50
  
  log_analytics_workspace_id = module.monitoring.workspace_id
  app_gateway_id             = module.networking.app_gateway_id
  
  tags = module.networking.tags
}

module "storage" {
  source = "../../modules/storage"
  
  environment       = "prod"
  resource_group_name = module.networking.resource_group_name
  
  blob_storage = {
    account_kind = "StorageV2"
    account_tier = "Premium"
    replication_type = "ZRS"
    
    containers = [
      "artifacts",
      "reports",
      "backups",
      "logs"
    ]
    
    lifecycle_policy = {
      "archive_after_days" = 90
      "delete_after_days"  = 365
    }
  }
  
  file_storage = {
    share_quota_gb = 5120
    shares = [
      "shared-data"
    ]
  }
  
  tags = module.networking.tags
}

module "monitoring" {
  source = "../../modules/monitoring"
  
  environment          = "prod"
  resource_group_name  = module.networking.resource_group_name
  subnet_id           = module.networking.subnet_ids["monitoring"]
  
  prometheus_config = {
    retention_days   = 30
    storage_size_gb  = 500
    scrape_interval  = "30s"
    evaluation_interval = "30s"
  }
  
  grafana_config = {
    admin_user     = "admin"
    smtp_enabled   = true
    smtp_host      = "smtp.sendgrid.net:587"
    from_address   = "alerts@security-orchestrator.com"
  }
  
  alertmanager_config = {
    slack_webhook_url = var.slack_webhook_url
    pagerduty_key    = var.pagerduty_key
    email_configs = [{
      to = "oncall@security-orchestrator.com"
    }]
  }
  
  tags = module.networking.tags
}

module "security" {
  source = "../../modules/security"
  
  environment         = "prod"
  resource_group_name = module.networking.resource_group_name
  
  key_vault_config = {
    sku_name = "premium"
    
    purge_protection_enabled   = true
    soft_delete_retention_days = 90
    
    network_acls = {
      default_action = "Deny"
      bypass         = "AzureServices"
      ip_rules       = []
      subnet_ids     = [
        module.networking.subnet_ids["aks"],
        module.networking.subnet_ids["monitoring"]
      ]
    }
  }
  
  defender_config = {
    enable_for_servers = true
    enable_for_sql     = true
    enable_for_storage = true
    enable_for_k8s     = true
  }
  
  sentinel_config = {
    enable = true
    retention_days = 90
  }
  
  tags = module.networking.tags
}

# Outputs
output "kube_config" {
  value     = module.kubernetes.kube_config
  sensitive = true
}

output "database_connection" {
  value = module.database.connection_string
  sensitive = true
}

output "redis_connection" {
  value = module.database.redis_connection
  sensitive = true
}