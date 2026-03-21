param(
    [string]$EnvFile = ".env"
)

$envPath = Join-Path $PSScriptRoot "..\\$EnvFile"
$envPath = [System.IO.Path]::GetFullPath($envPath)

if (-not (Test-Path $envPath)) {
    throw "Env file not found: $envPath"
}

Get-Content $envPath | ForEach-Object {
    $line = $_.Trim()

    if (-not $line -or $line.StartsWith("#")) {
        return
    }

    $parts = $line -split "=", 2
    if ($parts.Count -ne 2) {
        return
    }

    $name = $parts[0].Trim()
    $value = $parts[1].Trim()

    if (
        ($value.StartsWith('"') -and $value.EndsWith('"')) -or
        ($value.StartsWith("'") -and $value.EndsWith("'"))
    ) {
        $value = $value.Substring(1, $value.Length - 2)
    }

    if ($name) {
        [System.Environment]::SetEnvironmentVariable($name, $value, "Process")
    }
}

Write-Host "Loaded environment variables from $envPath into the current PowerShell session."
