#pragma once

#include "CoreMinimal.h"
#include "Combat/OpenStanceCombatTypes.h"
#include "Combat/OpenStanceFighterState.h"
#include "OpenStanceFootwork.generated.h"

/**
 * Footwork numbers, editable data (GDD 6.4). They are starting values for the Milestone 2 prototype; the Milestone 1
 * capture's measurements replace them. Distances are centimetres, times seconds.
 */
USTRUCT(BlueprintType)
struct OPENSTANCE_API FOpenStanceMovementTuning
{
	GENERATED_BODY()

	/** Distance of a tapped step forward or back. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Movement")
	float StepTapCm = 40.0f;

	/** Distance of a tapped side step, which circles the opponent. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Movement")
	float StepSideCm = 35.0f;

	/** Speed while the left stick is held. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Movement")
	float HoldSpeedCmPerSec = 120.0f;

	/** Speed a held stick slides the fighter during a technique: its normal step speed (GDD 7.4). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Movement")
	float AttackSlideSpeedCmPerSec = 120.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Movement")
	float DashDistanceCm = 100.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Movement")
	float DashSeconds = 0.3f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Movement")
	float DashStaminaCost = 12.0f;

	/** Time the visible side switch takes; the legs swap halfway through it. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Movement")
	float StanceSwitchSeconds = 0.35f;

	/** Time a guard change takes; the four guards differ in transition timing, not in stats (GDD 8.7). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Movement")
	float GuardTransitionSeconds = 0.2f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Movement")
	float BounceHz = 2.0f;

	/** Left-stick travel below which the stick counts as neutral. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Movement")
	float StickDeadZone = 0.2f;

	/** Capsule radius; fighters never overlap. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Collision")
	float CapsuleRadiusCm = 35.0f;

	/** The height the move table's reach is written for (GDD 6.4's base fighter). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Collision")
	float ReferenceHeightCm = 175.0f;
};

/** The D-pad, which selects the guard (GDD 7.3). */
UENUM(BlueprintType)
enum class EOpenStanceDPad : uint8
{
	None,
	Up,
	Down,
	Left,
	Right
};

/** One frame of movement input. The left stick is in the fighter's frame: Y toward the opponent, X to the fighter's right. */
struct OPENSTANCE_API FOpenStanceMotionInput
{
	FVector2D Move = FVector2D::ZeroVector;
	bool bDash = false;   // B
	bool bSwitch = false; // A
	EOpenStanceDPad DPad = EOpenStanceDPad::None;
};

/** Where a fighter is on the mat and what its feet are doing. Positions are mat-plane centimetres. */
struct OPENSTANCE_API FOpenStanceMotionState
{
	FVector2D Position = FVector2D::ZeroVector;

	/** Unit vector from the fighter toward the opponent. */
	FVector2D Facing = FVector2D(1.0, 0.0);

	float HeightCm = 175.0f;

	/** Velocity the last tick applied, cm/s. */
	FVector2D Velocity = FVector2D::ZeroVector;

	/** True from the start of a side switch until it has finished; no technique can start meanwhile. */
	bool bSwitching = false;
	float SwitchElapsed = 0.0f;

	/** 0 at the start of a switch to 1 at the end, smoothed; the pose mirrors with it instead of snapping. */
	float SwitchBlend = 0.0f;

	float DashRemaining = 0.0f;
	FVector2D DashDirection = FVector2D::ZeroVector;

	/** Distance left of a tapped step after the stick was released; the direction is in the stick's frame so a circling step keeps turning with the fighter. */
	float StepRemainingCm = 0.0f;
	FVector2D StepDirection = FVector2D::ZeroVector;

	bool bMoveHeld = false;

	EOpenStanceGuard PreviousGuard = EOpenStanceGuard::High;
	float GuardTransitionLeft = 0.0f;

	bool bPrevDash = false;
	bool bPrevSwitch = false;
	float BouncePhase = 0.0f;
};

/**
 * Footwork rules (GDD 6.4, 7.4, 8.7): tapped and held movement, circling, the dash, Switch Sides, the guard
 * selection and non-overlapping fighters. Pure functions on state, so the combat code and the tests drive them
 * without actors.
 */
struct OPENSTANCE_API FOpenStanceFootwork
{
	/** The guard a D-pad press selects: Up high, Left cross, Right mixed, Down low. */
	static bool GuardForDPad(EOpenStanceDPad DPad, EOpenStanceGuard& OutGuard);

	/** The other stance. */
	static EOpenStanceStance Opposite(EOpenStanceStance Stance);

	/** Reach scales with height: the table's reach is for the reference fighter. */
	static float ScaleReachCm(float ReachCm, float HeightCm, const FOpenStanceMovementTuning& Tuning);

	/** Pushes two fighters apart until their capsules do not overlap. */
	static void SeparateFighters(FVector2D& A, FVector2D& B, float RadiusCm);

	/** A technique can start: the fighter is not mid-switch. */
	static bool CanStartAttack(const FOpenStanceMotionState& Motion) { return !Motion.bSwitching; }

	/**
	 * Advances one fighter. The fighter turns to face the opponent; the left stick moves it (a tap is a fixed
	 * step, a hold is a steady speed, sideways motion circles the opponent at the same distance); B dashes; A
	 * switches sides; the D-pad picks the guard. During a technique the stick only slides the fighter at the
	 * technique's step speed, and a neutral stick roots it: movement never steers toward the opponent.
	 */
	static void Tick(float DeltaSeconds, const FOpenStanceMotionInput& Input, const FVector2D& OpponentPosition,
		FOpenStanceFighterState& State, FOpenStanceMotionState& Motion, const FOpenStanceMovementTuning& Tuning);
};
