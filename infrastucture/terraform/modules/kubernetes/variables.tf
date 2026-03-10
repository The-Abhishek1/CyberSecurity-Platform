# infrastructure/terraform/modules/kubernetes/variables.tf

variable "cluster_name" {
  description = "Name of the AKS cluster"
  type        = string
}

variable "location" {
  description = "Azure region"
  type        = string
}

variable "resource_group_name" {
  description = "Resource group name"
  type        = string
}

variable "dns_prefix" {
  description = "DNS prefix for the cluster"
  type        = string
}

variable "kubernetes_version" {
  description = "Kubernetes version"
  type        = string
  default     = "1.28"
}

variable "default_node_count" {
  description = "Default node count"
  type        = number
  default     = 3
}

variable "default_node_size" {
  description = "Default node VM size"
  type        = string
  default     = "Standard_D4s_v3"
}

variable "enable_auto_scaling" {
  description = "Enable auto-scaling"
  type        = bool
  default     = true
}

variable "min_node_count" {
  description = "Minimum node count"
  type        = number
  default     = 3
}

variable "max_node_count" {
  description = "Maximum node count"
  type        = number
  default     = 10
}

variable "worker_node_size" {
  description = "Worker node VM size"
  type        = string
  default     = "Standard_D8s_v3"
}

variable "worker_node_count" {
  description = "Initial worker node count"
  type        = number
  default     = 5
}

variable "worker_min_count" {
  description = "Minimum worker node count"
  type        = number
  default     = 5
}

variable "worker_max_count" {
  description = "Maximum worker node count"
  type        = number
  default     = 50
}

variable "log_analytics_workspace_id" {
  description = "Log Analytics workspace ID"
  type        = string
}

variable "app_gateway_id" {
  description = "Application Gateway ID"
  type        = string
}

variable "tags" {
  description = "Resource tags"
  type        = map(string)
  default     = {}
}