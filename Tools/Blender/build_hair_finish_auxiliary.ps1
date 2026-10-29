$ErrorActionPreference='Stop'
$exe='D:/Open-Stance-Gyeorugi/Saved/Tools/Blender522/blender.exe'
foreach($mode in @('tpose','aux','samples','workspace')) {
 & $exe --background --factory-startup -t 3 --python Tools/Blender/build_hair_finish_delivery.py -- $mode *> "Resources/Models/hair_finish_$mode.log"
 if($LASTEXITCODE -ne 0){throw "Blender failed $mode"}
}
