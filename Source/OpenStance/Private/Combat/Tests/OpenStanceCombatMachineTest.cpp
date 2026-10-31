#include "Combat/OpenStanceCombatMachine.h"
#include "Misc/AutomationTest.h"

#if WITH_DEV_AUTOMATION_TESTS

namespace
{
	using S = EOpenStanceCombatState;

	/** The minimal reproducible combat scenario: one fighter, live play, scripted time. */
	struct FCombatRig
	{
		FOpenStanceCombatMachine Machine;
		FOpenStanceFighterState State;
		FOpenStanceMatchStatus Match;
		TArray<FOpenStanceCombatEvent> Events;

		static constexpr float Tick = 1.0f / 120.0f;

		FCombatRig()
		{
			Match.State = EOpenStanceMatchState::Running;
			Machine.Random.Initialize(7);
		}

		FOpenStanceAttackRequest Request(const TCHAR* Row, bool bFake = false) const
		{
			FOpenStanceAttackRequest Result;
			Result.MoveName = Row;
			Result.Row = FOpenStanceMoveData::BuildSeedRows()[Row];
			Result.bFake = bFake;
			return Result;
		}

		bool Attack(const FOpenStanceAttackRequest& Request, bool bCanStart = true)
		{
			return Machine.RequestAttack(Request, State, Match, bCanStart, Events);
		}

		void Run(float Seconds)
		{
			const int32 Count = FMath::Max(1, FMath::RoundToInt(Seconds / Tick));
			for (int32 Index = 0; Index < Count; ++Index)
			{
				Machine.Tick(Tick, State, Match, Events);
			}
		}

		int32 Count(EOpenStanceCombatEventType Type) const
		{
			return Events.FilterByPredicate([Type](const FOpenStanceCombatEvent& E) { return E.Type == Type; }).Num();
		}

