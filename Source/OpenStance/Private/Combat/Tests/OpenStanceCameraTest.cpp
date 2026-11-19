#include "Combat/OpenStanceCameraDirector.h"
#include "Combat/OpenStanceMatchSim.h"
#include "Combat/OpenStanceMoveData.h"
#include "Misc/AutomationTest.h"

#if WITH_DEV_AUTOMATION_TESTS

namespace
{
	/** True if a point is on screen for a 16:9 frame, with a margin as a share of the half-width/height. */
	bool OnScreen(const FOpenStanceCameraFrame& Frame, const FVector& Point, float Margin = 0.92f)
	{
		const FRotationMatrix Axes(Frame.Rotation);
		const FVector D = Point - Frame.Position;
		const double Forward = FVector::DotProduct(D, Axes.GetScaledAxis(EAxis::X));
		if (Forward <= 1.0)
		{
			return false;
		}
		const double Right = FVector::DotProduct(D, Axes.GetScaledAxis(EAxis::Y));
		const double Up = FVector::DotProduct(D, Axes.GetScaledAxis(EAxis::Z));
		const double TanH = FMath::Tan(FMath::DegreesToRadians(Frame.FieldOfViewDeg * 0.5));
		const double TanV = TanH * 9.0 / 16.0;
		return FMath::Abs(Right / Forward) <= TanH * Margin && FMath::Abs(Up / Forward) <= TanV * Margin;
	}

	struct FCameraRig
	{
		FOpenStanceMatchSim Sim;
		FOpenStanceCameraDirector Director;

		FCameraRig()
		{
			Sim.SetMoveTable(FOpenStanceMoveData::CreateSeedTable(GetTransientPackage()));
			Sim.RoundRules.CeremonySeconds = 0.0f;
			Sim.PenaltyRules.PassivitySeconds = 0.0f;
			Sim.StartMatch(200.0f);
			Director.Reset(Sim);
		}

		void Place(const FVector2D& Player, const FVector2D& Opponent)
		{
			Sim.Fighters[0].Motion.Position = Player;
			Sim.Fighters[1].Motion.Position = Opponent;
		}

		/** Both fighters' feet and heads on screen. */
		bool BothInFrame(const FOpenStanceCameraFrame& Frame, FString& Why) const
		{
			for (int32 Index = 0; Index < 2; ++Index)
			{
				const FOpenStanceFighterSim& F = Sim.Fighters[Index];
				const FVector Feet(F.Motion.Position.X, F.Motion.Position.Y, 0.0);
				const bool bDown = F.State.CombatState == EOpenStanceCombatState::KnockedDown;
				const FVector Head = Feet + FVector(0.0, 0.0, bDown ? 30.0f : F.Motion.HeightCm);
				if (!OnScreen(Frame, Feet) || !OnScreen(Frame, Head))
				{
					Why = FString::Printf(TEXT("%s out of frame at (%.0f, %.0f)"), Index == 0 ? TEXT("player") : TEXT("opponent"), F.Motion.Position.X, F.Motion.Position.Y);
					return false;
				}
			}
			return true;
		}

