[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)]
  [ValidateNotNullOrEmpty()]
  [string]$BaseUrl,

  [Parameter(Mandatory = $true)]
  [ValidateLength(32, 256)]
  [string]$ApiKey,

  [Parameter(Mandatory = $true)]
  [ValidateScript({ Test-Path -LiteralPath $_ -PathType Leaf })]
  [string]$AudioPath,

  [string]$Transcript = ''
)

$ErrorActionPreference = 'Stop'
$resolvedAudio = (Resolve-Path -LiteralPath $AudioPath).Path
$endpoint = "$($BaseUrl.TrimEnd('/'))/tts/v1/voices/yaho"
$curlArguments = @(
  '-fsS',
  '-X', 'PUT',
  $endpoint,
  '-H', "Authorization: Bearer $ApiKey",
  '-F', "file=@$resolvedAudio"
)

if (-not [string]::IsNullOrWhiteSpace($Transcript)) {
  $curlArguments += @('-F', "transcript=$Transcript")
}

& curl.exe @curlArguments
if ($LASTEXITCODE -ne 0) {
  throw "Voice upload failed with curl exit code $LASTEXITCODE."
}
