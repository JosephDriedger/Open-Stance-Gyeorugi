$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$libraryRoot = Join-Path $projectRoot 'Models and Rigs'
$modelRoot = Join-Path $projectRoot 'Resources/Models'
$shell = New-Object -ComObject WScript.Shell
$entries = [System.Collections.Generic.List[object]]::new()

function Add-AssetLink([string]$Category, [string]$Name, [string]$Target, [string]$Purpose) {
    $absoluteTarget = [System.IO.Path]::GetFullPath((Join-Path $projectRoot $Target))
    if (-not (Test-Path -LiteralPath $absoluteTarget)) { throw "Missing asset: $absoluteTarget" }
    $folder = Join-Path $libraryRoot $Category
    New-Item -ItemType Directory -Path $folder -Force | Out-Null
    $linkPath = Join-Path $folder "$Name.lnk"
    $link = $shell.CreateShortcut($linkPath)
    $link.TargetPath = $absoluteTarget
    $link.WorkingDirectory = if (Test-Path -LiteralPath $absoluteTarget -PathType Container) { $absoluteTarget } else { Split-Path $absoluteTarget -Parent }
    $link.Description = $Purpose
    $link.Save()
    $verified = $shell.CreateShortcut($linkPath)
    if ($verified.TargetPath -ne $absoluteTarget -or -not (Test-Path -LiteralPath $verified.WorkingDirectory)) {
        throw "Shortcut verification failed: $linkPath"
    }
    $entries.Add([ordered]@{ category=$Category; name=$Name; target=$Target; purpose=$Purpose; shortcut=$linkPath.Substring($projectRoot.Length + 1) })
}

$bodies = @('Compact','Medium','Stocky','LeanTall','Tall')
foreach ($body in $bodies) {
    Add-AssetLink '01 Mocap - MotionBuilder targets' "$body - Characterized FK IK target.fbx" "Resources/Models/Animation/MotionBuilder/$body/OpenStance_$body.fbx" 'Production body skeleton with MotionBuilder control rig; calibrate and solve actual capture separately.'
    Add-AssetLink '02 Blender - Animation rigs' "$body - Body and face animation.blend" "Resources/Models/Animation/OpenStance_${body}_Animation.blend" 'Body FK, face FK, marker guides and animation layers; earlier visual assets.'
    foreach ($tier in @('High','Mid','Far')) {
        $category = "04 Gameplay - LODs and exports/$body"
        Add-AssetLink $category "$tier - Editable fighter.blend" "Resources/Models/CharacterSuite/$body/Gameplay_$tier.blend" 'Editable gameplay fighter; earlier chest protector and hair, not the latest preview design.'
        foreach ($outfit in @('Dobok','Sparring')) {
            Add-AssetLink $category "$tier - $outfit.fbx" "Resources/Models/CharacterSuite/$body/Gameplay_${tier}_$outfit.fbx" 'Gameplay export; not a characterized MotionBuilder target.'
        }
    }
    Add-AssetLink "04 Gameplay - LODs and exports/$body" 'Preview - Full detail.blend' "Resources/Models/CharacterSuite/$body/Preview.blend" 'Original size-suite preview; newer gender and hair previews are in category 03.'
    foreach ($tier in @('Near','Far')) {
        Add-AssetLink "05 Crowd - Rigs and animations/$body" "$tier - Editable crowd rig.blend" "Resources/Models/CharacterSuite/$body/Crowd_$tier.blend" 'Simplified 25-bone crowd skeleton, separate from the production fighter mocap target.'
        Add-AssetLink "05 Crowd - Rigs and animations/$body" "$tier - Crowd export.fbx" "Resources/Models/CharacterSuite/$body/Crowd_$tier.fbx" 'Simplified crowd export.'
    }
    foreach ($clip in @('Cheer','SeatedClap','SeatedIdle','StandingIdle','Wave')) {
        Add-AssetLink "05 Crowd - Rigs and animations/$body" "Animation - $clip.fbx" "Resources/Models/CharacterSuite/$body/Crowd_$clip.fbx" 'Existing crowd animation clip; use the matching crowd skeleton.'
    }
}
Add-AssetLink '02 Blender - Animation rigs' 'All five body sizes - Scene workspace.blend' 'Resources/Models/OpenStance_Characters_Workspace.blend' 'Select a Fighter scene; earlier visual assets.'
foreach ($preset in @('Male_Athletic','Male_Lean','Female_Athletic','Female_Strong')) {
    $category = "03 Characters - Latest hair and gear/$preset"
    Add-AssetLink $category "$preset - Editable character.blend" "Resources/Models/CharacterVariations/$preset/Character.blend" 'Latest preview with six hair styles, automatic helmet fitting and extended chest guard; body rig remains RIG_Body_Medium.'
    Add-AssetLink $category 'Portrait.png' "Resources/Models/CharacterVariations/$preset/Portrait.png" 'Saved character portrait.'
    Add-AssetLink $category 'Full body.png' "Resources/Models/CharacterVariations/$preset/Full_Body.png" 'Saved full body preview.'
}
Add-AssetLink '06 Gear - Editable libraries' 'Chest guards - Latest belt overlap.blend' 'Resources/Models/ProtectorReferenceV2/Chest_Protector_Library.blend' 'Latest two chest protector designs; edit the separate protector collections.'
Add-AssetLink '06 Gear - Editable libraries' 'Helmets - Three designs.blend' 'Resources/Models/HelmetVariants/Helmet_Design_Library.blend' 'Three helmet designs with separate editable parts.'
Add-AssetLink '07 Guides and validation' 'Mocap - 41 marker specification.md' 'Docs/Mocap_Marker_Set.md' 'Capture marker specification; guides require actual performer calibration.'
Add-AssetLink '07 Guides and validation' 'Blender animation and retargeting.md' 'Resources/Models/Animation/README.md' 'Detailed rig, marker and export workflow.'
Add-AssetLink '07 Guides and validation' 'Hair and character controls.md' 'Resources/Models/CharacterVariations/README.md' 'Style selectors and current preview limitations.'
Add-AssetLink '07 Guides and validation' 'Gameplay suite.md' 'Resources/Models/CharacterSuite/README.md' 'Original suite profiles, controls and exports.'
Add-AssetLink '07 Guides and validation' 'Helmet fit - 72 combinations.json' 'Resources/Models/CharacterVariations/helmet_fit_validation.json' 'Static selector and fit checks, not full animation collision certification.'
foreach ($source in @('Archive','MetaHuman','Textures','Modular','CreatorFighters','Fitted','GearUpgrade','HelmetStudy','ProtectorStudy','MotionBuilder','TestFighter','Referee')) {
    Add-AssetLink '90 Sources staging and legacy' $source "Resources/Models/$source" 'Pipeline source, staging or older asset; use categories 01-06 for current entry points.'
}
$manifest = [ordered]@{
    generated_at = (Get-Date).ToString('o')
    shortcut_count = $entries.Count
    validation = 'Every shortcut was reopened; target and working directory verified. Original assets are not moved or modified.'
    entries = $entries
}
$manifest | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $libraryRoot 'asset_index.json') -Encoding UTF8
Write-Output "Verified $($entries.Count) shortcuts in $libraryRoot"
