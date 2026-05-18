param(
    [string]$Profile = "ggarrido",
    [string]$Region = "us-east-2",
    [string]$TerraformDir = "infra/terraform",
    [switch]$SkipInit,
    [switch]$PlanOnly,
    [switch]$AutoApprove,
    [switch]$SkipVerify
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$TerraformPath = (Resolve-Path (Join-Path $RepoRoot $TerraformDir)).Path
$TerraformChdir = "-chdir=$TerraformPath"

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

function Invoke-CheckedCommandOutput {
    param(
        [Parameter(Mandatory = $true)][string]$Command,
        [Parameter(Mandatory = $true)][string[]]$Arguments
    )

    $Output = & $Command @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed with exit code ${LASTEXITCODE}: $Command $($Arguments -join ' ')"
    }

    return ($Output -join [Environment]::NewLine)
}

function Get-ImageTagFromUri {
    param([Parameter(Mandatory = $true)][string]$ImageUri)

    $LastColon = $ImageUri.LastIndexOf(":")
    if ($LastColon -lt 0 -or $LastColon -eq ($ImageUri.Length - 1)) {
        throw "Could not parse an image tag from Terraform output lambda_image_uri: '$ImageUri'."
    }

    return $ImageUri.Substring($LastColon + 1)
}

if ($PlanOnly -and $AutoApprove) {
    throw "Use either -PlanOnly or -AutoApprove, not both."
}

Require-Command "aws"
Require-Command "terraform"

$env:AWS_PROFILE = $Profile
$env:AWS_REGION = $Region

Write-Host "Using AWS profile '$Profile' in region '$Region'."
try {
    Invoke-CheckedCommand "aws" @("sts", "get-caller-identity", "--profile", $Profile, "--no-cli-pager")
} catch {
    throw "AWS credentials check failed. Run 'aws sso login --profile $Profile' and try again. Details: $($_.Exception.Message)"
}

if (-not $SkipInit) {
    Invoke-CheckedCommand "terraform" @($TerraformChdir, "init")
}

$LambdaImageUri = (Invoke-CheckedCommandOutput "terraform" @($TerraformChdir, "output", "-raw", "lambda_image_uri")).Trim()
$ImageTag = Get-ImageTagFromUri -ImageUri $LambdaImageUri
$LambdaImageTagVar = "lambda_image_tag=$ImageTag"
Write-Host "Preserving deployed Lambda image tag '$ImageTag' from Terraform state."

if ($PlanOnly) {
    Invoke-CheckedCommand "terraform" @($TerraformChdir, "plan", "-var", $LambdaImageTagVar)
    return
}

$PlanPath = Join-Path ([System.IO.Path]::GetTempPath()) "managed-schedulers-$PID.tfplan"
try {
    Invoke-CheckedCommand "terraform" @($TerraformChdir, "plan", "-out=$PlanPath", "-var", $LambdaImageTagVar)

    if (-not $AutoApprove) {
        $Confirmation = Read-Host "Apply this ingestion scheduler plan? Type 'yes' to continue"
        if ($Confirmation -ne "yes") {
            Write-Host "Apply cancelled."
            return
        }
    }

    Invoke-CheckedCommand "terraform" @($TerraformChdir, "apply", $PlanPath)

    if (-not $SkipVerify) {
        $ScheduleOutputNames = @(
            "mlb_teams_schedule_name",
            "kalshi_events_schedule_name",
            "kalshi_series_schedule_name",
            "kalshi_markets_schedule_name"
        )

        foreach ($OutputName in $ScheduleOutputNames) {
            $ScheduleName = (Invoke-CheckedCommandOutput "terraform" @($TerraformChdir, "output", "-raw", $OutputName)).Trim()
            Write-Host "Verifying EventBridge Scheduler schedule '$ScheduleName'."
            Invoke-CheckedCommand "aws" @(
                "scheduler",
                "get-schedule",
                "--name",
                $ScheduleName,
                "--group-name",
                "default",
                "--region",
                $Region,
                "--profile",
                $Profile,
                "--no-cli-pager"
            )
        }
    }
} finally {
    if (Test-Path $PlanPath) {
        Remove-Item -LiteralPath $PlanPath -Force
    }
}