		bool Entered(S To) const
		{
			return Events.ContainsByPredicate([To](const FOpenStanceCombatEvent& E) { return E.Type == EOpenStanceCombatEventType::StateChanged && E.To == To; });
		}
	};
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FOpenStanceCombatTransitionsTest, "OpenStance.Combat.Transitions", EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FOpenStanceCombatTransitionsTest::RunTest(const FString& Parameters)
{
	const S All[] = { S::IdleMovement, S::AttackStartup, S::AttackActive, S::AttackRecovery, S::ActiveDefense, S::HitReaction, S::Staggered, S::KnockedDown, S::Recovering, S::MatchFinished };

	auto Legal = [](S From, S To) { return FOpenStanceCombatMachine::IsLegalTransition(From, To, false); };

	// Exactly these, and no others.
	const TArray<TPair<S, S>> Allowed = {
		{ S::IdleMovement, S::AttackStartup }, { S::IdleMovement, S::ActiveDefense }, { S::IdleMovement, S::HitReaction }, { S::IdleMovement, S::Staggered }, { S::IdleMovement, S::KnockedDown },
		{ S::AttackStartup, S::AttackActive }, { S::AttackStartup, S::AttackRecovery }, { S::AttackStartup, S::HitReaction }, { S::AttackStartup, S::Staggered }, { S::AttackStartup, S::KnockedDown },
		{ S::AttackActive, S::AttackRecovery }, { S::AttackActive, S::HitReaction }, { S::AttackActive, S::Staggered }, { S::AttackActive, S::KnockedDown },
		{ S::AttackRecovery, S::IdleMovement }, { S::AttackRecovery, S::HitReaction }, { S::AttackRecovery, S::Staggered }, { S::AttackRecovery, S::KnockedDown },
		{ S::ActiveDefense, S::IdleMovement }, { S::ActiveDefense, S::HitReaction }, { S::ActiveDefense, S::Staggered }, { S::ActiveDefense, S::KnockedDown },
		{ S::HitReaction, S::IdleMovement }, { S::HitReaction, S::HitReaction }, { S::HitReaction, S::Staggered }, { S::HitReaction, S::KnockedDown },
		{ S::Staggered, S::IdleMovement }, { S::Staggered, S::HitReaction }, { S::Staggered, S::Staggered }, { S::Staggered, S::KnockedDown },
		{ S::KnockedDown, S::Recovering },
		{ S::Recovering, S::IdleMovement },
	};

	int32 Mismatches = 0;
	for (const S From : All)
	{
		for (const S To : All)
		{
			bool bExpected = To == S::MatchFinished && From != S::MatchFinished;
			for (const TPair<S, S>& Pair : Allowed)
			{
				bExpected |= Pair.Key == From && Pair.Value == To;
			}
			if (Legal(From, To) != bExpected)
			{
				AddError(FString::Printf(TEXT("%s -> %s should be %s"), *UEnum::GetValueAsString(From), *UEnum::GetValueAsString(To), bExpected ? TEXT("legal") : TEXT("illegal")));
				++Mismatches;
			}
		}
	}
	TestEqual(TEXT("the transition table matches the GDD's states"), Mismatches, 0);

	TestFalse(TEXT("a new technique cannot start in recovery"), FOpenStanceCombatMachine::IsLegalTransition(S::AttackRecovery, S::AttackStartup, false));
	TestTrue(TEXT("unless the move's cancel window is open"), FOpenStanceCombatMachine::IsLegalTransition(S::AttackRecovery, S::AttackStartup, true));
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FOpenStanceCombatPhasesTest, "OpenStance.Combat.Phases", EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FOpenStanceCombatPhasesTest::RunTest(const FString& Parameters)
{
	FCombatRig Rig;
	const FOpenStanceAttackRequest Kick = Rig.Request(TEXT("SideKick_Trunk")); // 0.25 / 0.10 / 0.45
	TestTrue(TEXT("the kick starts"), Rig.Attack(Kick));
	TestEqual(TEXT("in startup"), Rig.State.CombatState, S::AttackStartup);
	TestEqual(TEXT("it cost stamina"), Rig.State.Stamina, FOpenStanceFighterState::FullStamina - 8.0f, 0.001f);
	TestFalse(TEXT("startup does not score"), Rig.Machine.CanScore(Rig.State, Rig.Match));

	Rig.Run(0.20f);
	TestEqual(TEXT("still startup at 0.20 s"), Rig.State.CombatState, S::AttackStartup);
	Rig.Run(0.07f);
	TestEqual(TEXT("active at 0.27 s"), Rig.State.CombatState, S::AttackActive);
	TestTrue(TEXT("the active phase can score"), Rig.Machine.CanScore(Rig.State, Rig.Match));
	Rig.Run(0.10f);
	TestEqual(TEXT("recovery at 0.37 s"), Rig.State.CombatState, S::AttackRecovery);
	TestFalse(TEXT("recovery does not score"), Rig.Machine.CanScore(Rig.State, Rig.Match));
	Rig.Run(0.40f);
	TestEqual(TEXT("still recovering at 0.77 s: the punishable window is intact"), Rig.State.CombatState, S::AttackRecovery);
	Rig.Run(0.10f);
	TestEqual(TEXT("idle again at 0.87 s"), Rig.State.CombatState, S::IdleMovement);
	TestNull(TEXT("no current attack"), Rig.Machine.GetCurrentAttack());

	TestEqual(TEXT("active began once"), Rig.Count(EOpenStanceCombatEventType::ActiveBegan), 1);
	TestEqual(TEXT("and ended once"), Rig.Count(EOpenStanceCombatEventType::ActiveEnded), 1);

	// Attacks cannot start in recovery without a cancel window.
	FCombatRig Busy;
	Busy.Attack(Busy.Request(TEXT("SideKick_Trunk")));
	Busy.Run(0.5f);
	TestEqual(TEXT("now recovering"), Busy.State.CombatState, S::AttackRecovery);
	Busy.Events.Reset();
	TestFalse(TEXT("a new attack is refused in recovery"), Busy.Attack(Busy.Request(TEXT("Roundhouse_Trunk"))));
	TestEqual(TEXT("with a reason"), Busy.Count(EOpenStanceCombatEventType::AttackRejected), 1);

	// A move with a cancel window allows the next one from that point.
	FCombatRig Cancel;
	FOpenStanceAttackRequest Cancelable = Cancel.Request(TEXT("SideKick_Trunk"));
	Cancelable.Row.CancelWindowSeconds = 0.2f;
	Cancel.Attack(Cancelable);
	Cancel.Run(0.4f);
	TestEqual(TEXT("in recovery"), Cancel.State.CombatState, S::AttackRecovery);
	TestFalse(TEXT("before the cancel window opens"), Cancel.Attack(Cancel.Request(TEXT("Roundhouse_Trunk"))));
	Cancel.Run(0.15f);
	TestTrue(TEXT("the window is open"), Cancel.Machine.IsCancelWindowOpen(Cancel.State));
	TestTrue(TEXT("a new attack can cancel into it"), Cancel.Attack(Cancel.Request(TEXT("Roundhouse_Trunk"))));
	TestEqual(TEXT("and starts up"), Cancel.State.CombatState, S::AttackStartup);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FOpenStanceCombatFakeTest, "OpenStance.Combat.Fake", EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FOpenStanceCombatFakeTest::RunTest(const FString& Parameters)
{
	FCombatRig Rig;
	Rig.Attack(Rig.Request(TEXT("SpinSide_Trunk"), true));
	TestEqual(TEXT("a fake reports itself"), Rig.Count(EOpenStanceCombatEventType::FakeStarted), 1);
	bool bEverScored = false;
	for (int32 Index = 0; Index < 200; ++Index)
	{
		Rig.Run(0.01f);
		bEverScored |= Rig.Machine.CanScore(Rig.State, Rig.Match);
	}
	TestFalse(TEXT("a fake never scores"), bEverScored);
	TestFalse(TEXT("and never reaches the active phase"), Rig.Entered(S::AttackActive));
	TestTrue(TEXT("it went startup to recovery"), Rig.Entered(S::AttackRecovery));
	TestEqual(TEXT("and is idle again"), Rig.State.CombatState, S::IdleMovement);
	TestEqual(TEXT("no active events"), Rig.Count(EOpenStanceCombatEventType::ActiveBegan), 0);

	// A fake's recovery is shorter: nothing was committed.
	FCombatRig Timing;
	Timing.Attack(Timing.Request(TEXT("SideKick_Trunk"), true)); // 0.25 startup, 0.45 * 0.4 recovery
	Timing.Run(0.25f + 0.45f * 0.4f + 0.05f);
	TestEqual(TEXT("a fake is free again after its startup and short recovery"), Timing.State.CombatState, S::IdleMovement);

	// A notify arriving during a fake must not open the active phase.
	FCombatRig Notified;
	Notified.Attack(Notified.Request(TEXT("SideKick_Trunk"), true));
	Notified.Machine.NotifyActiveBegin(Notified.State, Notified.Events);
	TestEqual(TEXT("an active notify is ignored for a fake"), Notified.State.CombatState, S::AttackStartup);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FOpenStanceCombatStaminaTest, "OpenStance.Combat.Stamina", EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FOpenStanceCombatStaminaTest::RunTest(const FString& Parameters)
{
	// Low stamina never locks the controls; it lengthens recovery by 30% and cuts impact by 20%.
	FCombatRig Rig;
	Rig.State.Stamina = 30.0f;
	TestTrue(TEXT("a kick still starts"), Rig.Attack(Rig.Request(TEXT("SpinSide_Trunk")))); // costs 20, leaves 10
	TestTrue(TEXT("stamina is now low"), Rig.State.IsLowStamina());
	TestEqual(TEXT("impact is 80%"), Rig.Machine.GetImpactScale(Rig.State), 0.8f, 0.001f);
	Rig.Run(0.40f + 0.12f + 0.05f);
	TestEqual(TEXT("recovering"), Rig.State.CombatState, S::AttackRecovery);
	Rig.Run(0.60f + 0.05f);
	TestEqual(TEXT("0.6 s of recovery is not enough at low stamina"), Rig.State.CombatState, S::AttackRecovery);
	Rig.Run(0.60f * 0.3f + 0.05f);
	TestEqual(TEXT("30% longer finishes"), Rig.State.CombatState, S::IdleMovement);

	FCombatRig Empty;
	Empty.State.Stamina = 3.0f;
	TestTrue(TEXT("with almost nothing left the kick still starts"), Empty.Attack(Empty.Request(TEXT("SpinSide_Trunk"))));
	TestEqual(TEXT("stamina bottoms out at zero"), Empty.State.Stamina, 0.0f, 0.001f);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FOpenStanceCombatHitTest, "OpenStance.Combat.Hit", EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FOpenStanceCombatHitTest::RunTest(const FString& Parameters)
{
	using Sev = EOpenStanceReactionSeverity;

	// Interrupting startup: the technique never becomes active and nothing scores.
	{
		FCombatRig Rig;
		Rig.Attack(Rig.Request(TEXT("SideKick_Trunk")));
		Rig.Run(0.10f);
		Rig.Machine.ApplyHit(Sev::Normal, Rig.State, Rig.Events);
		TestEqual(TEXT("a Normal hit interrupts startup"), Rig.State.CombatState, S::HitReaction);
		TestNull(TEXT("the technique is gone"), Rig.Machine.GetCurrentAttack());
		Rig.Run(0.5f);
		TestFalse(TEXT("the interrupted technique never became active"), Rig.Entered(S::AttackActive));
		TestEqual(TEXT("control returns after about 0.4 s"), Rig.State.CombatState, S::IdleMovement);
	}
	// Interrupting the active phase closes the window at once.
	{
		FCombatRig Rig;
		Rig.Attack(Rig.Request(TEXT("SideKick_Trunk")));
		Rig.Run(0.28f);
		TestTrue(TEXT("active"), Rig.Machine.CanScore(Rig.State, Rig.Match));
		Rig.Machine.ApplyHit(Sev::Heavy, Rig.State, Rig.Events);
		TestEqual(TEXT("a Heavy hit staggers"), Rig.State.CombatState, S::Staggered);
		TestFalse(TEXT("the trace window is closed"), Rig.Machine.CanScore(Rig.State, Rig.Match));
		TestEqual(TEXT("the active phase ended"), Rig.Count(EOpenStanceCombatEventType::ActiveEnded), 1);
		Rig.Run(0.9f);
		TestEqual(TEXT("still staggered at 0.9 s"), Rig.State.CombatState, S::Staggered);
		Rig.Run(0.2f);
		TestEqual(TEXT("free after 1.0 s"), Rig.State.CombatState, S::IdleMovement);
	}
	// Minor hits are additive and change nothing.
	{
		FCombatRig Rig;
		Rig.Attack(Rig.Request(TEXT("SideKick_Trunk")));
		Rig.Machine.ApplyHit(Sev::Minor, Rig.State, Rig.Events);
		TestEqual(TEXT("a Minor hit keeps the technique going"), Rig.State.CombatState, S::AttackStartup);
		TestEqual(TEXT("but reports the reaction"), Rig.Count(EOpenStanceCombatEventType::HitReacted), 1);
	}
	// A knockdown from a hit goes to the floor, then gets up; it is not a foul.
	{
		FCombatRig Rig;
		Rig.Machine.ApplyHit(Sev::Knockdown, Rig.State, Rig.Events);
		TestEqual(TEXT("knocked down"), Rig.State.CombatState, S::KnockedDown);
		TestEqual(TEXT("the cause is the opponent's hit"), Rig.Machine.GetKnockdownCause(), EOpenStanceKnockdownCause::Hit);
		const TArray<FOpenStanceCombatEvent> Down = Rig.Events.FilterByPredicate([](const FOpenStanceCombatEvent& E) { return E.Type == EOpenStanceCombatEventType::KnockedDown; });
		if (TestEqual(TEXT("one knockdown event"), Down.Num(), 1))
		{
			TestFalse(TEXT("a hit knockdown is not the Falling penalty"), Down[0].bFoulFall);
		}
		Rig.Machine.ApplyHit(Sev::Heavy, Rig.State, Rig.Events);
		TestEqual(TEXT("a fighter on the floor cannot be hit again"), Rig.State.CombatState, S::KnockedDown);
		Rig.Run(3.1f);
		TestEqual(TEXT("getting up"), Rig.State.CombatState, S::Recovering);
		Rig.Run(0.7f);
		TestEqual(TEXT("back on their feet"), Rig.State.CombatState, S::IdleMovement);
		TestEqual(TEXT("the cause is cleared"), Rig.Machine.GetKnockdownCause(), EOpenStanceKnockdownCause::None);
	}
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FOpenStanceCombatFailedLandingTest, "OpenStance.Combat.FailedLanding", EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FOpenStanceCombatFailedLandingTest::RunTest(const FString& Parameters)
{
	// A failed landing is a knockdown that no hit caused: the Falling penalty.
	{
		FCombatRig Rig;
		FOpenStanceAttackRequest Spin = Rig.Request(TEXT("SpinSide_Trunk"));
		Spin.Row.SelfFallChance = 1.0f;
		Rig.Attack(Spin);
		Rig.Run(0.4f + 0.12f + 0.6f + 0.05f);
		TestEqual(TEXT("recovery ended in a fall"), Rig.State.CombatState, S::KnockedDown);
		TestEqual(TEXT("caused by the failed landing"), Rig.Machine.GetKnockdownCause(), EOpenStanceKnockdownCause::FailedLanding);
		const TArray<FOpenStanceCombatEvent> Down = Rig.Events.FilterByPredicate([](const FOpenStanceCombatEvent& E) { return E.Type == EOpenStanceCombatEventType::KnockedDown; });
		if (TestEqual(TEXT("one knockdown event"), Down.Num(), 1))
		{
			TestTrue(TEXT("flagged as a foul fall for the referee"), Down[0].bFoulFall);
			TestEqual(TEXT("with its cause"), Down[0].Cause, EOpenStanceKnockdownCause::FailedLanding);
		}
	}
	// With no chance it lands cleanly.
	{
		FCombatRig Rig;
		FOpenStanceAttackRequest Kick = Rig.Request(TEXT("SideKick_Trunk"));
		Kick.Row.SelfFallChance = 0.0f;
		Rig.Attack(Kick);
		Rig.Run(1.0f);
		TestEqual(TEXT("no fall at zero chance"), Rig.State.CombatState, S::IdleMovement);
	}
	// A fake never fails its landing.
	{
		FCombatRig Rig;
		FOpenStanceAttackRequest Fake = Rig.Request(TEXT("SpinSide_Trunk"), true);
		Fake.Row.SelfFallChance = 1.0f;
		Rig.Attack(Fake);
		Rig.Run(1.5f);
		TestEqual(TEXT("a fake recovers"), Rig.State.CombatState, S::IdleMovement);
	}
	// The chance is a probability over many throws.
	{
		int32 Falls = 0;
		for (int32 Seed = 0; Seed < 400; ++Seed)
		{
			FCombatRig Rig;
			Rig.Machine.Random.Initialize(Seed);
			FOpenStanceAttackRequest Spin = Rig.Request(TEXT("SpinSide_Trunk"));
			Spin.Row.SelfFallChance = 0.25f;
			Rig.Attack(Spin);
			Rig.Run(1.3f);
			Falls += Rig.State.CombatState == S::KnockedDown ? 1 : 0;
		}
		TestTrue(TEXT("about a quarter of throws fall at 0.25"), Falls > 60 && Falls < 140);
	}
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FOpenStanceCombatMatchTest, "OpenStance.Combat.Match", EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FOpenStanceCombatMatchTest::RunTest(const FString& Parameters)
{
	// Play stopped: no attacks, no scoring, and a technique in flight is cut off.
	FCombatRig Rig;
	Rig.Attack(Rig.Request(TEXT("SideKick_Trunk")));
	Rig.Run(0.28f);
	TestTrue(TEXT("active before the whistle"), Rig.Machine.CanScore(Rig.State, Rig.Match));
	Rig.Match.State = EOpenStanceMatchState::Stopped;
	TestFalse(TEXT("no scoring while stopped, even in an active phase"), Rig.Machine.CanScore(Rig.State, Rig.Match));
	Rig.Run(0.02f);
	TestEqual(TEXT("the technique is cut"), Rig.State.CombatState, S::IdleMovement);
	Rig.Events.Reset();
	TestFalse(TEXT("no attacks while stopped"), Rig.Attack(Rig.Request(TEXT("SideKick_Trunk"))));
	TestEqual(TEXT("rejected"), Rig.Count(EOpenStanceCombatEventType::AttackRejected), 1);
	Rig.Machine.SetDefense(true, Rig.State, Rig.Match, Rig.Events);
	TestEqual(TEXT("and no guard"), Rig.State.CombatState, S::IdleMovement);

	// Play resumes.
	Rig.Match.State = EOpenStanceMatchState::Running;
	TestTrue(TEXT("attacks work again once play is live"), Rig.Attack(Rig.Request(TEXT("SideKick_Trunk"))));

	// Finished: everything ends.
	Rig.Match.State = EOpenStanceMatchState::Finished;
	Rig.Run(0.02f);
	TestEqual(TEXT("the match is finished"), Rig.State.CombatState, S::MatchFinished);
	TestFalse(TEXT("no scoring"), Rig.Machine.CanScore(Rig.State, Rig.Match));
	TestFalse(TEXT("no attacks"), Rig.Attack(Rig.Request(TEXT("SideKick_Trunk"))));
	Rig.Machine.ApplyHit(EOpenStanceReactionSeverity::Knockdown, Rig.State, Rig.Events);
	TestEqual(TEXT("and no hits change a finished fighter"), Rig.State.CombatState, S::MatchFinished);

	// Switching sides blocks a technique.
	FCombatRig Switching;
	TestFalse(TEXT("an attack is refused mid-switch"), Switching.Attack(Switching.Request(TEXT("SideKick_Trunk")), false));
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FOpenStanceCombatDefenseTest, "OpenStance.Combat.Defense", EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FOpenStanceCombatDefenseTest::RunTest(const FString& Parameters)
{
	FCombatRig Rig;
	Rig.Machine.SetDefense(true, Rig.State, Rig.Match, Rig.Events);
	TestEqual(TEXT("LT enters Active Defense"), Rig.State.CombatState, S::ActiveDefense);
	TestFalse(TEXT("a technique cannot start from it"), Rig.Attack(Rig.Request(TEXT("SideKick_Trunk"))));
	Rig.Machine.SetDefense(false, Rig.State, Rig.Match, Rig.Events);
	TestEqual(TEXT("releasing LT returns to idle"), Rig.State.CombatState, S::IdleMovement);

	Rig.Attack(Rig.Request(TEXT("SideKick_Trunk")));
	Rig.Machine.SetDefense(true, Rig.State, Rig.Match, Rig.Events);
	TestEqual(TEXT("LT does not interrupt a technique"), Rig.State.CombatState, S::AttackStartup);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FOpenStanceCombatNotifyTest, "OpenStance.Combat.Notifies", EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FOpenStanceCombatNotifyTest::RunTest(const FString& Parameters)
{
	// Notify-driven: the montage decides when the trace window opens and closes.
	FCombatRig Rig;
	Rig.Machine.Tuning.bNotifyDriven = true;
	Rig.Attack(Rig.Request(TEXT("SideKick_Trunk"))); // 0.25 startup, bounded at 0.5
	Rig.Run(0.35f);
	TestEqual(TEXT("past the move's startup time the notify has not come: still startup"), Rig.State.CombatState, S::AttackStartup);
	Rig.Machine.NotifyActiveBegin(Rig.State, Rig.Events);
	TestEqual(TEXT("the notify opens the window"), Rig.State.CombatState, S::AttackActive);
	TestTrue(TEXT("scoring is possible"), Rig.Machine.CanScore(Rig.State, Rig.Match));
	Rig.Run(0.05f);
	Rig.Machine.NotifyActiveEnd(Rig.State, Rig.Events);
	TestEqual(TEXT("the end notify closes it"), Rig.State.CombatState, S::AttackRecovery);
	Rig.Machine.NotifyActiveEnd(Rig.State, Rig.Events);
	Rig.Machine.NotifyActiveBegin(Rig.State, Rig.Events);
	TestEqual(TEXT("notifies out of order are ignored"), Rig.State.CombatState, S::AttackRecovery);

	// A missing notify cannot freeze the fighter.
	FCombatRig Missing;
	Missing.Machine.Tuning.bNotifyDriven = true;
	Missing.Attack(Missing.Request(TEXT("SideKick_Trunk")));
	Missing.Run(0.55f);
	TestEqual(TEXT("the startup bound moves it to active anyway"), Missing.State.CombatState, S::AttackActive);
	Missing.Run(0.25f);
	TestEqual(TEXT("and the active bound to recovery"), Missing.State.CombatState, S::AttackRecovery);

	// Notifies at the wrong time do nothing.
	FCombatRig Idle;
	Idle.Machine.NotifyActiveBegin(Idle.State, Idle.Events);
	Idle.Machine.NotifyActiveEnd(Idle.State, Idle.Events);
	TestEqual(TEXT("notifies while idle are ignored"), Idle.State.CombatState, S::IdleMovement);
	return true;
}

#endif