		void Spin()
		{
			FOpenStanceContact Contact;
			Contact.Type = EOpenStanceContactType::Score;
			Contact.bSpinning = true;
			Contact.Points = 4;
			Sim.Contacts.Add(Contact);
		}
	};
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FOpenStanceCameraFramingTest, "OpenStance.Camera.Framing", EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FOpenStanceCameraFramingTest::RunTest(const FString& Parameters)
{
	FCameraRig Rig;
	FString Why;

	// Near and far: from a clinch to across the mat, both fighters stay in frame, and the camera backs off with the gap.
	float LastBack = 0.0f;
	for (const float Gap : { 70.0f, 120.0f, 200.0f, 350.0f, 500.0f, 650.0f })
	{
		Rig.Place(FVector2D(-Gap * 0.5, 0.0), FVector2D(Gap * 0.5, 0.0));
		const FOpenStanceCameraFrame Frame = Rig.Director.FrameCombat(Rig.Sim, 0);
		TestTrue(*FString::Printf(TEXT("%.0f cm apart, both in frame (%s)"), Gap, *Why), Rig.BothInFrame(Frame, Why));
		const float Back = static_cast<float>(FVector::Dist2D(Frame.Position, FVector(-Gap * 0.5, 0.0, 0.0)));
		if (Gap <= 350.0f) // past that the arena wall stops it backing off, and it cranes up instead
		{
			TestTrue(*FString::Printf(TEXT("%.0f cm apart, the camera is no closer than at a smaller gap"), Gap), Back >= LastBack - 1.0f);
		}
		LastBack = Back;
	}

	// Circling: the fighters turn all the way round the centre and the camera follows, inside the arena.
	for (int32 Step = 0; Step < 12; ++Step)
	{
		const FVector2D Dir(FMath::Cos(Step * UE_PI / 6.0), FMath::Sin(Step * UE_PI / 6.0));
		Rig.Place(-Dir * 100.0, Dir * 100.0);
		const FOpenStanceCameraFrame Frame = Rig.Director.FrameCombat(Rig.Sim, 0);
		TestTrue(*FString::Printf(TEXT("circling step %d, both in frame (%s)"), Step, *Why), Rig.BothInFrame(Frame, Why));
	}

	// The mat's edges and corners, the player's back to the edge: the camera stays inside the arena and still frames both.
	for (const FVector2D& Edge : { FVector2D(-370.0, 0.0), FVector2D(370.0, 0.0), FVector2D(0.0, -370.0), FVector2D(260.0, 260.0), FVector2D(-260.0, -260.0) })
	{
		Rig.Place(Edge, Edge * 0.4);
		const FOpenStanceCameraFrame Frame = Rig.Director.FrameCombat(Rig.Sim, 0);
		const float Half = Rig.Director.Tuning.ArenaHalfCm;
		TestTrue(*FString::Printf(TEXT("player at (%.0f, %.0f): camera inside the arena"), Edge.X, Edge.Y),
			FMath::Abs(Frame.Position.X) <= Half + 0.1 && FMath::Abs(Frame.Position.Y) <= Half + 0.1);
		TestTrue(*FString::Printf(TEXT("player at (%.0f, %.0f): both in frame (%s)"), Edge.X, Edge.Y, *Why), Rig.BothInFrame(Frame, Why));
	}

	// Tall and short fighters: the look height follows them.
	Rig.Place(FVector2D(-100.0, 0.0), FVector2D(100.0, 0.0));
	for (const float Height : { 150.0f, 200.0f })
	{
		Rig.Sim.Fighters[0].Motion.HeightCm = Rig.Sim.Fighters[1].Motion.HeightCm = Height;
		TestTrue(*FString::Printf(TEXT("%.0f cm fighters in frame (%s)"), Height, *Why), Rig.BothInFrame(Rig.Director.FrameCombat(Rig.Sim, 0), Why));
	}
	Rig.Sim.Fighters[0].Motion.HeightCm = Rig.Sim.Fighters[1].Motion.HeightCm = 175.0f;

	// A knockdown: the camera looks lower, and the fighter on the floor is in frame.
	const FOpenStanceCameraFrame Standing = Rig.Director.FrameCombat(Rig.Sim, 0);
	Rig.Sim.Fighters[1].State.CombatState = EOpenStanceCombatState::KnockedDown;
	const FOpenStanceCameraFrame Down = Rig.Director.FrameCombat(Rig.Sim, 0);
	TestTrue(TEXT("a knockdown tilts the camera down"), Down.Rotation.Pitch < Standing.Rotation.Pitch);
	TestTrue(*FString::Printf(TEXT("and the fighter on the floor is in frame (%s)"), *Why), Rig.BothInFrame(Down, Why));

	// Playing as Hong works the same from the other side.
	Rig.Sim.Fighters[1].State.CombatState = EOpenStanceCombatState::IdleMovement;
	TestTrue(*FString::Printf(TEXT("as Hong, both in frame (%s)"), *Why), Rig.BothInFrame(Rig.Director.FrameCombat(Rig.Sim, 1), Why));
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FOpenStanceCameraShotsTest, "OpenStance.Camera.Shots", EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FOpenStanceCameraShotsTest::RunTest(const FString& Parameters)
{
	// A spinning-kick score cuts to the side view for 1.5 s, then cuts straight back; the match clock never notices.
	{
		FCameraRig Rig;
		TestEqual(TEXT("play starts on the combat camera"), Rig.Director.Update(0.1f, Rig.Sim, 0, false).Shot, EOpenStanceShot::Combat);
		const float Clock = Rig.Sim.Match.ClockSeconds;
		Rig.Spin();
		const FOpenStanceCameraFrame Cut = Rig.Director.Update(0.1f, Rig.Sim, 0, false);
		TestEqual(TEXT("a spinning score cuts away"), Cut.Shot, EOpenStanceShot::SpinCut);
		TestTrue(TEXT("as a cut"), Cut.bCut);
		for (int32 Step = 0; Step < 12; ++Step)
		{
			Rig.Director.Update(0.1f, Rig.Sim, 0, false);
		}
		TestEqual(TEXT("still on the cut at 1.3 s"), Rig.Director.GetShot(), EOpenStanceShot::SpinCut);
		Rig.Director.Update(0.1f, Rig.Sim, 0, false);
		const FOpenStanceCameraFrame Back = Rig.Director.Update(0.1f, Rig.Sim, 0, false);
		TestEqual(TEXT("back to combat after 1.5 s"), Back.Shot, EOpenStanceShot::Combat);
		TestTrue(TEXT("with a cut"), Back.bCut);
		TestEqual(TEXT("the camera never touched the clock"), Rig.Sim.Match.ClockSeconds, Clock);

		// A score that is not a spinning kick is no cut.
		FOpenStanceContact Plain;
		Plain.Type = EOpenStanceContactType::Score;
		Plain.Points = 2;
		Rig.Sim.Contacts.Add(Plain);
		TestEqual(TEXT("a plain body kick stays on combat"), Rig.Director.Update(0.1f, Rig.Sim, 0, false).Shot, EOpenStanceShot::Combat);
	}

	// A pause holds the shot where it is: the cut's 1.5 s does not run out behind the pause menu.
	{
		FCameraRig Rig;
		Rig.Spin();
		const FOpenStanceCameraFrame Cut = Rig.Director.Update(0.1f, Rig.Sim, 0, false);
		for (int32 Step = 0; Step < 50; ++Step)
		{
			const FOpenStanceCameraFrame Held = Rig.Director.Update(0.1f, Rig.Sim, 0, true);
			if (Step == 0)
			{
				TestTrue(TEXT("paused, the camera holds its pose"), Held.Position.Equals(Cut.Position) && Held.Shot == EOpenStanceShot::SpinCut);
			}
		}
		TestEqual(TEXT("5 s of pause later, still on the cut"), Rig.Director.Update(0.1f, Rig.Sim, 0, false).Shot, EOpenStanceShot::SpinCut);
	}

	// The ceremony, the break and the results each have their view, and play always comes back to combat.
	{
		FCameraRig Rig;
		Rig.Sim.RoundRules = FOpenStanceRoundTuning();
		Rig.Sim.RoundRules.BreakSeconds = 1.0f;
		Rig.Sim.StartMatch(200.0f);
		Rig.Director.Reset(Rig.Sim);
		const FOpenStanceFighterControls Idle;
		const auto Run = [&](float Seconds)
		{
			FOpenStanceCameraFrame Frame;
			for (int32 Step = 0; Step < FMath::RoundToInt(Seconds * 60.0f); ++Step)
			{
				Rig.Sim.Step(1.0f / 60.0f, Idle, Idle);
				Frame = Rig.Director.Update(1.0f / 60.0f, Rig.Sim, 0, false);
			}
			return Frame;
		};
		TestEqual(TEXT("the opening ceremony"), Run(1.0f).Shot, EOpenStanceShot::Ceremony);
		TestEqual(TEXT("shi-jak: combat"), Run(3.5f).Shot, EOpenStanceShot::Combat);
		Rig.Sim.SetScore(2, 0);
		Rig.Sim.SetClock(0.05f);
		TestEqual(TEXT("the break"), Run(0.3f).Shot, EOpenStanceShot::Break);
		TestEqual(TEXT("the next round: combat again"), Run(1.0f).Shot, EOpenStanceShot::Combat);
		Rig.Sim.SetScore(2, 0);
		Rig.Sim.SetClock(0.05f);
		TestEqual(TEXT("the end: results"), Run(0.3f).Shot, EOpenStanceShot::Results);

		// A spin that wins the match: the results take over from the cut.
		FCameraRig Late;
		Late.Spin();
		Late.Director.Update(0.1f, Late.Sim, 0, false);
		Late.Sim.Match.State = EOpenStanceMatchState::Finished;
		for (int32 Step = 0; Step < 20; ++Step)
		{
			Late.Director.Update(0.1f, Late.Sim, 0, false);
		}
		TestEqual(TEXT("after the cut, the results view"), Late.Director.GetShot(), EOpenStanceShot::Results);
	}
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FOpenStanceCameraSplitTest, "OpenStance.Camera.SplitScreen", EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FOpenStanceCameraSplitTest::RunTest(const FString& Parameters)
{
	// 1P vs 2P side by side: each half is 8:9, and each player's camera, behind their own fighter, keeps both in frame.
	FCameraRig Rig;
	FOpenStanceCameraDirector Halves[2];
	for (FOpenStanceCameraDirector& Half : Halves)
	{
		Half.Tuning.AspectRatio = 8.0f / 9.0f;
		Half.Tuning.MaxFieldOfViewDeg = 95.0f;
	}
	for (int32 Player = 0; Player < 2; ++Player)
	{
		for (const float Gap : { 70.0f, 200.0f, 400.0f, 600.0f })
		{
			for (int32 Step = 0; Step < 4; ++Step)
			{
				const FVector2D Dir(FMath::Cos(Step * UE_PI / 2.0), FMath::Sin(Step * UE_PI / 2.0));
				Rig.Place(-Dir * Gap * 0.5, Dir * Gap * 0.5);
				const FOpenStanceCameraFrame Frame = Halves[Player].FrameCombat(Rig.Sim, Player);
				TestTrue(*FString::Printf(TEXT("player %d, %.0f cm apart, step %d: both in the half-screen"), Player + 1, Gap, Step),
					Halves[Player].FramesBoth(Frame, Rig.Sim));
			}
		}
	}

	// The two cameras sit behind different fighters: each player looks past their own fighter at the opponent.
	Rig.Place(FVector2D(-100.0, 0.0), FVector2D(100.0, 0.0));
	const FOpenStanceCameraFrame One = Halves[0].FrameCombat(Rig.Sim, 0);
	const FOpenStanceCameraFrame Two = Halves[1].FrameCombat(Rig.Sim, 1);
	TestTrue(TEXT("player 1's camera is behind Chung"), One.Position.X < -100.0);
	TestTrue(TEXT("player 2's camera is behind Hong"), Two.Position.X > 100.0);
	return true;
}

#endif
