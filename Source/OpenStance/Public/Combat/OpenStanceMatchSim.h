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

/** Clinch rules (GDD 6.4, 8.4, 11.3). Starting values, tuned in playtests. */
struct OPENSTANCE_API FOpenStanceClinchTuning
{
	/** Centres this close mean chest-to-chest contact: two 35 cm capsules touching, plus a little. */
	float ContactRangeCm = 76.0f;

	/** The referee calls kal-yeo this long into a clinch. Under the 2 s a Referee Mode player has before the call is late. */
	float RefereeCallSeconds = 0.8f;

	/** Grabbing, holding or pushing for longer than this is a gam-jeom for the fighter pressing in (GDD 8.4). */
	float HoldFoulSeconds = 1.0f;

	/** The referee steps between the fighters: their centres end this far apart. */
	float SeparationCm = 120.0f;

	/** Seconds from kal-yeo to kye-sok; play is stopped and the clock holds. */
	float StoppageSeconds = 0.8f;
};

/** Round and match length rules (WT rules, GDD 4.4). The same numbers the match HUD's model uses. */
struct OPENSTANCE_API FOpenStanceRoundTuning
{
	int32 RoundCount = 3;
	float RoundSeconds = 120.0f;

	/** The point gap that ends a match. */
	int32 GapToEnd = 12;

	/** The break between rounds, with the fighters back on their marks when it ends. */
	float BreakSeconds = 2.0f;
};

/** Where a clinch is: none, held while the referee is on the way, or the referee separating the fighters. */
enum class EOpenStanceClinchPhase : uint8
{
	None,
	Held,
	Separating
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

	/** Every input event so far, so a reader can tell how many are new when RecentInput has dropped old ones. */
	int32 InputEventCount = 0;

	/** X was down on the last step, so a held button throws one punch. */
	bool bPrevPunch = false;

	/** Why each of this fighter's gam-jeom was given, oldest first, for the HUD and the results page. */
	TArray<FString> PenaltyReasons;

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
	FOpenStanceClinchTuning ClinchRules;
	FOpenStanceRoundTuning RoundRules;

	/** Counts up with every log entry, so a reader can tell what is new when the log has dropped old ones. */
	int32 LogEventCount = 0;

	EOpenStanceClinchPhase ClinchPhase = EOpenStanceClinchPhase::None;

	/** Seconds into the current clinch. */
	float ClinchElapsed = 0.0f;

	bool IsInClinch() const { return ClinchPhase != EOpenStanceClinchPhase::None; }

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

	/** A gam-jeom for one fighter: the opponent gets the point (GDD 8.3, 8.4) and the reason is kept for the HUD. */
	void AddGamJeom(int32 Index, const FString& Reason);

private:
	void StepFighter(int32 Index, float DeltaSeconds, const FOpenStanceFighterControls& Controls);
	void RunTraces(int32 Index);
	void Start(int32 Index, const FOpenStanceInputEvent& Event);
	void ApplyContact(const FOpenStanceContact& Contact);
	void StepClinch(float DeltaSeconds, const FOpenStanceFighterControls& Chung, const FOpenStanceFighterControls& Hong);

	const UDataTable* MoveTable = nullptr;

	bool bClinchFouled = false;
	float ClinchStartDistance = 0.0f;

	/** Where the fighters start each round, and how long the break between rounds has run. */
	float StartDistanceCm = 200.0f;
	float RoundBreakElapsed = 0.0f;
};
