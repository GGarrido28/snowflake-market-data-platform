-- MLB teams Snowpipe scaffold.
--
-- Execution order:
-- 1. Apply Terraform once and capture output snowflake_s3_read_role_arn.
-- 2. Run the CREATE STORAGE INTEGRATION section with ACCOUNTADMIN or a role
--    that has CREATE INTEGRATION.
-- 3. Run DESC INTEGRATION and copy STORAGE_AWS_IAM_USER_ARN and
--    STORAGE_AWS_EXTERNAL_ID into infra/terraform/terraform.tfvars.
-- 4. Re-apply Terraform so the IAM role trusts Snowflake.
-- 5. Run the file format, stage, table, and pipe section.
-- 6. Run SHOW PIPES and copy the notification_channel ARN into the Terraform
--    Snowpipe S3 notification variables. See docs/snowpipe_s3_notifications.md.

USE DATABASE PROD;
USE SCHEMA RAW;

-- Replace the role ARN with Terraform output snowflake_s3_read_role_arn.
CREATE STORAGE INTEGRATION IF NOT EXISTS S3_MLB_TEAMS_INT
  TYPE = EXTERNAL_STAGE
  STORAGE_PROVIDER = 'S3'
  ENABLED = TRUE
  STORAGE_AWS_ROLE_ARN = '<snowflake_s3_read_role_arn>'
  STORAGE_ALLOWED_LOCATIONS = ('s3://snowflake-kalshi-project/raw/mlb/teams/');

DESC INTEGRATION S3_MLB_TEAMS_INT;

CREATE FILE FORMAT IF NOT EXISTS FF_MLB_JSONL
  TYPE = JSON
  COMPRESSION = AUTO
  MULTI_LINE = FALSE;

CREATE STAGE IF NOT EXISTS STG_MLB_TEAMS
  URL = 's3://snowflake-kalshi-project/raw/mlb/teams/'
  STORAGE_INTEGRATION = S3_MLB_TEAMS_INT
  FILE_FORMAT = (FORMAT_NAME = FF_MLB_JSONL);

CREATE TABLE IF NOT EXISTS RAW_MLB_TEAMS (
  team_id NUMBER,
  name VARCHAR,
  team_code VARCHAR,
  abbreviation VARCHAR,
  team_name VARCHAR,
  location_name VARCHAR,
  first_year_of_play NUMBER,
  sport_id NUMBER,
  sport_name VARCHAR,
  league_id NUMBER,
  league_name VARCHAR,
  division_id NUMBER,
  division_name VARCHAR,
  venue_id NUMBER,
  venue_name VARCHAR,
  active BOOLEAN,
  ingested_at TIMESTAMP_NTZ,
  raw_payload VARIANT,
  source_file VARCHAR,
  source_row_number NUMBER,
  snowpipe_loaded_at TIMESTAMP_NTZ
);

CREATE PIPE IF NOT EXISTS PIPE_MLB_TEAMS
  AUTO_INGEST = TRUE
AS
COPY INTO RAW_MLB_TEAMS (
  team_id,
  name,
  team_code,
  abbreviation,
  team_name,
  location_name,
  first_year_of_play,
  sport_id,
  sport_name,
  league_id,
  league_name,
  division_id,
  division_name,
  venue_id,
  venue_name,
  active,
  ingested_at,
  raw_payload,
  source_file,
  source_row_number,
  snowpipe_loaded_at
)
FROM (
  SELECT
    TRY_TO_NUMBER($1:team_id::VARCHAR),
    $1:name::VARCHAR,
    $1:team_code::VARCHAR,
    $1:abbreviation::VARCHAR,
    $1:team_name::VARCHAR,
    $1:location_name::VARCHAR,
    TRY_TO_NUMBER($1:first_year_of_play::VARCHAR),
    TRY_TO_NUMBER($1:sport_id::VARCHAR),
    $1:sport_name::VARCHAR,
    TRY_TO_NUMBER($1:league_id::VARCHAR),
    $1:league_name::VARCHAR,
    TRY_TO_NUMBER($1:division_id::VARCHAR),
    $1:division_name::VARCHAR,
    TRY_TO_NUMBER($1:venue_id::VARCHAR),
    $1:venue_name::VARCHAR,
    $1:active::BOOLEAN,
    TRY_TO_TIMESTAMP_NTZ($1:ingested_at::VARCHAR),
    $1:raw_payload::VARIANT,
    METADATA$FILENAME,
    METADATA$FILE_ROW_NUMBER,
    METADATA$START_SCAN_TIME
  FROM @STG_MLB_TEAMS
)
PATTERN = '.*[.]jsonl';

SHOW PIPES LIKE 'PIPE_MLB_TEAMS';

-- Use after S3 notifications are configured to queue recent files that landed
-- before the notification existed. For files older than 7 days, run COPY INTO
-- manually from STG_MLB_TEAMS.
-- ALTER PIPE PIPE_MLB_TEAMS REFRESH;
