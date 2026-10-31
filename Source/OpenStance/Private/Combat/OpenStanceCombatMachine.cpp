#include "Combat/OpenStanceCombatMachine.h"

namespace
{
	using S = EOpenStanceCombatState;

	bool IsAttackState(S State)
	{
		return State == S::AttackStartup || State == S::AttackActive || State == S::AttackRecovery;
	}

	bool IsReactionTarget(S To)
	{
		return To == S::HitReaction || To == S::Staggered || To == S::KnockedDown;
	}
}

bool FOpenStanceCombatMachine::IsLegalTransition(EOpenStanceCombatState From, EOpenStanceCombatState To, bool bCancelWindowOpen)
{
	if (From == S::MatchFinished)
	{
		return false;
	}
	if (To == S::MatchFinished)
	{
		return true;
	}

	switch (From)
	{
	case S::IdleMovement:
		return To == S::AttackStartup || To == S::ActiveDefense || IsReactionTarget(To);
	case S::AttackStartup:
		// Straight to recovery is a fake: it never reaches the active phase.
		return To == S::AttackActive || To == S::AttackRecovery || IsReactionTarget(To);
	case S::AttackActive:
		return To == S::AttackRecovery || IsReactionTarget(To);
	case S::AttackRecovery:
		// The recovery is the punishable window; only a technique's own cancel window lets a new one start inside it.
		return To == S::IdleMovement || IsReactionTarget(To) || (To == S::AttackStartup && bCancelWindowOpen);
	case S::ActiveDefense:
		return To == S::IdleMovement || IsReactionTarget(To);
	case S::HitReaction:
	case S::Staggered:
		return To == S::IdleMovement || IsReactionTarget(To);
	case S::KnockedDown:
		return To == S::Recovering;
	case S::Recovering:
		return To == S::IdleMovement;
	default:
		return false;
	}
}

bool FOpenStanceCombatMachine::IsCancelWindowOpen(const FOpenStanceFighterState& State) const
{
	return State.CombatState == S::AttackRecovery && bHasAttack
		&& Attack.Row.CancelWindowSeconds >= 0.0f && Elapsed >= Attack.Row.CancelWindowSeconds;
}

bool FOpenStanceCombatMachine::Enter(EOpenStanceCombatState To, FOpenStanceFighterState& State, TArray<FOpenStanceCombatEvent>& OutEvents, bool bForce)
{
	const S From = State.CombatState;
	if (!bForce && !IsLegalTransition(From, To, IsCancelWindowOpen(State)))
	{
		return false;
	}

	State.CombatState = To;
	Elapsed = 0.0f;
	if (To == S::IdleMovement)
	{
		Cause = EOpenStanceKnockdownCause::None;
	}

	FOpenStanceCombatEvent& Event = OutEvents.AddDefaulted_GetRef();
	Event.Type = EOpenStanceCombatEventType::StateChanged;
	Event.From = From;
	Event.To = To;
	Event.Move = bHasAttack ? Attack.MoveName : NAME_None;
	Event.Cause = Cause;

	if (From == S::AttackActive && To != S::AttackActive)
	{
		FOpenStanceCombatEvent& Ended = OutEvents.AddDefaulted_GetRef();
		Ended.Type = EOpenStanceCombatEventType::ActiveEnded;
		Ended.From = From;
		Ended.To = To;
		Ended.Move = Event.Move;
	}
	if (To == S::AttackActive)
	{
		FOpenStanceCombatEvent& Began = OutEvents.AddDefaulted_GetRef();
		Began.Type = EOpenStanceCombatEventType::ActiveBegan;
		Began.From = From;
		Began.To = To;
		Began.Move = Event.Move;
	}
	return true;
}

void FOpenStanceCombatMachine::EndAttack()
{
	bHasAttack = false;
}

void FOpenStanceCombatMachine::Reject(const FString& Reason, TArray<FOpenStanceCombatEvent>& OutEvents) const
{
	FOpenStanceCombatEvent& Event = OutEvents.AddDefaulted_GetRef();
	Event.Type = EOpenStanceCombatEventType::AttackRejected;
	Event.Reason = Reason;
}

float FOpenStanceCombatMachine::RecoveryDuration(const FOpenStanceFighterState& State) const
{
	float Seconds = Attack.Row.RecoverySeconds;
	if (Attack.bFake)
	{
		Seconds *= Tuning.FakeRecoveryScale;
	}
	if (State.IsLowStamina())
	{
		Seconds *= Tuning.LowStaminaRecoveryScale;
	}
	return Seconds;
}

