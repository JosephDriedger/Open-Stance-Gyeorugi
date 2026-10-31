#include "Combat/OpenStanceSkillStick.h"

namespace
{
	const TCHAR* DirName(EOpenStanceStickDir Dir)
	{
		switch (Dir)
		{
		case EOpenStanceStickDir::Up: return TEXT("Up");
		case EOpenStanceStickDir::Down: return TEXT("Down");
		case EOpenStanceStickDir::Left: return TEXT("Left");
		case EOpenStanceStickDir::Right: return TEXT("Right");
		default: return TEXT("Neutral");
		}
	}

	EOpenStanceStickDir Opposite(EOpenStanceStickDir Dir)
	{
		return Dir == EOpenStanceStickDir::Left ? EOpenStanceStickDir::Right : EOpenStanceStickDir::Left;
	}

	/**
	 * Moves Current to where the stick is now and returns true if it changed. A new direction needs the engage
	 * threshold; between release and engage the stick keeps the direction it had, so a wobble on the way back to
	 * centre never counts as a step.
	 */
	bool StepDirection(EOpenStanceStickDir& Current, const FVector2D& Stick, const FOpenStanceSkillStickConfig& Config)
	{
		const float Travel = static_cast<float>(Stick.Size());
		EOpenStanceStickDir Next = Current;
		if (Travel < Config.GetRelease())
		{
			Next = EOpenStanceStickDir::Neutral;
		}
		else if (Travel >= Config.GetEngage())
		{
			Next = FOpenStanceSkillStickRecognizer::ToDirection(Stick, Config.GetEngage());
		}
		const bool bChanged = Next != Current;
		Current = Next;
		return bChanged;
	}

	bool IsFinalTechnique(EOpenStanceTechnique Technique)
	{
		return Technique != EOpenStanceTechnique::None;
	}
}

FOpenStanceSkillStickConfig FOpenStanceSkillStickConfig::FromSettings(float DeadZonePercent, float InWindowSeconds)
{
	FOpenStanceSkillStickConfig Result;
	Result.DeadZone = FMath::Clamp(DeadZonePercent / 100.0f, 0.0f, 0.4f);
	Result.WindowSeconds = FMath::Clamp(InWindowSeconds, MinWindowSeconds, MaxWindowSeconds);
	Result.JumpPrimeSeconds = Result.WindowSeconds;
	return Result;
}

FOpenStanceSkillStickRecognizer::FOpenStanceSkillStickRecognizer()
{
	Gestures = MakeDefaultGestures();
}

TArray<FOpenStanceGestureDef> FOpenStanceSkillStickRecognizer::MakeDefaultGestures()
{
	using S = EOpenStanceGestureStep;
	using T = EOpenStanceTechnique;

	auto Make = [](T Technique, std::initializer_list<S> Steps, bool bCanJump)
	{
		FOpenStanceGestureDef Def;
		Def.Technique = Technique;
		Def.Steps = TArray<S>(Steps);
		Def.bCanJump = bCanJump;
		return Def;
	};

	// RS Up is the side or cut kick, RS toward the throwing leg's side the roundhouse and the other side the hook,
	// RS Down then Up the spin side kick (GDD 7.2). Jump covers side, roundhouse and hook, not spin side (GDD 7.4).
	return {
		Make(T::SideKick, { S::Up }, true),
		Make(T::Roundhouse, { S::Toward }, true),
		Make(T::Hook, { S::Away }, true),
		Make(T::SpinSide, { S::Down, S::Up }, false),
	};
}

void FOpenStanceSkillStickRecognizer::SetGestures(const TArray<FOpenStanceGestureDef>& InGestures)
{
	Gestures = InGestures;
}

void FOpenStanceSkillStickRecognizer::AddGesture(const FOpenStanceGestureDef& Gesture)
{
	Gestures.Add(Gesture);
}

EOpenStanceStickDir FOpenStanceSkillStickRecognizer::ToDirection(const FVector2D& Stick, float Engage)
{
	if (Stick.Size() < Engage)
	{
		return EOpenStanceStickDir::Neutral;
	}
	// The dominant axis decides; a perfect diagonal reads as vertical.
	if (FMath::Abs(Stick.X) > FMath::Abs(Stick.Y))
	{
		return Stick.X > 0.0 ? EOpenStanceStickDir::Right : EOpenStanceStickDir::Left;
	}
	return Stick.Y > 0.0 ? EOpenStanceStickDir::Up : EOpenStanceStickDir::Down;
}

FString FOpenStanceSkillStickRecognizer::PathToString(const TArray<EOpenStanceStickDir>& InPath)
{
	FString Text;
	for (const EOpenStanceStickDir Dir : InPath)
	{
		Text += Text.IsEmpty() ? FString(DirName(Dir)) : FString(TEXT(", ")) + DirName(Dir);
	}
	return Text;
}

