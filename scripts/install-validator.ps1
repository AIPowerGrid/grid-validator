# SPDX-FileCopyrightText: 2026 AI Power Grid
# SPDX-License-Identifier: AGPL-3.0-or-later

[CmdletBinding()]
param(
    [switch]$AcceptUnsignedPreview
)

$ErrorActionPreference = "Stop"

function Get-Setting {
    param([string]$Name, [string]$Default)
    $value = [Environment]::GetEnvironmentVariable($Name)
    if ([string]::IsNullOrWhiteSpace($value)) { return $Default }
    return $value
}

function Copy-Or-Download {
    param([string]$Source, [string]$Destination)
    $uri = $null
    if ([Uri]::TryCreate($Source, [UriKind]::Absolute, [ref]$uri) -and $uri.Scheme -in @("http", "https")) {
        Invoke-WebRequest -UseBasicParsing -Uri $Source -OutFile $Destination
        return
    }
    if ($Source.StartsWith("file://")) {
        $Source = ([Uri]$Source).LocalPath
    }
    Copy-Item -LiteralPath $Source -Destination $Destination
}

if (-not $AcceptUnsignedPreview) {
    throw "UNSIGNED PREVIEW: Windows is not Authenticode signed. Verify SHA256SUMS and GitHub provenance, then rerun with -AcceptUnsignedPreview."
}
if ($env:PROCESSOR_ARCHITECTURE -notin @("AMD64", "x86_64")) {
    throw "Only Windows x64 is supported by this preview installer."
}

$repo = Get-Setting "AIPG_VALIDATOR_REPO" "AIPowerGrid/grid-validator"
$version = Get-Setting "AIPG_VALIDATOR_VERSION" "v0.1.0-preview"
$installDir = Get-Setting "AIPG_VALIDATOR_INSTALL_DIR" (Join-Path $HOME ".local\bin")
$configDir = Get-Setting "AIPG_VALIDATOR_CONFIG_DIR" (Join-Path $HOME ".aipg-validator")
$asset = "aipg-validator-windows-x64.zip"
$assetUrl = Get-Setting "AIPG_VALIDATOR_URL" "https://github.com/$repo/releases/download/$version/$asset"
$checksumsUrl = Get-Setting "AIPG_VALIDATOR_CHECKSUMS_URL" "https://github.com/$repo/releases/download/$version/SHA256SUMS"

$tempDir = Join-Path ([IO.Path]::GetTempPath()) ("aipg-validator-" + [Guid]::NewGuid())
New-Item -ItemType Directory -Path $tempDir | Out-Null
try {
    $archive = Join-Path $tempDir $asset
    $checksums = Join-Path $tempDir "SHA256SUMS"
    Write-Warning "UNSIGNED PREVIEW: Windows is not Authenticode signed. No code will be installed before its SHA-256 checksum is verified."
    Copy-Or-Download $assetUrl $archive
    Copy-Or-Download $checksumsUrl $checksums

    $pattern = "^(?<hash>[0-9A-Fa-f]{64})\s+\*?" + [Regex]::Escape($asset) + "$"
    $expected = $null
    foreach ($line in Get-Content -LiteralPath $checksums) {
        if ($line -match $pattern) {
            $expected = $Matches.hash.ToLowerInvariant()
            break
        }
    }
    if (-not $expected) { throw "SHA256SUMS does not contain $asset" }
    $actual = (Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actual -ne $expected) { throw "Checksum mismatch for $asset" }
    Write-Host "Verified SHA-256: $actual"

    $extractDir = Join-Path $tempDir "extract"
    Expand-Archive -LiteralPath $archive -DestinationPath $extractDir
    $binary = Join-Path $extractDir "aipg-validator.exe"
    if (-not (Test-Path -LiteralPath $binary -PathType Leaf)) {
        throw "Release archive did not contain aipg-validator.exe"
    }
    New-Item -ItemType Directory -Force -Path $installDir | Out-Null
    New-Item -ItemType Directory -Force -Path $configDir | Out-Null
    $target = Join-Path $installDir "aipg-validator.exe"
    Copy-Item -LiteralPath $binary -Destination $target -Force
    & $target --help | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Installed validator failed its help smoke test" }

    Write-Host "Installed: $target"
    Write-Host "Next steps:"
    Write-Host "  Set-Location '$configDir'"
    Write-Host "  & '$target' init"
    Write-Host "  & '$target' check --no-probe"
    Write-Host "  & '$target' dashboard"
    Write-Host "  & '$target' run"
} finally {
    Remove-Item -LiteralPath $tempDir -Recurse -Force -ErrorAction SilentlyContinue
}
