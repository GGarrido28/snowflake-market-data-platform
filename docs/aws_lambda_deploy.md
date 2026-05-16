# AWS Lambda Deployment

This repo deploys ingestion jobs as AWS Lambda container images backed by ECR. Terraform owns the AWS resources; Docker and the AWS CLI build, push, and invoke the image.

## Prerequisites

- AWS CLI authenticated to the target account.
- Docker Desktop or another Docker engine with `buildx`.
- Terraform `>= 1.10`.
- Existing S3 landing bucket: `snowflake-kalshi-project`.
- Terraform remote state bootstrapped as described in [`terraform_state.md`](./terraform_state.md).

The managed Lambdas write to:

```text
s3://snowflake-kalshi-project/raw/mlb/teams/
s3://snowflake-kalshi-project/raw/kalshi/events/
s3://snowflake-kalshi-project/raw/kalshi/series/
```

## Configure Terraform

Copy the example variables file. This project uses `us-east-2` for AWS resources:

```powershell
Copy-Item infra/terraform/terraform.tfvars.example infra/terraform/terraform.tfvars
```

Initialize Terraform:

```powershell
terraform -chdir=infra/terraform init
```

The MLB teams schedule is intentionally created in a disabled state because team metadata is low-change reference data. Override `mlb_teams_schedule_expression`, `mlb_teams_schedule_timezone`, or set `mlb_teams_schedule_state = "ENABLED"` in `terraform.tfvars` if you need recurring refreshes before applying.

Kalshi Events and Series Lambdas are deployed without EventBridge schedules in this phase. Configure Kalshi authentication with `kalshi_api_secret_arn` or `kalshi_api_secret_name`; Terraform passes the matching `KALSHI_SECRET_ARN` or `KALSHI_SECRET_NAME` environment variable and grants the Lambda roles read access to that secret reference.

## Deploy With Script

The MLB Teams deploy path is:

```powershell
.\scripts\deploy_mlb_teams_lambda.ps1 -Profile ggarrido -Region us-east-2
```

The Kalshi Events and Series deploy path is:

```powershell
.\scripts\deploy_kalshi_lambdas.ps1 `
  -Profile ggarrido `
  -Region us-east-2 `
  -EventsSeriesTicker KXMLBSPREAD `
  -SeriesTicker KXMLBSPREAD
```

The scripts initialize Terraform, bootstrap ECR, log Docker into ECR, build and push the Lambda image, apply the full Terraform stack, and invoke smoke tests. Run them from PowerShell. The Kalshi script requires explicit smoke-test scope for Events and Series; use `-SkipInvoke`, `-SkipEventsInvoke`, or `-SkipSeriesInvoke` when deploying without smoke invokes.

## Deploy Scheduler Only

After the Lambda image has already been deployed, use the scheduler script to plan and apply Terraform without rebuilding or pushing a container image:

```powershell
.\scripts\deploy_mlb_teams_scheduler.ps1 -Profile ggarrido -Region us-east-2
```

The script reads the current `lambda_image_uri` from Terraform state and passes that image tag back into Terraform, so scheduler-only deploys do not accidentally change the Lambda image. To preview without applying, run:

```powershell
.\scripts\deploy_mlb_teams_scheduler.ps1 -Profile ggarrido -Region us-east-2 -PlanOnly
```

Use `-AutoApprove` only when you want the script to apply the saved Terraform plan without an interactive confirmation.

If your SSO session has expired, refresh it first:

```powershell
aws sso login --profile ggarrido
```

## Manual Bootstrap ECR

The Lambda function cannot be created until an image exists in ECR. Create the ECR repository first:

```powershell
terraform -chdir=infra/terraform apply "-target=aws_ecr_repository.mlb_teams"
```

## Build And Push The Lambda Image

Use the current Git commit as the image tag so Terraform can detect future image changes:

