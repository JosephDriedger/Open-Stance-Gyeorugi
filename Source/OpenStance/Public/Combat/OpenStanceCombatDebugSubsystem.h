#pragma once

#include "CoreMinimal.h"
#include "Combat/OpenStanceMatchSim.h"
#include "Subsystems/WorldSubsystem.h"
#include "OpenStanceCombatDebugSubsystem.generated.h"

class UCanvas;
class UDataTable;

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
	void SetInfiniteStamina(bool bOn);
	void SetScoreCheat(int32 Chung, int32 Hong);
	void SetClockCheat(float Seconds);
	bool SetAIMode(const FString& Mode, FString& OutMessage);

	/** Plays the scripted proof on a separate simulation and logs it; returns true if every stage passed. */
	bool RunProof();

private:
	void DrawOverlay(UCanvas* Canvas, APlayerController* Controller);
	void DrawWorld() const;
	FOpenStanceFighterControls PollController() const;
	FVector ToWorld(const FVector2D& Position, float Z = 0.0f) const;
	const UDataTable* GetMoveTable();

	FOpenStanceMatchSim Sim;

	UPROPERTY(Transient)
	TObjectPtr<UDataTable> MoveTable;

	UPROPERTY(Transient)
	TObjectPtr<AActor> Camera;

	FDelegateHandle DebugDrawHandle;
	FVector Origin = FVector::ZeroVector;
	EOpenStanceAIMode AIMode = EOpenStanceAIMode::Idle;
	float Accumulator = 0.0f;

	bool bGreybox = false;
	bool bCombatDebug = false;
	bool bShowHitboxes = false;
	bool bTrainingDisplay = false;
	bool bCheatsUsed = false;
};
