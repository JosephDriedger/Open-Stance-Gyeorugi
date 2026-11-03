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

	/** The kicks that spin the fighter half a turn, so they land with the sides switched. */
	bool LandsFacingFront(EOpenStanceTechnique Technique)
	{
		return Technique == EOpenStanceTechnique::SpinSide || Technique == EOpenStanceTechnique::SpinHook;
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
	LogEventCount = 0;
	StartDistanceCm = DistanceCm;
	RoundBreakElapsed = 0.0f;
	ClinchPhase = EOpenStanceClinchPhase::None;
	ClinchElapsed = 0.0f;
	bClinchFouled = false;
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
		F.InputEventCount = 0;
		F.bPrevPunch = false;
		F.PenaltyReasons.Reset();
		F.LastMove = F.LastTarget = F.LastLeg = F.LastResult = TEXT("-");
		F.PreviousStamina = F.State.Stamina;
		F.SinceSpend = 0.0f;
		F.bContactThisAttack = false;
		F.ResolvedSerial = 0;
	}
	Match = FOpenStanceMatchStatus();
	Match.State = EOpenStanceMatchState::Running;
	Match.ClockSeconds = RoundRules.RoundSeconds;
}

void FOpenStanceMatchSim::AddGamJeom(int32 Index, const FString& Reason)
{
	FOpenStanceFighterSim& F = Fighters[Index];
	F.State.GamJeom++;
	Fighters[1 - Index].State.Score++;
	F.LastResult = TEXT("FOUL");
	F.PenaltyReasons.Add(Reason);
	AddLog(F.Side, FString::Printf(TEXT("gam-jeom: %s"), *Reason.ToLower()));
}

void FOpenStanceMatchSim::AddLog(EOpenStanceSide Side, const FString& Text)
{
	++LogEventCount;
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
	if (IsInClinch())
	{
		// Chest to chest nobody can throw: the referee separates them first (GDD 11.3).
		F.LastResult = TEXT("clinch: wait for the referee");
		return;
	}
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
	Request.LegRole = Event.LegRole;
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
		AddGamJeom(Attacker, Contact.Type == EOpenStanceContactType::PunchToHead ? TEXT("Punch to the head") : TEXT("Kick below the belt"));
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
		++F.InputEventCount;
		if (F.RecentInput.Num() > MaxRecentInput)
		{
			F.RecentInput.RemoveAt(0);
		}
		if (Event.Type == EOpenStanceInputEventType::Attack || Event.Type == EOpenStanceInputEventType::GenericFake)
		{
			Start(Index, Event);
		}
	}

	// X throws a punch (GDD 9.3). The Skill Stick recognizer only reads the stick, so the press becomes the same Attack event
	// here: trunk only, one punch per press, none while LT reads the stick as defence, and LB makes it a fake.
	const bool bPunchPressed = Controls.bX && !F.bPrevPunch && !Controls.bLT;
	F.bPrevPunch = Controls.bX;
	if (bPunchPressed)
	{
		FOpenStanceInputEvent Punch;
		Punch.Type = EOpenStanceInputEventType::Attack;
		Punch.Technique = EOpenStanceTechnique::Punch;
		Punch.Target = EOpenStanceTarget::Trunk;
		Punch.Leg = F.State.GetLeadLeg();
		Punch.LegRole = EOpenStanceLegRole::Lead;
		Punch.bFake = Controls.bLB;
		Punch.Path = TEXT("X");
		F.RecentInput.Add(Punch);
		++F.InputEventCount;
		if (F.RecentInput.Num() > MaxRecentInput)
		{
			F.RecentInput.RemoveAt(0);
		}
		Start(Index, Punch);
	}

	TArray<FOpenStanceCombatEvent> Events;
	F.Machine.SetDefense(Controls.bLT, F.State, Match, Events);
	F.Machine.Tick(DeltaSeconds, F.State, Match, Events);
	for (const FOpenStanceCombatEvent& Event : Events)
	{
		// A back-leg kick, and a spin side or spin hook kick, land with the other leg in front: the sides switch as the
		// recovery begins, the same animated switch as the A button. Not specified in the GDD yet; see Combat_Input.md.
		if (Event.Type == EOpenStanceCombatEventType::ActiveEnded && Event.To == EOpenStanceCombatState::AttackRecovery && !F.Motion.bSwitching)
		{
			const FOpenStanceAttackRequest* Landing = F.Machine.GetCurrentAttack();
			if (Landing && !Landing->bFake && (Landing->LegRole == EOpenStanceLegRole::Back || LandsFacingFront(Landing->Row.Technique)))
			{
				F.Motion.bSwitching = true;
				F.Motion.SwitchElapsed = 0.0f;
				F.Motion.SwitchBlend = 0.0f;
			}
		}
		if (Event.Type == EOpenStanceCombatEventType::ActiveEnded && Event.To == EOpenStanceCombatState::AttackRecovery && !F.bContactThisAttack)
		{
			F.LastResult = TEXT("MISS");
			AddLog(F.Side, TEXT("miss"));
		}
		else if (Event.Type == EOpenStanceCombatEventType::KnockedDown && Event.bFoulFall)
		{
			AddGamJeom(Index, TEXT("Falling"));
		}
	}

	FOpenStanceMotionInput Motion;
	// In a clinch the fighters are locked chest to chest: no stepping, dashing or switching until the referee has separated them.
	Motion.Move = IsInClinch() ? FVector2D::ZeroVector : Controls.LeftStick;
	Motion.bDash = Controls.bB && !IsInClinch();
	Motion.bSwitch = Controls.bA && !IsInClinch();
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

