#pragma once

#include "CoreMinimal.h"
#include "Combat/OpenStanceCombatTypes.h"
#include "OpenStanceFighterState.generated.h"

/**
 * Stamina rules (GDD 8.9) that designers edit without code: Project Settings > Game > Open Stance Combat. Per-technique
 * costs live in MoveData and the dash cost in the footwork tuning. Starting values, tuned after the M2 playtests.
 */
USTRUCT(BlueprintType)
struct OPENSTANCE_API FOpenStanceStaminaTuning
{
	GENERATED_BODY()

	/** The pool at attribute 70, the Equal Terms baseline. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Stamina")
	float BasePool = 100.0f;

	/** Regeneration at attribute 70, once the fighter has gone RegenDelaySeconds without spending. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Stamina")
	float RegenPerSecond = 15.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Stamina")
	float RegenDelaySeconds = 1.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Stamina")
	float LowBelow = 25.0f;

	/** Below LowBelow recovery phases are 30% longer and impact 20% lower. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Stamina")
	float LowRecoveryScale = 1.3f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Stamina")
	float LowImpactScale = 0.8f;

	/** A fake's cost as a share of the technique's. 1: the GDD gives fakes no discount; tune after playtests. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Stamina")
	float FakeCostScale = 1.0f;

	/** Raising Active Defense costs stamina like an attack (GDD 8.8). Provisional: a punch's cost. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Stamina")
	float DefenseCost = 3.0f;

	/** After LT is released no technique starts for this long, so a mistimed block leaves an opening. Provisional. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Stamina")
	float DefenseRecoverySeconds = 0.2f;

	/** An attribute's effect: one third of a percent per point from 70, so 40 is 0.9 and 100 is 1.1 (GDD 5.4). */
	static float AttributeScale(int32 Attribute) { return 1.0f + (static_cast<float>(Attribute) - 70.0f) / 300.0f; }

	/** The pool for a Stamina attribute. */
	float GetPool(int32 StaminaAttribute) const { return BasePool * AttributeScale(StaminaAttribute); }

	/** Regeneration per second for a Recovery attribute. */
	float GetRegenPerSecond(int32 RecoveryAttribute) const { return RegenPerSecond * AttributeScale(RecoveryAttribute); }
};

/**
 * Everything the combat rules need to know about one fighter (GDD 16.3).
 *
 * Gameplay owns this state. The HUD and the debug overlay read it and never write it back, so a screen can be
 * rebuilt without touching the rules and the rules can run with no screen at all.
 */
USTRUCT(BlueprintType)
struct OPENSTANCE_API FOpenStanceFighterState
{
	GENERATED_BODY()

	/** Stamina is out of 100 for Equal Terms; below 25 recovery runs longer and impact drops (GDD 8.9). */
	static constexpr float FullStamina = 100.0f;
	static constexpr float LowStaminaBelow = 25.0f;

	/** This fighter's pool: 100 under Equal Terms, the Stamina attribute's in Career (GDD 5.4, 8.9). */
	UPROPERTY(BlueprintReadOnly, Category = "Open Stance|Fighter")
	float MaxStamina = FullStamina;

	/** Below this, recovery runs longer and impact drops. An absolute amount, not a share of the pool (GDD 8.9). */
	UPROPERTY(BlueprintReadOnly, Category = "Open Stance|Fighter")
	float LowStaminaThreshold = LowStaminaBelow;

	UPROPERTY(BlueprintReadOnly, Category = "Open Stance|Fighter")
	EOpenStanceStance Stance = EOpenStanceStance::RightLead;

	UPROPERTY(BlueprintReadOnly, Category = "Open Stance|Fighter")
	EOpenStanceGuard Guard = EOpenStanceGuard::High;

	/** RT held: the back leg throws the kick. */
	UPROPERTY(BlueprintReadOnly, Category = "Open Stance|Fighter")
	bool bBackLegHeld = false;

	/** RB held: kicks aim at the head. */
	UPROPERTY(BlueprintReadOnly, Category = "Open Stance|Fighter")
	bool bHeadHeld = false;

	/** LB held: the technique starts and recovers without an active phase. */
	UPROPERTY(BlueprintReadOnly, Category = "Open Stance|Fighter")
	bool bFakeHeld = false;

	/** LT held: the Skill Stick reads as defence and offensive recognition stops. */
	UPROPERTY(BlueprintReadOnly, Category = "Open Stance|Fighter")
	bool bDefenseHeld = false;

	/** A released tap of Y is waiting for the gesture that will throw the kick airborne. */
	UPROPERTY(BlueprintReadOnly, Category = "Open Stance|Fighter")
	bool bJumpPrimed = false;

	UPROPERTY(BlueprintReadOnly, Category = "Open Stance|Fighter")
	EOpenStanceCombatState CombatState = EOpenStanceCombatState::IdleMovement;

	UPROPERTY(BlueprintReadOnly, Category = "Open Stance|Fighter")
	float Stamina = FullStamina;

	UPROPERTY(BlueprintReadOnly, Category = "Open Stance|Fighter")
	int32 Score = 0;

	/** Penalties against this fighter in the current round. */
	UPROPERTY(BlueprintReadOnly, Category = "Open Stance|Fighter")
	int32 GamJeom = 0;

	bool IsLowStamina() const { return Stamina < LowStaminaThreshold; }

	/** The leg the fighter has forward, as a body side. */
	EOpenStanceLegSide GetLeadLeg() const { return Stance == EOpenStanceStance::LeftLead ? EOpenStanceLegSide::Left : EOpenStanceLegSide::Right; }

	/** The leg the fighter has behind, as a body side. */
	EOpenStanceLegSide GetBackLeg() const { return Stance == EOpenStanceStance::LeftLead ? EOpenStanceLegSide::Right : EOpenStanceLegSide::Left; }

	/** The leg that throws the next kick: back with RT held, lead otherwise. */
	EOpenStanceLegSide GetThrowingLeg() const { return bBackLegHeld ? GetBackLeg() : GetLeadLeg(); }

	/** True while the fighter is in an attack state, from the first startup frame to the end of recovery. */
	bool IsAttacking() const
	{
		return CombatState == EOpenStanceCombatState::AttackStartup
			|| CombatState == EOpenStanceCombatState::AttackActive
			|| CombatState == EOpenStanceCombatState::AttackRecovery;
	}
};

/** The match as the rules see it: whether play is live, the round and the clock. The HUD model mirrors this. */
USTRUCT(BlueprintType)
struct OPENSTANCE_API FOpenStanceMatchStatus
{
	GENERATED_BODY()

	UPROPERTY(BlueprintReadOnly, Category = "Open Stance|Match")
	EOpenStanceMatchState State = EOpenStanceMatchState::NotStarted;

	UPROPERTY(BlueprintReadOnly, Category = "Open Stance|Match")
	int32 Round = 1;

	UPROPERTY(BlueprintReadOnly, Category = "Open Stance|Match")
	float ClockSeconds = 120.0f;

	/** Attacks start and score only while the referee has play running. */
	bool IsPlayLive() const { return State == EOpenStanceMatchState::Running; }
};
