#pragma once

#include "CoreMinimal.h"
#include "Combat/OpenStanceCombatTypes.h"
#include "Combat/OpenStanceFighterState.h"
#include "Combat/OpenStanceMoveData.h"
#include "Math/RandomStream.h"

/** Why a fighter is on the floor; the penalty system and the referee read it (GDD 8.4, 8.10). */
enum class EOpenStanceKnockdownCause : uint8
{
	None,

	/** An opponent's technique landed: the referee counts, no penalty. */
	Hit,

	/** Attack Recovery ended in a failed landing: the Falling penalty. */
	FailedLanding
};

/** What the machine tells the rest of the game. The animation, score and penalty code react to these. */
enum class EOpenStanceCombatEventType : uint8
{
	StateChanged,
	AttackStarted,
	FakeStarted,
	ActiveBegan,
	ActiveEnded,
	AttackRejected,
	HitReacted,
	KnockedDown
};

struct OPENSTANCE_API FOpenStanceCombatEvent
{
	EOpenStanceCombatEventType Type = EOpenStanceCombatEventType::StateChanged;
	EOpenStanceCombatState From = EOpenStanceCombatState::IdleMovement;
	EOpenStanceCombatState To = EOpenStanceCombatState::IdleMovement;
	FName Move;
	EOpenStanceKnockdownCause Cause = EOpenStanceKnockdownCause::None;
	EOpenStanceReactionSeverity Severity = EOpenStanceReactionSeverity::Minor;

	/** For a rejected attack: why. */
	FString Reason;

	/** True for a KnockedDown event that is the Falling penalty rather than a real knockdown. */
	bool bFoulFall = false;
};

/** What the Skill Stick resolved to, with the move's row copied in so the machine holds no pointer into the table. */
struct OPENSTANCE_API FOpenStanceAttackRequest
{
	FName MoveName;
	FOpenStanceMoveRow Row;
	EOpenStanceLegSide Leg = EOpenStanceLegSide::Right;
	bool bFake = false;
	bool bJump = false;
};

/** Timing that is not per technique (GDD 8.9, 8.10). Starting values, tuned in playtests. */
struct OPENSTANCE_API FOpenStanceCombatTuning
{
	/** Control lost on a Normal hit; the GDD's 0.3-0.5 s. */
	float HitReactionSeconds = 0.4f;

	/** Control lost on a Heavy hit; the GDD's 0.8-1.2 s. */
	float StaggerSeconds = 1.0f;

	/** Time on the floor after a Knockdown or a failed landing; the GDD's 2.5-4.0 s. */
	float KnockdownSeconds = 3.0f;

	/** Time spent getting up. */
	float GetUpSeconds = 0.6f;

	/** A fake's recovery as a share of the technique's: nothing was committed. */
	float FakeRecoveryScale = 0.4f;

	/** Below 25 stamina recovery phases are 30% longer and impact 20% lower (GDD 8.9). */
	float LowStaminaRecoveryScale = 1.3f;
	float LowStaminaImpactScale = 0.8f;

	/**
	 * Phases follow the montage's notifies (NotifyActiveBegin and NotifyActiveEnd) instead of MoveData's times. The
	 * times still bound each phase at twice their length, so a missing notify cannot freeze a fighter.
	 */
	bool bNotifyDriven = false;
};

/**
 * One fighter's combat state machine (GDD 16.3, 8.6, 8.10).
 *
 * States: Idle/Movement, Attack Startup, Attack Active, Attack Recovery, Active Defense, Hit Reaction, Staggered,
 * Knocked Down, Recovering and Match Finished. Only the transitions in IsLegalTransition happen. A technique's
 * startup, active and recovery come from its MoveData row, or from the montage's notifies when bNotifyDriven, so
 * the same rules run on placeholder and captured animation.
 */
class OPENSTANCE_API FOpenStanceCombatMachine
{
public:
	FOpenStanceCombatTuning Tuning;

	/** Rolls a failed landing. Seed it for repeatable tests. */
	FRandomStream Random;

	/** True if the machine may go from one state to another; Match Finished can be entered from any state. */
	static bool IsLegalTransition(EOpenStanceCombatState From, EOpenStanceCombatState To, bool bCancelWindowOpen);

	/**
	 * Starts a technique. Returns false, with an AttackRejected event saying why, unless play is live, the fighter is
	 * free (or in the cancel window of the move it is recovering from) and not switching sides. The stamina cost is
	 * taken but never blocks the attack: low stamina only weakens it (GDD 8.9).
	 */
	bool RequestAttack(const FOpenStanceAttackRequest& Request, FOpenStanceFighterState& State, const FOpenStanceMatchStatus& Match,
		bool bCanStartAttack, TArray<FOpenStanceCombatEvent>& OutEvents);

	/** LT held or released: Active Defense. */
	void SetDefense(bool bHeld, FOpenStanceFighterState& State, const FOpenStanceMatchStatus& Match, TArray<FOpenStanceCombatEvent>& OutEvents);

	/**
	 * A technique landed on this fighter. Minor reactions are additive and change no state; Normal, Heavy and
	 * Knockdown interrupt whatever the fighter was doing. A hit that knocks the fighter down is a Hit knockdown.
	 */
	void ApplyHit(EOpenStanceReactionSeverity Severity, FOpenStanceFighterState& State, TArray<FOpenStanceCombatEvent>& OutEvents);

	/** Anim Notify: the trace window opens. Ignored unless this is a technique's startup. */
	void NotifyActiveBegin(FOpenStanceFighterState& State, TArray<FOpenStanceCombatEvent>& OutEvents);

	/** Anim Notify: the trace window closes. Ignored unless the technique is active. */
	void NotifyActiveEnd(FOpenStanceFighterState& State, TArray<FOpenStanceCombatEvent>& OutEvents);

	/** Advances the phase timers and follows the match: play stopping cuts attacks, the match ending finishes everything. */
	void Tick(float DeltaSeconds, FOpenStanceFighterState& State, const FOpenStanceMatchStatus& Match, TArray<FOpenStanceCombatEvent>& OutEvents);

	/** A trace may score only in a real technique's active phase, with play live (GDD 8.3). */
	bool CanScore(const FOpenStanceFighterState& State, const FOpenStanceMatchStatus& Match) const;

	/** Impact multiplier for the current stamina. */
	float GetImpactScale(const FOpenStanceFighterState& State) const;

	/** The technique being thrown, or null when none is. */
	const FOpenStanceAttackRequest* GetCurrentAttack() const { return bHasAttack ? &Attack : nullptr; }

	/** Why the fighter is down, or None. Stays set until the fighter is back on its feet. */
	EOpenStanceKnockdownCause GetKnockdownCause() const { return Cause; }

	/** Seconds spent in the current state. */
	float GetStateElapsed() const { return Elapsed; }

	bool IsCancelWindowOpen(const FOpenStanceFighterState& State) const;

private:
	bool Enter(EOpenStanceCombatState To, FOpenStanceFighterState& State, TArray<FOpenStanceCombatEvent>& OutEvents, bool bForce = false);
	float GetStateDuration(const FOpenStanceFighterState& State) const;
	void EndAttack();
	void Reject(const FString& Reason, TArray<FOpenStanceCombatEvent>& OutEvents) const;
	float RecoveryDuration(const FOpenStanceFighterState& State) const;

	FOpenStanceAttackRequest Attack;
	bool bHasAttack = false;
	float Elapsed = 0.0f;
	EOpenStanceKnockdownCause Cause = EOpenStanceKnockdownCause::None;
};
