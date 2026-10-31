#pragma once

#include "CoreMinimal.h"
#include "Combat/OpenStanceCombatMachine.h"
#include "Combat/OpenStanceFootwork.h"
#include "Combat/OpenStanceHit.h"
#include "Combat/OpenStanceSkillStick.h"
#include "Menu/OpenStanceMenuTypes.h"

class UDataTable;

/** Everything one player's controller does in a frame, in Xbox names. The left stick is in the fighter's frame. */
struct OPENSTANCE_API FOpenStanceFighterControls
{
	FVector2D LeftStick = FVector2D::ZeroVector;
	FVector2D RightStick = FVector2D::ZeroVector;
	bool bA = false; // switch sides
	bool bB = false; // dash
	bool bX = false; // punch
	bool bY = false; // jump tap
	bool bLB = false;
	bool bRB = false;
	bool bLT = false;
	bool bRT = false;
	EOpenStanceDPad DPad = EOpenStanceDPad::None;
};

/** One line of what happened in a match, for the overlay's feed and the greybox proof's record. */
struct OPENSTANCE_API FOpenStanceMatchLogEntry
{
	double Time = 0.0;
	EOpenStanceSide Side = EOpenStanceSide::Chung;
	FString Text;
};

/** One fighter in the simulation: the runtime state plus the systems that drive it. */
struct OPENSTANCE_API FOpenStanceFighterSim
{
	EOpenStanceSide Side = EOpenStanceSide::Chung;
	FOpenStanceFighterState State;
	FOpenStanceMotionState Motion;
	FOpenStanceSkillStickRecognizer Recognizer;
	FOpenStanceCombatMachine Machine;
	FOpenStanceHitRegistry Registry;

	/** Stick path of the last gestures and what became of them, newest last, for the overlay. */
	TArray<FOpenStanceInputEvent> RecentInput;

	/** What the last attack resolved to and how it ended. */
	FString LastMove = TEXT("-");
	FString LastTarget = TEXT("-");
	FString LastLeg = TEXT("-");
	FString LastResult = TEXT("-");

	/** Seconds since stamina was last spent; regeneration starts after one second (GDD 8.9). */
	float SinceSpend = 0.0f;
	float PreviousStamina = FOpenStanceFighterState::FullStamina;

	FVector2D PreviousTipXY = FVector2D::ZeroVector;
	FVector PreviousTip = FVector::ZeroVector;
	bool bContactThisAttack = false;
	int32 ResolvedSerial = 0;

	FOpenStanceFighterBody GetBody() const;
};

/**
 * Two fighters and the rules between them, with no actors or rendering (GDD 16.3): the Skill Stick recognizer, footwork,
 * combat state machine and hit registration of each fighter, the score, and the match state. The greybox proof, the
 * automation tests and the debug overlay all run on this; gameplay owns these numbers and the HUD only reads them.
 */
class OPENSTANCE_API FOpenStanceMatchSim
{
public:
	/** Fighters 0 and 1 are Chung and Hong. */
	FOpenStanceFighterSim Fighters[2];
	FOpenStanceMatchStatus Match;
	FOpenStanceMovementTuning Movement;
	FOpenStanceHitTuning Hits;

	/** Every score, penalty and miss since the match began. */
	TArray<FOpenStanceMatchLogEntry> Log;

	/** Every contact the hit registry produced, in order. */
	TArray<FOpenStanceContact> Contacts;

	/** Development cheat: stamina never drains (os.InfiniteStamina). */
	bool bInfiniteStamina = false;

	double Time = 0.0;

	/** Sets the move table the recognizer's gestures are looked up in. The table must outlive the simulation. */
	void SetMoveTable(const UDataTable* InTable) { MoveTable = InTable; }

	/** Places the fighters on their start marks facing each other and starts play. */
	void StartMatch(float DistanceCm = 200.0f);

	void Step(float DeltaSeconds, const FOpenStanceFighterControls& Chung, const FOpenStanceFighterControls& Hong);

	/** Cheats. Setting the clock and score changes the match, not the rules. */
	void SetScore(int32 Chung, int32 Hong);
	void SetClock(float Seconds);

	void AddLog(EOpenStanceSide Side, const FString& Text);

private:
	void StepFighter(int32 Index, float DeltaSeconds, const FOpenStanceFighterControls& Controls);
	void RunTraces(int32 Index);
	void Start(int32 Index, const FOpenStanceInputEvent& Event);
	void ApplyContact(const FOpenStanceContact& Contact);

	const UDataTable* MoveTable = nullptr;
};
