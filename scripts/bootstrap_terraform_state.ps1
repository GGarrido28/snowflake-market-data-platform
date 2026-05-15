param(
    [string]$Profile = "ggarrido",
    [string]$Region = "us-east-2",
    [string]$Bucket = "backend-893072528957-us-east-2-an"
)

$ErrorActionPreference = "Stop"

function Require-Command {
    param([string]$Name)

    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command '$Name' was not found on PATH."
    }
}

function Invoke-CheckedCommand {
    param(
        [Parameter(Mandatory = $true)][string]$Command,
        [Parameter(Mandatory = $true)][string[]]$Arguments
    )

    & $Command @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed with exit code ${LASTEXITCODE}: $Command $($Arguments -join ' ')"
    }
}

function Test-BucketExists {
    param([Parameter(Mandatory = $true)][string]$BucketName)

    & aws s3api head-bucket --bucket $BucketName --profile $Profile --region $Region 2>$null
    return $LASTEXITCODE -eq 0
}

Require-Command "aws"

$env:AWS_PROFILE = $Profile
$env:AWS_REGION = $Region

Write-Host "Using AWS profile '$Profile' in region '$Region'."
try {
    Invoke-CheckedCommand "aws" @("sts", "get-caller-identity", "--profile", $Profile)
} catch {
    throw "AWS credentials check failed. Run 'aws sso login --profile $Profile' and try again. Details: $($_.Exception.Message)"
}

if (Test-BucketExists -BucketName $Bucket) {
    Write-Host "Terraform state bucket '$Bucket' already exists and is accessible."
} else {
    Write-Host "Creating Terraform state bucket '$Bucket'."
    if ($Region -eq "us-east-1") {
        Invoke-CheckedCommand "aws" @(
            "s3api",
            "create-bucket",
            "--bucket",
            $Bucket,
            "--region",
            $Region,
            "--profile",
            $Profile
        )
    } else {
        Invoke-CheckedCommand "aws" @(
            "s3api",
            "create-bucket",
            "--bucket",
            $Bucket,
            "--region",
            $Region,
            "--create-bucket-configuration",
            "LocationConstraint=$Region",
            "--profile",
            $Profile
        )
    }

    Invoke-CheckedCommand "aws" @("s3api", "wait", "bucket-exists", "--bucket", $Bucket, "--profile", $Profile, "--region", $Region)
}

Write-Host "Blocking public access for Terraform state bucket '$Bucket'."
Invoke-CheckedCommand "aws" @(
    "s3api",
    "put-public-access-block",
    "--bucket",
    $Bucket,
    "--public-access-block-configuration",
    "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true",
    "--profile",
    $Profile,
    "--region",
    $Region
)

Write-Host "Enabling versioning for Terraform state bucket '$Bucket'."
Invoke-CheckedCommand "aws" @(
    "s3api",
    "put-bucket-versioning",
    "--bucket",
    $Bucket,
    "--versioning-configuration",
    "Status=Enabled",
    "--profile",
    $Profile,
    "--region",
    $Region
)

$EncryptionConfigPath = Join-Path ([System.IO.Path]::GetTempPath()) "terraform-state-encryption-$PID.json"
try {
    $EncryptionConfig = @{
        Rules = @(
            @{
                ApplyServerSideEncryptionByDefault = @{
                    SSEAlgorithm = "AES256"
                }
            }
        )
    } | ConvertTo-Json -Depth 5 -Compress

    Set-Content -LiteralPath $EncryptionConfigPath -Value $EncryptionConfig -NoNewline -Encoding ascii

    Write-Host "Enabling default encryption for Terraform state bucket '$Bucket'."
    Invoke-CheckedCommand "aws" @(
        "s3api",
        "put-bucket-encryption",
        "--bucket",
        $Bucket,
        "--server-side-encryption-configuration",
        "file://$EncryptionConfigPath",
        "--profile",
        $Profile,
        "--region",
        $Region
    )
} finally {
    if (Test-Path $EncryptionConfigPath) {
        Remove-Item -LiteralPath $EncryptionConfigPath -Force
    }
}

Write-Host "Terraform state bucket '$Bucket' is ready."
Write-Host "Next, migrate local state with: terraform -chdir=infra/terraform init -migrate-state"
