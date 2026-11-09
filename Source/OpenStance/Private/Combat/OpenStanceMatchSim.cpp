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
	Body.Facing = Motion.Facing;

	// The guard's limbs are only there while the fighter is in guard: throwing a technique, reeling or down leaves it open.
	const EOpenStanceCombatState CombatState = State.CombatState;
	if (CombatState == EOpenStanceCombatState::IdleMovement || CombatState == EOpenStanceCombatState::ActiveDefense)
	{
		EOpenStanceGuardCover Cover = EOpenStanceGuardCover::Posture;
		if (CombatState == EOpenStanceCombatState::ActiveDefense)
		{
			Cover = Guarding == EOpenStanceGuarding::ClosedGuard ? EOpenStanceGuardCover::Closed
				: Guarding == EOpenStanceGuarding::HighBlock ? EOpenStanceGuardCover::High
				: Guarding == EOpenStanceGuarding::LegCheck ? EOpenStanceGuardCover::LegCheck
				: EOpenStanceGuardCover::Posture;
			// The high block takes a moment to come up, longest from Low (GDD 8.7); until then the posture stands.
			if (Cover == EOpenStanceGuardCover::High && GuardingElapsed < HighBlockRaiseSeconds)
			{
				Cover = EOpenStanceGuardCover::Posture;
			}
		}
		// Hands moving between two guards cover nothing: changing guard is an opening (GDD 8.7).
		if (!(Cover == EOpenStanceGuardCover::Posture && Motion.GuardTransitionLeft > 0.0f))
		{
			FOpenStanceHitRegistry::BuildGuard(Body, State.Guard, Cover, State.Stance == EOpenStanceStance::RightLead);
		}
	}
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
		F.Watch = FOpenStancePenaltyWatch();
		F.Guarding = EOpenStanceGuarding::ClosedGuard;
		F.SwayElapsed = 0.0f;
		F.Blocks = 0;
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
	PenaltyStopLeft = 0.0f;
	bCounting = false;
	CountSaid = 0;
	CountElapsed = 0.0f;
	PreviousClinchPhase = EOpenStanceClinchPhase::None;
	RestartPassivity();
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

void FOpenStanceMatchSim::ApplyChoices(const TMap<FName, FString>& Choices)
{
	RoundRules = FOpenStanceRoundTuning();
	bNoGamJeom = false;
	if (const FString* Ruleset = Choices.Find(TEXT("Ruleset")))
	{
		// Golden Point is offered on the setup screen but not defined in the GDD yet: it plays as World Taekwondo.
		bNoGamJeom = Ruleset->StartsWith(TEXT("Casual"));
	}
	if (const FString* Rounds = Choices.Find(TEXT("Rounds")))
	{
		RoundRules.RoundCount = *Rounds == TEXT("Single Round") ? 1 : 3;
	}
	if (const FString* Length = Choices.Find(TEXT("RoundLength")))
	{
		RoundRules.RoundSeconds = *Length == TEXT("1:00") ? 60.0f : *Length == TEXT("1:30") ? 90.0f : 120.0f;
	}
	if (const FString* Gap = Choices.Find(TEXT("PointGap")))
	{
		RoundRules.GapToEnd = *Gap == TEXT("Off") ? 0 : *Gap == TEXT("20") ? 20 : 12;
	}
}

void FOpenStanceMatchSim::AddGamJeom(int32 Index, const FString& Reason)
{
	if (bNoGamJeom)
	{
		// Casual: the foul is noted for the overlay, nothing more.
		Fighters[Index].LastResult = TEXT("foul (casual: no gam-jeom)");
		AddLog(Fighters[Index].Side, FString::Printf(TEXT("foul, no gam-jeom: %s"), *Reason.ToLower()));
		return;
	}
	FOpenStanceFighterSim& F = Fighters[Index];
	FOpenStanceFighterSim& Other = Fighters[1 - Index];
	F.Round.GamJeom++;
	F.MatchGamJeom++;
	Other.Round.GamJeomPoints++;
	Other.Round.Points++;
	SyncFighterNumbers();
	F.LastResult = TEXT("FOUL");
	F.PenaltyReasons.Add(Reason);
	if (Reason == TEXT("Holding or pushing"))
	{
		// A fighter pushed over the edge by this is not penalized for it (WT Article 14, Explanation 1).
		Other.Watch.SinceForcedSeconds = 0.0f;
	}
	StopForPenalty();
	AddLog(F.Side, FString::Printf(TEXT("gam-jeom: %s"), *Reason.ToLower()));
}

