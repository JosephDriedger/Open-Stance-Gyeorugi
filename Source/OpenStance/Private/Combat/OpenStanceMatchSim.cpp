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
		F.Machine.Tuning.ApplyStamina(StaminaRules);
		// The pool and regeneration follow the Stamina and Recovery attributes in Career; Equal Terms holds them at 70.
		F.State.MaxStamina = StaminaRules.GetPool(bEqualTerms ? 70 : F.StaminaAttribute);
		F.State.Stamina = F.State.MaxStamina;
		F.State.LowStaminaThreshold = StaminaRules.LowBelow;
		F.RegenPerSecond = StaminaRules.GetRegenPerSecond(bEqualTerms ? 70 : F.RecoveryAttribute);
		F.RecentInput.Reset();
		F.InputEventCount = 0;
		F.bPrevPunch = false;
		F.PenaltyReasons.Reset();
		F.LastMove = F.LastTarget = F.LastLeg = F.LastResult = TEXT("-");
		F.PreviousStamina = F.State.Stamina;
		F.SinceSpend = 0.0f;
		F.bContactThisAttack = false;
		F.ResolvedSerial = 0;
		F.Round = FOpenStanceRoundTally();
		F.MatchGamJeom = 0;
		F.RoundWins = 0;
		F.CountedActiveSerial = 0;
	}
	RoundHistory.Reset();
	MatchWinner = EOpenStanceSide::Chung;
	MatchEnd = EOpenStanceRoundEnd::None;
	RefereeCoin.Initialize(7);
	RoundPlayed = 0.0f;
	CeremonyElapsed = 0.0f;
	Match = FOpenStanceMatchStatus();
	Match.ClockSeconds = RoundRules.RoundSeconds;
	if (RoundRules.CeremonySeconds > 0.0f)
	{
		// Charyeot first; kyeongrye, joon-bi and shi-jak follow through the ceremony (GDD 8.5).
		Match.State = EOpenStanceMatchState::Ready;
		AddLog(EOpenStanceSide::Chung, TEXT("charyeot"));
	}
	else
	{
		Match.State = EOpenStanceMatchState::Running;
	}
}

void FOpenStanceMatchSim::AddGamJeom(int32 Index, const FString& Reason)
{
	FOpenStanceFighterSim& F = Fighters[Index];
	FOpenStanceFighterSim& Other = Fighters[1 - Index];
	F.Round.GamJeom++;
	F.MatchGamJeom++;
	Other.Round.GamJeomPoints++;
	Other.Round.Points++;
	SyncFighterNumbers();
	F.LastResult = TEXT("FOUL");
	F.PenaltyReasons.Add(Reason);
	AddLog(F.Side, FString::Printf(TEXT("gam-jeom: %s"), *Reason.ToLower()));
}

void FOpenStanceMatchSim::SyncFighterNumbers()
{
	for (FOpenStanceFighterSim& F : Fighters)
	{
		F.State.Score = F.Round.Points;
		F.State.GamJeom = F.Round.GamJeom;
	}
}

bool FOpenStanceMatchSim::SkipBreak()
{
	if (Match.State != EOpenStanceMatchState::RoundBreak)
	{
		return false;
	}
	RoundBreakElapsed = FMath::Max(RoundBreakElapsed, RoundRules.BreakSeconds);
	return true;
}

float FOpenStanceMatchSim::GetPauseSecondsLeft() const
{
	switch (Match.State)
	{
	case EOpenStanceMatchState::Ready: return FMath::Max(0.0f, RoundRules.CeremonySeconds - CeremonyElapsed);
	case EOpenStanceMatchState::RoundBreak: return FMath::Max(0.0f, RoundRules.BreakSeconds - RoundBreakElapsed);
	default: return 0.0f;
	}
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
	Fighters[0].Round.Points = Chung;
	Fighters[1].Round.Points = Hong;
	SyncFighterNumbers();
}

void FOpenStanceMatchSim::SetClock(float Seconds)
{
	Match.ClockSeconds = FMath::Max(0.0f, Seconds);
}

