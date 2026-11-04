#include "Menu/OpenStanceFighterStudio.h"

#include "Animation/AnimSequenceBase.h"
#include "Components/PointLightComponent.h"
#include "Components/RectLightComponent.h"
#include "Components/SceneCaptureComponent2D.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/TextureRenderTarget2D.h"
#include "Engine/World.h"
#include "GameFramework/Actor.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialInterface.h"

namespace
{
	const TCHAR* PreviewMaterialPath = TEXT("/Game/Menu/FighterPreview/M_FighterPreview.M_FighterPreview");
	const TCHAR* StancePath = TEXT("/Game/Animation/Moves/Placeholder/AS_Placeholder_Stance.AS_Placeholder_Stance");

	const TCHAR* BodyTypeStem(EOpenStanceBodyType BodyType)
	{
		switch (BodyType)
		{
		case EOpenStanceBodyType::LeanTall: return TEXT("LeanTall");
		case EOpenStanceBodyType::Stocky: return TEXT("Stocky");
		case EOpenStanceBodyType::Tall: return TEXT("Tall");
		default: return TEXT("Compact");
		}
	}

	/**
	 * The portrait fighter of each body type and sex: the suite body in the traditional dobok, no gear
	 * (Tools/Blender/build_portrait_fighters.sh, Tools/Unreal/import_portrait_fighters.py). Built on the rig the
	 * placeholder clips are authored on, so the stance plays on it as authored.
	 */
	FString PortraitMeshPath(EOpenStanceBodyType BodyType, EOpenStanceSex Sex)
	{
		const FString Name = FString::Printf(TEXT("SK_Portrait_%s_%s"), BodyTypeStem(BodyType), Sex == EOpenStanceSex::Female ? TEXT("Female") : TEXT("Male"));
		return FString::Printf(TEXT("/Game/Characters/Fighters/Portrait/%s/%s.%s"), *Name.RightChop(12), *Name, *Name);
	}

	/** Fallback when a portrait fighter is missing: the body type's MetaHuman body build (no uniform). */
	FString BodyMeshPath(EOpenStanceBodyType BodyType)
	{
		const TCHAR* Stem = BodyTypeStem(BodyType);
		return FString::Printf(TEXT("/Game/Characters/Fighters/Export/MH_Fighter%s_FullBody.MH_Fighter%s_FullBody"), Stem, Stem);
	}

	// Studios sit well away from any level geometry, a few metres apart so one studio's lights do not reach the next.
	const FVector StudioBase(0.0, 0.0, -20000.0);
	const double StudioSpacing = 2000.0;
	int32 NextStudio = 0;

	// Camera: a long lens from the fighter's front, framing 2.0 m of height (the tallest build is 1.92 m).
	const double CameraDistance = 520.0;
	const double CameraHeight = 97.0;
	const float CameraFOV = 16.4f;

	/** Scene depth (cm) beyond which a pixel is empty; M_FighterPreview's DepthCutoff. */
	const float DepthCutoff = 10000.0f;
}

