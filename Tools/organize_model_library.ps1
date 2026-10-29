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

$bodies = @('Compact','Medium','Stocky','LeanTall','Tall','Male_Athletic','Male_Lean','Female_Athletic','Female_Strong')
if (Test-Path -LiteralPath (Join-Path $modelRoot 'FinalRefinement/UniformGeometryDelivery/published.json')) {
    Add-AssetLink '07 Guides and validation' 'Uniform UV and body-face repair.md' 'Resources/Models/FinalRefinement/UniformGeometryDelivery/README.md' 'Installed UV and collapsed export-face repair; rig preservation, mocap checks and remaining limitations.'
}
if (Test-Path -LiteralPath (Join-Path $modelRoot 'Animation/MotionBuilder_BeltChain/README.md')) {
    Add-AssetLink '09 Experimental - Belt physics' 'READ FIRST - Belt-chain target limitations.md' 'Resources/Models/Animation/MotionBuilder_BeltChain/README.md' 'Experimental targets; original MotionBuilder targets remain suitable for recording. Read root compatibility and physics limits.'
    Add-AssetLink '09 Experimental - Belt physics' 'Belt-chain MotionBuilder targets' 'Resources/Models/Animation/MotionBuilder_BeltChain' '36 experimental targets, nine presets and both uniform styles. Separate from the recommended recording targets.'
}
if (Test-Path -LiteralPath (Join-Path $modelRoot 'FinalRefinement/UniformMassDelivery/published.json')) {
    Add-AssetLink '07 Guides and validation' 'Uniform mass correction.md' 'Resources/Models/FinalRefinement/UniformMassDelivery/README.md' 'Installed total-mass controls in 101 Blender files; does not certify cloth motion.'
}
if (Test-Path -LiteralPath (Join-Path $modelRoot 'Animation/Physics/Body_Type_Studies/README.md')) {
    Add-AssetLink '08 Sample animations' 'EXPERIMENTAL - Body type cloth studies' 'Resources/Models/Animation/Physics/Body_Type_Studies' 'Nine body presets and a punching study. Read README; belt twisting and constrained uniform remain.'
}
foreach ($body in $bodies) {
    $dummyTarget = "Resources/Models/Animation/DummyMotionTests/$body/DummyMotion_$body.blend"
    if (Test-Path -LiteralPath (Join-Path $projectRoot $dummyTarget)) {
        Add-AssetLink '08 Sample animations/Dummy full-body tests' "$body - Dummy motion tests.blend" $dummyTarget '22 labeled synthetic range-of-motion sections. Cloth off; not mocap or production choreography.'
    }
    foreach ($outfit in @('Dobok','Sparring')) {
        $bunTarget = "Resources/Models/CharacterSuite/$body/HairstyleSamples/CompactBun_$outfit.fbx"
        if (Test-Path -LiteralPath (Join-Path $projectRoot $bunTarget)) {
            Add-AssetLink "04 Gameplay - LODs and exports/$body" "Compact bun - $outfit.fbx" $bunTarget 'Bun hairstyle sample with the shared gameplay skeleton; not a characterized MotionBuilder target.'
        }
    }

    Add-AssetLink '01 Mocap - MotionBuilder targets' "$body - Characterized FK IK target.fbx" "Resources/Models/Animation/MotionBuilder/$body/OpenStance_$body.fbx" 'Production body skeleton with MotionBuilder control rig; calibrate and solve actual capture separately.'
    Add-AssetLink '01 Mocap - MotionBuilder targets' "$body - Sparring characterized FK IK target.fbx" "Resources/Models/Animation/MotionBuilder/$body/OpenStance_${body}_Sparring.fbx" 'Updated sparring equipment and characterized MotionBuilder control rig.'
    if (Test-Path -LiteralPath (Join-Path $modelRoot "Animation/MotionBuilder/$body/WhiteVNeck/OpenStance_$body.fbx")) {
        Add-AssetLink '01 Mocap - MotionBuilder targets/White V-neck uniform' "$body - Dobok target.fbx" "Resources/Models/Animation/MotionBuilder/$body/WhiteVNeck/OpenStance_$body.fbx" 'Repaired V-neck uniform with characterized FK/IK control rig.'
        Add-AssetLink '01 Mocap - MotionBuilder targets/White V-neck uniform' "$body - Sparring target.fbx" "Resources/Models/Animation/MotionBuilder/$body/WhiteVNeck/OpenStance_${body}_Sparring.fbx" 'Repaired V-neck uniform and sparring gear with characterized FK/IK control rig.'
        Add-AssetLink "04 Gameplay - LODs and exports/$body" 'White V-neck - Exports and crowd clips' "Resources/Models/CharacterSuite/$body/WhiteVNeck" 'Alternate uniform gameplay and crowd FBXs, including five crowd animation clips.'
    }
    Add-AssetLink '02 Blender - Animation rigs' "$body - Body and face animation.blend" "Resources/Models/Animation/OpenStance_${body}_Animation.blend" 'Updated body and face rigs, modular appearance, marker guides and animation layers.'
    foreach ($tier in @('High','Mid','Far')) {
        $category = "04 Gameplay - LODs and exports/$body"
        Add-AssetLink $category "$tier - Editable fighter.blend" "Resources/Models/CharacterSuite/$body/Gameplay_$tier.blend" 'Updated editable gameplay fighter with modular hair, eyebrows and equipment.'
        foreach ($outfit in @('Dobok','Sparring')) {
            Add-AssetLink $category "$tier - $outfit.fbx" "Resources/Models/CharacterSuite/$body/Gameplay_${tier}_$outfit.fbx" 'Gameplay export; not a characterized MotionBuilder target.'
        }
    }
    Add-AssetLink "04 Gameplay - LODs and exports/$body" 'Preview - Full detail.blend' "Resources/Models/CharacterSuite/$body/Preview.blend" 'Current full-detail preview with separate body and face rigs and modular parts.'
    foreach ($tier in @('Near','Far')) {
        Add-AssetLink "05 Crowd - Rigs and animations/$body" "$tier - Editable crowd rig.blend" "Resources/Models/CharacterSuite/$body/Crowd_$tier.blend" 'Simplified 25-bone crowd skeleton, separate from the production fighter mocap target.'
        Add-AssetLink "05 Crowd - Rigs and animations/$body" "$tier - Crowd export.fbx" "Resources/Models/CharacterSuite/$body/Crowd_$tier.fbx" 'Simplified crowd export.'
    }
    foreach ($clip in @('Cheer','SeatedClap','SeatedIdle','StandingIdle','Wave')) {
        Add-AssetLink "05 Crowd - Rigs and animations/$body" "Animation - $clip.fbx" "Resources/Models/CharacterSuite/$body/Crowd_$clip.fbx" 'Existing crowd animation clip; use the matching crowd skeleton.'
    }
}
Add-AssetLink '02 Blender - Animation rigs' 'All nine presets - Scene workspace.blend' 'Resources/Models/OpenStance_Characters_Workspace.blend' 'Select one of nine updated Fighter scenes.'
if (Test-Path -LiteralPath (Join-Path $modelRoot 'Animation/DummyMotionTests/README.md')) {
    Add-AssetLink '08 Sample animations/Dummy full-body tests' 'READ ME - Dummy tests.md' 'Resources/Models/Animation/DummyMotionTests/README.md' 'Playback instructions, test scope and correct MotionBuilder capture target.'
}
foreach ($preset in @('Male_Athletic','Male_Lean','Female_Athletic','Female_Strong')) {
    $category = "03 Characters - Latest hair and gear/$preset"
    Add-AssetLink $category "$preset - Editable character.blend" "Resources/Models/CharacterVariations/$preset/Character.blend" "Updated modular preview; select RIG_Body_$preset for customization."
    Add-AssetLink $category 'Portrait.png' "Resources/Models/CharacterVariations/$preset/Portrait.png" 'Saved character portrait.'
    Add-AssetLink $category 'Full body.png' "Resources/Models/CharacterVariations/$preset/Full_Body.png" 'Saved full body preview.'
    if (Test-Path -LiteralPath (Join-Path $modelRoot "CharacterVariations/$preset/Eyebrows_Closeup.png")) {
        Add-AssetLink $category 'Eyebrows - Updated closeup.png' "Resources/Models/CharacterVariations/$preset/Eyebrows_Closeup.png" 'Fine tapered eyebrow fibers attached to the facial skin rig.'
    }
}
Add-AssetLink '06 Gear - Editable libraries' 'Chest guards - Latest belt overlap.blend' 'Resources/Models/ProtectorReferenceV2/Chest_Protector_Library.blend' 'Latest two chest protector designs; edit the separate protector collections.'
if (Test-Path -LiteralPath (Join-Path $modelRoot 'CharacterVariations/Eyebrow_Styles_Comparison.jpg')) {
    Add-AssetLink '03 Characters - Latest hair and gear' 'Eyebrow styles - Comparison.jpg' 'Resources/Models/CharacterVariations/Eyebrow_Styles_Comparison.jpg' 'Six styles available through EyebrowStyle on the body rig; earlier comparison render.'
}
Add-AssetLink '06 Gear - Editable libraries' 'Helmets - Three designs.blend' 'Resources/Models/HelmetVariants/Helmet_Design_Library.blend' 'Three helmet designs with separate editable parts.'
Add-AssetLink '07 Guides and validation' 'Mocap - 41 marker specification.md' 'Docs/Mocap_Marker_Set.md' 'Capture marker specification; guides require actual performer calibration.'
Add-AssetLink '07 Guides and validation' 'Blender animation and retargeting.md' 'Resources/Models/Animation/README.md' 'Detailed rig, marker and export workflow.'
Add-AssetLink '07 Guides and validation' 'Hair and character controls.md' 'Resources/Models/CharacterVariations/README.md' 'Style selectors and current preview limitations.'
Add-AssetLink '07 Guides and validation' 'Gameplay suite.md' 'Resources/Models/CharacterSuite/README.md' 'Current suite profiles, controls and exports.'
Add-AssetLink '07 Guides and validation' 'Current rebuild report.md' 'Resources/Models/CharacterSuite/REBUILD_REPORT.md' 'Published rebuild, validation scope and recovery archive.'
Add-AssetLink '07 Guides and validation' 'Helmet fit - 72 combinations.json' 'Resources/Models/CharacterVariations/helmet_fit_validation.json' 'Static selector and fit checks, not full animation collision certification.'
foreach ($source in @('Archive','MetaHuman','Textures','Modular','CreatorFighters','Fitted','GearUpgrade','HelmetStudy','ProtectorStudy','MotionBuilder','TestFighter','Referee')) {
    Add-AssetLink '90 Sources staging and legacy' $source "Resources/Models/$source" 'Pipeline source, staging or older asset; use categories 01-06 for current entry points.'
}
if (Test-Path -LiteralPath (Join-Path $modelRoot 'Animation/Samples/Medium_Sparring_Samples.blend')) {
    Add-AssetLink '08 Sample animations' 'Medium - Sparring demo.blend' 'Resources/Models/Animation/Samples/Medium_Sparring_Samples.blend' 'Authored guard, punch and front-kick rig tests; press Space in Blender.'
    Add-AssetLink '08 Sample animations' 'Sample animations and FBXs' 'Resources/Models/Animation/Samples' 'Three baked animation FBXs, editable Blender demo and rendered previews.'
    Add-AssetLink '08 Sample animations' 'Sample animation guide.md' 'Resources/Models/Animation/Samples/README.md' 'Playback, clip selection and test limitations.'
    if (Test-Path -LiteralPath (Join-Path $modelRoot 'Animation/Samples/Front_Kick.blend')) {
        Add-AssetLink '08 Sample animations' 'Latest cloth and belt revision.blend' 'Resources/Models/Animation/Samples/Front_Kick.blend' 'Fitted hip silhouette, pelvis/thigh garment weights, kick corrections and fitted belt.'
        Add-AssetLink '08 Sample animations' 'Cloth revision - files and guide' 'Resources/Models/ROMRepair' 'Current corrected sample, export validation and garment build guide.'
    }
}
if (Test-Path -LiteralPath (Join-Path $modelRoot 'Animation/RangeOfMotion/REPORT.md')) {
    Add-AssetLink '07 Guides and validation' 'Range of motion - Findings.md' 'Resources/Models/Animation/RangeOfMotion/REPORT.md' 'Historical failures before repair; follow the linked repair report for current status.'
    Add-AssetLink '08 Sample animations' 'Range of motion - Updated Medium.blend' 'Resources/Models/ROMRepair/Audit/Updated_Medium/ROM_Audit.blend' '23 labeled motion checkpoints; diagnostic scene, not a cleared production asset.'
    Add-AssetLink '08 Sample animations' 'Range of motion - All presets' 'Resources/Models/ROMRepair/Audit' 'Nine library presets plus updated Medium, with and without gear.'
}
foreach ($body in $bodies) {
    if (Test-Path -LiteralPath (Join-Path $modelRoot "TPose/OpenStance_${body}_Tpose.blend")) {
        Add-AssetLink '09 T-pose inspection' "OpenStance_${body}_Tpose" "Resources/Models/TPose/OpenStance_${body}_Tpose.blend" 'Full character inspection copy with horizontal arms and wardrobe controls.'
    }
}
if (Test-Path -LiteralPath (Join-Path $modelRoot 'CollarEarRepair/published.json')) {
    Add-AssetLink '07 Guides and validation' 'Garment repairs - Current scope.md' 'Resources/Models/CollarEarRepair/README.md' 'Collar clearance and rounded ear padding.'
    Add-AssetLink '07 Guides and validation' 'Garment repairs - Pose comparisons' 'Resources/Models/CollarEarRepair/QA' 'Collar motion and helmet detail comparisons across nine presets.'
    Add-AssetLink '08 Sample animations' 'White V-neck - Sample FBXs' 'Resources/Models/Animation/Samples/WhiteVNeck' 'Updated V-neck uniform with authored guard, punch and kick clips.'
    Add-AssetLink '08 Sample animations' 'Live Blender cloth - Front kick.blend' 'Resources/Models/Animation/Physics/LiveCloth_Pilot.blend' 'Hybrid demo: animated uniform and live belt-tail cloth; play from frame 1.'
    Add-AssetLink '08 Sample animations' 'Live Blender cloth - Guide.md' 'Resources/Models/Animation/Physics/README.md' 'Simulation workflow and limitations.'
} elseif (Test-Path -LiteralPath (Join-Path $modelRoot 'FinishRefinementV2/published.json')) {
    Add-AssetLink '07 Guides and validation' 'Garment repairs - Current scope.md' 'Resources/Models/FinishRefinementV2/README.md' 'Hair boundaries, ponytail detail, belt knot and export material refinements.'
    Add-AssetLink '07 Guides and validation' 'Garment repairs - Pose comparisons' 'Resources/Models/FinishRefinementV2/VisualQA' 'Sparring style and movement checks across nine presets.'
    Add-AssetLink '08 Sample animations' 'White V-neck - Sample FBXs' 'Resources/Models/Animation/Samples/WhiteVNeck' 'Updated V-neck uniform with authored guard, punch and kick clips.'
    Add-AssetLink '08 Sample animations' 'Live Blender cloth - Front kick.blend' 'Resources/Models/Animation/Physics/LiveCloth_Pilot.blend' 'Hybrid demo: animated uniform and live belt-tail cloth; play from frame 1.'
    Add-AssetLink '08 Sample animations' 'Live Blender cloth - Guide.md' 'Resources/Models/Animation/Physics/README.md' 'Simulation workflow and limitations.'
} elseif (Test-Path -LiteralPath (Join-Path $modelRoot 'SparringFitRepair/published.json')) {
    Add-AssetLink '07 Guides and validation' 'Garment repairs - Current scope.md' 'Resources/Models/SparringFitRepair/README.md' 'Shoulder and protector clearance, helmet taper and fitted hair coverage repairs.'
    Add-AssetLink '07 Guides and validation' 'Garment repairs - Pose comparisons' 'Resources/Models/SparringFitRepair/VisualQA' 'Sparring style and movement checks across nine presets.'
    Add-AssetLink '08 Sample animations' 'White V-neck - Sample FBXs' 'Resources/Models/Animation/Samples/WhiteVNeck' 'Updated V-neck uniform with authored guard, punch and kick clips.'
    Add-AssetLink '08 Sample animations' 'Live Blender cloth - Front kick.blend' 'Resources/Models/Animation/Physics/LiveCloth_Pilot.blend' 'Hybrid demo: animated uniform and live belt-tail cloth; play from frame 1.'
    Add-AssetLink '08 Sample animations' 'Live Blender cloth - Guide.md' 'Resources/Models/Animation/Physics/README.md' 'Simulation workflow and limitations.'
} elseif (Test-Path -LiteralPath (Join-Path $modelRoot 'VisualFitRepair/published.json')) {
    Add-AssetLink '07 Guides and validation' 'Garment repairs - Current scope.md' 'Resources/Models/VisualFitRepair/README.md' 'Sleeve clearance, coarse crowd hair coverage and chest protector fit repairs.'
    Add-AssetLink '07 Guides and validation' 'Garment repairs - Pose comparisons' 'Resources/Models/VisualFitRepair/VisualQA' 'Repeated front, back, side and movement checks after visual repairs.'
    Add-AssetLink '08 Sample animations' 'White V-neck - Sample FBXs' 'Resources/Models/Animation/Samples/WhiteVNeck' 'Updated V-neck uniform with authored guard, punch and kick clips.'
    Add-AssetLink '08 Sample animations' 'Live Blender cloth - Front kick.blend' 'Resources/Models/Animation/Physics/LiveCloth_Pilot.blend' 'Updated live cloth demonstration; play sequentially from frame 1.'
    Add-AssetLink '08 Sample animations' 'Live Blender cloth - Guide.md' 'Resources/Models/Animation/Physics/README.md' 'Simulation switch, cache workflow and Unreal runtime limitations.'
} elseif (Test-Path -LiteralPath (Join-Path $modelRoot 'HairClothRevision/published.json')) {
    Add-AssetLink '07 Guides and validation' 'Garment repairs - Current scope.md' 'Resources/Models/HairClothRevision/README.md' 'Crew-cut repair and optional Blender cloth workflow and limitations.'
    Add-AssetLink '07 Guides and validation' 'Garment repairs - Pose comparisons' 'Resources/Models/HairClothRevision' 'Hair comparisons, cloth trial and export validation.'
    Add-AssetLink '08 Sample animations' 'White V-neck - Sample FBXs' 'Resources/Models/Animation/Samples/WhiteVNeck' 'Updated V-neck uniform with authored guard, punch and kick clips.'
    Add-AssetLink '08 Sample animations' 'Live Blender cloth - Front kick.blend' 'Resources/Models/Animation/Physics/LiveCloth_Pilot.blend' 'Live cloth demonstration; play sequentially from frame 1.'
    Add-AssetLink '08 Sample animations' 'Live Blender cloth - Guide.md' 'Resources/Models/Animation/Physics/README.md' 'Simulation switch, cache workflow and Unreal runtime limitations.'
} elseif (Test-Path -LiteralPath (Join-Path $modelRoot 'OpeningRepair/published.json')) {
    Add-AssetLink '07 Guides and validation' 'Garment repairs - Current scope.md' 'Resources/Models/OpeningRepair/README.md' 'Repaired skin overlap inside wrist and ankle openings.'
    Add-AssetLink '07 Guides and validation' 'Garment repairs - Pose comparisons' 'Resources/Models/OpeningRepair' 'Wrist and ankle close-ups, motion checks and validation.'
    Add-AssetLink '08 Sample animations' 'White V-neck - Sample FBXs' 'Resources/Models/Animation/Samples/WhiteVNeck' 'Repaired V-neck uniform with authored guard, punch and kick clips.'
} elseif (Test-Path -LiteralPath (Join-Path $modelRoot 'TailoredDoboks/published.json')) {
    Add-AssetLink '07 Guides and validation' 'Garment repairs - Current scope.md' 'Resources/Models/TailoredDoboks/README.md' 'Slimmer fit for both dobok styles, with body shapes, rigs and animation preserved.'
    Add-AssetLink '07 Guides and validation' 'Garment repairs - Pose comparisons' 'Resources/Models/TailoredDoboks' 'Tailored uniform before/after images, motion checks and validation.'
    Add-AssetLink '08 Sample animations' 'White V-neck - Sample FBXs' 'Resources/Models/Animation/Samples/WhiteVNeck' 'Tailored V-neck uniform with authored guard, punch and kick clips.'
} elseif (Test-Path -LiteralPath (Join-Path $modelRoot 'AlternateJacketRepair/published.json')) {
    Add-AssetLink '07 Guides and validation' 'Garment repairs - Current scope.md' 'Resources/Models/AlternateJacketRepair/README.md' 'Both wrap and V-neck uniforms now use the repaired garment setup.'
    Add-AssetLink '07 Guides and validation' 'Garment repairs - Pose comparisons' 'Resources/Models/AlternateJacketRepair' 'Alternate jacket motion checks, validation and installed-file manifest.'
    Add-AssetLink '08 Sample animations' 'White V-neck - Sample FBXs' 'Resources/Models/Animation/Samples/WhiteVNeck' 'Guard, punch and front-kick clips with the repaired alternate uniform.'
} elseif (Test-Path -LiteralPath (Join-Path $modelRoot 'GarmentRollout/published.json')) {
    Add-AssetLink '07 Guides and validation' 'Garment repairs - Current scope.md' 'Resources/Models/GarmentRollout/README.md' 'Repaired previews, gameplay, crowds, animation masters and MotionBuilder targets.'
    Add-AssetLink '07 Guides and validation' 'Garment repairs - Pose comparisons' 'Resources/Models/GarmentRollout' 'Motion-check renders, per-profile validation and publication manifest.'
} elseif (Test-Path -LiteralPath (Join-Path $modelRoot 'ROMRepair/published.json')) {
    Add-AssetLink '07 Guides and validation' 'Garment repairs - Current scope.md' 'Resources/Models/ROMRepair/README.md' 'Repaired high-detail models, validation and remaining LOD scope.'
}
if (Test-Path -LiteralPath (Join-Path $modelRoot 'FinalRefinement/HairRepeat/published.json')) {
    Add-AssetLink '07 Guides and validation' 'Remaining model work.md' 'Resources/Models/FinalRefinement/REMAINING_WORK.md' 'Verified scope and unfinished hair, clothing, runtime and mocap checks.'
    Add-AssetLink '07 Guides and validation' 'Hair wrap repair and remaining work.md' 'Resources/Models/FinalRefinement/README.md' 'Installed hair seam repair, review images and explicit remaining limitations.'
    Add-AssetLink '08 Sample animations' 'EXPERIMENTAL - Secondary cloth kick.blend' 'Resources/Models/Animation/Physics/SecondaryCloth_Kick_Study.blend' 'Medium wrap: fitted belt contact and constrained uniform physics. Play from frame 1; other bodies/moves unvalidated.'
    if (Test-Path -LiteralPath (Join-Path $modelRoot 'Animation/Physics/SecondaryCloth_Kick_Study_VNeck.blend')) {
        Add-AssetLink '08 Sample animations' 'EXPERIMENTAL - V-neck secondary cloth kick.blend' 'Resources/Models/Animation/Physics/SecondaryCloth_Kick_Study_VNeck.blend' 'Medium V-neck: fitted belt contact and constrained uniform physics. Play from frame 1; other bodies/moves unvalidated.'
    }
}
$manifest = [ordered]@{
    generated_at = (Get-Date).ToString('o')
    shortcut_count = $entries.Count
    validation = 'Every shortcut was reopened; target and working directory verified. Original assets are not moved or modified.'
    entries = $entries
}
$manifest | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $libraryRoot 'asset_index.json') -Encoding UTF8
Write-Output "Verified $($entries.Count) shortcuts in $libraryRoot"
