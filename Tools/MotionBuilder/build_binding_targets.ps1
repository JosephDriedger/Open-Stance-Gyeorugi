$ErrorActionPreference='Stop'
$projectRoot=Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$stage=Join-Path $projectRoot 'Resources/Models/FinalRefinement/BindingDelivery'
$sdk='C:/Program Files/Autodesk/MotionBuilder 2027/bin/x64/mobupy.exe'
foreach ($preset in @('Medium','Compact','Stocky','LeanTall','Tall','Male_Athletic','Male_Lean','Female_Athletic','Female_Strong')) {
 $deadline=(Get-Date).AddMinutes(30)
 while (-not (Test-Path -LiteralPath (Join-Path $stage ($preset+'_exports.json')))) {
  if ((Get-Date) -gt $deadline) { throw "Exports unavailable: $preset" }
  Start-Sleep -Seconds 3
 }
 foreach ($style in @('','WhiteVNeck')) {
  $name="OpenStance_${preset}_Sparring"
  $source="Resources/Models/FinalRefinement/BindingDelivery/Files/Resources/Models/CharacterSuite/$preset/$style/Gameplay_High_Sparring.fbx"
  $destination="Resources/Models/FinalRefinement/BindingDelivery/Files/Resources/Models/Animation/MotionBuilder/$preset/$style"
  $report=Join-Path $projectRoot "$destination/validation_$name.json"
  if (Test-Path -LiteralPath $report) { continue }
  $log=Join-Path $stage ($preset+'_'+$style+'_sdk.log')
  $errorlog=Join-Path $stage ($preset+'_'+$style+'_sdk_error.log')
  for ($attempt=1; $attempt -le 3; $attempt++) {
   $process=Start-Process -FilePath $sdk -ArgumentList @("$projectRoot/Tools/MotionBuilder/prepare_test_character.py",'--source',$source,'--name',$name,'--output-dir',$destination) -WorkingDirectory $projectRoot -WindowStyle Hidden -RedirectStandardOutput $log -RedirectStandardError $errorlog -PassThru -Wait
   if ($process.ExitCode -eq 0) { break }
   Write-Output "SDK retry $preset $style attempt $attempt exit $($process.ExitCode)"
  }
  if ($process.ExitCode -ne 0) { throw "Characterization failed: $name $style" }
  $result=Get-Content -LiteralPath $report -Raw | ConvertFrom-Json
  if (-not ($result.characterized -and $result.control_rig -and $result.reopened_successfully)) { throw "Characterization validation failed: $name" }
  Write-Output "BINDING_TARGET_VERIFIED $preset $style"
 }
}