void FOpenStanceMatchSim::StopForPenalty()
{
	if (Match.State != EOpenStanceMatchState::Running || IsInClinch() || PenaltyRules.StopSeconds <= 0.0f)
	{
		return;
	}
	Match.State = EOpenStanceMatchState::Stopped;
	PenaltyStopLeft = PenaltyRules.StopSeconds;
	AddLog(EOpenStanceSide::Chung, TEXT("kal-yeo"));
}

void FOpenStanceMatchSim::StartCount(int32 Index)
{
	if (bCounting || (Match.State != EOpenStanceMatchState::Running && Match.State != EOpenStanceMatchState::Stopped))
	{
		return;
	}
	// The referee steps in: play stops, the clock holds, and any clinch or penalty stop gives way to the count.
	bCounting = true;
	CountFighter = Index;
	CountSaid = 0;
	CountElapsed = 0.0f;
	PenaltyStopLeft = 0.0f;
	ClinchPhase = EOpenStanceClinchPhase::None;
	ClinchElapsed = 0.0f;
	Match.State = EOpenStanceMatchState::Stopped;
	AddLog(Fighters[Index].Side, TEXT("kal-yeo"));
}

void FOpenStanceMatchSim::StepCount(float DeltaSeconds)
{
	if (!bCounting)
	{
		return;
	}
	CountElapsed += DeltaSeconds;
	const FOpenStanceFighterSim& Down = Fighters[CountFighter];
	while (CountSaid < CountRules.CountTo && CountElapsed >= (CountSaid + 1) * CountRules.SecondsPerCount)
	{
		++CountSaid;
		AddLog(Down.Side, FString::Printf(TEXT("count %d"), CountSaid));
	}
	// WT counts to eight even when the fighter is already up; play goes on once it has and the fighter is ready.
	const bool bUp = Down.State.CombatState != EOpenStanceCombatState::KnockedDown && Down.State.CombatState != EOpenStanceCombatState::Recovering;
	if (CountSaid >= CountRules.CountTo && CountElapsed >= CountRules.CountTo * CountRules.SecondsPerCount + CountRules.ResumeAfterSeconds && bUp)
	{
		bCounting = false;
		if (Match.State == EOpenStanceMatchState::Stopped)
		{
			Match.State = EOpenStanceMatchState::Running;
			AddLog(EOpenStanceSide::Chung, TEXT("kye-sok"));
		}
	}
}

void FOpenStanceMatchSim::RestartPassivity()
{
	PassivityElapsed = 0.0f;
	bPassivityCalled = false;
	for (FOpenStanceFighterSim& F : Fighters)
	{
		F.Watch.PassivityPressureCm = 0.0f;
	}
}

