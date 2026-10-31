#include "Combat/OpenStanceFootwork.h"

bool FOpenStanceFootwork::GuardForDPad(EOpenStanceDPad DPad, EOpenStanceGuard& OutGuard)
{
	switch (DPad)
	{
	case EOpenStanceDPad::Up: OutGuard = EOpenStanceGuard::High; return true;
	case EOpenStanceDPad::Left: OutGuard = EOpenStanceGuard::Cross; return true;
	case EOpenStanceDPad::Right: OutGuard = EOpenStanceGuard::Mixed; return true;
	case EOpenStanceDPad::Down: OutGuard = EOpenStanceGuard::Low; return true;
	default: return false;
	}
}

EOpenStanceStance FOpenStanceFootwork::Opposite(EOpenStanceStance Stance)
{
	return Stance == EOpenStanceStance::LeftLead ? EOpenStanceStance::RightLead : EOpenStanceStance::LeftLead;
}

float FOpenStanceFootwork::ScaleReachCm(float ReachCm, float HeightCm, const FOpenStanceMovementTuning& Tuning)
{
	return ReachCm * (HeightCm / FMath::Max(Tuning.ReferenceHeightCm, 1.0f));
}

void FOpenStanceFootwork::SeparateFighters(FVector2D& A, FVector2D& B, float RadiusCm)
{
	const float MinDistance = RadiusCm * 2.0f;
	FVector2D Offset = B - A;
	float Distance = static_cast<float>(Offset.Size());
	if (Distance >= MinDistance)
	{
		return;
	}
	// Exactly on top of each other has no direction to push along; use the mat's centre line.
	const FVector2D Axis = Distance > UE_SMALL_NUMBER ? Offset / Distance : FVector2D(1.0, 0.0);
	const float Push = (MinDistance - Distance) * 0.5f;
	A -= Axis * Push;
	B += Axis * Push;
}

namespace
{
	/** The stick in the fighter's frame as a world-plane direction: Y toward the opponent, X to the fighter's right. */
	FVector2D ToWorld(const FVector2D& Move, const FVector2D& Facing)
	{
		// Right of facing (looking from above, X forward, Y to the left of forward): rotate facing by -90 degrees.
		const FVector2D Right(Facing.Y, -Facing.X);
		return Facing * Move.Y + Right * Move.X;
	}

	/** Moves Position along Delta; sideways motion keeps the distance to the opponent so it circles. */
	void ApplyMove(FVector2D& Position, const FVector2D& Delta, const FVector2D& Opponent, const FVector2D& Facing)
	{
		const FVector2D ToOpponent = Opponent - Position;
		const float StartDistance = static_cast<float>(ToOpponent.Size());
		const FVector2D Moved = Position + Delta;
		const float Forward = static_cast<float>(FVector2D::DotProduct(Delta, Facing));
		const float Sideways = static_cast<float>(FMath::Abs(FVector2D::DotProduct(Delta, FVector2D(Facing.Y, -Facing.X))));
		if (Sideways <= UE_SMALL_NUMBER || StartDistance <= UE_SMALL_NUMBER)
		{
			Position = Moved;
			return;
		}
		// The forward part changes the distance; the sideways part only swings round the opponent.
		const float TargetDistance = FMath::Max(StartDistance - Forward, 0.0f);
		FVector2D Away = Moved - Opponent;
		const float AwayLength = static_cast<float>(Away.Size());
		if (AwayLength > UE_SMALL_NUMBER)
		{
			Position = Opponent + Away / AwayLength * TargetDistance;
		}
	}
}