EOpenStanceStickDir FOpenStanceSkillStickRecognizer::ResolveStep(EOpenStanceGestureStep Step, const FOpenStanceFighterState& State) const
{
	switch (Step)
	{
	case EOpenStanceGestureStep::Up:
		return EOpenStanceStickDir::Up;
	case EOpenStanceGestureStep::Down:
		return EOpenStanceStickDir::Down;
	default:
		break;
	}

	// Toward is the side of the leg throwing the kick: the lead leg without RT, the back leg with it. The back leg
	// is on the opposite side, so RT mirrors the direction and so does a change of stance.
	const EOpenStanceLegSide Throwing = bLatchedRT ? State.GetBackLeg() : State.GetLeadLeg();
	const EOpenStanceStickDir Toward = Throwing == EOpenStanceLegSide::Right ? EOpenStanceStickDir::Right : EOpenStanceStickDir::Left;
	return Step == EOpenStanceGestureStep::Toward ? Toward : Opposite(Toward);
}

FOpenStanceSkillStickRecognizer::FMatch FOpenStanceSkillStickRecognizer::MatchPath(const FOpenStanceFighterState& State) const
{
	FMatch Result;
	bool bLonger = false;
	bool bPartial = false;

	for (const FOpenStanceGestureDef& Def : Gestures)
	{
		if (!IsFinalTechnique(Def.Technique) || Def.Steps.Num() < Path.Num())
		{
			continue;
		}
		bool bPrefix = true;
		for (int32 Index = 0; Index < Path.Num(); ++Index)
		{
			if (ResolveStep(Def.Steps[Index], State) != Path[Index])
			{
				bPrefix = false;
				break;
			}
		}
		if (!bPrefix)
		{
			continue;
		}
		if (Def.Steps.Num() == Path.Num())
		{
			if (!Result.Def)
			{
				Result.Def = &Def;
			}
		}
		else
		{
			bLonger = true;
			bPartial = true;
		}
	}

	if (Result.Def)
	{
		Result.Kind = bLonger ? EMatch::ExactWithLonger : EMatch::Exact;
	}
	else
	{
		Result.Kind = bPartial ? EMatch::Partial : EMatch::None;
	}
	return Result;
}

void FOpenStanceSkillStickRecognizer::Emit(TArray<FOpenStanceInputEvent>& OutEvents, EOpenStanceInputEventType Type, const FOpenStanceFighterState& State) const
{
	FOpenStanceInputEvent& Event = OutEvents.AddDefaulted_GetRef();
	Event.Type = Type;
	Event.Time = Clock;
	Event.Path = PathToString(Path);
	Event.LegRole = bLatchedRT ? EOpenStanceLegRole::Back : EOpenStanceLegRole::Lead;
	Event.Leg = bLatchedRT ? State.GetBackLeg() : State.GetLeadLeg();
}

void FOpenStanceSkillStickRecognizer::BeginGesture(const FOpenStanceInputFrame& Input, FOpenStanceFighterState& State)
{
	bInGesture = true;
	GestureStart = Clock;
	Path.Reset();
	History.Reset();
	bLatchedRT = Input.bRT;
	bLatchedRB = Input.bRB;
	bLatchedLB = Input.bLB || bFakeCandidate;
	bLatchedJump = State.bJumpPrimed;
	bFakeCandidate = false;
}

void FOpenStanceSkillStickRecognizer::EndGesture()
{
	bInGesture = false;
	Path.Reset();
	bLatchedRT = bLatchedRB = bLatchedLB = bLatchedJump = false;
}

void FOpenStanceSkillStickRecognizer::Commit(const FMatch& Match, FOpenStanceFighterState& State, TArray<FOpenStanceInputEvent>& OutEvents)
{
	Emit(OutEvents, EOpenStanceInputEventType::Attack, State);
	FOpenStanceInputEvent& Event = OutEvents.Last();
	Event.Technique = Match.Def->Technique;
	Event.Target = bLatchedRB ? EOpenStanceTarget::Head : EOpenStanceTarget::Trunk;
	Event.bFake = bLatchedLB;
	Event.bJump = bLatchedJump && Match.Def->bCanJump;
	State.bJumpPrimed = false;
}

void FOpenStanceSkillStickRecognizer::Finish(FOpenStanceFighterState& State, TArray<FOpenStanceInputEvent>& OutEvents)
{
	const FMatch Match = MatchPath(State);
	if (Match.Kind == EMatch::Exact || Match.Kind == EMatch::ExactWithLonger)
	{
		Commit(Match, State, OutEvents);
	}
	else
	{
		Emit(OutEvents, Match.Kind == EMatch::Partial ? EOpenStanceInputEventType::GestureExpired : EOpenStanceInputEventType::GestureRejected, State);
		State.bJumpPrimed = false;
	}
	EndGesture();

	// A stick still held after the window must go back to neutral before it can start anything new.
	bSpent = CurrentDir != EOpenStanceStickDir::Neutral;
}

void FOpenStanceSkillStickRecognizer::Reset(FOpenStanceFighterState& State)
{
	EndGesture();
	History.Reset();
	bSpent = CurrentDir != EOpenStanceStickDir::Neutral;
	bFakeCandidate = false;
	bYHeldDuringGesture = false;
	JumpPrimeUntil = -1.0;
	State.bJumpPrimed = false;
}