bool UOpenStanceFighterStudio::Init(UWorld* World, bool bFaceLeft)
{
	UMaterialInterface* PreviewMaterial = LoadObject<UMaterialInterface>(nullptr, PreviewMaterialPath);
	Stance = LoadObject<UAnimSequenceBase>(nullptr, StancePath);
	if (!World || !PreviewMaterial || !Stance)
	{
		UE_LOG(LogTemp, Warning, TEXT("Fighter studio unavailable (world %s, material %s, stance %s)"),
			World ? TEXT("found") : TEXT("missing"), PreviewMaterial ? TEXT("found") : TEXT("missing"), Stance ? TEXT("found") : TEXT("missing"));
		return false;
	}

	const FVector Origin = StudioBase + FVector(StudioSpacing * (NextStudio++ % 64), 0.0, 0.0);
	FActorSpawnParameters Params;
	Params.ObjectFlags = RF_Transient;
	Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
#if WITH_EDITOR
	Params.bHideFromSceneOutliner = true;
#endif
	Actor = World->SpawnActor<AActor>(AActor::StaticClass(), FTransform(Origin), Params);
	if (!Actor)
	{
		return false;
	}
	USceneComponent* Root = NewObject<USceneComponent>(Actor, TEXT("StudioRoot"));
	Actor->SetRootComponent(Root);
	Root->RegisterComponent();
	Root->SetWorldLocation(Origin);

	// The fighter: the stance clip faces the mesh's +Y. Turned 45 degrees off the camera toward the side it faces on the
	// menu (right for Chung, left for Hong, mirrored so the lead leg is the one nearer the opponent's panel).
	Body = NewObject<USkeletalMeshComponent>(Actor, TEXT("StudioFighter"));
	Body->SetupAttachment(Root);
	Body->SetRelativeRotation(FRotator(0.0, bFaceLeft ? 45.0 : -45.0, 0.0));
	Body->SetRelativeScale3D(FVector(bFaceLeft ? -1.0 : 1.0, 1.0, 1.0));
	Body->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Body->SetCastShadow(false);
	Body->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
	Body->bUseBoundsFromLeaderPoseComponent = false;
	Body->RegisterComponent();

	// Lights: a soft key from the camera's left, a fill from its right and a rim from behind, each reaching only this studio.
	const auto AddLight = [this, Root](ULocalLightComponent* Light, const FVector& Offset, float Intensity, const FLinearColor& Colour)
	{
		Light->SetupAttachment(Root);
		Light->SetRelativeLocation(Offset);
		Light->SetRelativeRotation((-Offset + FVector(0.0, 0.0, CameraHeight)).Rotation());
		Light->SetIntensityUnits(ELightUnits::Candelas);
		Light->SetIntensity(Intensity);
		Light->SetLightColor(Colour);
		Light->SetCastShadows(false);
		Light->RegisterComponent();
	};
	URectLightComponent* Key = NewObject<URectLightComponent>(Actor, TEXT("StudioKey"));
	Key->SetSourceWidth(120.0f);
	Key->SetSourceHeight(160.0f);
	Key->SetAttenuationRadius(900.0f);
	AddLight(Key, FVector(-260.0, 330.0, 230.0), 60.0f, FLinearColor(1.0f, 0.96f, 0.9f));
	UPointLightComponent* Fill = NewObject<UPointLightComponent>(Actor, TEXT("StudioFill"));
	Fill->SetAttenuationRadius(900.0f);
	Fill->SetSourceRadius(60.0f);
	AddLight(Fill, FVector(300.0, 300.0, 120.0), 12.0f, FLinearColor(0.85f, 0.9f, 1.0f));
	UPointLightComponent* Rim = NewObject<UPointLightComponent>(Actor, TEXT("StudioRim"));
	Rim->SetAttenuationRadius(900.0f);
	Rim->SetSourceRadius(30.0f);
	AddLight(Rim, FVector(120.0, -260.0, 220.0), 40.0f, FLinearColor(0.8f, 0.88f, 1.0f));

	// Captures: colour (tonemapped, fixed exposure so the portrait never pumps) and scene depth for the cut-out.
	const FVector CameraOffset(0.0, CameraDistance, CameraHeight);
	const FRotator CameraRotation(0.0, -90.0, 0.0);
	const auto AddCapture = [this, Root, &CameraOffset, &CameraRotation](const TCHAR* Name, ESceneCaptureSource Source,
		UTextureRenderTarget2D* Target) -> USceneCaptureComponent2D*
	{
		USceneCaptureComponent2D* Capture = NewObject<USceneCaptureComponent2D>(Actor, Name);
		Capture->SetupAttachment(Root);
		Capture->SetRelativeLocationAndRotation(CameraOffset, CameraRotation);
		Capture->FOVAngle = CameraFOV;
		Capture->TextureTarget = Target;
		Capture->CaptureSource = Source;
		Capture->bCaptureEveryFrame = false;
		Capture->bCaptureOnMovement = false;
		Capture->bAlwaysPersistRenderingState = true;
		Capture->PrimitiveRenderMode = ESceneCapturePrimitiveRenderMode::PRM_UseShowOnlyList;
		Capture->ShowOnlyComponents.Add(Body);
		Capture->ShowFlags.SetMotionBlur(false);
		Capture->ShowFlags.SetFog(false);
		Capture->ShowFlags.SetVolumetricFog(false);
		Capture->ShowFlags.SetAtmosphere(false);
		Capture->RegisterComponent();
		return Capture;
	};
	ColorTarget = NewObject<UTextureRenderTarget2D>(this, TEXT("StudioColor"));
	ColorTarget->RenderTargetFormat = RTF_RGBA8_SRGB;
	ColorTarget->ClearColor = FLinearColor::Black;
	ColorTarget->InitAutoFormat(Width, Height);
	ColorTarget->UpdateResourceImmediate(true);
	DepthTarget = NewObject<UTextureRenderTarget2D>(this, TEXT("StudioDepth"));
	DepthTarget->RenderTargetFormat = RTF_R32f;
	DepthTarget->ClearColor = FLinearColor(1.0e6f, 0.0f, 0.0f, 1.0f);
	DepthTarget->InitAutoFormat(Width, Height);
	DepthTarget->UpdateResourceImmediate(true);

	ColorCapture = AddCapture(TEXT("StudioColorCapture"), ESceneCaptureSource::SCS_FinalColorLDR, ColorTarget);
	FPostProcessSettings& Post = ColorCapture->PostProcessSettings;
	Post.bOverride_AutoExposureMethod = true;
	Post.AutoExposureMethod = EAutoExposureMethod::AEM_Manual;
	Post.bOverride_AutoExposureApplyPhysicalCameraExposure = true;
	Post.AutoExposureApplyPhysicalCameraExposure = false;
	Post.bOverride_AutoExposureBias = true;
	Post.AutoExposureBias = 0.0f;
	Post.bOverride_BloomIntensity = true;
	Post.BloomIntensity = 0.0f;
	Post.bOverride_VignetteIntensity = true;
	Post.VignetteIntensity = 0.0f;
	ColorCapture->PostProcessBlendWeight = 1.0f;
	DepthCapture = AddCapture(TEXT("StudioDepthCapture"), ESceneCaptureSource::SCS_SceneDepth, DepthTarget);

	Material = UMaterialInstanceDynamic::Create(PreviewMaterial, this);
	Material->SetTextureParameterValue(TEXT("Color"), ColorTarget);
	Material->SetTextureParameterValue(TEXT("Depth"), DepthTarget);
	Material->SetScalarParameterValue(TEXT("DepthCutoff"), DepthCutoff);
	return true;
}