```powershell
$Region = "us-east-2"
$ImageTag = git rev-parse --short HEAD
$RepositoryUrl = terraform -chdir=infra/terraform output -raw ecr_repository_url
$Registry = $RepositoryUrl.Split("/")[0]
$ImageUri = "${RepositoryUrl}:${ImageTag}"

$Password = (aws ecr get-login-password --region $Region --profile ggarrido).Trim()
$Password | docker login --username AWS --password-stdin $Registry

docker buildx build --platform linux/amd64 -f aws/docker/Dockerfile.lambda -t $ImageUri --push .
```

## Deploy Lambda Resources

Apply the full Terraform stack, passing the image tag you pushed:

```powershell
terraform -chdir=infra/terraform apply -var "lambda_image_tag=$ImageTag"
```

Terraform creates:

- ECR repository for the Lambda image.
- IAM execution roles with CloudWatch logs permissions.
- S3 write policies scoped to `snowflake-kalshi-project/raw/mlb/teams/*`, `snowflake-kalshi-project/raw/kalshi/events/*`, and `snowflake-kalshi-project/raw/kalshi/series/*`.
- Optional Kalshi Secrets Manager read policy attached only to the Kalshi Lambda roles when `kalshi_api_secret_arn` or `kalshi_api_secret_name` is configured.
- IAM read role scoped to the managed MLB and Kalshi S3 prefixes for Snowflake external stage access.
- CloudWatch log groups.
- Lambda functions using the pushed container image.
- EventBridge Scheduler schedule for the Lambda, disabled by default but visible in AWS and Terraform.

Snowpipe setup instructions live in [`docs/mlb_teams_snowpipe.md`](./mlb_teams_snowpipe.md).

## Invoke A Smoke Test

Invoke the function once and inspect the returned S3 URI:

```powershell
$FunctionName = terraform -chdir=infra/terraform output -raw lambda_function_name

aws lambda invoke `
  --function-name $FunctionName `
  --payload "{}" `
  --cli-binary-format raw-in-base64-out `
  --region $Region `
  response.json

Get-Content response.json
```

The response should include `row_count` and an `s3_uri` under `s3://snowflake-kalshi-project/raw/mlb/teams/`.

For the intended one-time dimension load, run this smoke test after Snowpipe notifications are configured, then validate the file loaded into `PROD.RAW.RAW_MLB_TEAMS`.

## Invoke Kalshi Events And Series

The Kalshi deploy script smoke invokes both Lambdas when passed scoped ticker values. To invoke manually after deployment, Kalshi Events defaults to `status = "open"` and accepts either an event ticker or a series ticker:

```powershell
$EventsFunctionName = terraform -chdir=infra/terraform output -raw kalshi_events_lambda_function_name

aws lambda invoke `
  --function-name $EventsFunctionName `
  --payload '{"series_ticker":"KXMLBSPREAD","status":"open"}' `
  --cli-binary-format raw-in-base64-out `
  --region $Region `
  kalshi-events-response.json

Get-Content kalshi-events-response.json
```

Kalshi Series requires an exact series ticker in either the invocation payload or `kalshi_series_ticker`:

```powershell
$SeriesFunctionName = terraform -chdir=infra/terraform output -raw kalshi_series_lambda_function_name

aws lambda invoke `
  --function-name $SeriesFunctionName `
  --payload '{"series_ticker":"KXMLBSPREAD"}' `
  --cli-binary-format raw-in-base64-out `
  --region $Region `
  kalshi-series-response.json

Get-Content kalshi-series-response.json
```

The responses include `row_count` and `s3_uri` values under the `raw/kalshi/events/` or `raw/kalshi/series/` prefixes.

## Updating The Function

For code changes, repeat the image build and push with a new tag, then re-run Terraform:

```powershell
$ImageTag = git rev-parse --short HEAD
$ImageUri = "${RepositoryUrl}:${ImageTag}"
docker buildx build --platform linux/amd64 -f aws/docker/Dockerfile.lambda -t $ImageUri --push .
terraform -chdir=infra/terraform apply -var "lambda_image_tag=$ImageTag"
```
