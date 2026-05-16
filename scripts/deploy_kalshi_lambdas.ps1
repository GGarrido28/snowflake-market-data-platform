param(
    [string]$Profile = "ggarrido",
    [string]$Region = "us-east-2",
    [string]$TerraformDir = "infra/terraform",
    [string]$Dockerfile = "aws/docker/Dockerfile.lambda",
    [string]$EventsStatus = "open",
    [string]$EventsEventTicker,
    [string]$EventsSeriesTicker,
    [string[]]$EventsSeriesTickers = @("KXMLBSPREAD", "KXMLBTOTAL", "KXMLBGAME"),
    [string]$SeriesTicker,
    [string[]]$SeriesTags = @("BaseBall"),
    [switch]$SkipInit,
    [switch]$SkipBuild,
    [switch]$SkipInvoke,
    [switch]$SkipEventsInvoke,
    [switch]$SkipSeriesInvoke,
    [switch]$PlanOnly,
    [switch]$AutoApprove
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$TerraformPath = (Resolve-Path (Join-Path $RepoRoot $TerraformDir)).Path
$DockerfilePath = (Resolve-Path (Join-Path $RepoRoot $Dockerfile)).Path
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

function Get-JsonPayload {
    param([Parameter(Mandatory = $true)][hashtable]$Payload)

    return ($Payload | ConvertTo-Json -Depth 10 -Compress)
}

function Invoke-LambdaSmokeTest {
    param(
        [Parameter(Mandatory = $true)][string]$FunctionName,
        [Parameter(Mandatory = $true)][string]$PayloadJson,
        [Parameter(Mandatory = $true)][string]$ResponsePath
    )

    Write-Host "Invoking '$FunctionName' with payload: $PayloadJson"
    Invoke-CheckedCommand "aws" @(
        "lambda",
        "invoke",
        "--function-name",
        $FunctionName,
        "--payload",
        $PayloadJson,
        "--cli-binary-format",
        "raw-in-base64-out",
        "--region",
        $Region,
        "--profile",
        $Profile,
        $ResponsePath
    )

    Write-Host "Lambda response from '$ResponsePath':"
    Get-Content $ResponsePath | Write-Host
}

if ($PlanOnly -and $AutoApprove) {
    throw "Use either -PlanOnly or -AutoApprove, not both."
}

if ($EventsEventTicker -and $EventsSeriesTicker) {
    throw "Use either -EventsEventTicker or -EventsSeriesTicker, not both."
}

Require-Command "aws"
Require-Command "git"
Require-Command "terraform"
if (-not $SkipBuild -and -not $PlanOnly) {
    Require-Command "docker"
}

$env:AWS_PROFILE = $Profile
$env:AWS_REGION = $Region

Write-Host "Using AWS profile '$Profile' in region '$Region'."
try {
    Invoke-CheckedCommand "aws" @("sts", "get-caller-identity", "--profile", $Profile)
} catch {
    throw "AWS credentials check failed. Run 'aws sso login --profile $Profile' and try again. Details: $($_.Exception.Message)"
}

if (-not $SkipInit) {
    Invoke-CheckedCommand "terraform" @($TerraformChdir, "init")
}

if ($SkipBuild) {
    $LambdaImageUri = (Invoke-CheckedCommandOutput "terraform" @($TerraformChdir, "output", "-raw", "lambda_image_uri")).Trim()
    $ImageTag = Get-ImageTagFromUri -ImageUri $LambdaImageUri
    Write-Host "Preserving deployed Lambda image tag '$ImageTag' from Terraform state."
} else {
    $ImageTag = (Invoke-CheckedCommandOutput "git" @("rev-parse", "--short", "HEAD")).Trim()
    Write-Host "Using image tag '$ImageTag' from the current Git commit."
}

$LambdaImageTagVar = "lambda_image_tag=$ImageTag"

if ($PlanOnly) {
    Invoke-CheckedCommand "terraform" @($TerraformChdir, "plan", "-var", $LambdaImageTagVar)
    return
}

if (-not $AutoApprove) {
    $Confirmation = Read-Host "Build/push the Lambda image, apply Terraform, and smoke invoke Kalshi Lambdas? Type 'yes' to continue"
    if ($Confirmation -ne "yes") {
        Write-Host "Deploy cancelled."
        return
    }
}

if (-not $SkipBuild) {
    Write-Host "Ensuring ECR repository exists..."
    Invoke-CheckedCommand "terraform" @($TerraformChdir, "apply", "-target=aws_ecr_repository.mlb_teams", "-auto-approve")

    $RepositoryUrl = (Invoke-CheckedCommandOutput "terraform" @($TerraformChdir, "output", "-raw", "ecr_repository_url")).Trim()
    $Registry = $RepositoryUrl.Split("/")[0]
    $ImageUri = "${RepositoryUrl}:${ImageTag}"

    Write-Host "Logging Docker into ECR registry '$Registry'."
    $Password = (Invoke-CheckedCommandOutput "aws" @("ecr", "get-login-password", "--region", $Region, "--profile", $Profile)).Trim()
    if (-not $Password) {
        throw "AWS ECR login password was empty. Run 'aws sso login --profile $Profile' and try again."
    }

    $PasswordFile = [System.IO.Path]::GetTempFileName()
    try {
        [System.IO.File]::WriteAllText($PasswordFile, $Password)
        cmd.exe /d /c "type `"$PasswordFile`" | docker login --username AWS --password-stdin $Registry"
        if ($LASTEXITCODE -ne 0) {
            throw "Docker login failed with exit code $LASTEXITCODE."
        }
    } finally {
        if (Test-Path $PasswordFile) {
            Remove-Item -LiteralPath $PasswordFile -Force
        }
    }

    Write-Host "Building and pushing Lambda image '$ImageUri'."
    Push-Location $RepoRoot
    try {
        Invoke-CheckedCommand "docker" @("buildx", "build", "--platform", "linux/amd64", "-f", $DockerfilePath, "-t", $ImageUri, "--push", ".")
    } finally {
        Pop-Location
    }
}

Write-Host "Applying Terraform stack."
Invoke-CheckedCommand "terraform" @($TerraformChdir, "apply", "-var", $LambdaImageTagVar, "-auto-approve")

$EventsFunctionName = (Invoke-CheckedCommandOutput "terraform" @($TerraformChdir, "output", "-raw", "kalshi_events_lambda_function_name")).Trim()
$SeriesFunctionName = (Invoke-CheckedCommandOutput "terraform" @($TerraformChdir, "output", "-raw", "kalshi_series_lambda_function_name")).Trim()
Write-Host "Deployed Kalshi Events Lambda '$EventsFunctionName'."
Write-Host "Deployed Kalshi Series Lambda '$SeriesFunctionName'."

if ($SkipInvoke) {
    Write-Host "Skipping smoke invokes."
    return
}

if (-not $SkipEventsInvoke) {
    $EventsPayload = @{
        status = $EventsStatus
    }
    if ($EventsEventTicker) {
        $EventsPayload["event_ticker"] = $EventsEventTicker
    }
    if ($EventsSeriesTicker) {
        $EventsPayload["series_ticker"] = $EventsSeriesTicker
    }
    if (-not $EventsEventTicker -and -not $EventsSeriesTicker) {
        $EventsPayload["series_tickers"] = $EventsSeriesTickers
    }

    Invoke-LambdaSmokeTest `
        -FunctionName $EventsFunctionName `
        -PayloadJson (Get-JsonPayload -Payload $EventsPayload) `
        -ResponsePath (Join-Path $RepoRoot "kalshi-events-response.json")
}

if (-not $SkipSeriesInvoke) {
    $SeriesPayload = @{}
    if ($SeriesTicker) {
        $SeriesPayload["series_ticker"] = $SeriesTicker
    } else {
        $SeriesPayload["tags"] = $SeriesTags
    }

    Invoke-LambdaSmokeTest `
        -FunctionName $SeriesFunctionName `
        -PayloadJson (Get-JsonPayload -Payload $SeriesPayload) `
        -ResponsePath (Join-Path $RepoRoot "kalshi-series-response.json")
}
