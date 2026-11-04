$ErrorActionPreference='Stop'
$root=Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$delivery=Join-Path $root 'Resources/Models/FinalRefinement/GuardBodyDelivery'
$output=Join-Path $delivery 'MotionBuilder'
$mobupy='C:/Program Files/Autodesk/MotionBuilder 2027/bin/x64/mobupy.exe'
$script=Join-Path $PSScriptRoot 'prepare_test_character.py'
New-Item -ItemType Directory -Force -Path $output | Out-Null
$completed=@{}
$deadline=(Get-Date).AddMinutes(20)
while($completed.Count -lt 18){
    if((Get-Date) -gt $deadline){throw 'Timed out waiting for all 18 completed exports/targets.'}
    $manifest=Get-Content (Join-Path $delivery 'exports.json') -Raw|ConvertFrom-Json
    foreach($entry in $manifest.exports){
        $name=$entry.preset+'_'+$entry.style+'_Mocap'
        if($completed.ContainsKey($name)){continue}
        $source=Join-Path $delivery $entry.file
        $folder=Join-Path $output $entry.preset
        New-Item -ItemType Directory -Force -Path $folder | Out-Null
        $report=Join-Path $folder ('validation_'+$name+'.json')
        if(Test-Path -LiteralPath $report){
            $existing=Get-Content $report -Raw|ConvertFrom-Json
            if($existing.source_sha256 -ne (Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash.ToLowerInvariant()){throw "Existing target source changed: $name"}
        }else{
            $preparation=Join-Path $folder ('preparation_'+$name+'.json')
            if(!(Test-Path -LiteralPath $preparation)){
                for($attempt=1;$attempt -le 3 -and !(Test-Path -LiteralPath $preparation);$attempt++){
                    & $mobupy $script --source $source --name $name --output-dir $folder --defer-reopen *> (Join-Path $folder ($name+'_prepare_'+$attempt+'.log'))
                }
            }
            if(!(Test-Path -LiteralPath $preparation)){throw "Preparation evidence missing: $name"}
            $prepared=Get-Content $preparation -Raw|ConvertFrom-Json
            if($prepared.source_sha256 -ne (Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash.ToLowerInvariant()){throw "Preparation source changed: $name"}
            for($attempt=1;$attempt -le 3 -and !(Test-Path -LiteralPath $report);$attempt++){
                & $mobupy (Join-Path $PSScriptRoot 'verify_prepared_character.py') --preparation $preparation *> (Join-Path $folder ($name+'_reopen_'+$attempt+'.log'))
            }
            if(!(Test-Path -LiteralPath $report)){throw "MotionBuilder target validation missing: $name. Inspect its log."}
        }
        $result=Get-Content $report -Raw|ConvertFrom-Json
        if(!$result.characterized -or !$result.control_rig -or !$result.reopened_successfully){throw "Target failed: $name"}
        $completed[$name]=$result
        @($completed.Values)|ConvertTo-Json -Depth 6|Set-Content (Join-Path $output 'validation.json') -Encoding utf8
        Write-Output "READY $name"
    }
    if($completed.Count -lt 18){Start-Sleep -Seconds 2}
}
Write-Output 'PASS: 18 characterized targets, control rigs, wrist movement checks, and saved-file reopen checks.'
