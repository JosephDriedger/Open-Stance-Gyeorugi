#pragma once

#include "CoreMinimal.h"
#include "Combat/OpenStanceCombatMachine.h"
#include "Combat/OpenStanceFootwork.h"
#include "Combat/OpenStanceHit.h"
#include "Combat/OpenStanceMatchRules.h"
#include "Combat/OpenStancePenalties.h"
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

/** What a fighter holding LT is doing with the Skill Stick (GDD 8.8). */
enum class EOpenStanceGuarding : uint8
{
	/** LT alone: the hands and arms close the guard over the trunk, against punches and body kicks. */
	ClosedGuard,

	/** LT + RS Up: the high guard, against head kicks; the trunk is open. */
	HighBlock,

	/** LT + RS Down: a leg lifted to check a body kick; held over 3 s it is leg lifting (GDD 8.4). */
	LegCheck,

	/** LT + RS Left/Right: a sway or step off the line. In time it evades anything; late, it covers nothing. */
	Sway
};

/** Active Defense answers (GDD 8.8). Starting values, tuned in playtests. */
struct OPENSTANCE_API FOpenStanceDefenseTuning
{
	/** Right-stick travel that reads as a direction under LT. */
	float StickThreshold = 0.5f;

	/** A sway evades for this long after it starts; after that the fighter stands off line with no guard up. */
	float SwayEvadeSeconds = 0.35f;

	/** How far a sway steps the fighter sideways. */
	float SwayStepCm = 40.0f;
};

/**
 * Guard readiness (GDD 8.7): a guard changes how quickly techniques start and defenses come up, never a stat. Startup
 * scales multiply the technique's startup; 1 is Mixed, the balanced guard. Starting values, tuned in playtests.
 */
struct OPENSTANCE_API FOpenStanceGuardTuning
{
	/** High: the quickest guard to throw a head kick from and the slowest to start a body kick from. */
	float HighHeadStartup = 0.9f;
	float HighBodyStartup = 1.15f;

	/** Low: the quickest to start a body kick from, and the slowest to throw to the head. */
	float LowBodyStartup = 0.9f;
	float LowHeadStartup = 1.1f;

	/** Cross: a quick guard for the body. */
	float CrossBodyStartup = 0.95f;

	/** LT + RS Up raises the high block this fast, and slower from Low, the slowest guard to defend a head kick from. */
	float RaiseHighBlockSeconds = 0.05f;
	float RaiseHighBlockFromLowSeconds = 0.2f;

	/** The startup multiplier for a technique thrown from Guard at Target (a punch counts as a body technique). */
	float GetStartupScale(EOpenStanceGuard Guard, bool bHead) const
	{
		switch (Guard)
		{
		case EOpenStanceGuard::High: return bHead ? HighHeadStartup : HighBodyStartup;
		case EOpenStanceGuard::Low: return bHead ? LowHeadStartup : LowBodyStartup;
		case EOpenStanceGuard::Cross: return bHead ? 1.0f : CrossBodyStartup;
		default: return 1.0f;
		}
	}
};

/**
 * How hard a landed hit lands (GDD 8.10): the technique's authored reaction, moved a step by its impact against the
 * defender's Composure and stamina. Starting values, tuned in playtests.
 */
struct OPENSTANCE_API FOpenStanceSeverityTuning
{
	/** A defender on low stamina takes hits this much harder. */
	float TiredDefenderScale = 1.2f;

	/** Effective impact under this share of the technique's own is a step lighter; at or over StepUpFrom a step heavier. */
	float StepDownBelow = 0.9f;
	float StepUpFrom = 1.15f;
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

	/** Why each of this fighter's gam-jeom was given across the match, oldest first, for the HUD and the results page. */
	TArray<FString> PenaltyReasons;

	/** Under LT: which defense is up, how long it has been up, and how long a sway has run. */
	EOpenStanceGuarding Guarding = EOpenStanceGuarding::ClosedGuard;
	float GuardingElapsed = 0.0f;
	float SwayElapsed = 0.0f;

	/** Seconds the high block takes to come up from this fighter's guard; set each step for GetBody. */
	float HighBlockRaiseSeconds = 0.05f;

	/** Career attribute that weighs against a hit's impact (GDD 5.4, 8.10); Equal Terms holds it at 70. */
	int32 ComposureAttribute = 70;

	/** Attacks this fighter blocked or evaded this match, for the overlay and Results. */
	int32 Blocks = 0;

	/** Running timers for the penalties the referee watches for (GDD 8.4). */
	FOpenStancePenaltyWatch Watch;

	/** This round's points, penalties and tie-break counts; State.Score and State.GamJeom mirror its round numbers. */
	FOpenStanceRoundTally Round;

	/** Gam-jeom across the whole match, for the 10-gam-jeom match limit. */
	int32 MatchGamJeom = 0;

	int32 RoundWins = 0;

	/** The attack whose active phase was last counted in Round.ActiveAttacks. */
	int32 CountedActiveSerial = 0;

	/** What the last attack resolved to and how it ended. */
	FString LastMove = TEXT("-");
	FString LastTarget = TEXT("-");
	FString LastLeg = TEXT("-");
	FString LastResult = TEXT("-");

	/**
	 * Career attributes that change stamina (GDD 5.4): Stamina sizes the pool and Recovery the regeneration. Ignored under
	 * Equal Terms, which holds every attribute at 70. Set before StartMatch.
	 */
	int32 StaminaAttribute = 70;
	int32 RecoveryAttribute = 70;