void FOpenStanceMatchSim::StepClinch(float DeltaSeconds, const FOpenStanceFighterControls& Chung, const FOpenStanceFighterControls& Hong)
{
	FVector2D& PositionA = Fighters[0].Motion.Position;
	FVector2D& PositionB = Fighters[1].Motion.Position;
	const float Distance = static_cast<float>((PositionA - PositionB).Size());

	switch (ClinchPhase)
	{
	case EOpenStanceClinchPhase::None:
	{
		// Chest-to-chest contact starts a clinch, whether both fighters press in or one dashes onto the other (GDD 6.4). It
		// needs live play and two fighters who are not throwing a technique.
		const auto IsFree = [](const FOpenStanceFighterSim& F)
		{
			return F.State.CombatState == EOpenStanceCombatState::IdleMovement || F.State.CombatState == EOpenStanceCombatState::ActiveDefense;
		};
		if (Match.State == EOpenStanceMatchState::Running && Distance <= ClinchRules.ContactRangeCm && IsFree(Fighters[0]) && IsFree(Fighters[1]))
		{
			ClinchPhase = EOpenStanceClinchPhase::Held;
			ClinchElapsed = 0.0f;
			bClinchFouled = false;
			ClinchStartDistance = Distance;
			AddLog(EOpenStanceSide::Chung, TEXT("clinch"));
		}
		break;
	}
	case EOpenStanceClinchPhase::Held:
	{
		ClinchElapsed += DeltaSeconds;

		// Holding on or pushing for over a second is a gam-jeom for each fighter still pressing into the other (GDD 8.4).
		if (!bClinchFouled && ClinchElapsed > ClinchRules.HoldFoulSeconds)
		{
			bClinchFouled = true;
			const FOpenStanceFighterControls* Controls[2] = { &Chung, &Hong };
			for (int32 Index = 0; Index < 2; ++Index)
			{
				if (Controls[Index]->LeftStick.Y > 0.3)
				{
					AddGamJeom(Index, TEXT("Holding or pushing"));
				}
			}
		}

		// The referee calls kal-yeo and steps between them: play stops and the clock holds.
		if (ClinchElapsed >= ClinchRules.RefereeCallSeconds)
		{
			ClinchPhase = EOpenStanceClinchPhase::Separating;
			ClinchElapsed = 0.0f;
			Match.State = EOpenStanceMatchState::Stopped;
			AddLog(EOpenStanceSide::Chung, TEXT("kal-yeo"));
		}
		break;
	}
	case EOpenStanceClinchPhase::Separating:
	{
		ClinchElapsed += DeltaSeconds;

		// The fighters are drawn apart along the line between them over the first part of the stoppage, then kye-sok.
		const float Alpha = FMath::Clamp(ClinchElapsed / FMath::Max(ClinchRules.StoppageSeconds * 0.6f, 0.001f), 0.0f, 1.0f);
		const float Smooth = Alpha * Alpha * (3.0f - 2.0f * Alpha);
		const float Wanted = FMath::Lerp(ClinchStartDistance, ClinchRules.SeparationCm, Smooth);
		const FVector2D Mid = (PositionA + PositionB) * 0.5;
		const FVector2D Axis = Distance > UE_SMALL_NUMBER ? (PositionB - PositionA) / Distance : FVector2D(1.0, 0.0);
		PositionA = Mid - Axis * (Wanted * 0.5f);
		PositionB = Mid + Axis * (Wanted * 0.5f);

		if (ClinchElapsed >= ClinchRules.StoppageSeconds)
		{
			ClinchPhase = EOpenStanceClinchPhase::None;
			ClinchElapsed = 0.0f;
			Match.State = EOpenStanceMatchState::Running;
			AddLog(EOpenStanceSide::Chung, TEXT("kye-sok"));
		}
		break;
	}
	}
}

