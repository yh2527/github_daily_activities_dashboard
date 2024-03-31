# GCP Configuration Variables

# Update these variables to match your GCP Project ID, region, and zone preferences.
project_id = "github-activities-412623" # CHANGE-THIS
region     = "us-west2"        # CHANGE-THIS
zone       = "us-west2-a"      # CHANGE-THIS

# Additional Configuration
account_id         = "git-daily-project-account"
gce_name           = "vm-git-daily"
gce_static_ip_name = "static-git-pipeline"
storage_class      = "STANDARD"
data_lake_bucket   = "git-storage-bucket"
bq_dataset         = "git_activities_warehouse"
bq_table_id        = "git_activities_today"
