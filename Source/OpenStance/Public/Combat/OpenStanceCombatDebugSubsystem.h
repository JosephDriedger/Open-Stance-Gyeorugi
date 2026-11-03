#pragma once

#include "CoreMinimal.h"
#include "Combat/OpenStanceMatchModelSync.h"
#include "Combat/OpenStanceMatchSim.h"
#include "Menu/OpenStanceMenuTypes.h"
#include "Subsystems/WorldSubsystem.h"
#include "OpenStanceCombatDebugSubsystem.generated.h"

class UCanvas;
class UDataTable;
class UMaterialInstanceDynamic;
class UOpenStanceMatchModel;
class UOpenStanceMenuSubsystem;
class UStaticMeshComponent;

/** How the second fighter behaves while the AI does not exist yet (os.AIMode). */
UENUM()
enum class EOpenStanceAIMode : uint8
{
	Idle,
	Block
};

/**
 * Runs the Milestone 1 greybox match in a game world and draws the combat display over it (GDD 7.6, 7.7, 16.8).
 *
 * Player 1's controller drives Chung; Hong stands still or holds LT (os.AIMode). Both fighters run on
 * FOpenStanceMatchSim, which owns every number; this class only feeds it the controller, draws the result and hosts the
 * development console commands. The commands are compiled out of shipping builds, and AreCheatsActive says whether any
 * has changed the match so achievement reporting can be switched off.
 *
 * The player-facing Training display (last input, leg, move, target, stamina, hit result) is SetTrainingDisplay; the
 * full debug overlay is os.CombatDebug.
 */
UCLASS()
class OPENSTANCE_API UOpenStanceCombatDebugSubsystem : public UTickableWorldSubsystem
{
	GENERATED_BODY()

public:
	virtual bool ShouldCreateSubsystem(UObject* Outer) const override;
	virtual void Initialize(FSubsystemCollectionBase& Collection) override;
	virtual void Deinitialize() override;
	virtual void OnWorldBeginPlay(UWorld& InWorld) override;
	virtual void Tick(float DeltaTime) override;
	virtual TStatId GetStatId() const override;

	/** Starts or stops the greybox match: Chung on player 1's controller, Hong standing by, a side-on camera. */
	UFUNCTION(BlueprintCallable, Category = "Open Stance|Combat")
	void SetGreyboxActive(bool bActive);

	UFUNCTION(BlueprintPure, Category = "Open Stance|Combat")
	bool IsGreyboxActive() const { return bGreybox; }

	/** The Training display: controller icons for the last input, leg, move, target, stamina and hit result. */
	UFUNCTION(BlueprintCallable, Category = "Open Stance|Combat")
	void SetTrainingDisplay(bool bShow) { bTrainingDisplay = bShow; }

	/** True once a development command has changed the match; achievement reporting must be suppressed (GDD 16.8). */
	UFUNCTION(BlueprintPure, Category = "Open Stance|Combat")
	bool AreCheatsActive() const { return bCheatsUsed; }

	/** The simulation behind the display, for gameplay code that needs the state. */
	FOpenStanceMatchSim& GetSim() { return Sim; }

	// Development switches, driven by the os.* commands (compiled out of shipping builds).
	void SetCombatDebug(bool bOn) { bCombatDebug = bOn; }
	void SetShowHitboxes(bool bOn) { bShowHitboxes = bOn; }
	void SetShowInput(bool bOn);
	void SetInfiniteStamina(bool bOn);
	void SetScoreCheat(int32 Chung, int32 Hong);
	void SetClockCheat(float Seconds);
	bool SetAIMode(const FString& Mode, FString& OutMessage);

	/** Plays the scripted proof on a separate simulation and logs it; returns true if every stage passed. */
	bool RunProof();

private:
	void DrawOverlay(UCanvas* Canvas, APlayerController* Controller);
	void DrawWorld() const;
	void DrawInputPanel(UCanvas* Canvas, APlayerController* Controller) const;
	void UpdateInputLog();
	void PrintNewInputs();
	void HandleInvertToggle();
	void ShowLiveSticks(const FOpenStanceFighterControls& Controls) const;
	void GetFollowCameraPose(FVector& OutPosition, FRotator& OutRotation) const;
	void UpdateCamera(float DeltaTime);
	/** The menu system for the local player, whose match model is the HUD's; null in a world with no local player. */
	UOpenStanceMenuSubsystem* GetMenu() const;

	/** Hands the HUD's model over to this match (names, demo off) and shows the match HUD. */
	void LinkMatchModel();

	/** The menu raised a match: restart this one, or travel to the chosen arena from the menu level. */
	UFUNCTION()
	void HandleMatchRequested(const FOpenStanceMatchSetup& Setup);

	/** The menu is returning to the main menu: leave the arena for the menu level. */
	void HandleLeaveMatch();

	bool IsMenuMap() const;

	FVector FindArenaOrigin() const;
	void SetDefaultPawnHidden(bool bHidden);
	void BuildBodies();
	void DestroyBodies();
	void UpdateBodies();
	FOpenStanceFighterControls PollController() const;
	FVector ToWorld(const FVector2D& Position, float Z = 0.0f) const;
	const UDataTable* GetMoveTable();

	FOpenStanceMatchSim Sim;

	UPROPERTY(Transient)
	TObjectPtr<UDataTable> MoveTable;

	UPROPERTY(Transient)
	TObjectPtr<AActor> Camera;

	/** The solid greybox fighters: one actor each, built from the engine's basic shapes (see BuildBodies for the part order). */
	UPROPERTY(Transient)
	TArray<TObjectPtr<AActor>> BodyActors;

	UPROPERTY(Transient)
	TArray<TObjectPtr<UStaticMeshComponent>> BodyParts;

	UPROPERTY(Transient)
	TArray<TObjectPtr<UMaterialInstanceDynamic>> BodyMaterials;

	/** Mirrors the simulation into the match HUD while the menu's Match screen is showing. */
	FOpenStanceMatchModelSync ModelSync;
	bool bModelLinked = false;

	/** The fighter the controller drives: 0 is Chung, 1 is Hong (chosen on Side Select). */
	int32 PlayerIndex = 0;
	FDelegateHandle LeaveMatchHandle;

	int32 SeenContacts = 0;
	double FlashUntil[2] = { 0.0, 0.0 };
	bool bFlashing[2] = { false, false };

	FDelegateHandle DebugDrawHandle;
	FVector Origin = FVector::ZeroVector;
	EOpenStanceAIMode AIMode = EOpenStanceAIMode::Idle;
	float Accumulator = 0.0f;

	/** Button presses and releases seen by os.ShowInput, oldest first, and the buttons held on the last tick. */
	TArray<FString> InputLog;
	TSet<FName> HeldButtons;

	/** How many of Chung's input events have already been printed on screen. */
	int32 PrintedInputEvents = 0;

	bool bPrevInvertToggle = false;
	bool bAutoStartPending = false;
	bool bShowInput = false;
	bool bGreybox = false;
	bool bCombatDebug = false;
	bool bShowHitboxes = false;
	bool bTrainingDisplay = false;
	bool bCheatsUsed = false;
};