void FOpenStanceMatchSim::Step(float DeltaSeconds, const FOpenStanceFighterControls& Chung, const FOpenStanceFighterControls& Hong)
{
	Time += DeltaSeconds;
	StepFighter(0, DeltaSeconds, Chung);
	StepFighter(1, DeltaSeconds, Hong);
	FOpenStanceFootwork::SeparateFighters(Fighters[0].Motion.Position, Fighters[1].Motion.Position, Movement.CapsuleRadiusCm);
	StepClinch(DeltaSeconds, Chung, Hong);
	RunTraces(0);
	RunTraces(1);

	if (Match.State == EOpenStanceMatchState::Running)
	{
		Match.ClockSeconds = FMath::Max(0.0f, Match.ClockSeconds - DeltaSeconds);
		if (FMath::Abs(Fighters[0].State.Score - Fighters[1].State.Score) >= RoundRules.GapToEnd)
		{
			// The 12-point gap ends the match on the spot (WT rules, GDD 4.4).
			Match.State = EOpenStanceMatchState::Finished;
			AddLog(Fighters[0].State.Score > Fighters[1].State.Score ? EOpenStanceSide::Chung : EOpenStanceSide::Hong, TEXT("point gap"));
		}
		else if (Match.ClockSeconds <= 0.0f)
		{
			if (Match.Round < RoundRules.RoundCount)
			{
				// Keu-man: the round is over and the fighters rest before the next.
				Match.State = EOpenStanceMatchState::RoundBreak;
				RoundBreakElapsed = 0.0f;
				AddLog(EOpenStanceSide::Chung, TEXT("keu-man"));
			}
			else
			{
				Match.State = EOpenStanceMatchState::Finished;
				AddLog(EOpenStanceSide::Chung, TEXT("time"));
			}
		}
	}
	else if (Match.State == EOpenStanceMatchState::RoundBreak)
	{
		RoundBreakElapsed += DeltaSeconds;
		if (RoundBreakElapsed >= RoundRules.BreakSeconds)
		{
			// The next round: the clock is full again and the fighters are back on their marks, scores and penalties kept.
			++Match.Round;
			Match.ClockSeconds = RoundRules.RoundSeconds;
			Match.State = EOpenStanceMatchState::Running;
			Fighters[0].Motion.Position = FVector2D(-StartDistanceCm * 0.5, 0.0);
			Fighters[1].Motion.Position = FVector2D(StartDistanceCm * 0.5, 0.0);
			AddLog(EOpenStanceSide::Chung, TEXT("shi-jak"));
		}
	}
}
