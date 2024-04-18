{{ config(materialized='table') }}

select 
    date(created_at) as creation_date,
    'Star a Repo' as activity_type,
    JSON_EXTRACT_SCALAR(repo, '$.name') as repo_starred,
    count(*) as count
from {{ ref('stg_git_daily_data') }}
where type = 'WatchEvent' 
group by 1, 2, 3
order by 1, 2, 4 desc, 3
limit 10
