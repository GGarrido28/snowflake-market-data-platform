param(
    [string]$Profile = "ggarrido",
    [string]$Region = "us-east-2",
    [string]$TerraformDir = "infra/terraform",
    [string]$Dockerfile = "aws/docker/Dockerfile.lambda",
    [switch]$SkipInit,
    [switch]$SkipInvoke
)

$ErrorActionPreference = "Stop"

function Require-Command {
    param([string]$Name)

    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command '$Name' was not found on PATH."
    }
}

Require-Command "aws"
Require-Command "docker"
Require-Command "git"
Require-Command "terraform"

$env:AWS_PROFILE = $Profile
$env:AWS_REGION = $Region

Write-Host "Using AWS profile '$Profile' in region '$Region'."
aws sts get-caller-identity --profile $Profile | Write-Host

if (-not $SkipInit) {
    terraform -chdir=$TerraformDir init
}

$ImageTag = (git rev-parse --short HEAD).Trim()
Write-Host "Using image tag '$ImageTag'."

Write-Host "Ensuring ECR repository exists..."
terraform -chdir=$TerraformDir apply "-target=aws_ecr_repository.mlb_teams" -auto-approve

$RepositoryUrl = (terraform -chdir=$TerraformDir output -raw ecr_repository_url).Trim()
$Registry = $RepositoryUrl.Split("/")[0]
$ImageUri = "${RepositoryUrl}:${ImageTag}"

Write-Host "Logging Docker into ECR registry '$Registry'."
$Password = (aws ecr get-login-password --region $Region --profile $Profile).Trim()
if (-not $Password) {
    throw "AWS ECR login password was empty. Run 'aws sso login --profile $Profile' and try again."
}
$Password | docker login --username AWS --password-stdin $Registry

Write-Host "Building and pushing Lambda image '$ImageUri'."
docker buildx build --platform linux/amd64 -f $Dockerfile -t $ImageUri --push .

Write-Host "Applying full Terraform stack."
terraform -chdir=$TerraformDir apply -var "lambda_image_tag=$ImageTag" -auto-approve

$FunctionName = (terraform -chdir=$TerraformDir output -raw lambda_function_name).Trim()
Write-Host "Deployed Lambda function '$FunctionName'."

if (-not $SkipInvoke) {
    $ResponsePath = "response.json"
    Write-Host "Invoking '$FunctionName' for a smoke test."
    aws lambda invoke `
        --function-name $FunctionName `
        --payload "{}" `
        --cli-binary-format raw-in-base64-out `
        --region $Region `
        --profile $Profile `
        $ResponsePath | Write-Host

    Write-Host "Lambda response:"
    Get-Content $ResponsePath | Write-Host
}
