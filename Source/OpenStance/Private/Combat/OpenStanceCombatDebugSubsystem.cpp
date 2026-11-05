#include "Combat/OpenStanceCombatDebugSubsystem.h"

#include "Animation/AnimMontage.h"
#include "Animation/AnimSequenceBase.h"
#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "Combat/OpenStanceCameraPresets.h"
#include "Combat/OpenStanceCombatOverlay.h"
#include "Combat/OpenStanceGreyboxProof.h"
#include "DrawDebugHelpers.h"
#include "Engine/Canvas.h"
#include "Debug/DebugDrawService.h"
#include "Components/SceneComponent.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerStart.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/DataTable.h"
#include "Engine/StaticMesh.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialInterface.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "HAL/IConsoleManager.h"
#include "InputCoreTypes.h"
#include "Engine/LocalPlayer.h"
#include "Kismet/GameplayStatics.h"
#include "Menu/OpenStanceMatchModel.h"
#include "Menu/OpenStanceMenuContent.h"
#include "Menu/OpenStanceMenuSubsystem.h"
#include "Menu/OpenStanceUserSettings.h"
#include "Misc/ConfigCacheIni.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"

DEFINE_LOG_CATEGORY_STATIC(LogOpenStanceCombat, Log, All);

namespace
{
	constexpr float CombatDebugFixedStepSeconds = 1.0f / 60.0f;
	constexpr int32 InputLogLines = 8;

	// How fast the match camera catches up with its preset's pose (OpenStanceCameraPresets places it).
	constexpr float FollowCameraSpeed = 6.0f;
	const TCHAR* MoveTablePath = TEXT("/Game/Combat/DT_MoveData.DT_MoveData");
	const TCHAR* MenuMapName = TEXT("L_MainMenu");
	const TCHAR* InvertConfigSection = TEXT("OpenStance.Greybox");
	const TCHAR* InvertConfigKey = TEXT("InvertRightStickY");

#if !UE_BUILD_SHIPPING
	TAutoConsoleVariable<int32> CVarInvertRightStickY(TEXT("os.InvertRightStickY"), 0,
		TEXT("1 flips the right stick's Y axis before the greybox reads it, if the controller path reports up as negative. The View button toggles it and saves the choice."), ECVF_Default);

	TAutoConsoleVariable<int32> CVarGreyboxAutoStart(TEXT("os.GreyboxAutoStart"), 1,
		TEXT("1 starts the greybox when Play begins on any map except the main menu, so no console command is needed; 0 leaves it to os.Greybox."), ECVF_Default);
#endif

	// Shown on every build, so a demo can switch between the character fighters and the shapes.
	TAutoConsoleVariable<int32> CVarGreyboxFighterMesh(TEXT("os.GreyboxFighterMesh"), 1,
		TEXT("1 shows the greybox fighters as characters playing the technique animations (placeholders until mocap); 0 shows the shape fighters. Takes effect when the greybox starts."), ECVF_Default);

	// The character the greybox fighters wear: the production Medium body, its head and the Medium gear.
	const TCHAR* FighterBodyPath = TEXT("/Game/Characters/Fighters/Export/MH_FighterBase_Body.MH_FighterBase_Body");
	const TCHAR* FighterHeadPath = TEXT("/Game/Characters/Fighters/Export/MH_FighterBase_Head.MH_FighterBase_Head");
	const TCHAR* FighterGearFolder = TEXT("/Game/Characters/Fighters/Gear/Medium");
	const TCHAR* FighterGearParts[] = { TEXT("Jacket"), TEXT("Pants"), TEXT("Belt"), TEXT("Protector"), TEXT("Helmet"), TEXT("Gloves"), TEXT("FootGuards") };
	const TCHAR* TeamGearMaterials[2] = { TEXT("/Game/Characters/Fighters/Gear/Clean/MI_FighterGear_Chung.MI_FighterGear_Chung"),
		TEXT("/Game/Characters/Fighters/Gear/Clean/MI_FighterGear_Hong.MI_FighterGear_Hong") };
	const TCHAR* StanceAnimationPath = TEXT("/Game/Animation/Moves/Placeholder/AS_Placeholder_Stance.AS_Placeholder_Stance");

	/**
	 * The match fighter for a roster fighter and side: the suite body in the layered dobok with its sparring gear in the
	 * side's colour (Tools/Blender/build_match_fighters.sh, Tools/Unreal/import_match_fighters.py), on the rig the
	 * placeholder clips are authored on, so the techniques play on it without stretching the body out of the gear.
	 */
	FString MatchFighterPath(const FString& PortraitKey, int32 Side)
	{
		const FString Name = FString::Printf(TEXT("SK_Match_%s_%s"), *PortraitKey, Side == 0 ? TEXT("Chung") : TEXT("Hong"));
		return FString::Printf(TEXT("/Game/Characters/Fighters/Match/%s/%s.%s"), *Name.RightChop(9), *Name, *Name);
	}

	/**
	 * The mirrored copy of a placeholder clip (<clip>_Mirror beside it: left leg and right lead), or null. Playing it
	 * replaces scaling the fighter by -1, which turned the gear's faces inside out (it read as see-through from behind).
	 */
	UAnimSequenceBase* MirrorClip(UAnimSequenceBase* Clip)
	{
		static TMap<TWeakObjectPtr<UAnimSequenceBase>, TWeakObjectPtr<UAnimSequenceBase>> Mirrors;
		if (!Clip)
		{
			return nullptr;
		}
		if (const TWeakObjectPtr<UAnimSequenceBase>* Found = Mirrors.Find(Clip))
		{
			return Found->Get();
		}
		const FString Package = Clip->GetOutermost()->GetName() + TEXT("_Mirror");
		const FString Name = Clip->GetName() + TEXT("_Mirror");
		UAnimSequenceBase* Mirror = LoadObject<UAnimSequenceBase>(nullptr, *(Package + TEXT(".") + Name), nullptr, LOAD_NoWarn | LOAD_Quiet);
		Mirrors.Add(Clip, Mirror);
		return Mirror;
	}

	/** The animation a montage plays (its first segment), so the greybox can scrub it frame by frame. */
	UAnimSequenceBase* MontageClip(UAnimMontage* Montage)
	{
		if (!Montage || Montage->SlotAnimTracks.Num() == 0 || Montage->SlotAnimTracks[0].AnimTrack.AnimSegments.Num() == 0)
		{
			return nullptr;
		}
		return Montage->SlotAnimTracks[0].AnimTrack.AnimSegments[0].GetAnimReference();
	}

	struct FPadButton
	{
		FKey Key;
		const TCHAR* Name;
	};

	// Built on use: FKey statics are not safe to read from another file's static initializers.
	TArray<FPadButton> GetPadButtons()
	{
		return {
			{ EKeys::Gamepad_FaceButton_Bottom, TEXT("A") }, { EKeys::Gamepad_FaceButton_Right, TEXT("B") },
			{ EKeys::Gamepad_FaceButton_Left, TEXT("X") }, { EKeys::Gamepad_FaceButton_Top, TEXT("Y") },
			{ EKeys::Gamepad_LeftShoulder, TEXT("LB") }, { EKeys::Gamepad_RightShoulder, TEXT("RB") },
			{ EKeys::Gamepad_LeftTrigger, TEXT("LT") }, { EKeys::Gamepad_RightTrigger, TEXT("RT") },
			{ EKeys::Gamepad_LeftThumbstick, TEXT("L3") }, { EKeys::Gamepad_RightThumbstick, TEXT("R3") },
			{ EKeys::Gamepad_DPad_Up, TEXT("D-pad Up") }, { EKeys::Gamepad_DPad_Down, TEXT("D-pad Down") },
			{ EKeys::Gamepad_DPad_Left, TEXT("D-pad Left") }, { EKeys::Gamepad_DPad_Right, TEXT("D-pad Right") },
			{ EKeys::Gamepad_Special_Right, TEXT("Menu") }, { EKeys::Gamepad_Special_Left, TEXT("View") }
		};
	}
}

bool UOpenStanceCombatDebugSubsystem::ShouldCreateSubsystem(UObject* Outer) const
{
	const UWorld* World = Cast<UWorld>(Outer);
	return World && (World->IsGameWorld());
}

void UOpenStanceCombatDebugSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
	Super::Initialize(Collection);
	DebugDrawHandle = UDebugDrawService::Register(TEXT("Game"), FDebugDrawDelegate::CreateUObject(this, &UOpenStanceCombatDebugSubsystem::DrawOverlay));
#if !UE_BUILD_SHIPPING
	// The View button's saved choice (HandleInvertToggle) outlives the session; the config path is per user and not in Git.
	bool bSavedInvert = false;
	if (GConfig && GConfig->GetBool(InvertConfigSection, InvertConfigKey, bSavedInvert, GGameUserSettingsIni) && bSavedInvert)
	{
		CVarInvertRightStickY->Set(1, ECVF_SetByConsole);
	}
