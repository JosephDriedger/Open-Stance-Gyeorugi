#include "Combat/OpenStanceHit.h"
#include "Misc/AutomationTest.h"

#if WITH_DEV_AUTOMATION_TESTS

namespace
{
	using S = EOpenStanceCombatState;

	/** One attacker and one defender on the mat: a reproducible hit scenario with no actors. */
	struct FHitRig
	{
		FOpenStanceCombatMachine Machine;
		FOpenStanceFighterState State;
		FOpenStanceMatchStatus Match;
		FOpenStanceHitRegistry Registry;
		FOpenStanceFighterBody Attacker;
		FOpenStanceFighterBody Defender;
		TArray<FOpenStanceCombatEvent> Events;
		TArray<FOpenStanceContact> Contacts;
		bool bContactOutsideActive = false;

		static constexpr float Tick = 1.0f / 120.0f;

		FHitRig(float Gap = 100.0f)
		{
			Match.State = EOpenStanceMatchState::Running;
			Attacker.Root = FVector::ZeroVector;
			Attacker.Side = EOpenStanceSide::Chung;
			Defender.Root = FVector(Gap, 0.0, 0.0);
			Defender.Side = EOpenStanceSide::Hong;
		}

		static FOpenStanceAttackRequest Request(const TCHAR* Row, bool bFake = false)
		{
			FOpenStanceAttackRequest Result;
			Result.MoveName = Row;
			Result.Row = FOpenStanceMoveData::BuildSeedRows()[Row];
			Result.bFake = bFake;
			return Result;
		}

		static FOpenStanceAttackRequest PunchRequest(EOpenStanceTarget Target)
		{
			FOpenStanceAttackRequest Result = Request(TEXT("SideKick_Trunk"));
			Result.MoveName = TEXT("Punch");
			Result.Row.Technique = EOpenStanceTechnique::Punch;
			Result.Row.Target = Target;
			Result.Row.Limb = EOpenStanceStrikeLimb::Glove;
			Result.Row.Points = 1;
			Result.Row.ReachCm = 70.0f;
			Result.Row.Impact = 20.0f;
			return Result;
		}

		/** Throws the technique and traces its synthetic tip every frame until it has finished. */
		void Throw(const FOpenStanceAttackRequest& Request, float TipHeightOverride = -1.0f)
		{
			Machine.RequestAttack(Request, State, Match, true, Events);
			const float Total = Request.Row.GetTotalSeconds() + 0.1f;
			FVector Previous = Attacker.Root;
			for (float Time = 0.0f; Time < Total; Time += Tick)
			{
				Machine.Tick(Tick, State, Match, Events);

				const bool bActive = State.CombatState == S::AttackActive;
				const float Progress = bActive ? FMath::Clamp((Machine.GetStateElapsed()) / FMath::Max(Request.Row.ActiveSeconds, 0.001f), 0.0f, 1.0f) : 0.0f;
				FOpenStanceHitContext Context;
				Context.Attack = Machine.GetCurrentAttack();
				Context.bCanScore = Machine.CanScore(State, Match);
				Context.AttackSerial = Machine.GetAttackSerial();
				Context.ImpactScale = Machine.GetImpactScale(State);
				Context.Attacker = Attacker;
				Context.Defender = Defender;

				// Trace the tip at full reach through the whole sequence, so startup and recovery frames are tested too.
				FVector Tip = FOpenStanceHitRegistry::SyntheticTip(Attacker, FVector(1.0, 0.0, 0.0), Request.Row, bActive ? Progress : 1.0f, Registry.Tuning);
				if (TipHeightOverride >= 0.0f)
				{
					Tip.Z = TipHeightOverride;
				}
				Context.Trace.Start = Previous;
				Context.Trace.End = Tip;
				Context.Trace.Limb = Request.Row.Limb;
				Previous = Tip;

				const int32 Before = Contacts.Num();
				Registry.Trace(Context, Contacts);
				bContactOutsideActive |= Contacts.Num() > Before && !bActive;
			}
		}

