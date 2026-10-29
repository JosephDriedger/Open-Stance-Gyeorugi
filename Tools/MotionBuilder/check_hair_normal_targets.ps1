$ErrorActionPreference = 'Stop'
$root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$stage = Join-Path $root 'Resources/Models/FinalRefinement/HairNormalDelivery'
$sdk = 'C:/Program Files/Autodesk/MotionBuilder 2027/bin/x64/mobupy.exe'
$script = Join-Path $PSScriptRoot 'validate_hair_normal_targets.py'
foreach ($report in Get-ChildItem -LiteralPath $stage -Filter 'fbx_*.json') {
    $row = Get-Content -LiteralPath $report.FullName -Raw | ConvertFrom-Json
    if (-not $row.changed_geometry_ids.Count -or $row.file -notlike '*/Animation/MotionBuilder/*' -or $row.file -like '*/_Sources/*') { continue }
    $sha = [System.Security.Cryptography.SHA256]::Create()
    $key = [Convert]::ToHexString($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($row.file))).ToLower().Substring(0,16)
    $done = Join-Path $stage "MotionBuilderChecks/$key.json"
    if (Test-Path -LiteralPath $done) { continue }
    $log = Join-Path $stage "$key.sdk.log"
    $passed = $false
    for ($attempt=1; $attempt -le 3; $attempt++) {
        & $sdk $script $row.file *> $log
        if ($LASTEXITCODE -eq 0 -and (Test-Path -LiteralPath $done)) { $passed=$true;break }
    }
    if (-not $passed) { throw "MotionBuilder check failed: $($row.file). See $log" }
    Write-Output "MOTIONBUILDER_CHECKED $($row.file)"
}
