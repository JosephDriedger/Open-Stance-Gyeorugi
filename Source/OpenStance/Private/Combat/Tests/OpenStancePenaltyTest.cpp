#include "Combat/OpenStanceMatchModelSync.h"
#include "Combat/OpenStanceMatchSim.h"
#include "Combat/OpenStanceMoveData.h"
#include "Menu/OpenStanceMatchModel.h"
#include "Misc/AutomationTest.h"

#if WITH_DEV_AUTOMATION_TESTS

namespace
{
	/** Two idle fighters two metres apart, no ceremony. Passivity is off unless a test turns it on, so long checks stay clean. */
	struct FPenaltyRig
	{
		FOpenStanceMatchSim Sim;
		FOpenStanceFighterControls Chung;
		FOpenStanceFighterControls Hong;

		explicit FPenaltyRig(bool bPassivity = false)
		{
			Sim.SetMoveTable(FOpenStanceMoveData::CreateSeedTable(GetTransientPackage()));
			Sim.RoundRules.CeremonySeconds = 0.0f;
			if (!bPassivity)
			{
				Sim.PenaltyRules.PassivitySeconds = 0.0f;
			}
			Sim.StartMatch(200.0f);
		}

		void Run(float Seconds)
		{
			const int32 Count = FMath::Max(1, FMath::RoundToInt(Seconds * 60.0f));
			for (int32 Index = 0; Index < Count; ++Index)
			{
				Sim.Step(1.0f / 60.0f, Chung, Hong);
			}
		}

		FOpenStanceFighterSim& F(int32 Index) { return Sim.Fighters[Index]; }

		int32 Count(int32 Index, const TCHAR* Reason) const
		{
			int32 Found = 0;
			for (const FString& Given : Sim.Fighters[Index].PenaltyReasons)
			{
				Found += Given == Reason ? 1 : 0;
			}
			return Found;
		}

		bool LogHas(const TCHAR* Text) const
		{
			return Sim.Log.ContainsByPredicate([Text](const FOpenStanceMatchLogEntry& Entry) { return Entry.Text == Text; });
		}