float FOpenStanceCombatMachine::GetStateDuration(const FOpenStanceFighterState& State) const
{
	const float NotifyBound = Tuning.bNotifyDriven ? 2.0f : 1.0f;
	switch (State.CombatState)
	{
	case S::AttackStartup:
		return bHasAttack ? Attack.Row.StartupSeconds * NotifyBound : 0.0f;
	case S::AttackActive:
		return bHasAttack ? Attack.Row.ActiveSeconds * NotifyBound : 0.0f;
	case S::AttackRecovery:
		return bHasAttack ? RecoveryDuration(State) : 0.0f;
	case S::HitReaction:
		return Tuning.HitReactionSeconds;
	case S::Staggered:
		return Tuning.StaggerSeconds;
	case S::KnockedDown:
		return Tuning.KnockdownSeconds;
	case S::Recovering:
		return Tuning.GetUpSeconds;
	default:
		return -1.0f;
	}
}

bool FOpenStanceCombatMachine::RequestAttack(const FOpenStanceAttackRequest& Request, FOpenStanceFighterState& State, const FOpenStanceMatchStatus& Match,
	bool bCanStartAttack, TArray<FOpenStanceCombatEvent>& OutEvents)
{
	if (Match.State == EOpenStanceMatchState::Finished)
	{
		Reject(TEXT("the match is finished"), OutEvents);
		return false;
	}
	if (!Match.IsPlayLive())
	{
		Reject(TEXT("play is stopped"), OutEvents);
		return false;
	}
	if (!bCanStartAttack)
	{
		Reject(TEXT("the fighter is switching sides"), OutEvents);
		return false;
	}
	if (Request.Row.Technique == EOpenStanceTechnique::None)
	{
		Reject(TEXT("no move"), OutEvents);
		return false;
	}

	const bool bFree = State.CombatState == S::IdleMovement;
	if (!bFree && !IsCancelWindowOpen(State))
	{
		Reject(FString::Printf(TEXT("busy: %s"), *UEnum::GetValueAsString(State.CombatState)), OutEvents);
		return false;
	}
	if (!Enter(S::AttackStartup, State, OutEvents))
	{
		Reject(TEXT("not a legal transition"), OutEvents);
		return false;
	}

	// Stamina is spent when the technique starts and never locks the controls; a fake costs the same so it is not free.
	State.Stamina = FMath::Max(0.0f, State.Stamina - Request.Row.StaminaCost);
	Attack = Request;
	bHasAttack = true;
	++AttackSerial;

	FOpenStanceCombatEvent& Event = OutEvents.AddDefaulted_GetRef();
	Event.Type = Request.bFake ? EOpenStanceCombatEventType::FakeStarted : EOpenStanceCombatEventType::AttackStarted;
	Event.From = S::IdleMovement;
	Event.To = S::AttackStartup;
	Event.Move = Request.MoveName;
	return true;
}

void FOpenStanceCombatMachine::SetDefense(bool bHeld, FOpenStanceFighterState& State, const FOpenStanceMatchStatus& Match, TArray<FOpenStanceCombatEvent>& OutEvents)
{
	if (bHeld && State.CombatState == S::IdleMovement && Match.IsPlayLive())
	{
		Enter(S::ActiveDefense, State, OutEvents);
	}
	else if (!bHeld && State.CombatState == S::ActiveDefense)
	{
		Enter(S::IdleMovement, State, OutEvents);
	}
}

void FOpenStanceCombatMachine::ApplyHit(EOpenStanceReactionSeverity Severity, FOpenStanceFighterState& State, TArray<FOpenStanceCombatEvent>& OutEvents)
{
	// Nothing hits a fighter who is already down or getting up, or once the match is over.
	if (State.CombatState == S::KnockedDown || State.CombatState == S::Recovering || State.CombatState == S::MatchFinished)
	{
		return;
	}

	FOpenStanceCombatEvent& Reacted = OutEvents.AddDefaulted_GetRef();
	Reacted.Type = EOpenStanceCombatEventType::HitReacted;
	Reacted.Severity = Severity;
	Reacted.From = State.CombatState;
	Reacted.To = State.CombatState;

	if (Severity == EOpenStanceReactionSeverity::Minor)
	{
		// Additive torso or head reaction: movement continues and the state does not change.
		return;
	}

	const S Target = Severity == EOpenStanceReactionSeverity::Normal ? S::HitReaction
		: Severity == EOpenStanceReactionSeverity::Heavy ? S::Staggered
		: S::KnockedDown;

	// A hit cuts whatever the fighter was doing; its technique never reaches (or finishes) the active phase.
	EndAttack();
	if (Target == S::KnockedDown)
	{
		Cause = EOpenStanceKnockdownCause::Hit;
	}
	if (Enter(Target, State, OutEvents) && Target == S::KnockedDown)
	{
		FOpenStanceCombatEvent& Down = OutEvents.AddDefaulted_GetRef();
		Down.Type = EOpenStanceCombatEventType::KnockedDown;
		Down.Cause = EOpenStanceKnockdownCause::Hit;
		Down.Severity = Severity;
		Down.bFoulFall = false;
	}
}

