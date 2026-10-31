#pragma once

#include "CoreMinimal.h"
#include "Combat/OpenStanceCombatTypes.h"
#include "OpenStanceFighterState.generated.h"

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

	bool IsLowStamina() const { return Stamina < LowStaminaBelow; }

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