bool FOpenStanceMatchSim::ThrowMove(int32 Index, FName RowName, EOpenStanceLegSide Leg)
{
	const FOpenStanceMoveRow* Row = MoveTable ? MoveTable->FindRow<FOpenStanceMoveRow>(RowName, TEXT("ThrowMove"), false) : nullptr;
	if (!Row || Index < 0 || Index > 1)
	{
		return false;
	}
	FOpenStanceInputEvent Event;
	Event.Type = EOpenStanceInputEventType::Attack;
	Event.Technique = Row->Technique;
	Event.Target = Row->Target;
	Event.bJump = Row->bJump;
	Event.Leg = Leg;
	// The leg on the back of the current stance is the back leg.
	const bool bRightLead = Fighters[Index].State.Stance == EOpenStanceStance::RightLead;
	Event.LegRole = (Leg == EOpenStanceLegSide::Right) == bRightLead ? EOpenStanceLegRole::Lead : EOpenStanceLegRole::Back;
	Event.Path = TEXT("os.Throw");
	Start(Index, Event);
	return true;
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
		A.Round.AddScore(Contact.Points, Contact.Zone == EOpenStanceBodyZone::Head, Contact.Technique == EOpenStanceTechnique::Punch, Contact.bSpinning);
		SyncFighterNumbers();
		TArray<FOpenStanceCombatEvent> Events;
		D.Machine.ApplyHit(Contact.Reaction, D.State, Events);
		A.LastResult = FString::Printf(TEXT("HIT +%d (%s)"), Contact.Points, *ZoneName(Contact.Zone));
		D.LastResult = FString::Printf(TEXT("hit, %s reaction"), *UEnum::GetDisplayValueAsText(Contact.Reaction).ToString().ToLower());
		AddLog(A.Side, FString::Printf(TEXT("score +%d %s to the %s"), Contact.Points, *Contact.Move.ToString(), *ZoneName(Contact.Zone)));
		break;
	}
	case EOpenStanceContactType::WeakImpact:
		// The protector registered it without scoring: it counts late in a tie-break (WT Article 15).
		++A.Round.ProtectorHits;
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
	if (bActive && !Attack->bFake && F.CountedActiveSerial != F.Machine.GetAttackSerial())
	{
		// One more technique brought to its active phase: what the referee weighs when every other count is level.
		F.CountedActiveSerial = F.Machine.GetAttackSerial();
		++F.Round.ActiveAttacks;
		if (Attack->Row.bSpinning || Attack->bJump || Attack->Row.Technique == EOpenStanceTechnique::Tornado)
		{
			++F.Round.AdvancedAttacks;
		}
	}
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
	const FVector2D Before = F.Motion.Position;
	FOpenStanceFootwork::Tick(DeltaSeconds, Motion, Other.Motion.Position, F.State, F.Motion, Movement);

	// Pressure for the judges: net movement toward the opponent while play is live (WT Article 15, Explanation 1).
	if (Match.IsPlayLive())
	{
		const FVector2D Toward = (Other.Motion.Position - Before).GetSafeNormal();
		F.Round.PressureCm += static_cast<float>(FVector2D::DotProduct(F.Motion.Position - Before, Toward));
	}

	// Stamina comes back (15 per second at Recovery 70) after a second of not spending it (GDD 8.9).
	if (F.State.Stamina < F.PreviousStamina - 0.001f)
	{
		F.SinceSpend = 0.0f;
	}
	else
	{
		F.SinceSpend += DeltaSeconds;
		if (F.SinceSpend >= StaminaRules.RegenDelaySeconds)
		{
			F.State.Stamina = FMath::Min(F.State.MaxStamina, F.State.Stamina + F.RegenPerSecond * DeltaSeconds);
		}
	}
	if (bInfiniteStamina)
	{
		F.State.Stamina = F.State.MaxStamina;
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
	StepRules(DeltaSeconds);
}

void FOpenStanceMatchSim::StepRules(float DeltaSeconds)
{
	switch (Match.State)
	{
	case EOpenStanceMatchState::Ready:
	{
		// The opening ceremony: charyeot (logged at the start), kyeongrye at a quarter, joon-bi at half, shi-jak at the end.
		const float Before = CeremonyElapsed;
		CeremonyElapsed += DeltaSeconds;
		const float Length = RoundRules.CeremonySeconds;
		if (Before < Length * 0.25f && CeremonyElapsed >= Length * 0.25f)
		{
			AddLog(EOpenStanceSide::Chung, TEXT("kyeongrye"));
		}
		if (Before < Length * 0.5f && CeremonyElapsed >= Length * 0.5f)
		{
			AddLog(EOpenStanceSide::Chung, TEXT("joon-bi"));
		}
		if (CeremonyElapsed >= Length)
		{
			Match.State = EOpenStanceMatchState::Running;
			AddLog(EOpenStanceSide::Chung, TEXT("shi-jak"));
		}
		return;
	}
	case EOpenStanceMatchState::Running:
	case EOpenStanceMatchState::Stopped:
	{
		// The clock runs only while play does; a referee stop (a clinch) holds it.
		if (Match.State == EOpenStanceMatchState::Running)
		{
			Match.ClockSeconds = FMath::Max(0.0f, Match.ClockSeconds - DeltaSeconds);
			RoundPlayed += DeltaSeconds;
		}

		// The match gam-jeom limit loses the match at once, whatever the rounds (WT Article 14).
		for (int32 Index = 0; Index < 2; ++Index)
		{
			if (RoundRules.MatchGamJeomLimit > 0 && Fighters[Index].MatchGamJeom >= RoundRules.MatchGamJeomLimit)
			{
				EndRound(Fighters[1 - Index].Side, EOpenStanceRoundEnd::MatchPenaltyLimit);
				return;
			}
		}

		const FOpenStanceRoundTally Tally[2] = { Fighters[0].Round, Fighters[1].Round };
		EOpenStanceSide Winner;
		EOpenStanceRoundEnd Reason;
		if (FOpenStanceMatchRules::CheckRoundStop(RoundRules, Tally, Winner, Reason))
		{
			EndRound(Winner, Reason);
		}
		else if (Match.ClockSeconds <= 0.0f)
		{
			const EOpenStanceSide Coin = RefereeCoin.RandRange(0, 1) == 0 ? EOpenStanceSide::Chung : EOpenStanceSide::Hong;
			FOpenStanceMatchRules::DecideAtTime(Tally, Coin, Winner, Reason);
			EndRound(Winner, Reason);
		}
		return;
	}
	case EOpenStanceMatchState::RoundBreak:
		RoundBreakElapsed += DeltaSeconds;
		if (RoundBreakElapsed >= RoundRules.BreakSeconds)
		{
			StartRound();
		}
		return;
	default:
		return;
	}
}