void FOpenStanceCombatMachine::NotifyActiveBegin(FOpenStanceFighterState& State, TArray<FOpenStanceCombatEvent>& OutEvents)
{
	if (State.CombatState == S::AttackStartup && bHasAttack && !Attack.bFake)
	{
		Enter(S::AttackActive, State, OutEvents);
	}
}

void FOpenStanceCombatMachine::NotifyActiveEnd(FOpenStanceFighterState& State, TArray<FOpenStanceCombatEvent>& OutEvents)
{
	if (State.CombatState == S::AttackActive)
	{
		Enter(S::AttackRecovery, State, OutEvents);
	}
}

bool FOpenStanceCombatMachine::CanScore(const FOpenStanceFighterState& State, const FOpenStanceMatchStatus& Match) const
{
	return State.CombatState == S::AttackActive && bHasAttack && !Attack.bFake && Match.IsPlayLive();
}

float FOpenStanceCombatMachine::GetImpactScale(const FOpenStanceFighterState& State) const
{
	return State.IsLowStamina() ? Tuning.LowStaminaImpactScale : 1.0f;
}

void FOpenStanceCombatMachine::Tick(float DeltaSeconds, FOpenStanceFighterState& State, const FOpenStanceMatchStatus& Match, TArray<FOpenStanceCombatEvent>& OutEvents)
{
	if (Match.State == EOpenStanceMatchState::Finished)
	{
		if (State.CombatState != S::MatchFinished)
		{
			EndAttack();
			Enter(S::MatchFinished, State, OutEvents);
		}
		return;
	}
	if (State.CombatState == S::MatchFinished)
	{
		return;
	}

	// While the referee has play stopped no technique or guard carries on; a fighter being hit or getting up finishes that.
	if (!Match.IsPlayLive() && (IsAttackState(State.CombatState) || State.CombatState == S::ActiveDefense))
	{
		EndAttack();
		Enter(S::IdleMovement, State, OutEvents, true);
	}

	Elapsed += DeltaSeconds;
	for (int32 Guard = 0; Guard < 8; ++Guard)
	{
		const float Duration = GetStateDuration(State);
		if (Duration < 0.0f || Elapsed < Duration)
		{
			break;
		}
		const float Carry = Elapsed - Duration;

		switch (State.CombatState)
		{
		case S::AttackStartup:
			// A fake plays its startup and recovers: no active phase, no score.
			Enter(bHasAttack && Attack.bFake ? S::AttackRecovery : S::AttackActive, State, OutEvents);
			break;
		case S::AttackActive:
			Enter(S::AttackRecovery, State, OutEvents);
			break;
		case S::AttackRecovery:
			if (bHasAttack && !Attack.bFake && Random.FRand() < Attack.Row.SelfFallChance)
			{
				// A failed landing: the fighter falls without being hit, and the referee will call a Falling penalty.
				Cause = EOpenStanceKnockdownCause::FailedLanding;
				EndAttack();
				if (Enter(S::KnockedDown, State, OutEvents))
				{
					FOpenStanceCombatEvent& Down = OutEvents.AddDefaulted_GetRef();
					Down.Type = EOpenStanceCombatEventType::KnockedDown;
					Down.Cause = EOpenStanceKnockdownCause::FailedLanding;
					Down.Severity = EOpenStanceReactionSeverity::Knockdown;
					Down.bFoulFall = true;
				}
			}
			else
			{
				EndAttack();
				Enter(S::IdleMovement, State, OutEvents);
			}
			break;
		case S::HitReaction:
		case S::Staggered:
			Enter(S::IdleMovement, State, OutEvents);
			break;
		case S::KnockedDown:
			Enter(S::Recovering, State, OutEvents);
			break;
		case S::Recovering:
			Enter(S::IdleMovement, State, OutEvents);
			break;
		default:
			break;
		}
		Elapsed = Carry;
	}
}