#endif
}

void UOpenStanceCombatDebugSubsystem::Deinitialize()
{
	if (UOpenStanceMenuSubsystem* Menu = GetMenu())
	{
		Menu->OnMatchRequested.RemoveDynamic(this, &UOpenStanceCombatDebugSubsystem::HandleMatchRequested);
		Menu->OnLeaveMatch.Remove(LeaveMatchHandle);
	}
	DestroyBodies();
	UDebugDrawService::Unregister(DebugDrawHandle);
	Super::Deinitialize();
}

void UOpenStanceCombatDebugSubsystem::OnWorldBeginPlay(UWorld& InWorld)
{
	Super::OnWorldBeginPlay(InWorld);

	// The menu raises a match when one is chosen and again when the pause menu restarts it, and tells us when the player
	// goes back to the main menu. This is how the menu levels and the arenas hand over to each other.
	if (UOpenStanceMenuSubsystem* Menu = GetMenu())
	{
		if (!Menu->OnMatchRequested.IsAlreadyBound(this, &UOpenStanceCombatDebugSubsystem::HandleMatchRequested))
		{
			Menu->OnMatchRequested.AddDynamic(this, &UOpenStanceCombatDebugSubsystem::HandleMatchRequested);
		}
		LeaveMatchHandle = Menu->OnLeaveMatch.AddUObject(this, &UOpenStanceCombatDebugSubsystem::HandleLeaveMatch);
	}
#if !UE_BUILD_SHIPPING
	// Started from the first tick, not here: possessing the default pawn would take the view back from the greybox camera.
	bAutoStartPending = CVarGreyboxAutoStart.GetValueOnGameThread() != 0 && UWorld::RemovePIEPrefix(InWorld.GetMapName()) != MenuMapName;
#endif
}

TStatId UOpenStanceCombatDebugSubsystem::GetStatId() const
{
	RETURN_QUICK_DECLARE_CYCLE_STAT(UOpenStanceCombatDebugSubsystem, STATGROUP_Tickables);
}

const UDataTable* UOpenStanceCombatDebugSubsystem::GetMoveTable()
{
	if (!MoveTable)
	{
		// The reviewed table when it exists in the project, the built-in Milestone 1 moves otherwise.
		MoveTable = Cast<UDataTable>(FSoftObjectPath(MoveTablePath).TryLoad());
		if (!MoveTable || MoveTable->RowStruct != FOpenStanceMoveRow::StaticStruct())
		{
			MoveTable = FOpenStanceMoveData::CreateSeedTable(this);
		}
	}
	return MoveTable;
}

FVector UOpenStanceCombatDebugSubsystem::ToWorld(const FVector2D& Position, float Z) const
{
	return Origin + FVector(Position.X, Position.Y, Z);
}

void UOpenStanceCombatDebugSubsystem::SetGreyboxActive(bool bActive)
{
	bGreybox = bActive;
	UWorld* World = GetWorld();
	if (!bActive)
	{
		if (Camera)
		{
			Camera->Destroy();
			Camera = nullptr;
		}
		DestroyBodies();
		SetDefaultPawnHidden(false);
		bModelLinked = false;
		return;
	}

	// The overlay is what shows which move the Skill Stick produced, so starting the greybox turns it on.
	bCombatDebug = true;

	// The side chosen on Side Select: the controller drives that fighter and the other side is idle (or blocking, os.AIMode).
	if (const UOpenStanceMenuSubsystem* Menu = GetMenu())
	{
		PlayerIndex = Menu->GetSession().PlayerSide == EOpenStanceSide::Hong ? 1 : 0;
	}
	else
	{
		PlayerIndex = 0;
	}
	Sim.SetMoveTable(GetMoveTable());
	Sim.StartMatch(200.0f);

	// The Skill Stick follows the Options screen: the dead zone and the input window, 0.20 to 0.40 s (GDD 7.8).
	if (const UOpenStanceUserSettings* Settings = UOpenStanceUserSettings::Get())
	{
		Sim.Fighters[PlayerIndex].Recognizer.Config = FOpenStanceSkillStickConfig::FromSettings(Settings->SkillStickDeadZone, Settings->StickInputWindow);
	}
	Accumulator = 0.0f;
	PrintedInputEvents = 0;

	// The mat plane: the floor where the player spawned, inside the level, not under the world origin.
	Origin = FindArenaOrigin();

	// The camera follows the controlling fighter with the Match preset (OpenStanceCameraPresets): behind and out to the
	// side, looking at the point between the fighters, so the opponent stays in frame and the sticks match the screen.
	// UpdateCamera keeps it there every tick; os.CameraPreset previews the replay angles.
	if (APlayerController* Controller = World->GetFirstPlayerController())
	{
		BuildBodies();
		SetDefaultPawnHidden(true);
		FVector Position;
		FRotator Rotation;
		GetFollowCameraPose(Position, Rotation);
		Camera = World->SpawnActor<ACameraActor>(Position, Rotation);
		Camera->FindComponentByClass<UCameraComponent>()->SetFieldOfView(GetCameraPreset().FieldOfViewDeg);
		Controller->SetViewTargetWithBlend(Camera);
		LinkMatchModel();

		// With the match HUD showing, the side-bar debug text would overlap its name plates; os.CombatDebug 1 brings it back.
		if (bModelLinked)
		{
			bCombatDebug = false;
		}
	}
}

namespace
{
	// The parts of a greybox fighter, in the order they are stored per fighter.
	enum EBodyPart : int32
	{
		PartTorso, PartHead, PartBelt, PartLegLeft, PartLegRight, PartFootLeft, PartFootRight,
		PartArmLeft, PartArmRight, PartFistLeft, PartFistRight, BodyPartCount
	};

	enum class EBodyShape : uint8 { Cube, Sphere, Cylinder };

	EBodyShape ShapeOf(int32 Part)
	{
		switch (Part)
		{
		case PartTorso: case PartBelt: return EBodyShape::Cube;
		case PartLegLeft: case PartLegRight: case PartArmLeft: case PartArmRight: return EBodyShape::Cylinder;
		default: return EBodyShape::Sphere;
		}
	}

	FLinearColor BodyColour(int32 Fighter)
	{
		return Fighter == 0 ? FLinearColor(0.05f, 0.22f, 0.95f) : FLinearColor(0.95f, 0.06f, 0.06f);
	}

	FLinearColor PartColour(int32 Fighter, int32 Part)
	{
		switch (Part)
		{
		case PartHead: case PartFistLeft: case PartFistRight: return FLinearColor(0.80f, 0.55f, 0.38f);
		case PartBelt: return FLinearColor(0.01f, 0.01f, 0.01f);
		case PartFootLeft: case PartFootRight: return BodyColour(Fighter) * 0.45f;
		default: return BodyColour(Fighter);
		}
	}

	float Smooth01(float Alpha)
	{
		Alpha = FMath::Clamp(Alpha, 0.0f, 1.0f);
		return Alpha * Alpha * (3.0f - 2.0f * Alpha);
	}
}

void UOpenStanceCombatDebugSubsystem::BuildBodies()
{
	DestroyBodies();
	UWorld* World = GetWorld();
	UStaticMesh* Meshes[3] = {
		LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Cube.Cube")),
		LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Sphere.Sphere")),
		LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Cylinder.Cylinder"))
	};
	UMaterialInterface* BaseMaterial = LoadObject<UMaterialInterface>(nullptr, TEXT("/Engine/BasicShapes/BasicShapeMaterial.BasicShapeMaterial"));
	if (!World || !Meshes[0] || !Meshes[1] || !Meshes[2])
	{
		return;
	}

	for (int32 Fighter = 0; Fighter < 2; ++Fighter)
	{
		AActor* Actor = World->SpawnActor<AActor>();
		USceneComponent* Root = NewObject<USceneComponent>(Actor, TEXT("Root"));
		Root->SetMobility(EComponentMobility::Movable);
		Actor->SetRootComponent(Root);
		Root->RegisterComponent();
		BodyActors.Add(Actor);

		for (int32 Part = 0; Part < BodyPartCount; ++Part)
		{
			UStaticMeshComponent* Component = NewObject<UStaticMeshComponent>(Actor);
			Component->SetMobility(EComponentMobility::Movable);
			Component->SetStaticMesh(Meshes[static_cast<int32>(ShapeOf(Part))]);
			Component->SetCollisionEnabled(ECollisionEnabled::NoCollision);
			Component->SetupAttachment(Root);
			Component->RegisterComponent();

			UMaterialInstanceDynamic* Material = BaseMaterial ? UMaterialInstanceDynamic::Create(BaseMaterial, this) : nullptr;
			if (Material)
			{
				Material->SetVectorParameterValue(TEXT("Color"), PartColour(Fighter, Part));
				Component->SetMaterial(0, Material);
			}
			BodyParts.Add(Component);
			BodyMaterials.Add(Material);
		}
	}
	SeenContacts = 0;
	bFlashing[0] = bFlashing[1] = false;
	FlashUntil[0] = FlashUntil[1] = 0.0;

	// The character fighters replace the shapes when their assets load; the shapes keep updating underneath, hidden.
	if (CVarGreyboxFighterMesh.GetValueOnGameThread() != 0 && BuildFighterMeshes())
	{
		for (UStaticMeshComponent* Component : BodyParts)
		{
			Component->SetVisibility(false);
		}
	}
}

