from airflow.decorators import dag, task
import pendulum
from google.cloud import storage
from google.cloud import bigquery
from google.oauth2.service_account import Credentials
from google.cloud.exceptions import NotFound
import pandas as pd
import requests
import gzip
import json
import os
from datetime import date, datetime, timedelta
from typing import List, Dict
import io
import subprocess

@dag(
    #schedule=None,
    schedule_interval='30 1 * * *',  # daily run UTC time
    #schedule_interval='/10 * * * *',  # run every 10 minutes
    start_date=pendulum.datetime(2024, 3, 28, tz="UTC"),
    is_paused_upon_creation=False,
    catchup=False,
    tags=["daily-github-activities"],
)

def git_activity_ingestion():
    project_id = 'github-pipeline-demo' ##### PLEASE CHANGE TO YOUR GCP PROJECT ID #####
    bucket_name = 'git-storage-bucket'
    yesterday = date.today() - timedelta(days=1)
    airflow_path = '/tmp'

    def transformation(obj: dict) -> dict:
        """
        This function truncates the payload field for certain event types to make each row shorter
        """
        #obj["actor"] = {key: obj["actor"][key] for key in ['id', 'login', 'display_login', 'url']}
        """
        language_url = f"https://api.github.com/repos/{obj['repo']['name']}/languages"
        response = requests.get(language_url)
        if response.status_code == 200:
            repo_languages = response.json()
        else:
            print(f"Failed to fetch data for repo {obj['repo']['name']}. Status code: {response.status_code}")
            repo_languages = {}
        obj["repo"]["languages"] = repo_languages
        """
        if obj["type"] == 'CommitCommentEvent':
            try:
                obj["payload"] = {"comment": {"url": obj["payload"]["comment"]["url"]}}
            except KeyError:
                obj["payload"] = {"comment": {"url": None}}
        elif obj["type"] == 'ForkEvent':
            try:
                obj["payload"] = {"forkee": {"url": obj["payload"]["forkee"]["url"]}}
            except KeyError:
                obj["payload"] = {"forkee": {"url": None}}
        elif obj["type"] == 'IssueCommentEvent':
            try:
                obj["payload"] = {"comment": {"url": obj["payload"]["comment"]["url"]}}
            except KeyError:
                obj["payload"] = {"comment": {"url": None}}
        elif obj["type"] == 'IssuesEvent':
            try:
                obj["payload"] = {"issue": {"url": obj["payload"]["issue"]["url"]}}
            except KeyError:
                obj["payload"] = {"issue": {"url": None}}
        elif obj["type"] == 'MemberEvent':
            try:
                obj["payload"] = {"member": {"url": obj["payload"]["member"]["url"]}, 
                              'action': obj["payload"]["action"]}
            except KeyError:
                obj["payload"] = {"member": {"url": None}, 'action': obj["payload"]["action"]}
        elif obj["type"] == 'PullRequestEvent':
            try:
                obj["payload"] = {"pull_request": {"url": obj["payload"]["pull_request"]["url"]}, 
                              'action': obj["payload"]["action"]}
            except KeyError:
                obj["payload"] = {"pull_request": {"url": None}, 'action': obj["payload"]["action"]}
        elif obj["type"] == 'PullRequestReviewCommentEvent':
            try:
                obj["payload"] = {"comment": {"url": obj["payload"]["comment"]["url"]}, 
                              'action': obj["payload"]["action"]}
            except KeyError:
                obj["payload"] = {"comment": {"url": None}, 'action': obj["payload"]["action"]}
        elif obj["type"] == 'PullRequestReviewEvent':
            try:
                obj["payload"] = {"review": {"id": obj["payload"]["review"]["id"],
                                         "submitted_at": obj["payload"]["review"]["submitted_at"], 
                                         "html_url": obj["payload"]["review"]["html_url"], 
                                         "pull_request_url": obj["payload"]["review"]["pull_request_url"]}, 
                              'action': obj["payload"]["action"]}
            except KeyError:
                obj["payload"] = {"review": None, 'action': obj["payload"]["action"]}
        #elif obj["type"] == 'PushEvent':
        #    try:
        #        obj["payload"] = {"commits": {"url": obj["payload"]["commits"][0]["url"]}, 'push_id': obj["payload"]['push_id']}
        #    except IndexError:
        #        obj["payload"] = {"commits": {"url": None}, 'push_id': obj["payload"]['push_id']}
        elif obj["type"] == 'ReleaseEvent':
            try:
                obj["payload"] = {"release": {"url": obj["payload"]["release"]["url"]}, 
                              'action': obj["payload"]["action"]}
            except KeyError:
                obj["payload"] = {"release": {"url": None}, 'action': obj["payload"]["action"]}
        elif obj["type"] in ["PullRequestReviewThreadEvent", "SponsorshipEvent"]:
            obj["payload"] = {}

        elif obj["type"] not in ["CreateEvent", "DeleteEvent", "GollumEvent", "PublicEvent",
                                 "WatchEvent", "PushEvent"]:
            print(f"New activity type detected: {obj['type']}")
            obj["payload"] = {}

        return obj
    
    @task
    def download_data(date: date) -> list:
        """
        This functions download hourly data files and returns a list of paths for the day
        """
        daily_folder = f'{date.year}-{date.month:02d}-{date.day:02d}/'
        daily_folder_path = os.path.join(airflow_path, daily_folder)
        os.makedirs(daily_folder_path, exist_ok=True)
        path_list = []
        for i in range(24):
        #current_hour = datetime.now().hour
        #for i in range(current_hour-1, current_hour):
            url = f'http://data.gharchive.org/{date.year}-{date.month:02}-{date.day:02}-{i}.json.gz'
            path = f"github_activity-{date.year}-{date.month:02d}-{date.day:02d}-{i}.json.gz"
            print(f'airflow path is {airflow_path}')
            full_path = os.path.join(daily_folder_path, path)
            os.system(f'curl "{url}" -o "{full_path}"')
            print(f"Downloaded {url} to {full_path}")
            path_list.append(path)
        return path_list

    @task
    def daily_data(date: date, path_list: list) -> list:
        """
        This function reads a list of downloaded hourly data file of a specified day, parses and
        transforms each json object, and saves all the rows as one daily data file
        """
        daily_folder = f'{date.year}-{date.month:02d}-{date.day:02d}/'
        daily_folder_path = os.path.join(airflow_path, daily_folder)
        os.makedirs(daily_folder_path, exist_ok=True)
        output_list = []
        for path in path_list:
            full_input_path = os.path.join(daily_folder_path, path)
            # Read file contents from path.
            print(f'Processing {full_input_path}')
            file = gzip.open(full_input_path, mode='rt')

            # Extract newline-delimited JSONs incrementally (with retries for JSONs that span
            # multiple lines).
            json_list = []
            last_json = ''
            count = 1
            for line in file:
                if count % 100000 == 0:
                    print(f'Parsing line {count}')
                try:
                    json_obj = transformation(json.loads(last_json + line))
                    #json_obj = json.loads(last_json + line)
                    json_list.append(json_obj)
                    last_json = ''
                except json.JSONDecodeError as err:
                    last_json += line
                count += 1
            if last_json:
                print(f"Error: Parsing for file xxx is not complete.")
            else:
                print(f'Parsed {len(json_list)} records.')
            output_file = path[:-3]
            output_path = os.path.join(daily_folder_path, output_file)
            print(f'Saving JSON data to {output_path}')

            # Open a file in write ('w') mode and use json.dump to write the JSON data
            with open(output_path, 'w') as outfile:
                json.dump(json_list, outfile)

            print(f'Saved JSON data to {output_path}')
            output_list.append(output_file)
            if os.path.isfile(full_input_path):
                os.remove(full_input_path)
                print(f"File {full_input_path} has been deleted.")
            else:
                print(f"The file {full_input_path} does not exist.")
        return output_list

    # columns: id: number string, type: string, actor: json, repo: json, payload: json, public:
    # boolean, created_at: timestamp string, org: json

    def stringify_json(obj: dict) -> str:
        """
        This function checks if a given object is dictionary. If yes, returns the stringified version
        of the dictionary; if not, returns a string of empty dictionary '{}'.
        """
        if isinstance(obj, dict):
            return json.dumps(obj)
        if obj:
            print(f"Input object is not a dictionary: {obj}")
        return '{}'

    @task
    def normalize_data(date: date, path_list: list) -> list:
        """
        This function stringifies certain fields in preparation of conversion to ndjson
        """
        daily_folder = f'{date.year}-{date.month:02d}-{date.day:02d}/'
        daily_folder_path = os.path.join(airflow_path, daily_folder)
        os.makedirs(daily_folder_path, exist_ok=True)
        output_list = []
        for path in path_list:
            full_input_path = os.path.join(daily_folder_path, path)
            with open(full_input_path, 'r', encoding='utf-8') as input_file:
                data = json.load(input_file)
            
            # Convert fields with timestamp and dictionary values into string values
            for item in data:
                item['created_at'] = datetime.strptime(item['created_at'], '%Y-%m-%dT%H:%M:%SZ').strftime('%Y-%m-%dT%H:%M:%SZ')
                item['actor'] = stringify_json(item["actor"])
                item['repo'] = stringify_json(item["repo"])
                item['payload'] = stringify_json(item["payload"])
                item['org'] = stringify_json(item.get("org"))
            output_file = f'normalized-{path}'
            output_path = os.path.join(daily_folder_path, output_file)
            print(f'Saving JSON data to {output_path}')

            with open(output_path, 'w') as outfile:
                json.dump(data, outfile)

            print(f'Saved JSON data to {output_path}')
            output_list.append(output_file)
            
            if os.path.isfile(full_input_path):
                os.remove(full_input_path)
                print(f"File {full_input_path} has been deleted.")
            else:
                print(f"The file {full_input_path} does not exist.")
       
        return output_list


    @task
    def convert_json_to_ndjson(date: date, path_list: list) -> list:
        """
        BigQuery requires newline delimited json to make a table
        This function converts a list of json into newline delimited json
        """
        daily_folder = f'{date.year}-{date.month:02d}-{date.day:02d}/'
        daily_folder_path = os.path.join(airflow_path, daily_folder)
        os.makedirs(daily_folder_path, exist_ok=True)
        output_list = []
        for path in path_list:
            full_input_path = os.path.join(daily_folder_path, path)
            with open(full_input_path, 'r', encoding='utf-8') as input_file:
                data = json.load(input_file)
            
            prefix_index = path.find('-')
            output_file = path[prefix_index + 1:-4] + 'ndjson'
            #output_file = f'github_activity-{date.year}-{date.month:02}-{date.day:02}.ndjson'
            output_path = os.path.join(daily_folder_path, output_file)
            with open(output_path, 'w', encoding='utf-8') as file_object:
                for item in data:
                    try:
                        json.dump(item, file_object)
                        file_object.write('\n')
                    except Exception as e:
                        print(f"Error writing item to file: {type(item)} - {item}. Error: {e}")
            
            output_list.append(output_file)
            
            if os.path.isfile(full_input_path):
                os.remove(full_input_path)
                print(f"File {full_input_path} has been deleted.")
            else:
                print(f"The file {full_input_path} does not exist.")
        return output_list


    @task
    def upload_to_gcs(date: date, path_list: list, bucket_name: str):
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        
        daily_folder = f'{date.year}-{date.month:02d}-{date.day:02d}/'
        daily_folder_path = os.path.join(airflow_path, daily_folder)
        os.makedirs(daily_folder_path, exist_ok=True)
        output_list = []
        for path in path_list:
            full_input_path = os.path.join(daily_folder_path, path)
            gcs_file_name = path
            #gcs_file_name = f'github_activity-{date.year}-{date.month:02}-{date.day:02}.json' 
            blob_path = f'{daily_folder}{gcs_file_name}'
            blob = bucket.blob(blob_path)
            
            # delete file with the same name that already exists in gcs bucket
            if blob.exists():
                print(f"Blob {blob_path} already exists in {bucket_name}. Deleting...")
                blob.delete()
                print(f"Blob {blob_path} deleted.")
            
            blob.upload_from_filename(full_input_path, content_type='application/octet-stream')
            
            if os.path.isfile(full_input_path):
                os.remove(full_input_path)
                print(f"File {full_input_path} has been deleted.")
            else:
                print(f"The file {full_input_path} does not exist.")
        return
    
    
    @task
    def create_materialized_bq_table(date: date, bucket_name: str):
        client = bigquery.Client()

        dataset_id = f'{project_id}.git_activities_warehouse'
        table_id = 'github-today'
        table_ref = f"{dataset_id}.{table_id}"

        schema = [
            bigquery.SchemaField("org", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("public", "BOOLEAN", mode="NULLABLE"),
            bigquery.SchemaField("repo", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("payload", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("actor", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("created_at", "TIMESTAMP", mode="NULLABLE"),
            bigquery.SchemaField("type", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("id", "INTEGER", mode="NULLABLE"),
        ]

        job_config = bigquery.LoadJobConfig(
            schema=schema,
            source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
            clustering_fields=["type"],  # Specifies the columns to cluster by
        )

        uri = f"gs://{bucket_name}/{date.year}-{date.month:02d}-{date.day:02d}/*.ndjson"

        load_job = client.load_table_from_uri(
            uri,
            table_ref,
            job_config=job_config
        )  # API request

        load_job.result()  # Waits for the job to complete

        print(f"Created materialized table {table_id} and loaded data from {uri}")        
        
    path_list = download_data(yesterday)
    raw_data_path = daily_data(yesterday, path_list)
    norm_data_path = normalize_data(yesterday, raw_data_path)
    ndjson_path = convert_json_to_ndjson(yesterday, norm_data_path)
    gcs_upload_status = upload_to_gcs(yesterday, ndjson_path, bucket_name)
    
    gcs_upload_status >> create_materialized_bq_table(yesterday, bucket_name)

git_activity_ingestion()
