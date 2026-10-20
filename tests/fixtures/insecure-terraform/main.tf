# Deliberately insecure scanner positive control. Never provision this fixture.
resource "azurerm_storage_account" "insecure_fixture" {
  name                            = "scannerfixture"
  resource_group_name             = "scannerfixture"
  location                        = "canadacentral"
  account_tier                    = "Standard"
  account_replication_type        = "LRS"
  min_tls_version                 = "TLS1_0"
  https_traffic_only_enabled      = false
  allow_nested_items_to_be_public = true
}