bool UOpenStanceCombatDebugSubsystem::BuildFighterMeshes()
{
	USkeletalMesh* BodyMesh = LoadObject<USkeletalMesh>(nullptr, FighterBodyPath);
	StanceAnimation = LoadObject<UAnimSequenceBase>(nullptr, StanceAnimationPath);
	if (!BodyMesh || !StanceAnimation || BodyActors.Num() != 2)
	{
		UE_LOG(LogTemp, Warning, TEXT("Greybox: character fighters unavailable (body %s, stance animation %s); showing the shapes."),
			BodyMesh ? TEXT("found") : TEXT("missing"), StanceAnimation ? TEXT("found") : TEXT("missing"));
		return false;
	}
	USkeletalMesh* HeadMesh = LoadObject<USkeletalMesh>(nullptr, FighterHeadPath);
	// The fighters chosen on Fighter Select, as match fighters in their side's colour, when those are built
	const UOpenStanceMenuSubsystem* Menu = GetMenu();
	const TArray<FOpenStanceFighterProfile>& Roster = OpenStanceMenuContent::GetRoster();
	for (int32 Fighter = 0; Fighter < 2; ++Fighter)
	{
		const int32 RosterIndex = Menu ? (Fighter == 0 ? Menu->GetSession().ChungFighter : Menu->GetSession().HongFighter) : Fighter;
		USkeletalMesh* MatchMesh = Roster.IsValidIndex(RosterIndex)
			? LoadObject<USkeletalMesh>(nullptr, *MatchFighterPath(OpenStanceMenuContent::GetPortraitKey(Roster[RosterIndex]), Fighter), nullptr, LOAD_NoWarn | LOAD_Quiet)
			: nullptr;
		AActor* Actor = BodyActors[Fighter];
		USceneComponent* Pivot = NewObject<USceneComponent>(Actor, TEXT("FighterPivot"));
		Pivot->SetMobility(EComponentMobility::Movable);
		Pivot->SetupAttachment(Actor->GetRootComponent());
		Pivot->RegisterComponent();

		USkeletalMeshComponent* Body = NewObject<USkeletalMeshComponent>(Actor, TEXT("FighterBody"));
		Body->SetSkeletalMesh(MatchMesh ? MatchMesh : BodyMesh);
		Body->SetupAttachment(Pivot);
		// The fighter faces the mesh's +Y; the pivot's forward is +X.
		Body->SetRelativeRotation(FRotator(0.0, -90.0, 0.0));
		Body->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		Body->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
		Body->SetAnimationMode(EAnimationMode::AnimationSingleNode);
		Body->RegisterComponent();
		Body->SetAnimation(StanceAnimation);
		Body->SetPlayRate(0.0f);

		const auto Follower = [Actor, Body](USkeletalMesh* Mesh, const TCHAR* Name) -> USkeletalMeshComponent*
		{
			if (!Mesh)
			{
				return nullptr;
			}
			USkeletalMeshComponent* Part = NewObject<USkeletalMeshComponent>(Actor, Name);
			Part->SetSkeletalMesh(Mesh);
			Part->SetupAttachment(Body);
			Part->SetCollisionEnabled(ECollisionEnabled::NoCollision);
			Part->RegisterComponent();
			Part->SetLeaderPoseComponent(Body);
			return Part;
		};
		if (MatchMesh)
		{
			// One mesh: body, head, hair, dobok and gear (already in the side's colour)
			FighterPivots.Add(Pivot);
			FighterBodies.Add(Body);
			ShownAnimation[Fighter] = StanceAnimation;
			continue;
		}
		Follower(HeadMesh, TEXT("FighterHead"));
		UMaterialInterface* Team = LoadObject<UMaterialInterface>(nullptr, TeamGearMaterials[Fighter]);
		for (const TCHAR* Part : FighterGearParts)
		{
			const FString Path = FString::Printf(TEXT("%s/SK_Fighter_%s.SK_Fighter_%s"), FighterGearFolder, Part, Part);
			USkeletalMeshComponent* Gear = Follower(LoadObject<USkeletalMesh>(nullptr, *Path), *FString::Printf(TEXT("Fighter%s"), Part));
			// The protector and helmet take the side's colour (Chung blue, Hong red): their team-coloured slots only.
			if (Gear && Team && (FCString::Strcmp(Part, TEXT("Protector")) == 0 || FCString::Strcmp(Part, TEXT("Helmet")) == 0))
			{
				for (int32 Slot = 0; Slot < Gear->GetNumMaterials(); ++Slot)
				{
					const UMaterialInterface* Current = Gear->GetMaterial(Slot);
					if (Current && Current->GetName().Contains(TEXT("FighterGear")))
					{
						Gear->SetMaterial(Slot, Team);
					}
				}
			}
		}
		FighterPivots.Add(Pivot);
		FighterBodies.Add(Body);
		ShownAnimation[Fighter] = StanceAnimation;
	}
	return true;
}

void UOpenStanceCombatDebugSubsystem::UpdateFighterMesh(int32 Index, const FVector& Base, const FQuat& BodyRotation, bool bMirror,
	const FOpenStanceAttackRequest* Attack, float Overall)
{
	if (!FighterBodies.IsValidIndex(Index) || !FighterPivots.IsValidIndex(Index))
	{
		return;
	}
	USkeletalMeshComponent* Body = FighterBodies[Index];
	FighterPivots[Index]->SetWorldLocationAndRotation(Base, BodyRotation);

	UAnimSequenceBase* Clip = nullptr;
	float Time = 0.0f;
	if (Attack)
	{
		UAnimMontage* Montage = Attack->Row.ResolveMontage(Attack->Leg, true).LoadSynchronous();
		Clip = MontageClip(Montage);
		if (Clip)
		{
			// A feint only gets as far as the chamber.
			const float Fraction = Attack->bFake ? 0.5f * FMath::Clamp(Overall, 0.0f, 1.0f) : FMath::Clamp(Overall, 0.0f, 1.0f);
			Time = Fraction * Clip->GetPlayLength();
		}
	}
	if (!Clip)
	{
		Clip = StanceAnimation;
		const UWorld* World = GetWorld();
		Time = World && Clip ? FMath::Fmod(static_cast<float>(World->GetTimeSeconds()), FMath::Max(Clip->GetPlayLength(), 0.01f)) : 0.0f;
	}
	if (!Clip)
	{
		return;
	}
	// The mirror cases play the clip's mirrored copy; only without one does the fighter fall back to a -1 scale across
	// its own left-right axis (the mesh's X).
	UAnimSequenceBase* Mirrored = bMirror ? MirrorClip(Clip) : nullptr;
	if (Mirrored)
	{
		Time = Time / FMath::Max(Clip->GetPlayLength(), 0.01f) * Mirrored->GetPlayLength();
		Clip = Mirrored;
	}
	Body->SetRelativeScale3D(FVector(bMirror && !Mirrored ? -1.0 : 1.0, 1.0, 1.0));
	if (ShownAnimation[Index] != Clip)
	{
		Body->SetAnimation(Clip);
		Body->SetPlayRate(0.0f);
		ShownAnimation[Index] = Clip;
	}
	Body->SetPosition(Time, false);
}

void UOpenStanceCombatDebugSubsystem::DestroyBodies()
{
	for (AActor* Actor : BodyActors)
	{
		if (IsValid(Actor))
		{
			Actor->Destroy();
		}
	}
	BodyActors.Reset();
	BodyParts.Reset();
	BodyMaterials.Reset();
	FighterPivots.Reset();
	FighterBodies.Reset();
	ShownAnimation[0] = ShownAnimation[1] = nullptr;
}

