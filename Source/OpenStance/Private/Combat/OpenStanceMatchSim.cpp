#include "Combat/OpenStanceMatchSim.h"

#include "Engine/DataTable.h"

namespace
{
	constexpr int32 MaxRecentInput = 12;

	FString ZoneName(EOpenStanceBodyZone Zone)
	{
		switch (Zone)
		{
		case EOpenStanceBodyZone::Head: return TEXT("head");
		case EOpenStanceBodyZone::Trunk: return TEXT("trunk");
		case EOpenStanceBodyZone::BelowBelt: return TEXT("below the belt");
		default: return TEXT("nothing");
		}
	}

	FString LegText(const FOpenStanceInputEvent& Event)
	{
		return FString::Printf(TEXT("%s (%s)"), Event.Leg == EOpenStanceLegSide::Left ? TEXT("Left") : TEXT("Right"), Event.LegRole == EOpenStanceLegRole::Back ? TEXT("back") : TEXT("lead"));
	}
}

FOpenStanceFighterBody FOpenStanceFighterSim::GetBody() const
{
	FOpenStanceFighterBody Body;
	Body.Root = FVector(Motion.Position.X, Motion.Position.Y, 0.0);
	Body.HeightCm = Motion.HeightCm;
	Body.Side = Side;
	return Body;
}

void FOpenStanceMatchSim::StartMatch(float DistanceCm)
{
	Time = 0.0;
	Log.Reset();
	Contacts.Reset();
	for (int32 Index = 0; Index < 2; ++Index)
	{
		FOpenStanceFighterSim& F = Fighters[Index];
		const bool bChung = Index == 0;
		F.Side = bChung ? EOpenStanceSide::Chung : EOpenStanceSide::Hong;
		F.State = FOpenStanceFighterState();
		F.Motion = FOpenStanceMotionState();
		F.Motion.Position = FVector2D(bChung ? -DistanceCm * 0.5 : DistanceCm * 0.5, 0.0);
		F.Motion.Facing = FVector2D(bChung ? 1.0 : -1.0, 0.0);
		F.Recognizer.Reset(F.State);
		F.Registry.Reset();
		F.Machine = FOpenStanceCombatMachine();
		F.Machine.Random.Initialize(Index + 1);
		F.RecentInput.Reset();
		F.LastMove = F.LastTarget = F.LastLeg = F.LastResult = TEXT("-");
		F.PreviousStamina = F.State.Stamina;
		F.SinceSpend = 0.0f;
		F.bContactThisAttack = false;
		F.ResolvedSerial = 0;
	}
	Match = FOpenStanceMatchStatus();
	Match.State = EOpenStanceMatchState::Running;
	Match.ClockSeconds = 120.0f;
}

void FOpenStanceMatchSim::AddLog(EOpenStanceSide Side, const FString& Text)
{
	FOpenStanceMatchLogEntry& Entry = Log.AddDefaulted_GetRef();
	Entry.Time = Time;
	Entry.Side = Side;
	Entry.Text = Text;
	if (Log.Num() > 200)
	{
		Log.RemoveAt(0, Log.Num() - 200, EAllowShrinking::No);
	}
}

void FOpenStanceMatchSim::SetScore(int32 Chung, int32 Hong)
{
	Fighters[0].State.Score = Chung;
	Fighters[1].State.Score = Hong;
}

void FOpenStanceMatchSim::SetClock(float Seconds)
{
	Match.ClockSeconds = FMath::Max(0.0f, Seconds);
}

