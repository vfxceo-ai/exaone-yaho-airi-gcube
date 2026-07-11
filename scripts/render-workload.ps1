[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)]
  [ValidateNotNullOrEmpty()]
  [string]$GhcrOwner,

  [Parameter(Mandatory = $true)]
  [ValidateLength(32, 256)]
  [string]$ApiKey,

  [ValidateSet('stage1', 'stage2')]
  [string]$Stage = 'stage1',

  [ValidatePattern('^[0-9]{3}$')]
  [string]$GpuCode = ''
)

$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Parent $PSScriptRoot
$templatePath = Join-Path $projectRoot "workload-$Stage.template.yaml"
$outputPath = Join-Path $projectRoot "workload-$Stage.private.yaml"
$template = Get-Content -LiteralPath $templatePath -Raw
$rendered = $template.Replace('${GHCR_OWNER}', $GhcrOwner).Replace('${API_KEY}', $ApiKey)

if ($Stage -eq 'stage2') {
  if ([string]::IsNullOrWhiteSpace($GpuCode)) {
    throw 'GpuCode is required when rendering stage2.'
  }
  $rendered = $rendered.Replace('${GPU_CODE}', $GpuCode)
}

if ($rendered -match '\$\{[A-Z0-9_]+\}') {
  throw 'Manifest rendering left an unresolved required variable.'
}

Set-Content -LiteralPath $outputPath -Value $rendered -Encoding utf8NoBOM
Write-Host "Rendered private manifest: $outputPath"