void FOpenStanceFootwork::Tick(float DeltaSeconds, const FOpenStanceMotionInput& Input, const FVector2D& OpponentPosition,
	FOpenStanceFighterState& State, FOpenStanceMotionState& Motion, const FOpenStanceMovementTuning& Tuning)
{
	// Face the opponent. The stance, not the facing, is what mirrors the kicks.
	const FVector2D ToOpponent = OpponentPosition - Motion.Position;
	if (ToOpponent.SizeSquared() > UE_SMALL_NUMBER)
	{
		Motion.Facing = ToOpponent.GetSafeNormal();
	}

	Motion.BouncePhase = FMath::Fmod(Motion.BouncePhase + DeltaSeconds * Tuning.BounceHz, 1.0f);

	// Guard selection: set at once in the state; the transition timer is for the animation and the M2 defence.
	EOpenStanceGuard Guard;
	if (GuardForDPad(Input.DPad, Guard) && Guard != State.Guard)
	{
		Motion.PreviousGuard = State.Guard;
		State.Guard = Guard;
		Motion.GuardTransitionLeft = Tuning.GuardTransitionSeconds;
	}
	Motion.GuardTransitionLeft = FMath::Max(0.0f, Motion.GuardTransitionLeft - DeltaSeconds);

	const bool bAttacking = State.IsAttacking();
	const bool bStick = Input.Move.Size() >= Tuning.StickDeadZone;
	FVector2D Stick = bStick ? Input.Move : FVector2D::ZeroVector;
	if (Stick.SizeSquared() > 1.0)
	{
		Stick.Normalize();
	}

	// Switch Sides plays over time: the legs swap halfway, the pose mirrors with SwitchBlend, never in one frame.
	const bool bSwitchPressed = Input.bSwitch && !Motion.bPrevSwitch;
	if (bSwitchPressed && !Motion.bSwitching && !bAttacking && Motion.DashRemaining <= 0.0f)
	{
		Motion.bSwitching = true;
		Motion.SwitchElapsed = 0.0f;
		Motion.SwitchBlend = 0.0f;
	}
	if (Motion.bSwitching)
	{
		const float Duration = FMath::Max(Tuning.StanceSwitchSeconds, UE_SMALL_NUMBER);
		const float Before = Motion.SwitchElapsed;
		Motion.SwitchElapsed += DeltaSeconds;
		if (Before < Duration * 0.5f && Motion.SwitchElapsed >= Duration * 0.5f)
		{
			State.Stance = Opposite(State.Stance);
		}
		const float Alpha = FMath::Clamp(Motion.SwitchElapsed / Duration, 0.0f, 1.0f);
		Motion.SwitchBlend = Alpha * Alpha * (3.0f - 2.0f * Alpha);
		if (Motion.SwitchElapsed >= Duration)
		{
			Motion.bSwitching = false;
			Motion.SwitchBlend = 1.0f;
		}
	}

	FVector2D Velocity = FVector2D::ZeroVector;

	if (bAttacking)
	{
		// A technique roots the fighter unless the stick is held, and then it only slides at the step speed.
		// There is no steering toward the opponent and no change to reach, targets or points.
		Motion.DashRemaining = 0.0f;
		Motion.StepRemainingCm = 0.0f;
		Motion.bMoveHeld = false;
		if (bStick)
		{
			Velocity = ToWorld(Stick, Motion.Facing) * Tuning.AttackSlideSpeedCmPerSec;
		}
	}
	else
	{
		// Dash (B): a fixed distance over a fixed time, along the stick or toward the opponent.
		const bool bDashPressed = Input.bDash && !Motion.bPrevDash;
		if (bDashPressed && Motion.DashRemaining <= 0.0f && !Motion.bSwitching && State.Stamina > 0.0f)
		{
			Motion.DashRemaining = Tuning.DashSeconds;
			Motion.DashDirection = bStick ? ToWorld(Stick, Motion.Facing).GetSafeNormal() : Motion.Facing;
			State.Stamina = FMath::Max(0.0f, State.Stamina - Tuning.DashStaminaCost);
			Motion.StepRemainingCm = 0.0f;
		}

		if (Motion.DashRemaining > 0.0f)
		{
			const float Slice = FMath::Min(DeltaSeconds, Motion.DashRemaining);
			Motion.DashRemaining -= Slice;
			const float Speed = Tuning.DashDistanceCm / FMath::Max(Tuning.DashSeconds, UE_SMALL_NUMBER);
			Velocity = Motion.DashDirection * Speed * (Slice / FMath::Max(DeltaSeconds, UE_SMALL_NUMBER));
		}
		else
		{
			if (bStick)
			{
				if (!Motion.bMoveHeld)
				{
					// A new press: it owes at least one step, forward/back or sideways.
					const bool bSideways = FMath::Abs(Stick.X) > FMath::Abs(Stick.Y);
					Motion.StepRemainingCm = bSideways ? Tuning.StepSideCm : Tuning.StepTapCm;
				}
				Motion.bMoveHeld = true;
				Motion.StepDirection = Stick.GetSafeNormal();
				Velocity = ToWorld(Stick, Motion.Facing) * Tuning.HoldSpeedCmPerSec;
			}
			else
			{
				Motion.bMoveHeld = false;
				// Released early: finish the tapped step in the direction it was pressed.
				if (Motion.StepRemainingCm > 0.0f)
				{
					Velocity = ToWorld(Motion.StepDirection, Motion.Facing) * Tuning.HoldSpeedCmPerSec;
				}
			}
		}
	}

	// Distance covered this tick; a tapped step stops exactly at its length.
	FVector2D Delta = Velocity * DeltaSeconds;
	if (!bAttacking && Motion.DashRemaining <= 0.0f && Motion.StepRemainingCm > 0.0f)
	{
		const float Length = static_cast<float>(Delta.Size());
		if (!bStick && Length > Motion.StepRemainingCm)
		{
			Delta *= Motion.StepRemainingCm / Length;
		}
		Motion.StepRemainingCm = FMath::Max(0.0f, Motion.StepRemainingCm - static_cast<float>(Delta.Size()));
	}

	ApplyMove(Motion.Position, Delta, OpponentPosition, Motion.Facing);
	Motion.Velocity = DeltaSeconds > UE_SMALL_NUMBER ? Delta / DeltaSeconds : FVector2D::ZeroVector;
	Motion.bPrevDash = Input.bDash;
	Motion.bPrevSwitch = Input.bSwitch;
}