void UOpenStanceFighterStudio::SetFighter(EOpenStanceBodyType BodyType, EOpenStanceSex Sex)
{
	if (!Body || (bHasBody && BodyType == ShownBodyType && Sex == ShownSex))
	{
		return;
	}
	USkeletalMesh* Mesh = LoadObject<USkeletalMesh>(nullptr, *PortraitMeshPath(BodyType, Sex));
	if (!Mesh)
	{
		UE_LOG(LogTemp, Warning, TEXT("Fighter studio: no portrait fighter at %s; showing the body build"), *PortraitMeshPath(BodyType, Sex));
		Mesh = LoadObject<USkeletalMesh>(nullptr, *BodyMeshPath(BodyType));
	}
	if (!Mesh)
	{
		UE_LOG(LogTemp, Warning, TEXT("Fighter studio: no body build at %s"), *BodyMeshPath(BodyType));
		return;
	}
	ShownSex = Sex;
	Body->SetSkeletalMesh(Mesh);
	Body->SetAnimationMode(EAnimationMode::AnimationSingleNode);
	Body->SetAnimation(Stance);
	Body->SetPlayRate(0.0f);
	ShownBodyType = BodyType;
	bHasBody = true;
}

void UOpenStanceFighterStudio::Update(float Seconds)
{
	if (!Body || !bHasBody || !ColorCapture || !DepthCapture)
	{
		return;
	}
	// Posed by hand: menu captures also run in editor worlds, which never tick actors.
	const float Length = FMath::Max(Stance->GetPlayLength(), 0.01f);
	Body->SetPosition(FMath::Fmod(FMath::Max(Seconds, 0.0f), Length), false);
	Body->TickAnimation(0.0f, false);
	Body->RefreshBoneTransforms();
	Body->UpdateBounds();
	Body->MarkRenderDynamicDataDirty();
	ColorCapture->CaptureScene();
	DepthCapture->CaptureScene();
}

void UOpenStanceFighterStudio::Shutdown()
{
	if (IsValid(Actor))
	{
		Actor->Destroy();
	}
	Actor = nullptr;
	Body = nullptr;
	ColorCapture = nullptr;
	DepthCapture = nullptr;
}

void UOpenStanceFighterStudio::BeginDestroy()
{
	// Garbage collection may already be tearing the world down, so only drop the references here; the portrait widget
	// calls Shutdown when it goes, and the transient actor otherwise goes with its world.
	Actor = nullptr;
	Body = nullptr;
	ColorCapture = nullptr;
	DepthCapture = nullptr;
	Super::BeginDestroy();
}
