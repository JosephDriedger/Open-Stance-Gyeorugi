param(
    [Parameter(Mandatory=$true)][string]$PackageDirectory,
    [Parameter(Mandatory=$true)][string]$ReportDirectory
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$executable = Join-Path $PackageDirectory 'OpenStance/Binaries/Win64/OpenStance.exe'
if (!(Test-Path -LiteralPath $executable)) { throw "Packaged executable missing: $executable" }
New-Item -ItemType Directory -Force -Path $ReportDirectory | Out-Null
$ReportDirectory = (Resolve-Path -LiteralPath $ReportDirectory).Path
$maps = @(Get-Content (Join-Path $projectRoot 'Config/DefaultGame.ini') | ForEach-Object {
    if ($_ -match '^\+MapsToCook=\(FilePath="([^"]+)"\)') { $Matches[1] }
})
if (!$maps.Count) { throw 'No MapsToCook entries found.' }
$results = @()
foreach ($map in $maps) {
    $log = Join-Path $ReportDirectory ((Split-Path $map -Leaf) + '.log')
    # Fresh logs prevent an old successful proof from masking a failed launch.
    if (Test-Path -LiteralPath $log) { throw "Use a fresh report directory: $log exists" }
    $arguments = @($map, '-NullRHI', '-RenderOffscreen', '-unattended', '-nosplash', '-nosound',
        '"-ExecCmds=os.RunProof,quit"', ('"-abslog=' + $log + '"'))
    $process = Start-Process -FilePath $executable -ArgumentList $arguments -WindowStyle Hidden -PassThru
    if (!$process.WaitForExit(120000)) {
        Stop-Process -Id $process.Id
        throw "Packaged smoke timed out: $map"
    }
    $process.Refresh()
    $lines = if (Test-Path -LiteralPath $log) { Get-Content -LiteralPath $log } else { @() }
    $proof = [bool]($lines -match 'Greybox proof PASSED')
    $loaded = [bool]($lines -match ('LogLoad: LoadMap: ' + [regex]::Escape($map) + '(\?|\s|$)'))
    $errors = @($lines | Where-Object { $_ -match 'Error:|Fatal error|SkipPackage:|Failed to find object|TravelFailure' })
    $results += [pscustomobject]@{
        map=$map; exit_code=$process.ExitCode; loaded=$loaded; combat_proof=$proof
        errors=$errors; log=$log
        passed=($process.ExitCode -eq 0 -and $loaded -and $proof -and !$errors.Count)
    }
    $results | ConvertTo-Json -Depth 5 | Set-Content (Join-Path $ReportDirectory 'maps.json') -Encoding utf8
}
if (@($results | Where-Object { !$_.passed }).Count) { throw 'Packaged map smoke failed; see maps.json.' }
Write-Output "PASS: $($results.Count) packaged maps loaded and passed the combat proof. Headless only; no visual/physics acceptance."
