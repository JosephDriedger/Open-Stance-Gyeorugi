#include "Combat/OpenStanceFootwork.h"
#include "Combat/OpenStanceSkillStick.h"
#include "Misc/AutomationTest.h"

#if WITH_DEV_AUTOMATION_TESTS

namespace
{
	/** One fighter 200 cm from a stationary opponent, facing it along +X (the opponent is on the fighter's left). */
	struct FFootworkRig
	{
		FOpenStanceMovementTuning Tuning;
		FOpenStanceFighterState State;
		FOpenStanceMotionState Motion;
		FOpenStanceMotionInput Input;
		FVector2D Opponent = FVector2D(200.0, 0.0);

		static constexpr float Tick = 1.0f / 60.0f;

		FFootworkRig() { Motion.Position = FVector2D::ZeroVector; }

		void Run(float Seconds)
		{
			const int32 Count = FMath::Max(1, FMath::RoundToInt(Seconds / Tick));
			for (int32 Index = 0; Index < Count; ++Index)
			{
				FOpenStanceFootwork::Tick(Tick, Input, Opponent, State, Motion, Tuning);
			}
		}

		float DistanceToOpponent() const { return static_cast<float>(FVector2D::Distance(Motion.Position, Opponent)); }
	};
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FOpenStanceFootworkMovementTest, "OpenStance.Footwork.Movement", EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FOpenStanceFootworkMovementTest::RunTest(const FString& Parameters)
{
	// A tap is a 40 cm step forward, whatever the length of the press.
	{
		FFootworkRig Rig;
		Rig.Input.Move = FVector2D(0.0, 1.0);
		Rig.Run(0.05f);
		Rig.Input.Move = FVector2D::ZeroVector;
		Rig.Run(1.0f);
		TestEqual(TEXT("a tap forward closes 40 cm"), 200.0f - Rig.DistanceToOpponent(), 40.0f, 0.5f);
	}
	{
		FFootworkRig Rig;
		Rig.Input.Move = FVector2D(0.0, -1.0);
		Rig.Run(0.05f);
		Rig.Input.Move = FVector2D::ZeroVector;
		Rig.Run(1.0f);
		TestEqual(TEXT("a tap back opens 40 cm"), Rig.DistanceToOpponent() - 200.0f, 40.0f, 0.5f);
	}
	// A hold is 1.2 m/s.
	{
		FFootworkRig Rig;
		Rig.Input.Move = FVector2D(0.0, 1.0);
		Rig.Run(0.5f);
		TestEqual(TEXT("held for half a second: 60 cm"), 200.0f - Rig.DistanceToOpponent(), 60.0f, 1.0f);
		TestEqual(TEXT("velocity is the hold speed"), static_cast<float>(Rig.Motion.Velocity.Size()), 120.0f, 0.5f);
	}
	// Sideways circles at the same distance, 35 cm per tapped step.
	{
		FFootworkRig Rig;
		Rig.Input.Move = FVector2D(1.0, 0.0);
		Rig.Run(0.05f);
		Rig.Input.Move = FVector2D::ZeroVector;
		Rig.Run(1.0f);
		TestEqual(TEXT("circling keeps the distance"), Rig.DistanceToOpponent(), 200.0f, 0.5f);
		const FVector2D FromOpponent = Rig.Motion.Position - Rig.Opponent;
		const float Swung = static_cast<float>(FMath::Atan2(FMath::Abs(FromOpponent.Y), -FromOpponent.X)) * 200.0f;
		TestEqual(TEXT("the arc covers a 35 cm step"), Swung, 35.0f, 1.5f);
		TestTrue(TEXT("a right step goes toward the fighter's right (negative Y here)"), Rig.Motion.Position.Y < 0.0);
	}
	{
		FFootworkRig Rig;
		Rig.Input.Move = FVector2D(-1.0, 0.0);
		Rig.Run(2.0f);
		TestEqual(TEXT("holding sideways keeps circling at the same distance"), Rig.DistanceToOpponent(), 200.0f, 0.5f);
		TestTrue(TEXT("a left step goes the other way"), Rig.Motion.Position.Y > 0.0);
	}
	// A stick inside the dead zone does nothing.
	{
		FFootworkRig Rig;
		Rig.Input.Move = FVector2D(0.0, 0.1);
		Rig.Run(1.0f);
		TestEqual(TEXT("dead zone"), Rig.Motion.Position.Size(), 0.0, 0.001);
	}
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FOpenStanceFootworkDashTest, "OpenStance.Footwork.Dash", EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FOpenStanceFootworkDashTest::RunTest(const FString& Parameters)
{
	FFootworkRig Rig;
	Rig.Opponent = FVector2D(400.0, 0.0);
	Rig.Input.bDash = true;
	Rig.Run(0.05f);
	Rig.Input.bDash = false;
	Rig.Run(0.5f);
	TestEqual(TEXT("a dash covers 1.0 m"), static_cast<float>(Rig.Motion.Position.X), 100.0f, 0.5f);
	TestEqual(TEXT("and costs 12 stamina"), Rig.State.Stamina, FOpenStanceFighterState::FullStamina - 12.0f, 0.01f);

	// It takes 0.3 s: after a tenth of a second only a third of it is done.
	FFootworkRig Timed;
	Timed.Opponent = FVector2D(400.0, 0.0);
	Timed.Input.bDash = true;
	Timed.Run(0.1f);
	TestEqual(TEXT("a third of the dash after 0.1 s"), static_cast<float>(Timed.Motion.Position.X), 33.3f, 1.0f);

	// Held B does not chain dashes.
	FFootworkRig Held;
	Held.Opponent = FVector2D(600.0, 0.0);
	Held.Input.bDash = true;
	Held.Run(1.0f);
	TestEqual(TEXT("holding B dashes once"), static_cast<float>(Held.Motion.Position.X), 100.0f, 0.5f);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FOpenStanceFootworkAttackTest, "OpenStance.Footwork.Attack", EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FOpenStanceFootworkAttackTest::RunTest(const FString& Parameters)
{
	// A neutral stick roots the technique.
	{
		FFootworkRig Rig;
		Rig.State.CombatState = EOpenStanceCombatState::AttackStartup;
		Rig.Run(0.5f);
		TestEqual(TEXT("no stick: rooted"), Rig.Motion.Position.Size(), 0.0, 0.001);
	}
	// A held stick slides at the step speed and never homes: back goes away, forward goes in, nothing else changes.
	{
		FFootworkRig Rig;
		Rig.State.CombatState = EOpenStanceCombatState::AttackActive;
		Rig.Input.Move = FVector2D(0.0, 1.0);
		Rig.Run(0.5f);
		TestEqual(TEXT("forward slides at 120 cm/s"), static_cast<float>(Rig.Motion.Position.X), 60.0f, 1.0f);
	}
	{
		FFootworkRig Rig;
		Rig.State.CombatState = EOpenStanceCombatState::AttackRecovery;
		Rig.Input.Move = FVector2D(0.0, -1.0);
		Rig.Run(0.5f);
		TestEqual(TEXT("back steps out at the same speed"), static_cast<float>(Rig.Motion.Position.X), -60.0f, 1.0f);
	}
	// Out of range stays out of range: a technique's slide is the stick's, with no pull from the opponent.
	{
		FFootworkRig Rig;
		Rig.Opponent = FVector2D(500.0, 0.0);
		Rig.State.CombatState = EOpenStanceCombatState::AttackStartup;
		Rig.Run(0.4f);
		TestEqual(TEXT("an attack thrown from 5 m with a neutral stick stays at 5 m"), Rig.DistanceToOpponent(), 500.0f, 0.01f);
	}
	// An attack cancels a pending dash or tapped step.
	{
		FFootworkRig Rig;
		Rig.Input.Move = FVector2D(0.0, 1.0);
		Rig.Run(0.02f);
		Rig.Input.Move = FVector2D::ZeroVector;
		Rig.State.CombatState = EOpenStanceCombatState::AttackStartup;
		const FVector2D Before = Rig.Motion.Position;
		Rig.Run(0.5f);
		TestEqual(TEXT("a technique stops the rest of a tapped step"), static_cast<float>(FVector2D::Distance(Before, Rig.Motion.Position)), 0.0f, 0.5f);
	}
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FOpenStanceFootworkStanceTest, "OpenStance.Footwork.Stance", EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FOpenStanceFootworkStanceTest::RunTest(const FString& Parameters)
{
	FFootworkRig Rig;
	Rig.State.Stance = EOpenStanceStance::RightLead;
	Rig.Input.bSwitch = true;
	Rig.Run(0.05f);
	Rig.Input.bSwitch = false;
	TestTrue(TEXT("a switch is under way"), Rig.Motion.bSwitching);
	TestEqual(TEXT("the legs have not swapped yet"), Rig.State.Stance, EOpenStanceStance::RightLead);
	TestFalse(TEXT("no technique can start mid-switch"), FOpenStanceFootwork::CanStartAttack(Rig.Motion));
	TestTrue(TEXT("the pose is partway, not mirrored in one frame"), Rig.Motion.SwitchBlend > 0.0f && Rig.Motion.SwitchBlend < 1.0f);

	float Last = Rig.Motion.SwitchBlend;
	bool bMonotonic = true;
	for (int32 Index = 0; Index < 10; ++Index)
	{
		Rig.Run(0.02f);
		bMonotonic &= Rig.Motion.SwitchBlend >= Last;
		Last = Rig.Motion.SwitchBlend;
	}
	TestTrue(TEXT("the blend only rises"), bMonotonic);
	Rig.Run(0.3f);
	TestFalse(TEXT("the switch finished"), Rig.Motion.bSwitching);
	TestEqual(TEXT("lead and back swapped"), Rig.State.Stance, EOpenStanceStance::LeftLead);
	TestEqual(TEXT("blend completes"), Rig.Motion.SwitchBlend, 1.0f);
	TestTrue(TEXT("a technique can start again"), FOpenStanceFootwork::CanStartAttack(Rig.Motion));

	// Held A switches once, and a switch cannot start in the middle of a technique.
	FFootworkRig Held;
	Held.Input.bSwitch = true;
	Held.Run(2.0f);
	TestEqual(TEXT("holding A switches once"), Held.State.Stance, EOpenStanceStance::LeftLead);
	FFootworkRig Busy;
	Busy.State.CombatState = EOpenStanceCombatState::AttackRecovery;
	Busy.Input.bSwitch = true;
	Busy.Run(1.0f);
	TestEqual(TEXT("no switch during a technique"), Busy.State.Stance, EOpenStanceStance::RightLead);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FOpenStanceFootworkSideSwitchKickTest, "OpenStance.Footwork.SameKickAfterSwitch", EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FOpenStanceFootworkSideSwitchKickTest::RunTest(const FString& Parameters)
{
	// The same RT roundhouse in both stances: the physical leg changes with the stance and the stick side mirrors.
	FFootworkRig Rig;
	FOpenStanceSkillStickRecognizer Recognizer;
	TArray<FOpenStanceInputEvent> Events;
	FOpenStanceInputFrame Frame;
	Frame.bRT = true;

	auto Flick = [&](const FVector2D& Stick)
	{
		Events.Reset();
		Frame.RightStick = Stick;
		for (int32 Index = 0; Index < 3; ++Index)
		{
			Recognizer.Update(FFootworkRig::Tick, Frame, Rig.State, Events);
		}
		Frame.RightStick = FVector2D::ZeroVector;
		for (int32 Index = 0; Index < 6; ++Index)
		{
			Recognizer.Update(FFootworkRig::Tick, Frame, Rig.State, Events);
		}
		return Events.FilterByPredicate([](const FOpenStanceInputEvent& E) { return E.Type == EOpenStanceInputEventType::Attack; });
	};

	Rig.State.Stance = EOpenStanceStance::RightLead;
	TArray<FOpenStanceInputEvent> Before = Flick(FVector2D(-1.0, 0.0));
	if (TestEqual(TEXT("Right Lead RT roundhouse is RS Left"), Before.Num(), 1))
	{
		TestEqual(TEXT("roundhouse"), Before[0].Technique, EOpenStanceTechnique::Roundhouse);
		TestEqual(TEXT("thrown with the left leg"), Before[0].Leg, EOpenStanceLegSide::Left);
	}

	Rig.Input.bSwitch = true;
	Rig.Run(0.6f);
	Rig.Input.bSwitch = false;
	TestEqual(TEXT("now Left Lead"), Rig.State.Stance, EOpenStanceStance::LeftLead);

	TArray<FOpenStanceInputEvent> After = Flick(FVector2D(1.0, 0.0));
	if (TestEqual(TEXT("Left Lead RT roundhouse is RS Right"), After.Num(), 1))
	{
		TestEqual(TEXT("still a roundhouse"), After[0].Technique, EOpenStanceTechnique::Roundhouse);
		TestEqual(TEXT("still the back leg"), After[0].LegRole, EOpenStanceLegRole::Back);
		TestEqual(TEXT("thrown with the right leg"), After[0].Leg, EOpenStanceLegSide::Right);
	}
	After = Flick(FVector2D(-1.0, 0.0));
	if (TestEqual(TEXT("the old stick side is now the hook"), After.Num(), 1))
	{
		TestEqual(TEXT("hook"), After[0].Technique, EOpenStanceTechnique::Hook);
	}
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FOpenStanceFootworkCollisionTest, "OpenStance.Footwork.Collision", EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FOpenStanceFootworkCollisionTest::RunTest(const FString& Parameters)
{
	FVector2D A(0.0, 0.0);
	FVector2D B(40.0, 0.0);
	FOpenStanceFootwork::SeparateFighters(A, B, 35.0f);
	TestEqual(TEXT("overlapping fighters end up two radii apart"), static_cast<float>(FVector2D::Distance(A, B)), 70.0f, 0.01f);
	TestEqual(TEXT("pushed apart evenly"), static_cast<float>((A + B).X), 40.0f, 0.01f);

	FVector2D C(0.0, 0.0);
	FVector2D D(0.0, 0.0);
	FOpenStanceFootwork::SeparateFighters(C, D, 35.0f);
	TestEqual(TEXT("fighters exactly on top of each other still separate"), static_cast<float>(FVector2D::Distance(C, D)), 70.0f, 0.01f);

	FVector2D E(0.0, 0.0);
	FVector2D F(100.0, 0.0);
	FOpenStanceFootwork::SeparateFighters(E, F, 35.0f);
	TestEqual(TEXT("fighters far enough apart are left alone"), static_cast<float>(F.X), 100.0f, 0.001f);

	const FOpenStanceMovementTuning Tuning;
	TestEqual(TEXT("reach for the reference fighter is unchanged"), FOpenStanceFootwork::ScaleReachCm(110.0f, 175.0f, Tuning), 110.0f, 0.001f);
	TestTrue(TEXT("a taller fighter reaches further"), FOpenStanceFootwork::ScaleReachCm(110.0f, 192.0f, Tuning) > 110.0f);
	TestTrue(TEXT("a shorter fighter reaches less"), FOpenStanceFootwork::ScaleReachCm(110.0f, 165.0f, Tuning) < 110.0f);
	TestEqual(TEXT("reach scales in proportion to height"), FOpenStanceFootwork::ScaleReachCm(110.0f, 192.0f, Tuning), 110.0f * 192.0f / 175.0f, 0.01f);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FOpenStanceFootworkGuardTest, "OpenStance.Footwork.Guard", EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FOpenStanceFootworkGuardTest::RunTest(const FString& Parameters)
{
	EOpenStanceGuard Guard = EOpenStanceGuard::High;
	TestTrue(TEXT("Up"), FOpenStanceFootwork::GuardForDPad(EOpenStanceDPad::Up, Guard) && Guard == EOpenStanceGuard::High);
	TestTrue(TEXT("Left"), FOpenStanceFootwork::GuardForDPad(EOpenStanceDPad::Left, Guard) && Guard == EOpenStanceGuard::Cross);
	TestTrue(TEXT("Right"), FOpenStanceFootwork::GuardForDPad(EOpenStanceDPad::Right, Guard) && Guard == EOpenStanceGuard::Mixed);
	TestTrue(TEXT("Down"), FOpenStanceFootwork::GuardForDPad(EOpenStanceDPad::Down, Guard) && Guard == EOpenStanceGuard::Low);
	TestFalse(TEXT("no press selects nothing"), FOpenStanceFootwork::GuardForDPad(EOpenStanceDPad::None, Guard));

	FFootworkRig Rig;
	Rig.Input.DPad = EOpenStanceDPad::Left;
	Rig.Run(0.05f);
	TestEqual(TEXT("the runtime state holds the guard"), Rig.State.Guard, EOpenStanceGuard::Cross);
	TestEqual(TEXT("the previous guard is kept for the transition"), Rig.Motion.PreviousGuard, EOpenStanceGuard::High);
	TestTrue(TEXT("a transition is running"), Rig.Motion.GuardTransitionLeft > 0.0f);
	Rig.Input.DPad = EOpenStanceDPad::None;
	Rig.Run(0.5f);
	TestEqual(TEXT("the transition ends"), Rig.Motion.GuardTransitionLeft, 0.0f);
	TestEqual(TEXT("and the guard stays"), Rig.State.Guard, EOpenStanceGuard::Cross);
	return true;
}

#endif