void FOpenStanceMatchSim::Start(int32 Index, const FOpenStanceInputEvent& Event)
{
	FOpenStanceFighterSim& F = Fighters[Index];
	EOpenStanceTechnique Technique = Event.Technique;
	EOpenStanceTarget Target = Event.Target;
	bool bFake = Event.bFake;
	if (Event.Type == EOpenStanceInputEventType::GenericFake)
	{
		// LB alone: the side kick's startup stands in for a generic fake until it has its own animation.
		Technique = EOpenStanceTechnique::SideKick;
		Target = EOpenStanceTarget::Trunk;
		bFake = true;
	}

	FName RowName;
	const FOpenStanceMoveRow* Row = MoveTable ? FOpenStanceMoveData::Find(*MoveTable, Technique, Target, Event.bJump, &RowName) : nullptr;
	if (!Row)
	{
		F.LastMove = FString::Printf(TEXT("unmapped %s"), *UEnum::GetValueAsString(Technique));
		F.LastResult = TEXT("no move for this input");
		AddLog(F.Side, F.LastMove);
		return;
	}

	FOpenStanceAttackRequest Request;
	Request.MoveName = RowName;
	Request.Row = *Row;
	Request.Leg = Event.Leg;
	Request.bFake = bFake;
	Request.bJump = Event.bJump;

	TArray<FOpenStanceCombatEvent> Events;
	if (F.Machine.RequestAttack(Request, F.State, Match, FOpenStanceFootwork::CanStartAttack(F.Motion), Events))
	{
		F.LastMove = bFake ? Row->DisplayName + TEXT(" (fake)") : Row->DisplayName;
		F.LastTarget = Target == EOpenStanceTarget::Head ? TEXT("Head") : TEXT("Trunk");
		F.LastLeg = LegText(Event);
		F.LastResult = bFake ? TEXT("fake") : TEXT("in flight");
		F.bContactThisAttack = false;
	}
	else
	{
		for (const FOpenStanceCombatEvent& E : Events)
		{
			if (E.Type == EOpenStanceCombatEventType::AttackRejected)
			{
				F.LastResult = FString::Printf(TEXT("refused: %s"), *E.Reason);
			}
		}
	}
}

void FOpenStanceMatchSim::ApplyContact(const FOpenStanceContact& Contact)
{
	const int32 Attacker = Contact.Attacker == EOpenStanceSide::Chung ? 0 : 1;
	const int32 Defender = 1 - Attacker;
	FOpenStanceFighterSim& A = Fighters[Attacker];
	FOpenStanceFighterSim& D = Fighters[Defender];
	Contacts.Add(Contact);
	A.bContactThisAttack = true;

	switch (Contact.Type)
	{
	case EOpenStanceContactType::Score:
	{
		A.State.Score += Contact.Points;
		TArray<FOpenStanceCombatEvent> Events;
		D.Machine.ApplyHit(Contact.Reaction, D.State, Events);
		A.LastResult = FString::Printf(TEXT("HIT +%d (%s)"), Contact.Points, *ZoneName(Contact.Zone));
		D.LastResult = FString::Printf(TEXT("hit, %s"), *UEnum::GetValueAsString(Contact.Reaction));
		AddLog(A.Side, FString::Printf(TEXT("score +%d %s to the %s"), Contact.Points, *Contact.Move.ToString(), *ZoneName(Contact.Zone)));
		break;
	}
	case EOpenStanceContactType::WeakImpact:
		A.LastResult = TEXT("NO SCORE: low impact");
		AddLog(A.Side, FString::Printf(TEXT("%s touched the trunk below the impact threshold (%.0f)"), *Contact.Move.ToString(), Contact.Impact));
		break;
	case EOpenStanceContactType::PunchToHead:
	case EOpenStanceContactType::KickBelowBelt:
		// A gam-jeom gives the opponent a point (GDD 8.3, 8.4).
		A.State.GamJeom++;
		D.State.Score++;
		A.LastResult = TEXT("FOUL");
		AddLog(A.Side, Contact.Type == EOpenStanceContactType::PunchToHead ? TEXT("gam-jeom: punch to the head") : TEXT("gam-jeom: kick below the belt"));
		break;
	}
}

void FOpenStanceMatchSim::RunTraces(int32 Index)
{
	FOpenStanceFighterSim& F = Fighters[Index];
	FOpenStanceFighterSim& D = Fighters[1 - Index];
	const FOpenStanceAttackRequest* Attack = F.Machine.GetCurrentAttack();
	if (!Attack)
	{
		return;
	}

	F.Registry.Tuning = Hits;
	const bool bActive = F.State.CombatState == EOpenStanceCombatState::AttackActive;
	const float Progress = bActive ? FMath::Clamp(F.Machine.GetStateElapsed() / FMath::Max(Attack->Row.ActiveSeconds, 0.001f), 0.0f, 1.0f) : 0.0f;
	const FOpenStanceFighterBody Body = F.GetBody();
	const FVector Tip = FOpenStanceHitRegistry::SyntheticTip(Body, FVector(F.Motion.Facing.X, F.Motion.Facing.Y, 0.0), Attack->Row, Progress, Hits);

	// A new technique starts its sweep from its own first position, not from where the last one ended.
	if (F.Machine.GetAttackSerial() != F.ResolvedSerial)
	{
		F.ResolvedSerial = F.Machine.GetAttackSerial();
		F.PreviousTip = Tip;
	}

	FOpenStanceHitContext Context;
	Context.Attack = Attack;
	Context.bCanScore = F.Machine.CanScore(F.State, Match);
	Context.AttackSerial = F.Machine.GetAttackSerial();
	Context.ImpactScale = F.Machine.GetImpactScale(F.State);
	Context.Attacker = Body;
	Context.Defender = D.GetBody();
	Context.Trace.Start = F.PreviousTip;
	Context.Trace.End = Tip;
	Context.Trace.Limb = Attack->Row.Limb;
	F.PreviousTip = Tip;

	TArray<FOpenStanceContact> Found;
	F.Registry.Trace(Context, Found);
	for (const FOpenStanceContact& Contact : Found)
	{
		ApplyContact(Contact);
	}
}