void UOpenStanceCombatDebugSubsystem::UpdateBodies()
{
	UWorld* World = GetWorld();
	if (!World || BodyParts.Num() != 2 * BodyPartCount)
	{
		return;
	}

	// A new contact flashes the defender white for a moment.
	for (; SeenContacts < Sim.Contacts.Num(); ++SeenContacts)
	{
		FlashUntil[Sim.Contacts[SeenContacts].Defender == EOpenStanceSide::Chung ? 0 : 1] = World->GetTimeSeconds() + 0.15;
	}

	for (int32 Index = 0; Index < 2; ++Index)
	{
		const FOpenStanceFighterSim& F = Sim.Fighters[Index];
		const float H = F.Motion.HeightCm;
		const FOpenStanceAttackRequest* Attack = F.Machine.GetCurrentAttack();
		const EOpenStanceCombatState CombatState = F.State.CombatState;

		// How far through the technique the fighter is. Blend is the limb's reach, 0 resting to 1 fully extended; Overall is
		// the fraction of the whole animation; SpinFraction is how much of the body turn has happened.
		float Blend = 0.0f, Overall = 0.0f, SpinFraction = 0.0f;
		if (Attack && (CombatState == EOpenStanceCombatState::AttackStartup || CombatState == EOpenStanceCombatState::AttackActive || CombatState == EOpenStanceCombatState::AttackRecovery))
		{
			const FOpenStanceMoveRow& Row = Attack->Row;
			const float Total = FMath::Max(Row.StartupSeconds + Row.ActiveSeconds + Row.RecoverySeconds, 0.001f);
			const float Elapsed = F.Machine.GetStateElapsed();
			const float Reach = Attack->bFake ? 0.5f : 1.0f;
			if (CombatState == EOpenStanceCombatState::AttackStartup)
			{
				const float Progress = FMath::Clamp(Elapsed / FMath::Max(Row.StartupSeconds, 0.001f), 0.0f, 1.0f);
				Blend = 0.6f * Reach * Progress;
				Overall = Elapsed / Total;
				SpinFraction = 0.5f * Progress;
			}
			else if (CombatState == EOpenStanceCombatState::AttackActive)
			{
				const float Progress = FMath::Clamp(Elapsed / FMath::Max(Row.ActiveSeconds, 0.001f), 0.0f, 1.0f);
				Blend = Reach * (0.6f + 0.4f * Progress);
				Overall = (Row.StartupSeconds + Elapsed) / Total;
				SpinFraction = 0.5f + 0.5f * Progress;
			}
			else
			{
				const float Progress = FMath::Clamp(Elapsed / FMath::Max(Row.RecoverySeconds, 0.001f), 0.0f, 1.0f);
				Blend = Reach * (1.0f - Progress) * (Attack->bFake ? 0.5f : 1.0f);
				Overall = (Row.StartupSeconds + Row.ActiveSeconds + Elapsed) / Total;
				SpinFraction = 1.0f;
			}
		}

		// Spinning kicks turn the whole body round once; jump kicks leave the ground.
		const float SpinDegrees = Attack && Attack->Row.bSpinning && !Attack->bFake ? 360.0f * Smooth01(SpinFraction) : 0.0f;
		const float Lift = Attack && Attack->bJump ? 0.26f * H * FMath::Sin(PI * FMath::Clamp(Overall, 0.0f, 1.0f)) : 0.0f;

		const FVector Facing0 = FVector(F.Motion.Facing.X, F.Motion.Facing.Y, 0.0).GetSafeNormal();
		const FVector Facing = FQuat(FVector::UpVector, FMath::DegreesToRadians(SpinDegrees)).RotateVector(Facing0);
		const FVector Right(-Facing.Y, Facing.X, 0.0);
		const FQuat BodyRotation = FRotationMatrix::MakeFromXY(Facing, Right).ToQuat();
		const FVector Base = ToWorld(F.Motion.Position, Lift);
		const FVector Up = FVector::UpVector;

		const float Bob = FMath::Sin(F.Motion.BouncePhase * 2.0f * PI) * 0.012f * H;
		const float Hop = F.Motion.bSwitching ? FMath::Sin(PI * F.Motion.SwitchBlend) * 0.05f * H : 0.0f;
		const FVector Hip = Base + Up * (0.49f * H + Bob);

		// The feet at rest: the lead foot forward and the back foot behind, on the sides the stance names.
		const bool bRightLead = F.State.Stance == EOpenStanceStance::RightLead;
		const float Forward = 0.14f * H, Lateral = 0.09f * H;
		FVector FootRight = Base + Facing * (bRightLead ? Forward : -Forward) + Right * Lateral + Up * (0.04f * H + Hop);
		FVector FootLeft = Base + Facing * (bRightLead ? -Forward : Forward) - Right * Lateral + Up * (0.04f * H + Hop);

		// The guard sets the fists' height.
		float GuardHeight = 0.70f;
		switch (F.State.Guard)
		{
		case EOpenStanceGuard::High: GuardHeight = 0.80f; break;
		case EOpenStanceGuard::Cross: GuardHeight = 0.72f; break;
		case EOpenStanceGuard::Mixed: GuardHeight = 0.68f; break;
		default: GuardHeight = 0.56f; break;
		}
		FVector FistRight = Base + Up * (GuardHeight * H) + Facing * (0.17f * H + (bRightLead ? 0.04f * H : 0.0f)) + Right * (0.07f * H);
		FVector FistLeft = Base + Up * (GuardHeight * H) + Facing * (0.17f * H + (bRightLead ? 0.0f : 0.04f * H)) - Right * (0.07f * H);

		// The throwing limb reaches for the trace's tip.
		if (Attack && Blend > 0.0f)
		{
			const FVector Tip = FOpenStanceHitRegistry::SyntheticTip(F.GetBody(), Facing0, Attack->Row, 1.0f, Sim.Hits) + Origin + Up * Lift;
			const bool bRightSide = Attack->Leg == EOpenStanceLegSide::Right;
			if (Attack->Row.Limb == EOpenStanceStrikeLimb::Glove)
			{
				FVector& Fist = bRightSide ? FistRight : FistLeft;
				Fist = FMath::Lerp(Fist, Tip, Smooth01(Blend));
			}
			else
			{
				FVector& Foot = bRightSide ? FootRight : FootLeft;
				Foot = FMath::Lerp(Foot, Tip, Smooth01(Blend));
			}
		}

		const auto Part = [this, Index](int32 Which) { return BodyParts[Index * BodyPartCount + Which].Get(); };
		const auto Limb = [](UStaticMeshComponent* Component, const FVector& From, const FVector& To, float Radius)
		{
			const FVector Along = To - From;
			const float Length = FMath::Max(static_cast<float>(Along.Size()), 1.0f);
			Component->SetWorldLocationAndRotation((From + To) * 0.5, FRotationMatrix::MakeFromZ(Along).ToQuat());
			Component->SetWorldScale3D(FVector(Radius * 2.0f / 100.0f, Radius * 2.0f / 100.0f, Length / 100.0f));
		};
		const auto Ball = [](UStaticMeshComponent* Component, const FVector& Centre, float Radius)
		{
			Component->SetWorldLocationAndRotation(Centre, FQuat::Identity);
			Component->SetWorldScale3D(FVector(Radius * 2.0f / 100.0f));
		};
		const auto Box = [&BodyRotation](UStaticMeshComponent* Component, const FVector& Centre, const FVector& Size)
		{
			Component->SetWorldLocationAndRotation(Centre, BodyRotation);
			Component->SetWorldScale3D(Size / 100.0f);
		};

		// The character fighter: authored right-leg from a left-lead stance, so a left-leg technique (or, idle, a right-lead
		// stance) is the mirror image.
		const bool bAttacking = Attack && (CombatState == EOpenStanceCombatState::AttackStartup || CombatState == EOpenStanceCombatState::AttackActive
			|| CombatState == EOpenStanceCombatState::AttackRecovery);
		const bool bMirror = bAttacking ? Attack->Leg == EOpenStanceLegSide::Left : bRightLead;
		UpdateFighterMesh(Index, Base, BodyRotation, bMirror, bAttacking ? Attack : nullptr, Overall);

		const FVector HipLeft = Hip - Right * (0.055f * H), HipRight = Hip + Right * (0.055f * H);
		const FVector Shoulder = Hip + Up * (0.30f * H);
		Limb(Part(PartLegLeft), HipLeft, FootLeft, 0.055f * H);
		Limb(Part(PartLegRight), HipRight, FootRight, 0.055f * H);
		Ball(Part(PartFootLeft), FootLeft, 0.05f * H);
		Ball(Part(PartFootRight), FootRight, 0.05f * H);
		Box(Part(PartTorso), Hip + Up * (0.17f * H), FVector(0.11f * H, 0.22f * H, 0.31f * H));
		Box(Part(PartBelt), Hip + Up * (0.035f * H), FVector(0.125f * H, 0.235f * H, 0.03f * H));
		Ball(Part(PartHead), Hip + Up * (0.405f * H), 0.062f * H);
		Limb(Part(PartArmLeft), Shoulder - Right * (0.125f * H), FistLeft, 0.04f * H);
		Limb(Part(PartArmRight), Shoulder + Right * (0.125f * H), FistRight, 0.04f * H);
		Ball(Part(PartFistLeft), FistLeft, 0.05f * H);
		Ball(Part(PartFistRight), FistRight, 0.05f * H);

		// The hit flash: the defender's limbs and trunk go white while it lasts.
		const bool bFlash = World->GetTimeSeconds() < FlashUntil[Index];
		if (bFlash != bFlashing[Index])
		{
			bFlashing[Index] = bFlash;
			for (const int32 Which : { static_cast<int32>(PartTorso), static_cast<int32>(PartLegLeft), static_cast<int32>(PartLegRight), static_cast<int32>(PartArmLeft), static_cast<int32>(PartArmRight) })
			{
				if (UMaterialInstanceDynamic* Material = BodyMaterials[Index * BodyPartCount + Which].Get())
				{
					Material->SetVectorParameterValue(TEXT("Color"), bFlash ? FLinearColor::White : BodyColour(Index));
				}
			}
		}
	}
}

