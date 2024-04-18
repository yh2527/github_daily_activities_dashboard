{{ config(materialized='table') }}

with gitdata as 
(
  select *,
    row_number() over(partition by id) as rn
  from {{ source('staging','github-today') }}
)
select *
from gitdata
where rn = 1  -- remove the duplicates
