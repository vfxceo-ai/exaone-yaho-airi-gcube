[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)]
  [ValidateNotNullOrEmpty()]
  [string]$GhcrOwner,

  [Parameter(Mandatory = $true)]
  [ValidateLength(32, 256)]
  [string]$ApiKey
)

$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Parent $PSScriptRoot
$templatePath = Join-Path $projectRoot 'workload-stage1.template.yaml'
$outputPath = Join-Path $projectRoot 'workload-stage1.private.yaml'
$template = Get-Content -LiteralPath $templatePath -Raw
$rendered = $template.Replace('${GHCR_OWNER}', $GhcrOwner).Replace('${API_KEY}', $ApiKey)

if ($rendered.Contains('${GHCR_OWNER}') -or $rendered.Contains('${API_KEY}')) {
  throw 'Manifest rendering left an unresolved required variable.'
}

Set-Content -LiteralPath $outputPath -Value $rendered -Encoding utf8NoBOM
Write-Host "Rendered private manifest: $outputPath"