void FOpenStanceMatchSim::StepFighter(int32 Index, float DeltaSeconds, const FOpenStanceFighterControls& Controls)
{
	FOpenStanceFighterSim& F = Fighters[Index];
	FOpenStanceFighterSim& Other = Fighters[1 - Index];

	FOpenStanceInputFrame Frame;
	Frame.RightStick = Controls.RightStick;
	Frame.bRT = Controls.bRT;
	Frame.bRB = Controls.bRB;
	Frame.bLB = Controls.bLB;
	Frame.bLT = Controls.bLT;
	Frame.bY = Controls.bY;

	TArray<FOpenStanceInputEvent> Input;
	F.Recognizer.Update(DeltaSeconds, Frame, F.State, Input);
	for (const FOpenStanceInputEvent& Event : Input)
	{
		F.RecentInput.Add(Event);
		if (F.RecentInput.Num() > MaxRecentInput)
		{
			F.RecentInput.RemoveAt(0);
		}
		if (Event.Type == EOpenStanceInputEventType::Attack || Event.Type == EOpenStanceInputEventType::GenericFake)
		{
			Start(Index, Event);
		}
	}

	TArray<FOpenStanceCombatEvent> Events;
	F.Machine.SetDefense(Controls.bLT, F.State, Match, Events);
	F.Machine.Tick(DeltaSeconds, F.State, Match, Events);
	for (const FOpenStanceCombatEvent& Event : Events)
	{
		if (Event.Type == EOpenStanceCombatEventType::ActiveEnded && Event.To == EOpenStanceCombatState::AttackRecovery && !F.bContactThisAttack)
		{
			F.LastResult = TEXT("MISS");
			AddLog(F.Side, TEXT("miss"));
		}
		else if (Event.Type == EOpenStanceCombatEventType::KnockedDown && Event.bFoulFall)
		{
			F.State.GamJeom++;
			Other.State.Score++;
			AddLog(F.Side, TEXT("gam-jeom: fell without being hit"));
		}
	}

	FOpenStanceMotionInput Motion;
	Motion.Move = Controls.LeftStick;
	Motion.bDash = Controls.bB;
	Motion.bSwitch = Controls.bA;
	Motion.DPad = Controls.DPad;
	FOpenStanceFootwork::Tick(DeltaSeconds, Motion, Other.Motion.Position, F.State, F.Motion, Movement);

	// Stamina comes back at 15 per second after a second of not spending it (GDD 8.9).
	if (F.State.Stamina < F.PreviousStamina - 0.001f)
	{
		F.SinceSpend = 0.0f;
	}
	else
	{
		F.SinceSpend += DeltaSeconds;
		if (F.SinceSpend >= 1.0f)
		{
			F.State.Stamina = FMath::Min(FOpenStanceFighterState::FullStamina, F.State.Stamina + 15.0f * DeltaSeconds);
		}
	}
	if (bInfiniteStamina)
	{
		F.State.Stamina = FOpenStanceFighterState::FullStamina;
	}
	F.PreviousStamina = F.State.Stamina;
}

void FOpenStanceMatchSim::Step(float DeltaSeconds, const FOpenStanceFighterControls& Chung, const FOpenStanceFighterControls& Hong)
{
	Time += DeltaSeconds;
	StepFighter(0, DeltaSeconds, Chung);
	StepFighter(1, DeltaSeconds, Hong);
	FOpenStanceFootwork::SeparateFighters(Fighters[0].Motion.Position, Fighters[1].Motion.Position, Movement.CapsuleRadiusCm);
	RunTraces(0);
	RunTraces(1);

	if (Match.State == EOpenStanceMatchState::Running)
	{
		Match.ClockSeconds = FMath::Max(0.0f, Match.ClockSeconds - DeltaSeconds);
		if (Match.ClockSeconds <= 0.0f)
		{
			Match.State = EOpenStanceMatchState::Finished;
			AddLog(EOpenStanceSide::Chung, TEXT("time"));
		}
	}
}