void FOpenStanceMatchSim::EndRound(EOpenStanceSide Winner, EOpenStanceRoundEnd Reason)
{
	const int32 WinnerIndex = Winner == EOpenStanceSide::Chung ? 0 : 1;
	FOpenStanceRoundResult& Result = RoundHistory.AddDefaulted_GetRef();
	Result.Round = Match.Round;
	Result.Winner = Winner;
	Result.Reason = Reason;
	Result.Tally[0] = Fighters[0].Round;
	Result.Tally[1] = Fighters[1].Round;
	Result.PlayedSeconds = RoundPlayed;
	++Fighters[WinnerIndex].RoundWins;

	// A clinch the round ended in is over with it.
	ClinchPhase = EOpenStanceClinchPhase::None;
	ClinchElapsed = 0.0f;

	AddLog(EOpenStanceSide::Chung, TEXT("keu-man"));
	if (Reason == EOpenStanceRoundEnd::RefereeDecision)
	{
		// Woo-se-girok: the referee records superiority, and the votes go in the log.
		int32 Votes[2];
		EOpenStanceSide Ignored;
		const FOpenStanceRoundTally Tally[2] = { Fighters[0].Round, Fighters[1].Round };
		FOpenStanceMatchRules::JudgeSuperiority(Tally, Votes, Ignored);
		AddLog(EOpenStanceSide::Chung, TEXT("woo-se-girok"));
		AddLog(Winner, FString::Printf(TEXT("superiority votes %d-%d"), Votes[0], Votes[1]));
	}
	AddLog(Winner, FString::Printf(TEXT("round %d: %s"), Match.Round, *FOpenStanceMatchRules::Describe(Reason).ToLower()));

	// Two round wins take a best of three; a match gam-jeom limit ends it now; the last round always ends it.
	if (Reason == EOpenStanceRoundEnd::MatchPenaltyLimit || Fighters[WinnerIndex].RoundWins >= RoundRules.GetRoundsToWin() || Match.Round >= RoundRules.RoundCount)
	{
		const EOpenStanceSide MatchSide = Reason == EOpenStanceRoundEnd::MatchPenaltyLimit || Fighters[0].RoundWins == Fighters[1].RoundWins
			? Winner
			: (Fighters[0].RoundWins > Fighters[1].RoundWins ? EOpenStanceSide::Chung : EOpenStanceSide::Hong);
		FinishMatch(MatchSide, Reason);
		return;
	}
	Match.State = EOpenStanceMatchState::RoundBreak;
	RoundBreakElapsed = 0.0f;
}

void FOpenStanceMatchSim::FinishMatch(EOpenStanceSide Winner, EOpenStanceRoundEnd Reason)
{
	Match.State = EOpenStanceMatchState::Finished;
	MatchWinner = Winner;
	MatchEnd = Reason;
	// The winner's hand goes up with the side named, then the final bow (GDD 8.5).
	AddLog(Winner, Winner == EOpenStanceSide::Chung ? TEXT("chung seung") : TEXT("hong seung"));
	AddLog(EOpenStanceSide::Chung, TEXT("kyeongrye"));
}

void FOpenStanceMatchSim::StartRound()
{
	// The next round: a full clock, the round's score and gam-jeom back to zero, stamina refilled and the fighters on their
	// marks facing each other (GDD 8.2, 8.9). Round wins, match gam-jeom and the history carry on.
	++Match.Round;
	Match.ClockSeconds = RoundRules.RoundSeconds;
	Match.State = EOpenStanceMatchState::Running;
	RoundPlayed = 0.0f;
	for (int32 Index = 0; Index < 2; ++Index)
	{
		FOpenStanceFighterSim& F = Fighters[Index];
		const bool bChung = Index == 0;
		F.Round = FOpenStanceRoundTally();
		F.State.Stamina = F.State.MaxStamina;
		F.PreviousStamina = F.State.Stamina;
		F.SinceSpend = 0.0f;
		F.Motion.Position = FVector2D(bChung ? -StartDistanceCm * 0.5 : StartDistanceCm * 0.5, 0.0);
		F.Motion.Facing = FVector2D(bChung ? 1.0 : -1.0, 0.0);
	}
	SyncFighterNumbers();
	AddLog(EOpenStanceSide::Chung, TEXT("shi-jak"));
}
