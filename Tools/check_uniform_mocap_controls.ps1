$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
$env:OPENSTANCE_PATCH_DELIVERY=Join-Path $root 'Resources/Models/FinalRefinement/UniformGeometryDelivery'
$kinds=@('Medium','Compact','Stocky','LeanTall','Tall','Male_Athletic','Male_Lean','Female_Athletic','Female_Strong')
$paths=@($kinds | ForEach-Object {"Resources/Models/Animation/MotionBuilder_BeltChain/$_/OpenStance_$($_)_Sparring.fbx"})
$paths+=@('Medium','Male_Lean','Female_Strong') | ForEach-Object {"Resources/Models/Animation/MotionBuilder/$_/WhiteVNeck/OpenStance_$($_).fbx"}
foreach($rel in $paths){
 $target=Join-Path $env:OPENSTANCE_PATCH_DELIVERY "Files/$rel"
 $deadline=(Get-Date).AddMinutes(30)
 while(!(Test-Path -LiteralPath $target)) {if((Get-Date) -gt $deadline){throw "Missing $rel"};Start-Sleep -Seconds 2}
 & 'C:/Program Files/Autodesk/MotionBuilder 2027/bin/x64/mobupy.exe' Tools/MotionBuilder/validate_hair_normal_targets.py $rel
 if($LASTEXITCODE -ne 0){throw "Mocap validation failed: $rel"}
}
Write-Output 'ALL_UNIFORM_MOCAP_CONTROLS_PASSED'