		int32 Count(EOpenStanceContactType Type) const
		{
			return Contacts.FilterByPredicate([Type](const FOpenStanceContact& C) { return C.Type == Type; }).Num();
		}
	};
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FOpenStanceHitPointsTest, "OpenStance.Hit.Points", EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FOpenStanceHitPointsTest::RunTest(const FString& Parameters)
{
	struct FCase
	{
		const TCHAR* Name;
		FOpenStanceAttackRequest Request;
		float Gap;
		int32 Points;
		EOpenStanceBodyZone Zone;
	};
	const FCase Cases[] = {
		{ TEXT("punch to the trunk"), FHitRig::PunchRequest(EOpenStanceTarget::Trunk), 70.0f, 1, EOpenStanceBodyZone::Trunk },
		{ TEXT("body kick"), FHitRig::Request(TEXT("SideKick_Trunk")), 100.0f, 2, EOpenStanceBodyZone::Trunk },
		{ TEXT("head kick"), FHitRig::Request(TEXT("SideKick_Head")), 100.0f, 3, EOpenStanceBodyZone::Head },
		{ TEXT("spinning body kick"), FHitRig::Request(TEXT("SpinSide_Trunk")), 110.0f, 4, EOpenStanceBodyZone::Trunk },
		{ TEXT("spinning head kick"), FHitRig::Request(TEXT("SpinSide_Head")), 110.0f, 6, EOpenStanceBodyZone::Head },
	};

	for (const FCase& Case : Cases)
	{
		FHitRig Rig(Case.Gap);
		Rig.Throw(Case.Request);
		if (TestEqual(*FString::Printf(TEXT("%s: one score event"), Case.Name), Rig.Count(EOpenStanceContactType::Score), 1))
		{
			const FOpenStanceContact& Contact = Rig.Contacts[0];
			TestEqual(*FString::Printf(TEXT("%s: points"), Case.Name), Contact.Points, Case.Points);
			TestEqual(*FString::Printf(TEXT("%s: zone"), Case.Name), Contact.Zone, Case.Zone);
			TestEqual(*FString::Printf(TEXT("%s: technique"), Case.Name), Contact.Technique, Case.Request.Row.Technique);
			TestEqual(*FString::Printf(TEXT("%s: attacker"), Case.Name), Contact.Attacker, EOpenStanceSide::Chung);
			TestEqual(*FString::Printf(TEXT("%s: target"), Case.Name), Contact.Defender, EOpenStanceSide::Hong);
			TestEqual(*FString::Printf(TEXT("%s: spin classification"), Case.Name), Contact.bSpinning, Case.Request.Row.bSpinning);
		}
		TestFalse(*FString::Printf(TEXT("%s: nothing registered outside the active phase"), Case.Name), Rig.bContactOutsideActive);
	}
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FOpenStanceHitDedupTest, "OpenStance.Hit.Dedup", EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FOpenStanceHitDedupTest::RunTest(const FString& Parameters)
{
	// The trace overlaps the defender on every active frame; the technique still scores once.
	FHitRig Rig;
	const FOpenStanceAttackRequest Kick = FHitRig::Request(TEXT("SideKick_Trunk"));
	Rig.Throw(Kick);
	TestEqual(TEXT("one score for the whole technique"), Rig.Contacts.Num(), 1);

	// The next technique is a new attack and can score again.
	Rig.Throw(Kick);
	TestEqual(TEXT("a second kick scores again"), Rig.Contacts.Num(), 2);

	// Directly: the same attack's traces after the first contact are ignored and say why.
	FHitRig Direct;
	Direct.Machine.RequestAttack(Kick, Direct.State, Direct.Match, true, Direct.Events);
	Direct.Machine.Tick(0.3f, Direct.State, Direct.Match, Direct.Events);
	TestEqual(TEXT("active"), Direct.State.CombatState, S::AttackActive);
	FOpenStanceHitContext Context;
	Context.Attack = Direct.Machine.GetCurrentAttack();
	Context.bCanScore = true;
	Context.AttackSerial = Direct.Machine.GetAttackSerial();
	Context.Attacker = Direct.Attacker;
	Context.Defender = Direct.Defender;
	Context.Trace.Start = FVector(90.0, 0.0, 120.0);
	Context.Trace.End = FVector(100.0, 0.0, 120.0);
	TestTrue(TEXT("first trace registers"), Direct.Registry.Trace(Context, Direct.Contacts));
	TestFalse(TEXT("second trace of the same attack does not"), Direct.Registry.Trace(Context, Direct.Contacts));
	TestTrue(TEXT("and the overlay is told why"), Direct.Registry.GetLastTrace().Ignored.Contains(TEXT("already")));
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FOpenStanceHitNoScoreTest, "OpenStance.Hit.NoScore", EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FOpenStanceHitNoScoreTest::RunTest(const FString& Parameters)
{
	// A clean miss: the defender is well out of reach.
	{
		FHitRig Rig(300.0f);
		Rig.Throw(FHitRig::Request(TEXT("SideKick_Trunk")));
		TestEqual(TEXT("a kick from 3 m registers nothing"), Rig.Contacts.Num(), 0);
	}
	// Close enough in range but the tip passes wide of the defender.
	{
		FHitRig Rig(100.0f);
		Rig.Defender.Root.Y = 80.0;
		Rig.Throw(FHitRig::Request(TEXT("SideKick_Trunk")));
		TestEqual(TEXT("a kick that goes past registers nothing"), Rig.Contacts.Num(), 0);
	}
	// A fake plays startup and recovery and never scores, even with the defender standing in its path.
	{
		FHitRig Rig;
		Rig.Throw(FHitRig::Request(TEXT("SideKick_Trunk"), true));
		TestEqual(TEXT("a fake registers nothing"), Rig.Contacts.Num(), 0);
	}
	// Startup and recovery frames are ignored; so is a stopped match.
	{
		FHitRig Rig;
		const FOpenStanceAttackRequest Kick = FHitRig::Request(TEXT("SideKick_Trunk"));
		Rig.Machine.RequestAttack(Kick, Rig.State, Rig.Match, true, Rig.Events);
		FOpenStanceHitContext Context;
		Context.Attack = Rig.Machine.GetCurrentAttack();
		Context.bCanScore = Rig.Machine.CanScore(Rig.State, Rig.Match);
		Context.AttackSerial = Rig.Machine.GetAttackSerial();
		Context.Attacker = Rig.Attacker;
		Context.Defender = Rig.Defender;
		Context.Trace.Start = FVector(90.0, 0.0, 120.0);
		Context.Trace.End = FVector(100.0, 0.0, 120.0);
		TestFalse(TEXT("startup does not register"), Rig.Registry.Trace(Context, Rig.Contacts));
		Rig.Machine.Tick(0.3f, Rig.State, Rig.Match, Rig.Events);
		Rig.Match.State = EOpenStanceMatchState::Stopped;
		Context.bCanScore = Rig.Machine.CanScore(Rig.State, Rig.Match);
		TestFalse(TEXT("a stopped match does not register"), Rig.Registry.Trace(Context, Rig.Contacts));
		TestEqual(TEXT("nothing was recorded"), Rig.Contacts.Num(), 0);
	}
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FOpenStanceHitIllegalTest, "OpenStance.Hit.Illegal", EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FOpenStanceHitIllegalTest::RunTest(const FString& Parameters)
{
	// A punch to the head is illegal, not a score.
	{
		FHitRig Rig(70.0f);
		Rig.Throw(FHitRig::PunchRequest(EOpenStanceTarget::Head), 160.0f);
		TestEqual(TEXT("no score"), Rig.Count(EOpenStanceContactType::Score), 0);
		if (TestEqual(TEXT("an invalid-contact event for the referee"), Rig.Count(EOpenStanceContactType::PunchToHead), 1))
		{
			TestEqual(TEXT("worth nothing"), Rig.Contacts[0].Points, 0);
			TestEqual(TEXT("on the head"), Rig.Contacts[0].Zone, EOpenStanceBodyZone::Head);
		}
	}
	// A kick that lands below the belt line is a foul.
	{
		FHitRig Rig(100.0f);
		Rig.Throw(FHitRig::Request(TEXT("Roundhouse_Trunk")), 70.0f);
		TestEqual(TEXT("no score"), Rig.Count(EOpenStanceContactType::Score), 0);
		if (TestEqual(TEXT("a below-belt event for the referee"), Rig.Count(EOpenStanceContactType::KickBelowBelt), 1))
		{
			TestEqual(TEXT("below the belt"), Rig.Contacts[0].Zone, EOpenStanceBodyZone::BelowBelt);
		}
	}
	// A punch below the belt just misses the protector.
	{
		FHitRig Rig(70.0f);
		Rig.Throw(FHitRig::PunchRequest(EOpenStanceTarget::Trunk), 70.0f);
		TestEqual(TEXT("a low punch registers nothing"), Rig.Contacts.Num(), 0);
	}
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FOpenStanceHitImpactTest, "OpenStance.Hit.Impact", EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FOpenStanceHitImpactTest::RunTest(const FString& Parameters)
{
	// The trunk protector needs impact at or above the threshold; the head does not.
	{
		FHitRig Rig;
		FOpenStanceAttackRequest Soft = FHitRig::Request(TEXT("SideKick_Trunk"));
		Soft.Row.Impact = 29.0f;
		Rig.Throw(Soft);
		TestEqual(TEXT("below the threshold there is contact but no score"), Rig.Count(EOpenStanceContactType::WeakImpact), 1);
		TestEqual(TEXT("and no points"), Rig.Count(EOpenStanceContactType::Score), 0);
	}
	{
		FHitRig Rig;
		FOpenStanceAttackRequest Edge = FHitRig::Request(TEXT("SideKick_Trunk"));
		Edge.Row.Impact = 30.0f;
		Rig.Throw(Edge);
		TestEqual(TEXT("at the threshold it scores"), Rig.Count(EOpenStanceContactType::Score), 1);
	}
	{
		FHitRig Rig;
		FOpenStanceAttackRequest Soft = FHitRig::Request(TEXT("SideKick_Head"));
		Soft.Row.Impact = 5.0f;
		Rig.Throw(Soft);
		TestEqual(TEXT("a head kick needs only valid contact"), Rig.Count(EOpenStanceContactType::Score), 1);
	}
	// Low stamina weakens the kick enough to drop under the threshold.
	{
		FHitRig Rig;
		Rig.State.Stamina = 30.0f;
		FOpenStanceAttackRequest Kick = FHitRig::Request(TEXT("SideKick_Trunk"));
		Kick.Row.Impact = 35.0f;
		Kick.Row.StaminaCost = 10.0f; // leaves 20: low stamina, impact 28
		Rig.Throw(Kick);
		TestEqual(TEXT("35 impact at low stamina is 28 and does not register"), Rig.Count(EOpenStanceContactType::WeakImpact), 1);
	}
	// A kick aimed at the trunk that lands on the head scores the head value.
	{
		FHitRig Rig;
		Rig.Throw(FHitRig::Request(TEXT("SideKick_Trunk")), 160.0f);
		if (TestEqual(TEXT("scored"), Rig.Count(EOpenStanceContactType::Score), 1))
		{
			TestEqual(TEXT("the zone touched sets the value"), Rig.Contacts[0].Points, 3);
		}
	}
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FOpenStanceHitAlignmentTest, "OpenStance.Hit.Alignment", EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FOpenStanceHitAlignmentTest::RunTest(const FString& Parameters)
{
	const FOpenStanceHitTuning Tuning;
	FOpenStanceFighterBody Body;
	Body.Root = FVector::ZeroVector;

	// Trunk radius 19.25 + foot 9 + alignment 8 = 36.25: a tip inside that is nudged in, outside it is not.
	FOpenStanceLimbTrace Near;
	Near.Start = Near.End = FVector(35.0, 0.0, 120.0);
	FVector Point;
	TestEqual(TEXT("a tip 35 cm from the centre is nudged into the trunk"), FOpenStanceHitRegistry::FindContact(Near, Body, Tuning, Point), EOpenStanceBodyZone::Trunk);

	FOpenStanceLimbTrace Far;
	Far.Start = Far.End = FVector(40.0, 0.0, 120.0);
	TestEqual(TEXT("a tip 40 cm out is not pulled in"), FOpenStanceHitRegistry::FindContact(Far, Body, Tuning, Point), EOpenStanceBodyZone::None);

	// The correction never makes an out-of-range attack reach: the move's reach gates the contact first.
	FHitRig Rig(148.0f); // reach 105 + trunk 19.25 + alignment 8 = 132 < 148
	FOpenStanceAttackRequest Kick = FHitRig::Request(TEXT("SideKick_Trunk"));
	Rig.Machine.RequestAttack(Kick, Rig.State, Rig.Match, true, Rig.Events);
	Rig.Machine.Tick(0.3f, Rig.State, Rig.Match, Rig.Events);
	FOpenStanceHitContext Context;
	Context.Attack = Rig.Machine.GetCurrentAttack();
	Context.bCanScore = true;
	Context.AttackSerial = Rig.Machine.GetAttackSerial();
	Context.Attacker = Rig.Attacker;
	Context.Defender = Rig.Defender;
	Context.Trace.Start = FVector(140.0, 0.0, 120.0); // a trace that sits on the defender regardless
	Context.Trace.End = FVector(148.0, 0.0, 120.0);
	TestFalse(TEXT("an attack from beyond its reach does not connect, even with a trace on the defender"), Rig.Registry.Trace(Context, Rig.Contacts));
	TestTrue(TEXT("and it is flagged out of range"), Rig.Registry.GetLastTrace().bOutOfRange);

	// A taller attacker reaches further with the same move.
	FHitRig Tall(140.0f);
	Tall.Attacker.HeightCm = 192.0f;
	Tall.Throw(FHitRig::Request(TEXT("SideKick_Trunk")));
	TestEqual(TEXT("a 192 cm fighter's scaled reach covers 140 cm"), Tall.Contacts.Num(), 1);
	FHitRig Short(140.0f);
	Short.Throw(FHitRig::Request(TEXT("SideKick_Trunk")));
	TestEqual(TEXT("the 175 cm fighter's does not"), Short.Contacts.Num(), 0);
	return true;
}

#endif
