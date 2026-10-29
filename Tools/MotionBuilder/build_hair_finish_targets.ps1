$ErrorActionPreference='Stop'
$projectRoot=Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$stage=Join-Path $projectRoot 'Resources/Models/HairExportFinish'
$sdk='C:/Program Files/Autodesk/MotionBuilder 2027/bin/x64/mobupy.exe'
$presets=@('Medium','Compact','Stocky','LeanTall','Tall','Male_Athletic','Male_Lean','Female_Athletic','Female_Strong')
try {
 foreach ($preset in $presets) {
  foreach ($style in @('WhiteWrap','WhiteVNeck')) {
  $ready=Join-Path $stage "$preset/$style/export_validation.json"
  $deadline=(Get-Date).AddMinutes(45)
  while (-not (Test-Path -LiteralPath $ready)) {
   if ((Get-Date) -gt $deadline) { throw "Timed out waiting for exports: $preset" }
   Start-Sleep -Seconds 5
  }
  foreach ($outfit in @('Dobok','Sparring')) {
   $targetName=if ($outfit -eq 'Dobok') { "OpenStance_$preset" } else { "OpenStance_${preset}_Sparring" }
   $source="Resources/Models/HairExportFinish/$preset/$style/Gameplay_High_$outfit.fbx"
   $destination="Resources/Models/HairExportFinish/MotionBuilder/$preset/$style"
   $reportPath=Join-Path $projectRoot "$destination/validation_$targetName.json"
   if ((Test-Path -LiteralPath $reportPath) -and (Test-Path -LiteralPath (Join-Path $projectRoot "$destination/$targetName.fbx"))) {
    $existing=Get-Content -LiteralPath $reportPath -Raw | ConvertFrom-Json
    $hashProvider=[System.Security.Cryptography.SHA256]::Create()
    $sourceHash=[System.BitConverter]::ToString($hashProvider.ComputeHash([System.IO.File]::ReadAllBytes((Join-Path $projectRoot $source)))).Replace('-','').ToLower()
    $hashProvider.Dispose()
    if ($existing.reopened_successfully -and $existing.source_sha256 -eq $sourceHash) { continue }
   }
   $stdout=Join-Path $stage "$style-$targetName.sdk.log"
   $stderr=Join-Path $stage "$style-$targetName.sdk_error.log"
   for ($attempt=1; $attempt -le 3; $attempt++) {
    $process=Start-Process -FilePath $sdk -ArgumentList @("$projectRoot/Tools/MotionBuilder/prepare_test_character.py",'--source',$source,'--name',$targetName,'--output-dir',$destination) -WorkingDirectory $projectRoot -WindowStyle Hidden -RedirectStandardOutput $stdout -RedirectStandardError $stderr -PassThru -Wait
    if ($process.ExitCode -eq 0) { break }
    Start-Sleep -Seconds 3
   }
   if ($process.ExitCode -ne 0) { throw "MotionBuilder failed for $targetName; see $stderr" }
   $result=Get-Content -LiteralPath (Join-Path $projectRoot "$destination/validation_$targetName.json") -Raw | ConvertFrom-Json
   if (-not ($result.characterized -and $result.control_rig -and $result.reopened_successfully)) { throw "Invalid target $targetName" }
   Add-Content -LiteralPath (Join-Path $stage 'motionbuilder.log') -Value "COMPLETE $targetName"
  }
 }
 }
 Add-Content -LiteralPath (Join-Path $stage 'motionbuilder.log') -Value 'ALL TARGETS COMPLETE'
} catch {
 Add-Content -LiteralPath (Join-Path $stage 'motionbuilder.log') -Value $_.Exception.ToString()
 exit 1
}




