{{ config(materialized='table') }}

select 
    date(created_at) as creation_date,
    'Commit' as activity_type,
    --JSON_EXTRACT_SCALAR(actor, '$.display_login') as committer,
    JSON_EXTRACT_SCALAR(element, '$.author.name') as commit_author,
    count(*) as count
from {{ ref('stg_git_daily_data') }},
    UNNEST(JSON_EXTRACT_ARRAY(payload, '$.commits')) AS element
where type = 'PushEvent' 
group by 1, 2, 3
order by 1, 2, 4 desc, 3
limit 10