		/** Puts Chung at X on the mat's centre line, facing Hong, and lets one step run. */
		void PlaceChung(float X)
		{
			F(0).Motion.Position = FVector2D(X, 0.0);
			Run(1.0f / 60.0f);
		}
	};
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FOpenStancePenaltyBoundaryTest, "OpenStance.Penalty.Boundary", EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FOpenStancePenaltyBoundaryTest::RunTest(const FString& Parameters)
{
	// Walking backwards off the mat: one gam-jeom, a referee's stop, and the fighter is brought back in.
	{
		FPenaltyRig Rig;
		Rig.Chung.LeftStick = FVector2D(0.0, -1.0);
		for (int32 Step = 0; Step < 400 && Rig.F(0).MatchGamJeom == 0; ++Step)
		{
			Rig.Run(1.0f / 60.0f);
		}
		Rig.Chung.LeftStick = FVector2D::ZeroVector;
		TestEqual(TEXT("a foot over the edge is a gam-jeom"), Rig.Count(0, TEXT("Boundary")), 1);
		TestEqual(TEXT("the opponent gets the point"), Rig.F(1).State.Score, 1);
		TestEqual(TEXT("the referee stops play"), Rig.Sim.Match.State, EOpenStanceMatchState::Stopped);
		TestTrue(TEXT("with kal-yeo"), Rig.LogHas(TEXT("kal-yeo")));
		TestFalse(TEXT("and the fighter is back inside"), Rig.Sim.PenaltyRules.IsFootOut(Rig.F(0).Motion.Position, Rig.F(0).Motion.Facing));
		const float Clock = Rig.Sim.Match.ClockSeconds;
		Rig.Run(0.5f);
		TestEqual(TEXT("the clock holds in the stop"), Rig.Sim.Match.ClockSeconds, Clock);
		Rig.Run(0.6f);
		TestEqual(TEXT("kye-sok resumes play"), Rig.Sim.Match.State, EOpenStanceMatchState::Running);
		TestTrue(TEXT("with the call"), Rig.LogHas(TEXT("kye-sok")));
		TestEqual(TEXT("one incident, one gam-jeom"), Rig.F(0).MatchGamJeom, 1);
	}

	// Near the line: on it or just past it is safe; the whole foot over is not. The back foot is 30 cm behind the centre.
	{
		FPenaltyRig Rig;
		Rig.PlaceChung(-370.0f);
		Rig.Run(0.3f);
		TestEqual(TEXT("a foot on the line is safe"), Rig.F(0).MatchGamJeom, 0);
		Rig.PlaceChung(-381.0f);
		Rig.Run(0.3f);
		TestEqual(TEXT("a foot mostly on the line is safe"), Rig.F(0).MatchGamJeom, 0);
		Rig.PlaceChung(-384.0f);
		TestEqual(TEXT("a whole foot over is a gam-jeom"), Rig.F(0).MatchGamJeom, 1);
	}

	// Corners count too: the octagon's diagonal edge is as far from the centre as its flat ones.
	{
		FPenaltyRig Rig;
		Rig.F(0).Motion.Position = FVector2D(-300.0, -300.0); // 424 cm along the diagonal
		Rig.Run(1.0f / 60.0f);
		TestEqual(TEXT("off a diagonal edge"), Rig.F(0).MatchGamJeom, 1);
	}

	// Pushed out by the opponent's holding or pushing: no penalty, but still brought back in.
	{
		FPenaltyRig Rig;
		Rig.F(0).Watch.SinceForcedSeconds = 0.0f;
		Rig.PlaceChung(-440.0f);
		TestEqual(TEXT("forced out is not a foul"), Rig.F(0).MatchGamJeom, 0);
		TestFalse(TEXT("but the fighter is back inside"), Rig.Sim.PenaltyRules.IsFootOut(Rig.F(0).Motion.Position, Rig.F(0).Motion.Facing));
	}
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FOpenStancePenaltyAvoidingTest, "OpenStance.Penalty.AvoidingAndLegLift", EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FOpenStancePenaltyAvoidingTest::RunTest(const FString& Parameters)
{
	// Turning the back: more than 90 degrees for more than a second, counted once per turn.
	{
		FPenaltyRig Rig;
		Rig.F(0).Motion.TurnedAwayDeg = 85.0f;
		Rig.Run(2.0f);
		TestEqual(TEXT("85 degrees is not turning the back"), Rig.F(0).MatchGamJeom, 0);
		Rig.F(0).Motion.TurnedAwayDeg = 120.0f;
		Rig.Run(0.95f);
		TestEqual(TEXT("under a second is not"), Rig.F(0).MatchGamJeom, 0);
		Rig.Run(0.1f);
		TestEqual(TEXT("over a second is"), Rig.Count(0, TEXT("Turning the back")), 1);
		Rig.Run(3.0f);
		TestEqual(TEXT("staying turned is the same incident"), Rig.Count(0, TEXT("Turning the back")), 1);
		Rig.F(0).Motion.TurnedAwayDeg = 0.0f;
		Rig.Run(0.2f);
		Rig.F(0).Motion.TurnedAwayDeg = 120.0f;
		Rig.Run(1.1f);
		TestEqual(TEXT("turning away again is a new one"), Rig.Count(0, TEXT("Turning the back")), 2);
	}

	// Crouching below Low Guard for over a second; Low Guard itself never counts.
	{
		FPenaltyRig Rig;
		Rig.Chung.DPad = EOpenStanceDPad::Down;
		Rig.Run(0.1f);
		Rig.Chung.DPad = EOpenStanceDPad::None;
		Rig.Run(3.0f);
		TestEqual(TEXT("Low Guard"), Rig.F(0).State.Guard, EOpenStanceGuard::Low);
		TestEqual(TEXT("is not crouching"), Rig.F(0).MatchGamJeom, 0);
		Rig.F(0).Motion.CrouchCm = 8.0f;
		Rig.Run(0.95f);
		TestEqual(TEXT("under a second below it is not"), Rig.F(0).MatchGamJeom, 0);
		Rig.Run(0.1f);
		TestEqual(TEXT("over a second is"), Rig.Count(0, TEXT("Crouching")), 1);
	}

	// Leg lifting: over 3 s above the hip outside a technique.
	{
		FPenaltyRig Rig;
		Rig.F(1).Motion.bLegRaised = true;
		Rig.Run(2.95f);
		TestEqual(TEXT("under 3 s is not leg lifting"), Rig.F(1).MatchGamJeom, 0);
		Rig.Run(0.1f);
		TestEqual(TEXT("over 3 s is"), Rig.Count(1, TEXT("Leg lifting")), 1);
		Rig.Run(4.0f);
		TestEqual(TEXT("once per lift"), Rig.Count(1, TEXT("Leg lifting")), 1);
	}
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FOpenStancePenaltyPassivityTest, "OpenStance.Penalty.Passivity", EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FOpenStancePenaltyPassivityTest::RunTest(const FString& Parameters)
{
	// Neither fighter engages: GONG-GYEOK at 3 s, a gam-jeom for both at 6 s.
	{
		FPenaltyRig Rig(true);
		UOpenStanceMatchModel* Model = NewObject<UOpenStanceMatchModel>(GetTransientPackage());
		FOpenStanceMatchModelSync Sync;
		Sync.Begin(Rig.Sim, *Model, TEXT("A"), TEXT("B"), nullptr);
		Rig.Run(3.05f);
		Sync.Update(Rig.Sim, *Model);
		TestEqual(TEXT("GONG-GYEOK at 3 s"), Model->GetCallTerm(), FString(TEXT("GONG-GYEOK")));
		TestEqual(TEXT("no gam-jeom yet"), Rig.F(0).MatchGamJeom + Rig.F(1).MatchGamJeom, 0);
		Rig.Run(3.0f);
		TestEqual(TEXT("at 6 s both are penalized"), Rig.Count(0, TEXT("Not engaging")) + Rig.Count(1, TEXT("Not engaging")), 2);
		TestEqual(TEXT("so the score stays level"), Rig.F(0).State.Score, Rig.F(1).State.Score);
	}

	// One backs away: only that one is penalized.
	{
		FPenaltyRig Rig(true);
		Rig.Hong.LeftStick = FVector2D(0.0, -1.0);
		Rig.Run(1.0f);
		Rig.Hong.LeftStick = FVector2D::ZeroVector;
		Rig.Run(5.05f);
		TestEqual(TEXT("the one who moved back"), Rig.Count(1, TEXT("Moving back")), 1);
		TestEqual(TEXT("and not the other"), Rig.F(0).MatchGamJeom, 0);
	}

	// A technique reaching its active phase restarts the timer; a fake does not count.
	{
		FPenaltyRig Rig(true);
		Rig.Run(5.0f);
		Rig.Sim.ThrowMove(0, TEXT("Roundhouse_Trunk"), EOpenStanceLegSide::Right);
		Rig.Run(2.0f);
		TestEqual(TEXT("an attack resets the passivity timer"), Rig.F(0).MatchGamJeom + Rig.F(1).MatchGamJeom, 0);
	}
	return true;
}

#endif