UOpenStanceMenuSubsystem* UOpenStanceCombatDebugSubsystem::GetMenu() const
{
	UWorld* World = GetWorld();
	ULocalPlayer* LocalPlayer = World ? World->GetFirstLocalPlayerFromController() : nullptr;
	return LocalPlayer ? LocalPlayer->GetSubsystem<UOpenStanceMenuSubsystem>() : nullptr;
}

bool UOpenStanceCombatDebugSubsystem::IsMenuMap() const
{
	return GetWorld() && UWorld::RemovePIEPrefix(GetWorld()->GetMapName()) == MenuMapName;
}

void UOpenStanceCombatDebugSubsystem::LinkMatchModel()
{
	// The Match screen's scoreboard, stamina bars, clock, penalties and referee call now show this match, and the pause menu
	// holds it. The model is told once per change; the HUD only reads it.
	UOpenStanceMenuSubsystem* Menu = GetMenu();
	if (!Menu)
	{
		bModelLinked = false;
		return;
	}
	const TArray<FOpenStanceFighterProfile>& Roster = OpenStanceMenuContent::GetRoster();
	const FOpenStanceMenuSession& Session = Menu->GetSession();
	const FString ChungName = Roster.IsValidIndex(Session.ChungFighter) ? Roster[Session.ChungFighter].Name : FString(TEXT("Chung"));
	const FString HongName = Roster.IsValidIndex(Session.HongFighter) ? Roster[Session.HongFighter].Name : FString(TEXT("Hong"));
	ModelSync.Begin(Sim, *Menu->GetMatchModel(), ChungName, HongName, GetMoveTable());
	bModelLinked = true;

	// The HUD is a widget of the level the menu was in; a new arena needs it built again.
	Menu->ReplaceScreen(EOpenStanceMenuScreen::Match);
}

void UOpenStanceCombatDebugSubsystem::HandleMatchRequested(const FOpenStanceMatchSetup& Setup)
{
	if (bGreybox)
	{
		// The pause menu's Restart: a fresh match in this arena.
		SetGreyboxActive(true);
		return;
	}
	if (!IsMenuMap())
	{
		return;
	}

	// From the menu level: travel to the chosen arena, where the match starts itself (OnWorldBeginPlay).
	const FString* Arena = Setup.Choices.Find(TEXT("Arena"));
	FString Map = TEXT("L_TrainingDojang");
	if (Arena)
	{
		if (*Arena == TEXT("Club Dojang")) { Map = TEXT("L_ClubDojang"); }
		else if (*Arena == TEXT("National Arena")) { Map = TEXT("L_NationalArena"); }
		else if (*Arena == TEXT("Olympic Arena")) { Map = TEXT("L_CompetitionArena"); }
	}
	UGameplayStatics::OpenLevel(this, FName(*(FString(TEXT("/Game/Maps/")) + Map)));
}

void UOpenStanceCombatDebugSubsystem::HandleLeaveMatch()
{
	if (IsMenuMap())
	{
		return;
	}

	// Back from an arena to the menu level, opening at the main menu rather than the title.
	if (UOpenStanceMenuSubsystem* Menu = GetMenu())
	{
		Menu->bReturnToMainOnLoad = true;
	}
	UGameplayStatics::OpenLevel(this, FName(*(FString(TEXT("/Game/Maps/")) + MenuMapName)));
}

void UOpenStanceCombatDebugSubsystem::SetDefaultPawnHidden(bool bHidden)
{
	// The engine's default pawn is a visible grey ball the sticks fly around. While the greybox runs the fighters are the
	// display and the sticks belong to Chung, so the pawn is hidden and ignores movement and look input.
	APlayerController* Controller = GetWorld() ? GetWorld()->GetFirstPlayerController() : nullptr;
	if (!Controller)
	{
		return;
	}
	if (APawn* Pawn = Controller->GetPawn())
	{
		Pawn->SetActorHiddenInGame(bHidden);
		Pawn->SetActorEnableCollision(!bHidden);
	}
	if (bHidden)
	{
		Controller->SetIgnoreMoveInput(true);
		Controller->SetIgnoreLookInput(true);
	}
	else
	{
		Controller->ResetIgnoreMoveInput();
		Controller->ResetIgnoreLookInput();
	}
}

FVector UOpenStanceCombatDebugSubsystem::FindArenaOrigin() const
{
	UWorld* World = GetWorld();
	if (!World)
	{
		return FVector::ZeroVector;
	}

	// The centre of the ring: the levels name the four lines of the fighting square Mat_Square_N, _S, _E and _W. The PlayerStart
	// is at one end of the ring and the world origin is not always inside the room.
	FBox Ring(ForceInit);
	for (TActorIterator<AActor> Candidate(World); Candidate; ++Candidate)
	{
		if (Candidate->GetActorNameOrLabel().StartsWith(TEXT("Mat_Square")))
		{
			Ring += Candidate->GetComponentsBoundingBox(true);
		}
	}
	if (Ring.IsValid)
	{
		return FVector(Ring.GetCenter().X, Ring.GetCenter().Y, Ring.Max.Z);
	}

	// No named ring: start where the player is, the pawn the level spawned, else the level's PlayerStart, else the world
	// origin. A trace from high above the origin would land on the roof.
	FVector Start = FVector::ZeroVector;
	AActor* Pawn = nullptr;
	if (const APlayerController* Controller = World->GetFirstPlayerController())
	{
		Pawn = Controller->GetPawn();
	}
	if (Pawn)
	{
		Start = Pawn->GetActorLocation();
	}
	else
	{
		for (TActorIterator<APlayerStart> PlayerStart(World); PlayerStart; ++PlayerStart)
		{
			Start = PlayerStart->GetActorLocation();
			break;
		}
	}

	// The floor: the first surface below that point. Starting a little above it keeps the trace inside the room.
	FCollisionQueryParams Params(SCENE_QUERY_STAT(OpenStanceArenaFloor), false);
	if (Pawn)
	{
		Params.AddIgnoredActor(Pawn);
	}
	FHitResult Hit;
	if (World->LineTraceSingleByChannel(Hit, Start + FVector(0.0, 0.0, 50.0), Start - FVector(0.0, 0.0, 2000.0), ECC_Visibility, Params))
	{
		Start.Z = Hit.ImpactPoint.Z;
	}
	return Start;
}

const FOpenStanceCameraPreset& UOpenStanceCombatDebugSubsystem::GetCameraPreset() const
{
	const FOpenStanceCameraPreset* Preset = OpenStanceCameraPresets::Find(CameraPreset);
	return Preset ? *Preset : OpenStanceCameraPresets::Match();
}

bool UOpenStanceCombatDebugSubsystem::SetCameraPreset(FName Name, FString& OutMessage)
{
	if (const FOpenStanceCameraPreset* Preset = OpenStanceCameraPresets::Find(Name))
	{
		CameraPreset = Preset->Name;
		OutMessage = FString::Printf(TEXT("Camera: %s - %s"), *Preset->Name.ToString(), Preset->Use);
		return true;
	}
	OutMessage = TEXT("Usage: os.CameraPreset <Name>. Presets:");
	for (const FOpenStanceCameraPreset& Preset : OpenStanceCameraPresets::All())
	{
		OutMessage += FString::Printf(TEXT("\n  %s - %s"), *Preset.Name.ToString(), Preset.Use);
	}
	return false;
}

void UOpenStanceCombatDebugSubsystem::GetFollowCameraPose(FVector& OutPosition, FRotator& OutRotation) const
{
	// Placed from the fighter the controller drives, whichever side that is.
	const FOpenStanceFighterSim& Player = Sim.Fighters[PlayerIndex];
	const FOpenStanceFighterSim& Opponent = Sim.Fighters[1 - PlayerIndex];
	OpenStanceCameraPresets::Pose(GetCameraPreset(), ToWorld(Player.Motion.Position), ToWorld(Opponent.Motion.Position), OutPosition, OutRotation);
}

