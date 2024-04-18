{{ config(materialized='table') }}

select 
    date(created_at) as creation_date,
    case when type = 'CreateEvent' then 'Create'
        when  type like '%Comment%' then 'Comment'
        when  type = 'ForkEvent' then 'Fork a Repo'    
        when  type = 'IssuesEvent' then 'Action on Issue'
        when  type = 'MemberEvent' then 'Collab Change'
        when  type = 'PullRequestEvent' then 'Pull Request'
        when  type like 'PullRequestReview%' then 'Pull Request Review'
        when  type = 'ReleaseEvent' then 'Release'
        when  type = 'SponsorshipEvent' then 'Sponsorship'
        when  type = 'DeleteEvent' then 'Delete'
        when  type = 'GollumEvent' then 'Wiki Page'
        when  type = 'PublicEvent' then 'Public a Repo'
        when  type = 'WatchEvent' then 'Star a Repo'
        when  type = 'PushEvent' then 'Commit'
        else type
    end as activity_type,
    count(*) as count
    --round(count(*)/(sum(count(*)) over()), 4) as percentage
from {{ ref('stg_git_daily_data') }}
group by 1, 2
order by 1, 3 desc
limit 10