void FOpenStanceSkillStickRecognizer::Update(float DeltaSeconds, const FOpenStanceInputFrame& Input, FOpenStanceFighterState& State, TArray<FOpenStanceInputEvent>& OutEvents)
{
	Clock += DeltaSeconds;
	State.bBackLegHeld = Input.bRT;
	State.bHeadHeld = Input.bRB;
	State.bFakeHeld = Input.bLB;
	State.bDefenseHeld = Input.bLT;

	const float Window = FMath::Clamp(Config.WindowSeconds, FOpenStanceSkillStickConfig::MinWindowSeconds, FOpenStanceSkillStickConfig::MaxWindowSeconds);

	// Jump: a released tap of Y primes the next gesture. A press that began once the stick was already moving is too
	// late, and a prime that no gesture follows runs out.
	if (Input.bY && !bPrevY && (bInGesture || CurrentDir != EOpenStanceStickDir::Neutral))
	{
		bYHeldDuringGesture = true;
	}
	if (!Input.bY && bPrevY)
	{
		if (!bYHeldDuringGesture && !bInGesture && !Input.bLT)
		{
			State.bJumpPrimed = true;
			JumpPrimeUntil = Clock + Config.JumpPrimeSeconds;
			Emit(OutEvents, EOpenStanceInputEventType::JumpPrimed, State);
		}
		bYHeldDuringGesture = false;
	}
	if (State.bJumpPrimed && !bInGesture && Clock > JumpPrimeUntil)
	{
		State.bJumpPrimed = false;
		Emit(OutEvents, EOpenStanceInputEventType::JumpPrimeExpired, State);
	}

	const bool bChanged = StepDirection(CurrentDir, Input.RightStick, Config);

	// Active Defense: LT reads the stick as defence and stops offensive recognition (GDD 8.8).
	if (Input.bLT)
	{
		if (!bPrevLT)
		{
			if (bInGesture)
			{
				Emit(OutEvents, EOpenStanceInputEventType::GestureCancelled, State);
				EndGesture();
			}
			bFakeCandidate = false;
			State.bJumpPrimed = false;
		}
		if (bChanged && CurrentDir != EOpenStanceStickDir::Neutral)
		{
			Emit(OutEvents, EOpenStanceInputEventType::Defense, State);
			FOpenStanceInputEvent& Event = OutEvents.Last();
			Event.DefenseKind = CurrentDir == EOpenStanceStickDir::Up ? EOpenStanceDefenseKind::HighBlock
				: CurrentDir == EOpenStanceStickDir::Down ? EOpenStanceDefenseKind::LegCheck
				: EOpenStanceDefenseKind::Sway;
			Event.Path = DirName(CurrentDir);
		}
		// Whatever the stick is doing under LT, it must reach neutral before offence can start again.
		bSpent = true;
		bPrevLT = true;
		bPrevLB = Input.bLB;
		bPrevY = Input.bY;
		return;
	}
	bPrevLT = false;

	// A gesture's modifiers latch: anything held from its first step to its commit counts.
	if (bInGesture)
	{
		bLatchedRT |= Input.bRT;
		bLatchedRB |= Input.bRB;
		bLatchedLB |= Input.bLB;
		if (Clock - GestureStart > Window)
		{
			Finish(State, OutEvents);
			// A step that arrived on this very frame belongs to a new gesture, not to the one that just closed.
			if (bChanged)
			{
				bSpent = false;
			}
		}
	}

	// LB with no gesture is a generic fake: on release, or once the window passes with no stick step.
	if (Input.bLB && !bPrevLB && !bInGesture)
	{
		bFakeCandidate = true;
		FakeCandidateStart = Clock;
	}
	if (bFakeCandidate && !bInGesture && (!Input.bLB || Clock - FakeCandidateStart >= Window))
	{
		Emit(OutEvents, EOpenStanceInputEventType::GenericFake, State);
		OutEvents.Last().bFake = true;
		bFakeCandidate = false;
	}

	if (CurrentDir == EOpenStanceStickDir::Neutral)
	{
		if (bChanged)
		{
			bSpent = false;
			if (bInGesture)
			{
				Finish(State, OutEvents);
				bSpent = false;
			}
		}
	}
	else if (bChanged && !bSpent)
	{
		if (!bInGesture)
		{
			BeginGesture(Input, State);
		}
		Path.Add(CurrentDir);
		History.Add({ CurrentDir, Clock });

		const FMatch Match = MatchPath(State);
		if (Match.Kind == EMatch::Exact)
		{
			Commit(Match, State, OutEvents);
			EndGesture();
			bSpent = true;
		}
		else if (Match.Kind == EMatch::None)
		{
			// Nothing can start with this path, so reject it now rather than wait out the window.
			Emit(OutEvents, EOpenStanceInputEventType::GestureRejected, State);
			State.bJumpPrimed = false;
			EndGesture();
			bSpent = true;
		}
	}

	bPrevLB = Input.bLB;
	bPrevY = Input.bY;
}