void UOpenStanceCombatDebugSubsystem::UpdateCamera(float DeltaTime)
{
	if (!Camera)
	{
		return;
	}
	FVector Position;
	FRotator Rotation;
	GetFollowCameraPose(Position, Rotation);
	Camera->SetActorLocationAndRotation(FMath::VInterpTo(Camera->GetActorLocation(), Position, DeltaTime, FollowCameraSpeed),
		FMath::RInterpTo(Camera->GetActorRotation(), Rotation, DeltaTime, FollowCameraSpeed));
	if (UCameraComponent* Lens = Camera->FindComponentByClass<UCameraComponent>())
	{
		Lens->SetFieldOfView(FMath::FInterpTo(Lens->FieldOfView, GetCameraPreset().FieldOfViewDeg, DeltaTime, FollowCameraSpeed));
	}
}

void UOpenStanceCombatDebugSubsystem::SetShowInput(bool bOn)
{
	bShowInput = bOn;
	InputLog.Reset();
	HeldButtons.Reset();
}

void UOpenStanceCombatDebugSubsystem::UpdateInputLog()
{
	const APlayerController* PC = GetWorld() ? GetWorld()->GetFirstPlayerController() : nullptr;
	if (!PC)
	{
		return;
	}
	for (const FPadButton& Button : GetPadButtons())
	{
		const FName Name(Button.Name);
		const bool bDown = PC->IsInputKeyDown(Button.Key);
		if (bDown == HeldButtons.Contains(Name))
		{
			continue;
		}
		if (bDown)
		{
			HeldButtons.Add(Name);
		}
		else
		{
			HeldButtons.Remove(Name);
		}
		InputLog.Add(FString::Printf(TEXT("%7.2f  %s %s"), GetWorld()->GetTimeSeconds(), Button.Name, bDown ? TEXT("pressed") : TEXT("released")));
		if (InputLog.Num() > InputLogLines)
		{
			InputLog.RemoveAt(0);
		}
	}
}

void UOpenStanceCombatDebugSubsystem::ShowLiveSticks(const FOpenStanceFighterControls& Controls) const
{
	if (!GEngine)
	{
		return;
	}
	// One line per stick under fixed keys, so each updates in place instead of stacking.
	const auto Name = [](const FVector2D& Stick)
	{
		switch (FOpenStanceSkillStickRecognizer::ToDirection(Stick, 0.6f))
		{
		case EOpenStanceStickDir::Up: return TEXT("UP");
		case EOpenStanceStickDir::Down: return TEXT("DOWN");
		case EOpenStanceStickDir::Left: return TEXT("LEFT");
		case EOpenStanceStickDir::Right: return TEXT("RIGHT");
		default: return TEXT("-");
		}
	};
	GEngine->AddOnScreenDebugMessage(9001, 0.1f, FColor::White, FString::Printf(TEXT("Right stick  x %+.2f  y %+.2f  = %s"), Controls.RightStick.X, Controls.RightStick.Y, Name(Controls.RightStick)));
#if !UE_BUILD_SHIPPING
	GEngine->AddOnScreenDebugMessage(9003, 0.1f, FColor::Cyan, FString::Printf(TEXT("Right stick Y inversion: %s  (View button flips it)"), CVarInvertRightStickY.GetValueOnGameThread() != 0 ? TEXT("ON") : TEXT("OFF")));
#endif
	GEngine->AddOnScreenDebugMessage(9002, 0.1f, FColor::White,FString::Printf(TEXT("Left stick   x %+.2f  y %+.2f  = %s"), Controls.LeftStick.X, Controls.LeftStick.Y, Name(Controls.LeftStick)));
}

void UOpenStanceCombatDebugSubsystem::HandleInvertToggle()
{
#if !UE_BUILD_SHIPPING
	// The View button flips the stick Y axes and remembers the choice, so a controller path that reports up as negative can be
	// corrected from the pad with no console command.
	const APlayerController* PC = GetWorld() ? GetWorld()->GetFirstPlayerController() : nullptr;
	const bool bPressed = PC && PC->IsInputKeyDown(EKeys::Gamepad_Special_Left);
	if (bPressed && !bPrevInvertToggle)
	{
		const bool bInvert = CVarInvertRightStickY.GetValueOnGameThread() == 0;
		CVarInvertRightStickY->Set(bInvert ? 1 : 0, ECVF_SetByConsole);
		if (GConfig)
		{
			GConfig->SetBool(InvertConfigSection, InvertConfigKey, bInvert, GGameUserSettingsIni);
			GConfig->Flush(false, GGameUserSettingsIni);
		}
	}
	bPrevInvertToggle = bPressed;
#endif
}

void UOpenStanceCombatDebugSubsystem::PrintNewInputs()
{
	const FOpenStanceFighterSim& Chung = Sim.Fighters[PlayerIndex]; // the fighter the controller drives
	const int32 NewEvents = FMath::Min(Chung.InputEventCount - PrintedInputEvents, Chung.RecentInput.Num());
	PrintedInputEvents = Chung.InputEventCount;
	if (!GEngine)
	{
		return;
	}
	for (int32 Index = Chung.RecentInput.Num() - NewEvents; Index < Chung.RecentInput.Num(); ++Index)
	{
		const FOpenStanceInputEvent& Event = Chung.RecentInput[Index];
		const bool bFailed = Event.Type == EOpenStanceInputEventType::GestureRejected || Event.Type == EOpenStanceInputEventType::GestureExpired
			|| Event.Type == EOpenStanceInputEventType::GestureCancelled;
		const FColor Colour = bFailed ? FColor::Red : Event.Type == EOpenStanceInputEventType::Attack && !Event.bFake ? FColor::Green : FColor::Yellow;
		GEngine->AddOnScreenDebugMessage(-1, 3.0f, Colour, FOpenStanceCombatOverlay::DescribeInput(Event));
	}
}

void UOpenStanceCombatDebugSubsystem::SetInfiniteStamina(bool bOn)
{
	Sim.bInfiniteStamina = bOn;
	bCheatsUsed |= bOn;
}

void UOpenStanceCombatDebugSubsystem::SetScoreCheat(int32 Chung, int32 Hong)
{
	Sim.SetScore(Chung, Hong);
	bCheatsUsed = true;
}

void UOpenStanceCombatDebugSubsystem::SetClockCheat(float Seconds)
{
	Sim.SetClock(Seconds);
	bCheatsUsed = true;
}

bool UOpenStanceCombatDebugSubsystem::SetAIMode(const FString& Mode, FString& OutMessage)
{
	if (Mode.Equals(TEXT("idle"), ESearchCase::IgnoreCase))
	{
		AIMode = EOpenStanceAIMode::Idle;
	}
	else if (Mode.Equals(TEXT("block"), ESearchCase::IgnoreCase))
	{
		AIMode = EOpenStanceAIMode::Block;
	}
	else if (Mode.Equals(TEXT("mirror"), ESearchCase::IgnoreCase) || Mode.Equals(TEXT("normal"), ESearchCase::IgnoreCase))
	{
		OutMessage = TEXT("The AI opponent does not exist yet, so only idle and block are available.");
		return false;
	}
	else
	{
		OutMessage = TEXT("Usage: os.AIMode idle|block|mirror|normal");
		return false;
	}
	bCheatsUsed = true;
	OutMessage = FString::Printf(TEXT("AI mode: %s"), *Mode.ToLower());
	return true;
}

