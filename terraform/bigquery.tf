# Terraform Configuration for BigQuery Dataset and External Tables Setup

resource "google_bigquery_dataset" "bq_dataset" {
  dataset_id                 = var.bq_dataset
  project                    = var.project_id
  location                   = var.region
  delete_contents_on_destroy = true
}


