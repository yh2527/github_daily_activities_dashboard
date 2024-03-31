# Terraform Script for Google Cloud Storage Bucket Configuration

# This Terraform script configures a Google Cloud Storage bucket for a specified project ID and
# region. It sets up the bucket with defined naming conventions, location, storage class, and
# enables uniform bucket-level access. Additionally, it configures versioning and a lifecycle rule
# to delete objects older than 30 days, with an option for forced destruction of the bucket.

resource "google_storage_bucket" "data-lake-bucket" {
  name                        = "${var.data_lake_bucket}_${var.project_id}"
  location                    = var.region
  storage_class               = var.storage_class
  uniform_bucket_level_access = true
  versioning {
    enabled = true
  }
  lifecycle_rule {
    action {
      type = "Delete"
    }
    condition {
      age = 30
    }
  }
  force_destroy = true
}