bool UOpenStanceCombatDebugSubsystem::RunProof()
{
	FOpenStanceMatchSim ProofSim;
	ProofSim.SetMoveTable(GetMoveTable());
	const TArray<FOpenStanceGreyboxProof::FStage> Stages = FOpenStanceGreyboxProof::Run(ProofSim);
	const FString Text = FOpenStanceGreyboxProof::Format(Stages, ProofSim);
	UE_LOG(LogOpenStanceCombat, Log, TEXT("%s"), *Text);
	FFileHelper::SaveStringToFile(Text, *(FPaths::ProjectLogDir() / TEXT("OpenStanceGreyboxProof.txt")), FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
	return FOpenStanceGreyboxProof::AllPassed(Stages);
}

FOpenStanceFighterControls UOpenStanceCombatDebugSubsystem::PollController() const
{
	FOpenStanceFighterControls C;
	const APlayerController* PC = GetWorld() ? GetWorld()->GetFirstPlayerController() : nullptr;
	if (!PC)
	{
		return C;
	}
	C.LeftStick = FVector2D(PC->GetInputAnalogKeyState(EKeys::Gamepad_LeftX), PC->GetInputAnalogKeyState(EKeys::Gamepad_LeftY));
	C.RightStick = FVector2D(PC->GetInputAnalogKeyState(EKeys::Gamepad_RightX), PC->GetInputAnalogKeyState(EKeys::Gamepad_RightY));
#if !UE_BUILD_SHIPPING
	if (CVarInvertRightStickY.GetValueOnGameThread() != 0)
	{
		C.RightStick.Y = -C.RightStick.Y;
	}
#endif
	C.bA = PC->IsInputKeyDown(EKeys::Gamepad_FaceButton_Bottom);
	C.bB = PC->IsInputKeyDown(EKeys::Gamepad_FaceButton_Right);
	C.bX = PC->IsInputKeyDown(EKeys::Gamepad_FaceButton_Left);
	C.bY = PC->IsInputKeyDown(EKeys::Gamepad_FaceButton_Top);
	C.bLB = PC->IsInputKeyDown(EKeys::Gamepad_LeftShoulder);
	C.bRB = PC->IsInputKeyDown(EKeys::Gamepad_RightShoulder);
	C.bLT = PC->IsInputKeyDown(EKeys::Gamepad_LeftTrigger);
	C.bRT = PC->IsInputKeyDown(EKeys::Gamepad_RightTrigger);
	if (PC->IsInputKeyDown(EKeys::Gamepad_DPad_Up)) { C.DPad = EOpenStanceDPad::Up; }
	else if (PC->IsInputKeyDown(EKeys::Gamepad_DPad_Left)) { C.DPad = EOpenStanceDPad::Left; }
	else if (PC->IsInputKeyDown(EKeys::Gamepad_DPad_Right)) { C.DPad = EOpenStanceDPad::Right; }
	else if (PC->IsInputKeyDown(EKeys::Gamepad_DPad_Down)) { C.DPad = EOpenStanceDPad::Down; }
	return C;
}

void UOpenStanceCombatDebugSubsystem::Tick(float DeltaTime)
{
	Super::Tick(DeltaTime);
	if (bAutoStartPending && GetWorld()->GetFirstPlayerController())
	{
		bAutoStartPending = false;
		SetGreyboxActive(true);
	}
	if (bShowInput)
	{
		UpdateInputLog();
	}
	if (!bGreybox)
	{
		return;
	}

	// The pause menu holds the match through the HUD's model: the simulation stops while it is paused.
	UOpenStanceMatchModel* Model = nullptr;
	if (bModelLinked)
	{
		if (UOpenStanceMenuSubsystem* Menu = GetMenu())
		{
			Model = Menu->GetMatchModel();
		}
	}
	const bool bHeld = Model && Model->IsPaused();

	// A fixed step keeps the simulation the same whatever the frame rate, and slomo scales DeltaTime for free.
	Accumulator = bHeld ? 0.0f : Accumulator + FMath::Min(DeltaTime, 0.1f);
	const FOpenStanceFighterControls PlayerControls = PollController();
	FOpenStanceFighterControls OpponentControls;
	OpponentControls.bLT = AIMode == EOpenStanceAIMode::Block;
	const FOpenStanceFighterControls& Chung = PlayerIndex == 0 ? PlayerControls : OpponentControls;
	const FOpenStanceFighterControls& Hong = PlayerIndex == 0 ? OpponentControls : PlayerControls;
	while (Accumulator >= CombatDebugFixedStepSeconds)
	{
		Sim.Step(CombatDebugFixedStepSeconds, Chung, Hong);
		Accumulator -= CombatDebugFixedStepSeconds;
	}
	if (Model)
	{
		ModelSync.Update(Sim, *Model);
	}
	UpdateCamera(DeltaTime);
	UpdateBodies();
	HandleInvertToggle();
	PrintNewInputs();
	ShowLiveSticks(PlayerControls);
	DrawWorld();
}

void UOpenStanceCombatDebugSubsystem::DrawWorld() const
{
#if ENABLE_DRAW_DEBUG
	UWorld* World = GetWorld();
	for (int32 Index = 0; Index < 2; ++Index)
	{
		const FOpenStanceFighterSim& F = Sim.Fighters[Index];
		const FColor Colour = F.Side == EOpenStanceSide::Chung ? FColor(70, 120, 255) : FColor(235, 70, 70);
		const FOpenStanceFighterBody Body = F.GetBody();
		const float Radius = Sim.Movement.CapsuleRadiusCm;
		// The solid fighters are the display; the capsule and facing arrow are the hitbox view (os.ShowHitboxes).
		if (bShowHitboxes)
		{
			DrawDebugCapsule(World, ToWorld(F.Motion.Position, Body.HeightCm * 0.5f), Body.HeightCm * 0.5f, Radius, FQuat::Identity, Colour, false, 0.0f, 0, 1.5f);
		}
		const FVector Chest = ToWorld(F.Motion.Position, Body.HeightCm * 0.7f);
		if (bShowHitboxes)
		{
			DrawDebugDirectionalArrow(World, Chest, Chest + FVector(F.Motion.Facing.X, F.Motion.Facing.Y, 0.0) * 50.0f, 20.0f, Colour, false, 0.0f, 0, 1.5f);
		}

		if (!bShowHitboxes)
		{
			continue;
		}
		// Target zones on the fighter and the limb trace of its attack (os.ShowHitboxes).
		const EOpenStanceBodyZone Zones[] = { EOpenStanceBodyZone::Head, EOpenStanceBodyZone::Trunk, EOpenStanceBodyZone::BelowBelt };
		const FColor ZoneColours[] = { FColor::Yellow, FColor::Orange, FColor(150, 150, 150) };
		for (int32 Zone = 0; Zone < 3; ++Zone)
		{
			float Bottom, Top, ZoneRadius;
			FOpenStanceHitRegistry::GetZoneBounds(Body, Zones[Zone], Sim.Hits, Bottom, Top, ZoneRadius);
			DrawDebugCylinder(World, ToWorld(F.Motion.Position, Bottom), ToWorld(F.Motion.Position, Top), ZoneRadius, 16, ZoneColours[Zone], false, 0.0f, 0, 1.0f);
		}
		const FOpenStanceTraceDebug& Trace = F.Registry.GetLastTrace();
		if (Trace.bEvaluated)
		{
			DrawDebugLine(World, Origin + Trace.Start, Origin + Trace.End, Trace.ZoneHit != EOpenStanceBodyZone::None ? FColor::Green : FColor::White, false, 0.0f, 0, 3.0f);
		}
	}
#endif
}

void UOpenStanceCombatDebugSubsystem::DrawInputPanel(UCanvas* Canvas, APlayerController* Controller) const
{
	if (!Controller || Controller->GetWorld() != GetWorld())
	{
		return;
	}
	UFont* Font = GEngine->GetSmallFont();
	const float LineHeight = Font ? Font->GetMaxCharHeight() + 2.0f : 14.0f;

	TArray<FString> Held;
	for (const FPadButton& Button : GetPadButtons())
	{
		if (HeldButtons.Contains(FName(Button.Name)))
		{
			Held.Add(Button.Name);
		}
	}

	TArray<FString> Lines;
	Lines.Add(TEXT("CONTROLLER INPUT"));
	Lines.Add(FString::Printf(TEXT("LS  x %+.2f  y %+.2f"), Controller->GetInputAnalogKeyState(EKeys::Gamepad_LeftX), Controller->GetInputAnalogKeyState(EKeys::Gamepad_LeftY)));
	Lines.Add(FString::Printf(TEXT("RS  x %+.2f  y %+.2f"), Controller->GetInputAnalogKeyState(EKeys::Gamepad_RightX), Controller->GetInputAnalogKeyState(EKeys::Gamepad_RightY)));
	Lines.Add(FString::Printf(TEXT("LT  %.2f   RT  %.2f"), Controller->GetInputAnalogKeyState(EKeys::Gamepad_LeftTriggerAxis), Controller->GetInputAnalogKeyState(EKeys::Gamepad_RightTriggerAxis)));
	Lines.Add(FString::Printf(TEXT("Held: %s"), Held.Num() ? *FString::Join(Held, TEXT(" ")) : TEXT("-")));
	Lines.Add(TEXT(""));
	Lines.Append(InputLog);

	float Y = Canvas->SizeY * 0.03f;
	for (const FString& Line : Lines)
	{
		float Width = 0.0f, Height = 0.0f;
		Canvas->StrLen(Font, Line, Width, Height);
		FCanvasTextItem Item(FVector2D((Canvas->SizeX - Width) * 0.5f, Y), FText::FromString(Line), Font, FColor::White);
		Item.EnableShadow(FLinearColor::Black);
		Canvas->DrawItem(Item);
		Y += LineHeight;
	}
}

void UOpenStanceCombatDebugSubsystem::DrawOverlay(UCanvas* Canvas, APlayerController* Controller)
{
	if (bShowInput && Canvas && GEngine)
	{
		DrawInputPanel(Canvas, Controller);
	}
	if (!bGreybox || !Canvas || (!bCombatDebug && !bTrainingDisplay) || !GEngine)
	{
		return;
	}
	UFont* Font = GEngine->GetSmallFont();
	const float LineHeight = Font ? Font->GetMaxCharHeight() + 2.0f : 14.0f;

	// One bar per fighter at its own edge of the screen: Chung on the left, Hong on the right (GDD 7.6).
	for (int32 Index = 0; Index < 2; ++Index)
	{
		const TArray<FString> Lines = FOpenStanceCombatOverlay::BuildLines(Sim, Index, !bCombatDebug);
		const FColor Colour = Index == 0 ? FColor(150, 190, 255) : FColor(255, 150, 150);
		float Y = Canvas->SizeY * 0.15f;
		for (const FString& Line : Lines)
		{
			float Width = 0.0f, Height = 0.0f;
			Canvas->StrLen(Font, Line, Width, Height);
			const float X = Index == 0 ? 20.0f : Canvas->SizeX - 20.0f - Width;
			FCanvasTextItem Item(FVector2D(X, Y), FText::FromString(Line), Font, Colour);
			Item.EnableShadow(FLinearColor::Black);
			Canvas->DrawItem(Item);
			Y += LineHeight;
		}
	}
}

#if !UE_BUILD_SHIPPING
namespace
{
	UOpenStanceCombatDebugSubsystem* Find(UWorld* World)
	{
		return World ? World->GetSubsystem<UOpenStanceCombatDebugSubsystem>() : nullptr;
	}

	bool ParseFlag(const TArray<FString>& Args, bool& bOut)
	{
		if (Args.Num() < 1)
		{
			return false;
		}
		bOut = Args[0] != TEXT("0") && !Args[0].Equals(TEXT("false"), ESearchCase::IgnoreCase);
		return true;
	}

	FAutoConsoleCommandWithWorldAndArgs GreyboxCommand(TEXT("os.Greybox"), TEXT("os.Greybox 0|1 - start or stop the Milestone 1 greybox match (player 1 is Chung)"),
		FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
		{
			bool bOn = true;
			ParseFlag(Args, bOn);
			if (UOpenStanceCombatDebugSubsystem* Subsystem = Find(World))
			{
				Subsystem->SetGreyboxActive(bOn);
			}
		}));

	FAutoConsoleCommandWithWorldAndArgs InfiniteStaminaCommand(TEXT("os.InfiniteStamina"), TEXT("os.InfiniteStamina 0|1 - stamina never drains"),
		FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
		{
			bool bOn = false;
			if (UOpenStanceCombatDebugSubsystem* Subsystem = Find(World); Subsystem && ParseFlag(Args, bOn))
			{
				Subsystem->SetInfiniteStamina(bOn);
			}
		}));

	FAutoConsoleCommandWithWorldAndArgs SetScoreCommand(TEXT("os.SetScore"), TEXT("os.SetScore <Chung> <Hong> - sets the score"),
		FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
		{
			if (UOpenStanceCombatDebugSubsystem* Subsystem = Find(World); Subsystem && Args.Num() >= 2)
			{
				Subsystem->SetScoreCheat(FCString::Atoi(*Args[0]), FCString::Atoi(*Args[1]));
			}
		}));

	FAutoConsoleCommandWithWorldAndArgs ThrowCommand(TEXT("os.Throw"),
		TEXT("os.Throw <MoveRow> [Left|Right] - the player's fighter throws that DT_MoveData row now (default the back leg), as if from the Skill Stick"),
		FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
		{
			if (UOpenStanceCombatDebugSubsystem* Subsystem = Find(World); Subsystem && Args.Num() >= 1)
			{
				FOpenStanceMatchSim& Sim = Subsystem->GetSim();
				const int32 Index = Subsystem->GetPlayerIndex();
				EOpenStanceLegSide Leg = Sim.Fighters[Index].State.Stance == EOpenStanceStance::RightLead ? EOpenStanceLegSide::Left : EOpenStanceLegSide::Right;
				if (Args.Num() >= 2)
				{
					Leg = Args[1].Equals(TEXT("Left"), ESearchCase::IgnoreCase) ? EOpenStanceLegSide::Left : EOpenStanceLegSide::Right;
				}
				if (!Sim.ThrowMove(Index, FName(*Args[0]), Leg))
				{
					UE_LOG(LogTemp, Warning, TEXT("os.Throw: no move row %s"), *Args[0]);
				}
			}
		}));

	FAutoConsoleCommandWithWorldAndArgs SetClockCommand(TEXT("os.SetClock"), TEXT("os.SetClock <seconds> - sets the round clock"),
		FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
		{
			if (UOpenStanceCombatDebugSubsystem* Subsystem = Find(World); Subsystem && Args.Num() >= 1)
			{
				Subsystem->SetClockCheat(FCString::Atof(*Args[0]));
			}
		}));

	FAutoConsoleCommandWithWorldAndArgs AIModeCommand(TEXT("os.AIMode"), TEXT("os.AIMode idle|block|mirror|normal - freezes or scripts the opponent (idle and block until the AI exists)"),
		FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
		{
			if (UOpenStanceCombatDebugSubsystem* Subsystem = Find(World))
			{
				FString Message;
				Subsystem->SetAIMode(Args.Num() ? Args[0] : FString(), Message);
				UE_LOG(LogOpenStanceCombat, Display, TEXT("%s"), *Message);
			}
		}));

	FAutoConsoleCommandWithWorldAndArgs CameraPresetCommand(TEXT("os.CameraPreset"),
		TEXT("os.CameraPreset <Name> - views the match from a camera preset (Match is the combat camera; the others are for replays). No name lists them"),
		FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
		{
			if (UOpenStanceCombatDebugSubsystem* Subsystem = Find(World))
			{
				FString Message;
				Subsystem->SetCameraPreset(Args.Num() ? FName(*Args[0]) : FName(), Message);
				UE_LOG(LogOpenStanceCombat, Display, TEXT("%s"), *Message);
				if (GEngine)
				{
					GEngine->AddOnScreenDebugMessage(9010, 4.0f, FColor::Cyan, Message);
				}
			}
		}));

	FAutoConsoleCommandWithWorldAndArgs ShowHitboxesCommand(TEXT("os.ShowHitboxes"), TEXT("os.ShowHitboxes 0|1 - draws limb traces and target zones"),
		FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
		{
			bool bOn = false;
			if (UOpenStanceCombatDebugSubsystem* Subsystem = Find(World); Subsystem && ParseFlag(Args, bOn))
			{
				Subsystem->SetShowHitboxes(bOn);
			}
		}));

	FAutoConsoleCommandWithWorldAndArgs CombatDebugCommand(TEXT("os.CombatDebug"), TEXT("os.CombatDebug 0|1 - the combat debug overlay with input icons"),
		FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
		{
			bool bOn = false;
			if (UOpenStanceCombatDebugSubsystem* Subsystem = Find(World); Subsystem && ParseFlag(Args, bOn))
			{
				Subsystem->SetCombatDebug(bOn);
			}
		}));

	FAutoConsoleCommandWithWorldAndArgs ShowInputCommand(TEXT("os.ShowInput"), TEXT("os.ShowInput 0|1 - prints the live controller input (sticks, triggers, buttons) on screen; works without the greybox"),
		FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
		{
			bool bOn = true;
			ParseFlag(Args, bOn);
			if (UOpenStanceCombatDebugSubsystem* Subsystem = Find(World))
			{
				Subsystem->SetShowInput(bOn);
			}
			else
			{
				UE_LOG(LogOpenStanceCombat, Warning, TEXT("os.ShowInput needs a game world: run it while Play is active, from the in-game console."));
			}
		}));

	FAutoConsoleCommandWithWorldAndArgs TrainingDisplayCommand(TEXT("os.TrainingDisplay"), TEXT("os.TrainingDisplay 0|1 - the player-facing Training input display"),
		FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
		{
			bool bOn = false;
			if (UOpenStanceCombatDebugSubsystem* Subsystem = Find(World); Subsystem && ParseFlag(Args, bOn))
			{
				Subsystem->SetTrainingDisplay(bOn);
			}
		}));

	FAutoConsoleCommandWithWorldAndArgs RunProofCommand(TEXT("os.RunProof"), TEXT("os.RunProof - plays the scripted M1 greybox proof and writes Saved/Logs/OpenStanceGreyboxProof.txt"),
		FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
		{
			if (UOpenStanceCombatDebugSubsystem* Subsystem = Find(World))
			{
				UE_LOG(LogOpenStanceCombat, Display, TEXT("Greybox proof %s"), Subsystem->RunProof() ? TEXT("PASSED") : TEXT("FAILED"));
			}
		}));
}
#endif
