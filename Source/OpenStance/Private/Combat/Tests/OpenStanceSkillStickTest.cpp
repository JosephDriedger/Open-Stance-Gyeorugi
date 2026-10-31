#include "Combat/OpenStanceSkillStick.h"
#include "Misc/AutomationTest.h"

#if WITH_DEV_AUTOMATION_TESTS

namespace
{
	/** Feeds the recognizer scripted frames at 60 Hz and keeps every event it reports. */
	struct FSkillStickRig
	{
		FOpenStanceSkillStickRecognizer Recognizer;
		FOpenStanceFighterState State;
		TArray<FOpenStanceInputEvent> Events;
		FOpenStanceInputFrame Frame;

		static constexpr float Tick = 1.0f / 60.0f;

		FVector2D Up() const { return FVector2D(0.0, 1.0); }
		FVector2D Down() const { return FVector2D(0.0, -1.0); }
		FVector2D Left() const { return FVector2D(-1.0, 0.0); }
		FVector2D Right() const { return FVector2D(1.0, 0.0); }

		void Hold(float Seconds, FVector2D Stick)
		{
			Frame.RightStick = Stick;
			const int32 Count = FMath::Max(1, FMath::RoundToInt(Seconds / Tick));
			for (int32 Index = 0; Index < Count; ++Index)
			{
				Recognizer.Update(Tick, Frame, State, Events);
			}
		}

		void Neutral(float Seconds = 0.1f) { Hold(Seconds, FVector2D::ZeroVector); }

		/** A flick: the stick pushed one way for a few frames, then back to centre. */
		void Flick(FVector2D Stick, float HoldSeconds = 0.05f)
		{
			Hold(HoldSeconds, Stick);
			Neutral();
		}

		TArray<FOpenStanceInputEvent> Of(EOpenStanceInputEventType Type) const
		{
			return Events.FilterByPredicate([Type](const FOpenStanceInputEvent& Event) { return Event.Type == Type; });
		}

