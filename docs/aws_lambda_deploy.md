# AWS Lambda Deployment

This repo deploys the MLB teams job as an AWS Lambda container image backed by ECR. Terraform owns the AWS resources; Docker and the AWS CLI build, push, and invoke the image.

## Prerequisites

- AWS CLI authenticated to the target account.
- Docker Desktop or another Docker engine with `buildx`.
- Terraform `>= 1.6`.
- Existing S3 landing bucket: `snowflake-kalshi-project`.

The first Lambda writes to:

```text
s3://snowflake-kalshi-project/raw/mlb/teams/
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

## Bootstrap ECR

The Lambda function cannot be created until an image exists in ECR. Create the ECR repository first:

```powershell
terraform -chdir=infra/terraform apply -target=aws_ecr_repository.mlb_teams
```

## Build And Push The Lambda Image

Use the current Git commit as the image tag so Terraform can detect future image changes:

```powershell
$Region = "us-east-2"
$ImageTag = git rev-parse --short HEAD
$RepositoryUrl = terraform -chdir=infra/terraform output -raw ecr_repository_url
$Registry = $RepositoryUrl.Split("/")[0]
$ImageUri = "${RepositoryUrl}:${ImageTag}"

aws ecr get-login-password --region $Region |
  docker login --username AWS --password-stdin $Registry

docker buildx build --platform linux/amd64 -f aws/docker/Dockerfile.lambda -t $ImageUri .
docker push $ImageUri
```

## Deploy Lambda Resources

Apply the full Terraform stack, passing the image tag you pushed:

```powershell
terraform -chdir=infra/terraform apply -var "lambda_image_tag=$ImageTag"
```

Terraform creates:

- ECR repository for the Lambda image.
- IAM execution role with CloudWatch logs permissions.
- S3 write policy scoped to `snowflake-kalshi-project/raw/mlb/teams/*`.
- CloudWatch log group.
- Lambda function using the pushed container image.

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

## Updating The Function

For code changes, repeat the image build and push with a new tag, then re-run Terraform:

```powershell
$ImageTag = git rev-parse --short HEAD
$ImageUri = "${RepositoryUrl}:${ImageTag}"
docker buildx build --platform linux/amd64 -f aws/docker/Dockerfile.lambda -t $ImageUri .
docker push $ImageUri
terraform -chdir=infra/terraform apply -var "lambda_image_tag=$ImageTag"
```