	/** This fighter's regeneration per second, from the rules and its Recovery attribute; set by StartMatch. */
	float RegenPerSecond = 15.0f;

	/** Seconds since stamina was last spent; regeneration starts after RegenDelaySeconds (GDD 8.9). */
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
	FOpenStanceStaminaTuning StaminaRules;
	FOpenStancePenaltyTuning PenaltyRules;
	FOpenStanceDefenseTuning DefenseRules;
	FOpenStanceGuardTuning GuardRules;
	FOpenStanceSeverityTuning SeverityRules;

	/**
	 * The reaction a landed hit causes (GDD 8.10): the authored one, a step lighter when the effective impact is well
	 * under the technique's own (a tired attacker, a composed defender), a step heavier when well over it (a tired or
	 * rattled defender). Impact already carries the attacker's low-stamina cut.
	 */
	static EOpenStanceReactionSeverity ResolveSeverity(EOpenStanceReactionSeverity Authored, float Impact, float TechniqueImpact, int32 Composure,
		bool bDefenderLowStamina, const FOpenStanceSeverityTuning& Tuning);

	/** Seconds since a technique of either fighter last reached its active phase, while play runs (the passivity timer). */
	float PassivityElapsed = 0.0f;

	/** Every attribute at 70, so only skill decides (GDD 5.6). The default in Sparring and Tournament. */
	bool bEqualTerms = true;

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

	/** Every round played so far, in order, for the referee, the HUD and the results page. */
	TArray<FOpenStanceRoundResult> RoundHistory;

	/** Set when the match is Finished. */
	EOpenStanceSide MatchWinner = EOpenStanceSide::Chung;
	EOpenStanceRoundEnd MatchEnd = EOpenStanceRoundEnd::None;

	/**
	 * Places the fighters on their start marks facing each other and starts the opening ceremony (Match.State Ready),
	 * then play. With RoundRules.CeremonySeconds at 0 play starts at once.
	 */
	void StartMatch(float DistanceCm = 200.0f);

	void Step(float DeltaSeconds, const FOpenStanceFighterControls& Chung, const FOpenStanceFighterControls& Hong);

	/** Local play may skip the break between rounds (GDD 8.2): the next round starts on the next step. */
	bool SkipBreak();

	/** Seconds left in the opening ceremony or the round break; 0 otherwise. */
	float GetPauseSecondsLeft() const;

	/** Cheats. Setting the clock and score changes the match, not the rules. The score is the current round's. */
	void SetScore(int32 Chung, int32 Hong);
	void SetClock(float Seconds);

	void AddLog(EOpenStanceSide Side, const FString& Text);

	/** A gam-jeom for one fighter: the opponent gets the point (GDD 8.3, 8.4) and the reason is kept for the HUD. */
	void AddGamJeom(int32 Index, const FString& Reason);

	/**
	 * Development: fighter Index throws the move table row RowName with Leg, exactly as if the Skill Stick had produced it
	 * (os.Throw, for demos and captures). Returns false if the row is not in the table.
	 */
	bool ThrowMove(int32 Index, FName RowName, EOpenStanceLegSide Leg);

private:
	void StepFighter(int32 Index, float DeltaSeconds, const FOpenStanceFighterControls& Controls);
	void RunTraces(int32 Index);
	void Start(int32 Index, const FOpenStanceInputEvent& Event);
	void ApplyContact(const FOpenStanceContact& Contact);
	void StepClinch(float DeltaSeconds, const FOpenStanceFighterControls& Chung, const FOpenStanceFighterControls& Hong);

	/** The round and match flow: ceremony, clock, round stops, breaks and the end (GDD 8.2-8.4). */
	void StepRules(float DeltaSeconds);
	void EndRound(EOpenStanceSide Winner, EOpenStanceRoundEnd Reason);
	void FinishMatch(EOpenStanceSide Winner, EOpenStanceRoundEnd Reason);
	void StartRound();
	void SyncFighterNumbers();

	/** The penalties found by watching the fighters: boundary, turning away, crouching, leg lifting, passivity (GDD 8.4). */
	void StepPenalties(float DeltaSeconds);

	/** The referee stops play to declare a gam-jeom, unless play is already stopped or in a clinch, which has its own stop. */
	void StopForPenalty();
	void RestartPassivity();

	/** Reads the right stick under LT into a guard, and steps a sway sideways. */
	void StepGuard(int32 Index, float DeltaSeconds, const FOpenStanceFighterControls& Controls);

	/** True if the defender swayed out of line in time; sets OutType to Evaded. Blocks come from the guard's limbs. */
	bool IsDefended(const FOpenStanceFighterSim& Defender, const FOpenStanceContact& Contact, EOpenStanceContactType& OutType) const;

	const UDataTable* MoveTable = nullptr;

	bool bClinchFouled = false;
	float ClinchStartDistance = 0.0f;

	/** Where the fighters start each round, and how long the ceremony or the break between rounds has run. */
	float StartDistanceCm = 200.0f;
	float RoundBreakElapsed = 0.0f;
	float CeremonyElapsed = 0.0f;

	/** Seconds of play in the current round, for its result. */
	float RoundPlayed = 0.0f;

	/** Seconds left in a referee's stop to declare a gam-jeom; kye-sok when it runs out. */
	float PenaltyStopLeft = 0.0f;
	bool bPassivityCalled = false;
	EOpenStanceClinchPhase PreviousClinchPhase = EOpenStanceClinchPhase::None;

	/** Breaks the referee's decision when every count is level: a seeded coin, so a replay decides the same. */
	FRandomStream RefereeCoin;
};
