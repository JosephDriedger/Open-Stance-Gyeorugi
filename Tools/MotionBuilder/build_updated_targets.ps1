$ErrorActionPreference='Stop'
$projectRoot=Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$stage=Join-Path $projectRoot 'Resources/Models/UpdatedBuild'
$sdk='C:/Program Files/Autodesk/MotionBuilder 2027/bin/x64/mobupy.exe'
$log=Join-Path $stage 'motionbuilder_build.log'
$presets=@('Medium','Compact','Stocky','LeanTall','Tall','Male_Athletic','Male_Lean','Female_Athletic','Female_Strong')
try {
 foreach ($preset in $presets) {
  $validation=Join-Path $stage "$preset/export_validation.json"
  $deadline=(Get-Date).AddMinutes(45)
  do {
   $ready=$false
   if (Test-Path -LiteralPath $validation) {
    try { $data=Get-Content -LiteralPath $validation -Raw | ConvertFrom-Json; $ready=$data.passed -and $data.files.Count -eq 14 } catch { $ready=$false }
   }
   if (-not $ready) {
    if ((Get-Date) -gt $deadline) { throw "Timed out waiting for validated exports: $preset" }
    Start-Sleep -Seconds 10
   }
  } until ($ready)
  foreach ($outfit in @('Dobok','Sparring')) {
   $targetName=if ($outfit -eq 'Dobok') { "OpenStance_$preset" } else { "OpenStance_${preset}_Sparring" }
   $source=if ($outfit -eq 'Dobok') { "Resources/Models/UpdatedBuild/$preset/OpenStance_${preset}_Mocap_Source.fbx" } else { "Resources/Models/UpdatedBuild/$preset/Gameplay_High_Sparring.fbx" }
   $destination="Resources/Models/UpdatedBuild/MotionBuilder/$preset"
   $stdout=Join-Path $stage "$targetName.sdk.log"; $stderr=Join-Path $stage "$targetName.sdk_error.log"
   for ($attempt=1; $attempt -le 3; $attempt++) {
    $runStart=(Get-Date).ToUniversalTime()
    $process=Start-Process -FilePath $sdk -ArgumentList @("$projectRoot/Tools/MotionBuilder/prepare_test_character.py",'--source',$source,'--name',$targetName,'--output-dir',$destination) -WorkingDirectory $projectRoot -WindowStyle Hidden -RedirectStandardOutput $stdout -RedirectStandardError $stderr -PassThru -Wait
    if ($process.ExitCode -eq 0) { break }
    Add-Content -LiteralPath $log -Value "SDK exit $($process.ExitCode) for $targetName attempt $attempt"
    Start-Sleep -Seconds 5
   }
   if ($process.ExitCode -ne 0) { throw "MotionBuilder failed for $targetName; see $stderr" }
   $report=Join-Path $projectRoot "$destination/validation_$targetName.json"
   if (-not (Test-Path -LiteralPath $report) -or (Get-Item -LiteralPath $report).LastWriteTimeUtc -lt $runStart) { throw "No fresh validation for $targetName" }
   $result=Get-Content -LiteralPath $report -Raw | ConvertFrom-Json
   if (-not ($result.characterized -and $result.control_rig -and $result.reopened_successfully)) { throw "Invalid target $targetName" }
   Add-Content -LiteralPath $log -Value "COMPLETE $targetName"
   Start-Sleep -Seconds 3
  }
 }
 Add-Content -LiteralPath $log -Value 'ALL TARGETS COMPLETE'
} catch {
 Add-Content -LiteralPath $log -Value $_.Exception.ToString()
 exit 1
}