void FOpenStanceMatchSim::StepPenalties(float DeltaSeconds)
{
	StepCount(DeltaSeconds);

	// A referee's stop for a gam-jeom: the clock holds, then kye-sok.
	if (PenaltyStopLeft > 0.0f)
	{
		PenaltyStopLeft -= DeltaSeconds;
		if (PenaltyStopLeft <= 0.0f && Match.State == EOpenStanceMatchState::Stopped && !IsInClinch() && !bCounting)
		{
			PenaltyStopLeft = 0.0f;
			Match.State = EOpenStanceMatchState::Running;
			AddLog(EOpenStanceSide::Chung, TEXT("kye-sok"));
		}
	}

	// The referee's separation leaves both fighters inside the mat: being parted over the edge is not a foul.
	if (ClinchPhase == EOpenStanceClinchPhase::Separating || (PreviousClinchPhase != EOpenStanceClinchPhase::None && ClinchPhase == EOpenStanceClinchPhase::None))
	{
		for (FOpenStanceFighterSim& F : Fighters)
		{
			F.Motion.Position = PenaltyRules.KeepInside(F.Motion.Position, 10.0f);
		}
	}
	PreviousClinchPhase = ClinchPhase;

	for (FOpenStanceFighterSim& F : Fighters)
	{
		F.Watch.SinceForcedSeconds = IsInClinch() ? 0.0f : F.Watch.SinceForcedSeconds + DeltaSeconds;
	}

	if (Match.State != EOpenStanceMatchState::Running)
	{
		return;
	}

	for (int32 Index = 0; Index < 2 && Match.State == EOpenStanceMatchState::Running; ++Index)
	{
		FOpenStanceFighterSim& F = Fighters[Index];
		const FOpenStanceFighterSim& Other = Fighters[1 - Index];
		FOpenStancePenaltyWatch& W = F.Watch;
		const EOpenStanceCombatState CombatState = F.State.CombatState;
		const bool bInTechnique = F.State.IsAttacking();
		const bool bOnFeet = CombatState != EOpenStanceCombatState::KnockedDown && CombatState != EOpenStanceCombatState::Recovering
			&& CombatState != EOpenStanceCombatState::HitReaction && CombatState != EOpenStanceCombatState::Staggered;

		// Boundary: a whole foot over the octagon's edge (GDD 8.4, 6.3). Then the referee brings the fighter back in.
		if (PenaltyRules.MatApothemCm > 0.0f && PenaltyRules.IsFootOut(F.Motion.Position, F.Motion.Facing))
		{
			if (W.SinceForcedSeconds > PenaltyRules.ForcedOutGraceSeconds && bOnFeet)
			{
				AddGamJeom(Index, TEXT("Boundary"));
			}
			F.Motion.Position = PenaltyRules.KeepInside(F.Motion.Position, 30.0f);
			F.Motion.DashRemaining = 0.0f;
			F.Motion.StepRemainingCm = 0.0f;
			continue;
		}

		// Turning the back: facing more than 90 degrees away from the opponent for over a second, outside a technique.
		const FVector2D Toward = (Other.Motion.Position - F.Motion.Position).GetSafeNormal();
		const FVector2D Body = F.Motion.Facing.GetSafeNormal().GetRotated(F.Motion.TurnedAwayDeg);
		const float Cos = static_cast<float>(FVector2D::DotProduct(Body, Toward));
		const bool bTurned = PenaltyRules.TurnAwaySeconds > 0.0f && !bInTechnique && bOnFeet && !F.Motion.bSwitching
			&& Cos < FMath::Cos(FMath::DegreesToRadians(PenaltyRules.TurnAwayDegrees));
		W.TurnedAwaySeconds = bTurned ? W.TurnedAwaySeconds + DeltaSeconds : 0.0f;
		W.bTurnCounted = bTurned && W.bTurnCounted;
		if (bTurned && !W.bTurnCounted && W.TurnedAwaySeconds > PenaltyRules.TurnAwaySeconds)
		{
			W.bTurnCounted = true;
			AddGamJeom(Index, TEXT("Turning the back"));
			continue;
		}

		// Crouching below Low Guard's posture without attacking; Low Guard itself never counts (GDD 8.4).
		const bool bCrouched = PenaltyRules.CrouchSeconds > 0.0f && !bInTechnique && bOnFeet && F.Motion.CrouchCm > 0.0f;
		W.CrouchedSeconds = bCrouched ? W.CrouchedSeconds + DeltaSeconds : 0.0f;
		W.bCrouchCounted = bCrouched && W.bCrouchCounted;
		if (bCrouched && !W.bCrouchCounted && W.CrouchedSeconds > PenaltyRules.CrouchSeconds)
		{
			W.bCrouchCounted = true;
			AddGamJeom(Index, TEXT("Crouching"));
			continue;
		}

		// Leg lifting: a leg above the hip for over 3 s outside its own technique (GDD 8.4, WT Article 14 4.1.5).
		const bool bLifted = PenaltyRules.LegLiftSeconds > 0.0f && !bInTechnique && F.Motion.bLegRaised;
		W.LegRaisedSeconds = bLifted ? W.LegRaisedSeconds + DeltaSeconds : 0.0f;
		W.bLegCounted = bLifted && W.bLegCounted;
		if (bLifted && !W.bLegCounted && W.LegRaisedSeconds > PenaltyRules.LegLiftSeconds)
		{
			W.bLegCounted = true;
			AddGamJeom(Index, TEXT("Leg lifting"));
			continue;
		}
	}

	// Passivity: no technique of either fighter reaching its active phase. GONG-GYEOK at 3 s, a gam-jeom at 6 s to the
	// fighter who moved back, or to both (GDD 8.4, 8.5; WT Article 14, Explanation 1).
	if (PenaltyRules.PassivitySeconds <= 0.0f || Match.State != EOpenStanceMatchState::Running || IsInClinch())
	{
		return;
	}
	PassivityElapsed += DeltaSeconds;
	if (!bPassivityCalled && PassivityElapsed >= PenaltyRules.PassivityCallSeconds)
	{
		bPassivityCalled = true;
		AddLog(EOpenStanceSide::Chung, TEXT("gong-gyeok"));
	}
	if (PassivityElapsed >= PenaltyRules.PassivitySeconds)
	{
		const bool bBack[2] =
		{
			Fighters[0].Watch.PassivityPressureCm < -PenaltyRules.RetreatMarginCm,
			Fighters[1].Watch.PassivityPressureCm < -PenaltyRules.RetreatMarginCm
		};
		RestartPassivity();
		if (bBack[0] != bBack[1])
		{
			AddGamJeom(bBack[0] ? 0 : 1, TEXT("Moving back"));
		}
		else
		{
			AddGamJeom(0, TEXT("Not engaging"));
			AddGamJeom(1, TEXT("Not engaging"));
		}
	}
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
	// Guard readiness: the guard the technique starts from makes its startup quicker or slower (GDD 8.7).
	{
		const float Scale = GuardRules.GetStartupScale(F.State.Guard, Target == EOpenStanceTarget::Head);
		const float Extra = Request.Row.StartupSeconds * (Scale - 1.0f);
		Request.Row.StartupSeconds += Extra;
		Request.Row.AnimationSeconds += Extra;
	}
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
	A.bContactThisAttack = true;

	// The guard's arms or a leg check met it first: blocked, nothing registers and the defender is not hurt.
	if (Contact.Type == EOpenStanceContactType::Blocked)
	{
		Contacts.Add(Contact);
		++D.Blocks;
		A.LastResult = TEXT("BLOCKED");
		D.LastResult = TEXT("blocked");
		AddLog(D.Side, FString::Printf(TEXT("blocked %s"), *Contact.Move.ToString()));
		return;
	}

	// A sway in time: the technique passes by.
	EOpenStanceContactType Defended;
	if (IsDefended(D, Contact, Defended))
	{
		FOpenStanceContact Stopped = Contact;
		Stopped.Type = Defended;
		Stopped.Points = 0;
		Contacts.Add(Stopped);
		++D.Blocks;
		const bool bEvaded = Defended == EOpenStanceContactType::Evaded;
		A.LastResult = bEvaded ? TEXT("EVADED") : TEXT("BLOCKED");
		D.LastResult = bEvaded ? TEXT("swayed clear") : TEXT("blocked");
		AddLog(D.Side, FString::Printf(TEXT("%s %s"), bEvaded ? TEXT("evaded") : TEXT("blocked"), *Contact.Move.ToString()));
		return;
	}
	Contacts.Add(Contact);

	switch (Contact.Type)
	{
	case EOpenStanceContactType::Score:
	{
		A.Round.AddScore(Contact.Points, Contact.Zone == EOpenStanceBodyZone::Head, Contact.Technique == EOpenStanceTechnique::Punch, Contact.bSpinning);
		SyncFighterNumbers();
		// The reaction: the technique's, weighed against the defender's Composure and stamina (GDD 8.10).
		{
			const FOpenStanceAttackRequest* Attack = A.Machine.GetCurrentAttack();
			const float TechniqueImpact = Attack ? Attack->Row.Impact : Contact.Impact;
			Contacts.Last().Reaction = ResolveSeverity(Contact.Reaction, Contact.Impact, TechniqueImpact, bEqualTerms ? 70 : D.ComposureAttribute,
				D.State.IsLowStamina(), SeverityRules);
		}
		const EOpenStanceReactionSeverity Reaction = Contacts.Last().Reaction;
		TArray<FOpenStanceCombatEvent> Events;
		D.Machine.ApplyHit(Reaction, D.State, Events);
		if (D.State.CombatState == EOpenStanceCombatState::KnockedDown)
		{
			StartCount(Defender);
		}
		A.LastResult = FString::Printf(TEXT("HIT +%d (%s)"), Contact.Points, *ZoneName(Contact.Zone));
		D.LastResult = FString::Printf(TEXT("hit, %s reaction"), *UEnum::GetDisplayValueAsText(Reaction).ToString().ToLower());
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
	default:
		break;
	}
}

EOpenStanceReactionSeverity FOpenStanceMatchSim::ResolveSeverity(EOpenStanceReactionSeverity Authored, float Impact, float TechniqueImpact, int32 Composure,
	bool bDefenderLowStamina, const FOpenStanceSeverityTuning& Tuning)
{
	// Composure works like any attribute, a third of a percent per point from 70, here against the impact (GDD 5.4).
	float Effective = Impact / FOpenStanceStaminaTuning::AttributeScale(Composure);
	if (bDefenderLowStamina)
	{
		Effective *= Tuning.TiredDefenderScale;
	}
	const float Ratio = Effective / FMath::Max(TechniqueImpact, 1.0f);
	int32 Step = static_cast<int32>(Authored);
	if (Ratio < Tuning.StepDownBelow)
	{
		--Step;
	}
	else if (Ratio >= Tuning.StepUpFrom)
	{
		++Step;
	}
	return static_cast<EOpenStanceReactionSeverity>(FMath::Clamp(Step, static_cast<int32>(EOpenStanceReactionSeverity::Minor), static_cast<int32>(EOpenStanceReactionSeverity::Knockdown)));
}

void FOpenStanceMatchSim::StepGuard(int32 Index, float DeltaSeconds, const FOpenStanceFighterControls& Controls)
{
	FOpenStanceFighterSim& F = Fighters[Index];
	const EOpenStanceGuarding Before = F.Guarding;
	if (F.State.CombatState != EOpenStanceCombatState::ActiveDefense)
	{
		// Leaving defense (released, or hit) lowers a leg the leg check raised; a leg raised some other way stays up.
		if (Before == EOpenStanceGuarding::LegCheck)
		{
			F.Motion.bLegRaised = false;
		}
		F.Guarding = EOpenStanceGuarding::ClosedGuard;
		F.GuardingElapsed = 0.0f;
		F.SwayElapsed = 0.0f;
		return;
	}

	// The stick's main direction under LT picks the answer; neutral is the closed guard (GDD 8.8).
	const FVector2D Stick = Controls.RightStick;
	EOpenStanceGuarding Now = EOpenStanceGuarding::ClosedGuard;
	if (Stick.Size() >= DefenseRules.StickThreshold)
	{
		if (FMath::Abs(Stick.Y) >= FMath::Abs(Stick.X))
		{
			Now = Stick.Y > 0.0 ? EOpenStanceGuarding::HighBlock : EOpenStanceGuarding::LegCheck;
		}
		else
		{
			Now = EOpenStanceGuarding::Sway;
		}
	}
	F.Guarding = Now;
	F.GuardingElapsed = Now == Before ? F.GuardingElapsed + DeltaSeconds : 0.0f;
	F.HighBlockRaiseSeconds = F.State.Guard == EOpenStanceGuard::Low ? GuardRules.RaiseHighBlockFromLowSeconds : GuardRules.RaiseHighBlockSeconds;
	if (Now == EOpenStanceGuarding::LegCheck || Before == EOpenStanceGuarding::LegCheck)
	{
		F.Motion.bLegRaised = Now == EOpenStanceGuarding::LegCheck;
	}

	if (Now == EOpenStanceGuarding::Sway)
	{
		if (Before != EOpenStanceGuarding::Sway)
		{
			// A sway steps off the line toward the stick's side.
			F.SwayElapsed = 0.0f;
			F.Motion.StepDirection = FVector2D(Stick.X > 0.0 ? 1.0 : -1.0, 0.0);
			F.Motion.StepRemainingCm = DefenseRules.SwayStepCm;
		}
		F.SwayElapsed += DeltaSeconds;
	}
	else
	{
		F.SwayElapsed = 0.0f;
	}
}

bool FOpenStanceMatchSim::IsDefended(const FOpenStanceFighterSim& Defender, const FOpenStanceContact& Contact, EOpenStanceContactType& OutType) const
{
	if (Defender.State.CombatState != EOpenStanceCombatState::ActiveDefense)
	{
		return false;
	}
	// Only contacts that would register: fouls stay fouls whatever the guard.
	if (Contact.Type != EOpenStanceContactType::Score && Contact.Type != EOpenStanceContactType::WeakImpact)
	{
		return false;
	}
	// Blocks come from the guard's limbs in hit registration; only the sway's timing is decided here.
	OutType = EOpenStanceContactType::Evaded;
	return Defender.Guarding == EOpenStanceGuarding::Sway && Defender.SwayElapsed <= DefenseRules.SwayEvadeSeconds;
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
		RestartPassivity();
		if (Attack->Row.bSpinning || Attack->bJump || Attack->Row.Technique == EOpenStanceTechnique::Tornado)
		{
			++F.Round.AdvancedAttacks;
		}
	}
	const float Progress = bActive ? FMath::Clamp(F.Machine.GetStateElapsed() / FMath::Max(Attack->Row.ActiveSeconds, 0.001f), 0.0f, 1.0f) : 0.0f;
	const FOpenStanceFighterBody Body = F.GetBody();
	const FVector Tip = FOpenStanceHitRegistry::SyntheticTip(Body, FVector(F.Motion.Facing.X, F.Motion.Facing.Y, 0.0), Attack->Row, Progress, Hits, Attack->Leg);

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
	StepGuard(Index, DeltaSeconds, Controls);
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
		const float Forward = static_cast<float>(FVector2D::DotProduct(F.Motion.Position - Before, Toward));
		F.Round.PressureCm += Forward;
		F.Watch.PassivityPressureCm += Forward;
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
	StepPenalties(DeltaSeconds);
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

	// A clinch or a penalty stop the round ended in is over with it.
	ClinchPhase = EOpenStanceClinchPhase::None;
	ClinchElapsed = 0.0f;
	PenaltyStopLeft = 0.0f;
	bCounting = false;

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
		F.Watch = FOpenStancePenaltyWatch();
		F.State.Stamina = F.State.MaxStamina;
		F.PreviousStamina = F.State.Stamina;
		F.SinceSpend = 0.0f;
		F.Motion.Position = FVector2D(bChung ? -StartDistanceCm * 0.5 : StartDistanceCm * 0.5, 0.0);
		F.Motion.Facing = FVector2D(bChung ? 1.0 : -1.0, 0.0);
	}
	SyncFighterNumbers();
	RestartPassivity();
	AddLog(EOpenStanceSide::Chung, TEXT("shi-jak"));
}
