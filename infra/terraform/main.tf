terraform {
  required_version = ">= 1.9, < 2.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.55"
    }
  }
}
provider "azurerm" {
  features {}
  subscription_id                 = var.subscription_id
  resource_provider_registrations = "none"
}
variable "subscription_id" {
  type        = string
  description = "Approved Azure subscription. No default; never apply without authorization."
}
variable "location" {
  type    = string
  default = "canadacentral"
}
variable "prefix" {
  type    = string
  default = "shapeops"
}
variable "storage_name" {
  type        = string
  description = "Globally unique lowercase storage account name."
}
variable "image" {
  type        = string
  description = "Approved, scanned, digest-pinned public GHCR image."
  validation {
    condition     = can(regex("^ghcr.io/.+@sha256:[a-f0-9]{64}$", var.image))
    error_message = "Use a digest-pinned public GHCR image."
  }
}
resource "azurerm_resource_group" "platform" {
  name     = "${var.prefix}-rg"
  location = var.location
  tags     = { project = "ShapeOps", environment = "approved-production" }
}
resource "azurerm_user_assigned_identity" "app" {
  name                = "${var.prefix}-identity"
  location            = azurerm_resource_group.platform.location
  resource_group_name = azurerm_resource_group.platform.name
}
resource "azurerm_storage_account" "artifacts" {
  name                            = var.storage_name
  resource_group_name             = azurerm_resource_group.platform.name
  location                        = azurerm_resource_group.platform.location
  account_tier                    = "Standard"
  account_replication_type        = "LRS"
  min_tls_version                 = "TLS1_2"
  shared_access_key_enabled       = false
  allow_nested_items_to_be_public = false
  https_traffic_only_enabled      = true
  public_network_access_enabled   = false
  network_rules {
    default_action = "Deny"
    bypass         = ["AzureServices"]
  }
  blob_properties {
    delete_retention_policy { days = 7 }
  }
}
resource "azurerm_role_assignment" "artifacts" {
  scope                = azurerm_storage_account.artifacts.id
  role_definition_name = "Storage Blob Data Reader"
  principal_id         = azurerm_user_assigned_identity.app.principal_id
}
resource "azurerm_container_app_environment" "platform" {
  name                = "${var.prefix}-environment"
  location            = azurerm_resource_group.platform.location
  resource_group_name = azurerm_resource_group.platform.name
  logs_destination    = "azure-monitor"
}
resource "azurerm_container_app" "platform" {
  name                         = var.prefix
  resource_group_name          = azurerm_resource_group.platform.name
  container_app_environment_id = azurerm_container_app_environment.platform.id
  revision_mode                = "Single"
  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.app.id]
  }
  ingress {
    external_enabled           = true
    target_port                = 8000
    transport                  = "http"
    allow_insecure_connections = false
    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }
  template {
    min_replicas = 0
    max_replicas = 1
    http_scale_rule {
      name                = "bounded-http"
      concurrent_requests = "2"
    }
    container {
      name   = "shapeops"
      image  = var.image
      cpu    = 2
      memory = "4Gi"
      env {
        name  = "AZURE_CLIENT_ID"
        value = azurerm_user_assigned_identity.app.client_id
      }
      startup_probe {
        transport               = "HTTP"
        port                    = 8000
        path                    = "/api/health"
        interval_seconds        = 5
        failure_count_threshold = 30
      }
      liveness_probe {
        transport        = "HTTP"
        port             = 8000
        path             = "/api/health"
        interval_seconds = 30
      }
      readiness_probe {
        transport        = "HTTP"
        port             = 8000
        path             = "/api/health"
        interval_seconds = 10
      }
    }
  }
  lifecycle {
    prevent_destroy = true
  }
}
output "application_hostname" {
  value = azurerm_container_app.platform.latest_revision_fqdn
}
output "storage_endpoint" {
  value = azurerm_storage_account.artifacts.primary_blob_endpoint
}
