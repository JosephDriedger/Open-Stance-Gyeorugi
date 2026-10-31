#include "Combat/OpenStanceCombatDebugSubsystem.h"

#include "Camera/CameraActor.h"
#include "Combat/OpenStanceCombatOverlay.h"
#include "Combat/OpenStanceGreyboxProof.h"
#include "DrawDebugHelpers.h"
#include "Engine/Canvas.h"
#include "Debug/DebugDrawService.h"
#include "Engine/DataTable.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "HAL/IConsoleManager.h"
#include "InputCoreTypes.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"

DEFINE_LOG_CATEGORY_STATIC(LogOpenStanceCombat, Log, All);

namespace
{
	constexpr float Step = 1.0f / 60.0f;
	const TCHAR* MoveTablePath = TEXT("/Game/Combat/DT_MoveData.DT_MoveData");
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
}

void UOpenStanceCombatDebugSubsystem::Deinitialize()
{
	UDebugDrawService::Unregister(DebugDrawHandle);
	Super::Deinitialize();
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
		return;
	}

	Sim.SetMoveTable(GetMoveTable());
	Sim.StartMatch(200.0f);
	Accumulator = 0.0f;

	// The mat plane: the floor under the world origin if there is one.
	Origin = FVector::ZeroVector;
	FHitResult Hit;
	if (World->LineTraceSingleByChannel(Hit, FVector(0.0, 0.0, 2000.0), FVector(0.0, 0.0, -2000.0), ECC_Visibility))
	{
		Origin.Z = Hit.ImpactPoint.Z;
	}

	// Side-on combat camera (GDD 6.3): the fighters move along X, the camera looks along Y.
	if (APlayerController* Controller = World->GetFirstPlayerController())
	{
		const FVector Position = Origin + FVector(0.0, -500.0, 150.0);
		const FRotator Rotation = (Origin + FVector(0.0, 0.0, 100.0) - Position).Rotation();
		Camera = World->SpawnActor<ACameraActor>(Position, Rotation);
		Controller->SetViewTargetWithBlend(Camera);
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
	if (!bGreybox)
	{
		return;
	}

	// A fixed step keeps the simulation the same whatever the frame rate, and slomo scales DeltaTime for free.
	Accumulator += FMath::Min(DeltaTime, 0.1f);
	const FOpenStanceFighterControls Chung = PollController();
	FOpenStanceFighterControls Hong;
	Hong.bLT = AIMode == EOpenStanceAIMode::Block;
	while (Accumulator >= Step)
	{
		Sim.Step(Step, Chung, Hong);
		Accumulator -= Step;
	}
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
		DrawDebugCapsule(World, ToWorld(F.Motion.Position, Body.HeightCm * 0.5f), Body.HeightCm * 0.5f, Radius, FQuat::Identity, Colour, false, 0.0f, 0, 1.5f);
		const FVector Chest = ToWorld(F.Motion.Position, Body.HeightCm * 0.7f);
		DrawDebugDirectionalArrow(World, Chest, Chest + FVector(F.Motion.Facing.X, F.Motion.Facing.Y, 0.0) * 50.0f, 20.0f, Colour, false, 0.0f, 0, 1.5f);

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

void UOpenStanceCombatDebugSubsystem::DrawOverlay(UCanvas* Canvas, APlayerController* Controller)
{
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