		int32 CountOf(EOpenStanceInputEventType Type) const { return Of(Type).Num(); }
		int32 Attacks() const { return CountOf(EOpenStanceInputEventType::Attack); }
		FOpenStanceInputEvent LastAttack() const { return Of(EOpenStanceInputEventType::Attack).Last(); }
		void Clear() { Events.Reset(); }
	};
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FOpenStanceSkillStickBasicTest, "OpenStance.SkillStick.Basic", EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FOpenStanceSkillStickBasicTest::RunTest(const FString& Parameters)
{
	FSkillStickRig Rig;
	Rig.Flick(Rig.Up());
	if (TestEqual(TEXT("RS Up throws one attack"), Rig.Attacks(), 1))
	{
		TestEqual(TEXT("it is the side kick"), Rig.LastAttack().Technique, EOpenStanceTechnique::SideKick);
		TestEqual(TEXT("to the trunk"), Rig.LastAttack().Target, EOpenStanceTarget::Trunk);
		TestEqual(TEXT("with the lead leg"), Rig.LastAttack().LegRole, EOpenStanceLegRole::Lead);
		TestFalse(TEXT("not a fake"), Rig.LastAttack().bFake);
		TestFalse(TEXT("not airborne"), Rig.LastAttack().bJump);
	}

	// Spin side is Down then Up and must not also throw a side kick on its final Up.
	Rig.Clear();
	Rig.Hold(0.05f, Rig.Down());
	Rig.Hold(0.05f, Rig.Up());
	Rig.Neutral();
	TestEqual(TEXT("Down, Up is a single attack"), Rig.Attacks(), 1);
	if (Rig.Attacks() == 1)
	{
		TestEqual(TEXT("the spin side kick"), Rig.LastAttack().Technique, EOpenStanceTechnique::SpinSide);
	}

	// A held stick repeats nothing.
	Rig.Clear();
	Rig.Hold(1.0f, Rig.Up());
	TestEqual(TEXT("a stick held up for a second throws one kick"), Rig.Attacks(), 1);
	Rig.Neutral();
	Rig.Flick(Rig.Up());
	TestEqual(TEXT("and the next flick throws another"), Rig.Attacks(), 2);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FOpenStanceSkillStickMirrorTest, "OpenStance.SkillStick.Mirror", EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FOpenStanceSkillStickMirrorTest::RunTest(const FString& Parameters)
{
	struct FCase
	{
		EOpenStanceStance Stance;
		bool bBackLeg;
		bool bStickRight;
		EOpenStanceTechnique Expected;
		EOpenStanceLegSide Leg;
		const TCHAR* Name;
	};
	const FCase Cases[] = {
		{ EOpenStanceStance::RightLead, false, true, EOpenStanceTechnique::Roundhouse, EOpenStanceLegSide::Right, TEXT("Right Lead, RS Right: lead-leg roundhouse") },
		{ EOpenStanceStance::RightLead, false, false, EOpenStanceTechnique::Hook, EOpenStanceLegSide::Right, TEXT("Right Lead, RS Left: lead-leg hook") },
		{ EOpenStanceStance::LeftLead, false, false, EOpenStanceTechnique::Roundhouse, EOpenStanceLegSide::Left, TEXT("Left Lead, RS Left: lead-leg roundhouse") },
		{ EOpenStanceStance::LeftLead, false, true, EOpenStanceTechnique::Hook, EOpenStanceLegSide::Left, TEXT("Left Lead, RS Right: lead-leg hook") },
		{ EOpenStanceStance::RightLead, true, false, EOpenStanceTechnique::Roundhouse, EOpenStanceLegSide::Left, TEXT("Right Lead + RT, RS Left: back-leg roundhouse") },
		{ EOpenStanceStance::RightLead, true, true, EOpenStanceTechnique::Hook, EOpenStanceLegSide::Left, TEXT("Right Lead + RT, RS Right: back-leg hook") },
		{ EOpenStanceStance::LeftLead, true, true, EOpenStanceTechnique::Roundhouse, EOpenStanceLegSide::Right, TEXT("Left Lead + RT, RS Right: back-leg roundhouse") },
		{ EOpenStanceStance::LeftLead, true, false, EOpenStanceTechnique::Hook, EOpenStanceLegSide::Right, TEXT("Left Lead + RT, RS Left: back-leg hook") },
	};

	for (const FCase& Case : Cases)
	{
		FSkillStickRig Rig;
		Rig.State.Stance = Case.Stance;
		Rig.Frame.bRT = Case.bBackLeg;
		Rig.Flick(Case.bStickRight ? Rig.Right() : Rig.Left());
		if (TestEqual(*FString::Printf(TEXT("%s: one attack"), Case.Name), Rig.Attacks(), 1))
		{
			TestEqual(*FString::Printf(TEXT("%s: technique"), Case.Name), Rig.LastAttack().Technique, Case.Expected);
			TestEqual(*FString::Printf(TEXT("%s: physical leg"), Case.Name), Rig.LastAttack().Leg, Case.Leg);
			TestEqual(*FString::Printf(TEXT("%s: leg role"), Case.Name), Rig.LastAttack().LegRole, Case.bBackLeg ? EOpenStanceLegRole::Back : EOpenStanceLegRole::Lead);
		}
	}

	// RS Up needs no mirroring: it is the same kick on either stance.
	FSkillStickRig Rig;
	Rig.State.Stance = EOpenStanceStance::LeftLead;
	Rig.Flick(Rig.Up());
	TestEqual(TEXT("Left Lead RS Up is the side kick"), Rig.LastAttack().Technique, EOpenStanceTechnique::SideKick);
	TestEqual(TEXT("with the left leg"), Rig.LastAttack().Leg, EOpenStanceLegSide::Left);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FOpenStanceSkillStickModifierTest, "OpenStance.SkillStick.Modifiers", EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FOpenStanceSkillStickModifierTest::RunTest(const FString& Parameters)
{
	// RB aims at the head and combines with RT.
	{
		FSkillStickRig Rig;
		Rig.Frame.bRB = true;
		Rig.Flick(Rig.Up());
		TestEqual(TEXT("RB sends the kick to the head"), Rig.LastAttack().Target, EOpenStanceTarget::Head);
		TestTrue(TEXT("the fighter state shows the head modifier"), Rig.State.bHeadHeld);
	}
	{
		FSkillStickRig Rig;
		Rig.Frame.bRB = true;
		Rig.Frame.bRT = true;
		Rig.Flick(Rig.Left());
		TestEqual(TEXT("RT + RB: head"), Rig.LastAttack().Target, EOpenStanceTarget::Head);
		TestEqual(TEXT("RT + RB: back leg"), Rig.LastAttack().LegRole, EOpenStanceLegRole::Back);
		TestEqual(TEXT("RT + RB: Right Lead back-leg roundhouse is RS Left"), Rig.LastAttack().Technique, EOpenStanceTechnique::Roundhouse);
	}

	// LB through a gesture fakes that technique.
	{
		FSkillStickRig Rig;
		Rig.Frame.bLB = true;
		Rig.Flick(Rig.Up());
		TestEqual(TEXT("one attack"), Rig.Attacks(), 1);
		TestTrue(TEXT("LB makes it a fake"), Rig.LastAttack().bFake);
		TestEqual(TEXT("of the side kick"), Rig.LastAttack().Technique, EOpenStanceTechnique::SideKick);
		TestEqual(TEXT("and no separate generic fake"), Rig.CountOf(EOpenStanceInputEventType::GenericFake), 0);
	}

	// LB alone: a generic fake, on release.
	{
		FSkillStickRig Rig;
		Rig.Frame.bLB = true;
		Rig.Neutral(0.1f);
		Rig.Frame.bLB = false;
		Rig.Neutral(0.1f);
		TestEqual(TEXT("tapping LB is a generic fake"), Rig.CountOf(EOpenStanceInputEventType::GenericFake), 1);
		TestEqual(TEXT("with no attack"), Rig.Attacks(), 0);
	}

	// LB held alone past the window: one generic fake, not one per frame.
	{
		FSkillStickRig Rig;
		Rig.Frame.bLB = true;
		Rig.Neutral(1.0f);
		TestEqual(TEXT("holding LB is one generic fake"), Rig.CountOf(EOpenStanceInputEventType::GenericFake), 1);
	}

	// A modifier pressed after the flick but before the gesture commits still counts: with a longer gesture
	// registered the roundhouse waits for the stick to settle, and RT turns it into the back-leg hook.
	{
		FSkillStickRig Rig;
		FOpenStanceGestureDef Axe;
		Axe.Technique = EOpenStanceTechnique::Axe;
		Axe.Steps = { EOpenStanceGestureStep::Toward, EOpenStanceGestureStep::Down };
		Rig.Recognizer.AddGesture(Axe);

		Rig.Hold(0.04f, Rig.Right());
		Rig.Frame.bRT = true;
		Rig.Hold(0.04f, Rig.Right());
		Rig.Neutral();
		if (TestEqual(TEXT("one attack"), Rig.Attacks(), 1))
		{
			TestEqual(TEXT("RT latched during the gesture sets the back leg"), Rig.LastAttack().LegRole, EOpenStanceLegRole::Back);
			TestEqual(TEXT("and mirrors RS Right into the back-leg hook"), Rig.LastAttack().Technique, EOpenStanceTechnique::Hook);
		}
	}
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FOpenStanceSkillStickWindowTest, "OpenStance.SkillStick.Window", EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FOpenStanceSkillStickWindowTest::RunTest(const FString& Parameters)
{
	TestEqual(TEXT("window above the range clamps to 0.40"), FOpenStanceSkillStickConfig::FromSettings(15.0f, 0.9f).WindowSeconds, 0.40f);
	TestEqual(TEXT("window below the range clamps to 0.20"), FOpenStanceSkillStickConfig::FromSettings(15.0f, 0.05f).WindowSeconds, 0.20f);
	TestEqual(TEXT("default window"), FOpenStanceSkillStickConfig().WindowSeconds, 0.25f);
	TestEqual(TEXT("dead zone percent becomes a fraction"), FOpenStanceSkillStickConfig::FromSettings(15.0f, 0.25f).DeadZone, 0.15f);

	// Down, Up inside the window is a spin side kick; Up after the window is not.
	{
		FSkillStickRig Rig;
		Rig.Hold(0.10f, Rig.Down());
		Rig.Hold(0.10f, Rig.Up());
		Rig.Neutral();
		TestEqual(TEXT("0.10 s between steps is inside the default window"), Rig.CountOf(EOpenStanceInputEventType::Attack), 1);
	}
	{
		FSkillStickRig Rig;
		Rig.Hold(0.40f, Rig.Down());
		TestEqual(TEXT("the partial gesture expired"), Rig.CountOf(EOpenStanceInputEventType::GestureExpired), 1);
		Rig.Neutral();
		Rig.Flick(Rig.Up());
		TestEqual(TEXT("an Up after the expiry is a plain side kick"), Rig.Attacks(), 1);
		if (Rig.Attacks() == 1)
		{
			TestEqual(TEXT("not a spin side kick"), Rig.LastAttack().Technique, EOpenStanceTechnique::SideKick);
		}
	}
	{
		// A wider window lets a slower Down, Up through.
		FSkillStickRig Rig;
		Rig.Recognizer.Config = FOpenStanceSkillStickConfig::FromSettings(15.0f, 0.40f);
		Rig.Hold(0.15f, Rig.Down());
		Rig.Hold(0.15f, Rig.Up());
		Rig.Neutral();
		TestEqual(TEXT("0.30 s total works with a 0.40 s window"), Rig.Attacks(), 1);
		if (Rig.Attacks() == 1)
		{
			TestEqual(TEXT("as a spin side kick"), Rig.LastAttack().Technique, EOpenStanceTechnique::SpinSide);
		}
	}
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FOpenStanceSkillStickDeadZoneTest, "OpenStance.SkillStick.DeadZone", EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FOpenStanceSkillStickDeadZoneTest::RunTest(const FString& Parameters)
{
	FSkillStickRig Rig;
	Rig.Hold(0.3f, FVector2D(0.0, 0.10));
	Rig.Hold(0.3f, FVector2D(0.0, 0.50));
	TestEqual(TEXT("a nudge inside the dead zone and a half push do nothing"), Rig.Events.Num(), 0);
	Rig.Hold(0.05f, FVector2D(0.0, 0.8));
	TestEqual(TEXT("a full push throws"), Rig.Attacks(), 1);

	// A raised dead zone moves the engage threshold with it.
	FSkillStickRig Wide;
	Wide.Recognizer.Config.DeadZone = 0.75f;
	Wide.Hold(0.1f, FVector2D(0.0, 0.7));
	TestEqual(TEXT("0.7 travel is inside a 0.75 dead zone"), Wide.Events.Num(), 0);
	Wide.Hold(0.1f, FVector2D(0.0, 0.9));
	TestEqual(TEXT("0.9 gets out of it"), Wide.Attacks(), 1);

	// A direction change that stays beyond the dead zone counts as a step.
	TestEqual(TEXT("dominant axis picks the direction"), FOpenStanceSkillStickRecognizer::ToDirection(FVector2D(0.9, 0.5), 0.6f), EOpenStanceStickDir::Right);
	TestEqual(TEXT("vertical when Y dominates"), FOpenStanceSkillStickRecognizer::ToDirection(FVector2D(-0.5, -0.9), 0.6f), EOpenStanceStickDir::Down);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FOpenStanceSkillStickAmbiguityTest, "OpenStance.SkillStick.Ambiguity", EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FOpenStanceSkillStickAmbiguityTest::RunTest(const FString& Parameters)
{
	FOpenStanceGestureDef Axe;
	Axe.Technique = EOpenStanceTechnique::Axe;
	Axe.Steps = { EOpenStanceGestureStep::Toward, EOpenStanceGestureStep::Down };

	// Toward is a roundhouse, but with a longer gesture that starts the same way it waits to see what follows.
	{
		FSkillStickRig Rig;
		Rig.Recognizer.AddGesture(Axe);
		Rig.Hold(0.05f, Rig.Right());
		TestEqual(TEXT("the roundhouse does not fire at once"), Rig.Attacks(), 0);
		Rig.Neutral();
		TestEqual(TEXT("it fires when the stick returns to neutral"), Rig.Attacks(), 1);
		TestEqual(TEXT("as a roundhouse"), Rig.LastAttack().Technique, EOpenStanceTechnique::Roundhouse);
	}
	{
		FSkillStickRig Rig;
		Rig.Recognizer.AddGesture(Axe);
		Rig.Hold(0.05f, Rig.Right());
		Rig.Hold(0.05f, Rig.Down());
		Rig.Neutral();
		TestEqual(TEXT("Toward then Down is the axe kick only"), Rig.Attacks(), 1);
		TestEqual(TEXT("the axe"), Rig.LastAttack().Technique, EOpenStanceTechnique::Axe);
	}
	{
		FSkillStickRig Rig;
		Rig.Recognizer.AddGesture(Axe);
		Rig.Hold(0.5f, Rig.Right());
		TestEqual(TEXT("holding the stick past the window fires the roundhouse once"), Rig.Attacks(), 1);
		TestEqual(TEXT("as a roundhouse"), Rig.LastAttack().Technique, EOpenStanceTechnique::Roundhouse);
	}

	// A path no gesture starts with is rejected at once.
	{
		FSkillStickRig Rig;
		Rig.Hold(0.05f, Rig.Down());
		Rig.Hold(0.05f, Rig.Left());
		Rig.Neutral();
		TestEqual(TEXT("Down, Left matches nothing"), Rig.CountOf(EOpenStanceInputEventType::GestureRejected), 1);
		TestEqual(TEXT("and throws nothing"), Rig.Attacks(), 0);
	}

	// Down alone is only the start of the spin side kick.
	{
		FSkillStickRig Rig;
		Rig.Flick(Rig.Down());
		TestEqual(TEXT("Down alone is a partial gesture"), Rig.CountOf(EOpenStanceInputEventType::GestureExpired), 1);
		TestEqual(TEXT("and throws nothing"), Rig.Attacks(), 0);
	}

	// After a kick fires, the rest of the stick's travel is ignored until neutral.
	{
		FSkillStickRig Rig;
		Rig.Hold(0.05f, Rig.Up());
		Rig.Hold(0.05f, Rig.Right());
		Rig.Neutral();
		TestEqual(TEXT("Up then Right throws only the side kick"), Rig.Attacks(), 1);
	}
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FOpenStanceSkillStickJumpTest, "OpenStance.SkillStick.Jump", EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FOpenStanceSkillStickJumpTest::RunTest(const FString& Parameters)
{
	// A released tap of Y primes the next gesture and the flag is kept in the fighter state.
	{
		FSkillStickRig Rig;
		Rig.Frame.bY = true;
		Rig.Neutral(0.05f);
		Rig.Frame.bY = false;
		Rig.Neutral(0.05f);
		TestTrue(TEXT("the runtime state is jump-primed after the tap"), Rig.State.bJumpPrimed);
		TestEqual(TEXT("a JumpPrimed event was reported"), Rig.CountOf(EOpenStanceInputEventType::JumpPrimed), 1);
		Rig.Flick(Rig.Up());
		TestTrue(TEXT("the side kick is airborne"), Rig.LastAttack().bJump);
		TestFalse(TEXT("the prime is spent"), Rig.State.bJumpPrimed);
	}

	// Without a tap the same gesture is grounded.
	{
		FSkillStickRig Rig;
		Rig.Flick(Rig.Up());
		TestFalse(TEXT("no tap, no jump"), Rig.LastAttack().bJump);
	}

	// A tap that nothing follows runs out.
	{
		FSkillStickRig Rig;
		Rig.Frame.bY = true;
		Rig.Neutral(0.05f);
		Rig.Frame.bY = false;
		Rig.Neutral(0.6f);
		TestFalse(TEXT("the prime expired"), Rig.State.bJumpPrimed);
		TestEqual(TEXT("and said so"), Rig.CountOf(EOpenStanceInputEventType::JumpPrimeExpired), 1);
		Rig.Flick(Rig.Up());
		TestFalse(TEXT("a later flick is grounded"), Rig.LastAttack().bJump);
	}

	// Y held while the stick moves cannot prime: the thumb cannot do both.
	{
		FSkillStickRig Rig;
		Rig.Hold(0.05f, Rig.Up());
		Rig.Frame.bY = true;
		Rig.Hold(0.05f, Rig.Up());
		Rig.Frame.bY = false;
		Rig.Neutral();
		TestFalse(TEXT("a Y pressed mid-gesture does not prime"), Rig.State.bJumpPrimed);
	}

	// Spin side has no jump version: the tap is spent, the kick stays grounded.
	{
		FSkillStickRig Rig;
		Rig.Frame.bY = true;
		Rig.Neutral(0.05f);
		Rig.Frame.bY = false;
		Rig.Neutral(0.05f);
		Rig.Hold(0.05f, Rig.Down());
		Rig.Hold(0.05f, Rig.Up());
		Rig.Neutral();
		TestEqual(TEXT("spin side thrown"), Rig.LastAttack().Technique, EOpenStanceTechnique::SpinSide);
		TestFalse(TEXT("not airborne"), Rig.LastAttack().bJump);
		TestFalse(TEXT("prime spent"), Rig.State.bJumpPrimed);
	}

	// A prime survives a gesture that is still waiting past the prime time.
	{
		FSkillStickRig Rig;
		Rig.Frame.bY = true;
		Rig.Neutral(0.05f);
		Rig.Frame.bY = false;
		Rig.Neutral(0.15f);
		Rig.Hold(0.15f, Rig.Down());
		TestTrue(TEXT("the prime holds while a gesture is in progress"), Rig.State.bJumpPrimed);
	}
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FOpenStanceSkillStickDefenseTest, "OpenStance.SkillStick.Defense", EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FOpenStanceSkillStickDefenseTest::RunTest(const FString& Parameters)
{
	{
		FSkillStickRig Rig;
		Rig.Frame.bLT = true;
		Rig.Flick(Rig.Up());
		Rig.Flick(Rig.Down());
		Rig.Flick(Rig.Right());
		Rig.Flick(Rig.Left());
		TestEqual(TEXT("no offensive attack under LT"), Rig.Attacks(), 0);
		const TArray<FOpenStanceInputEvent> Defense = Rig.Of(EOpenStanceInputEventType::Defense);
		if (TestEqual(TEXT("four defensive answers"), Defense.Num(), 4))
		{
			TestEqual(TEXT("RS Up is a high block"), Defense[0].DefenseKind, EOpenStanceDefenseKind::HighBlock);
			TestEqual(TEXT("RS Down is a leg check"), Defense[1].DefenseKind, EOpenStanceDefenseKind::LegCheck);
			TestEqual(TEXT("RS Right is a sway"), Defense[2].DefenseKind, EOpenStanceDefenseKind::Sway);
			TestEqual(TEXT("RS Left is a sway"), Defense[3].DefenseKind, EOpenStanceDefenseKind::Sway);
		}
		TestTrue(TEXT("the fighter state shows defence held"), Rig.State.bDefenseHeld);
	}

	// LT arriving mid-gesture drops it, and a stick still held when LT lets go does not fire.
	{
		FSkillStickRig Rig;
		Rig.Hold(0.05f, Rig.Down());
		Rig.Frame.bLT = true;
		Rig.Hold(0.05f, Rig.Down());
		TestEqual(TEXT("the gesture in progress was cancelled"), Rig.CountOf(EOpenStanceInputEventType::GestureCancelled), 1);
		Rig.Frame.bLT = false;
		Rig.Hold(0.1f, Rig.Up());
		TestEqual(TEXT("releasing LT with the stick off-centre throws nothing"), Rig.Attacks(), 0);
		Rig.Neutral();
		Rig.Flick(Rig.Up());
		TestEqual(TEXT("after a return to neutral offence works again"), Rig.Attacks(), 1);
	}

	// A generic fake cannot start under LT.
	{
		FSkillStickRig Rig;
		Rig.Frame.bLT = true;
		Rig.Frame.bLB = true;
		Rig.Neutral(0.5f);
		TestEqual(TEXT("no fake under LT"), Rig.CountOf(EOpenStanceInputEventType::GenericFake), 0);
	}
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FOpenStanceSkillStickResetTest, "OpenStance.SkillStick.Reset", EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FOpenStanceSkillStickResetTest::RunTest(const FString& Parameters)
{
	FSkillStickRig Rig;
	Rig.Frame.bY = true;
	Rig.Neutral(0.05f);
	Rig.Frame.bY = false;
	Rig.Neutral(0.05f);
	Rig.Hold(0.05f, Rig.Down());
	TestTrue(TEXT("a gesture is in progress"), Rig.Recognizer.IsGestureInProgress());
	Rig.Recognizer.Reset(Rig.State);
	TestFalse(TEXT("reset drops it"), Rig.Recognizer.IsGestureInProgress());
	TestFalse(TEXT("and the jump prime"), Rig.State.bJumpPrimed);
	Rig.Clear();
	Rig.Hold(0.1f, Rig.Up());
	TestEqual(TEXT("a stick held through the reset does not fire until it is released"), Rig.Attacks(), 0);
	return true;
}

#endif
