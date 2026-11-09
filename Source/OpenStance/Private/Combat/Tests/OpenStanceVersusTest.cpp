#include "Combat/OpenStanceMatchSim.h"
#include "Combat/OpenStanceMoveData.h"
#include "Menu/OpenStanceMenuContent.h"
#include "Misc/AutomationTest.h"

#if WITH_DEV_AUTOMATION_TESTS

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FOpenStanceVersusRulesTest, "OpenStance.Versus.SetupRules", EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FOpenStanceVersusRulesTest::RunTest(const FString& Parameters)
{
	// The Sparring setup's rows set the match's rules (GDD 8.2).
	FOpenStanceMatchSim Sim;
	Sim.ApplyChoices({});
	TestEqual(TEXT("no choices: best of three"), Sim.RoundRules.RoundCount, 3);
	TestEqual(TEXT("2:00 rounds"), Sim.RoundRules.RoundSeconds, 120.0f);
	TestEqual(TEXT("12-point gap"), Sim.RoundRules.GapToEnd, 12);
	TestFalse(TEXT("gam-jeom on"), Sim.bNoGamJeom);

	Sim.ApplyChoices({ { TEXT("Rounds"), TEXT("Single Round") }, { TEXT("RoundLength"), TEXT("1:30") }, { TEXT("PointGap"), TEXT("Off") },
		{ TEXT("Ruleset"), TEXT("Casual (No Gam-jeom)") } });
	TestEqual(TEXT("single round"), Sim.RoundRules.RoundCount, 1);
	TestEqual(TEXT("1:30"), Sim.RoundRules.RoundSeconds, 90.0f);
	TestEqual(TEXT("gap off"), Sim.RoundRules.GapToEnd, 0);
	TestTrue(TEXT("casual: no gam-jeom"), Sim.bNoGamJeom);
	Sim.ApplyChoices({ { TEXT("RoundLength"), TEXT("1:00") }, { TEXT("PointGap"), TEXT("20") }, { TEXT("Ruleset"), TEXT("World Taekwondo") } });
	TestEqual(TEXT("1:00"), Sim.RoundRules.RoundSeconds, 60.0f);
	TestEqual(TEXT("20-point gap"), Sim.RoundRules.GapToEnd, 20);
	TestFalse(TEXT("WT: gam-jeom back on"), Sim.bNoGamJeom);

	// Casual: a foul is noted, gives no point and does not stop play.
	Sim.SetMoveTable(FOpenStanceMoveData::CreateSeedTable(GetTransientPackage()));
	Sim.ApplyChoices({ { TEXT("Ruleset"), TEXT("Casual (No Gam-jeom)") } });
	Sim.RoundRules.CeremonySeconds = 0.0f;
	Sim.StartMatch(200.0f);
	Sim.AddGamJeom(0, TEXT("Boundary"));
	TestEqual(TEXT("no gam-jeom"), Sim.Fighters[0].MatchGamJeom, 0);
	TestEqual(TEXT("no point for the other side"), Sim.Fighters[1].State.Score, 0);
	TestEqual(TEXT("play goes on"), Sim.Match.State, EOpenStanceMatchState::Running);

	// The rows are on the Sparring setup, with the WT values first.
	const auto* Setup = OpenStanceMenuContent::FindSetup(EOpenStanceMenuScreen::Sparring);
	if (TestNotNull(TEXT("the Sparring setup"), Setup))
	{
		for (const TCHAR* Row : { TEXT("Players"), TEXT("Ruleset"), TEXT("Rounds"), TEXT("RoundLength"), TEXT("PointGap"), TEXT("Arena") })
		{
			TestTrue(*FString::Printf(TEXT("has the %s row"), Row), Setup->Rows.ContainsByPredicate([Row](const auto& R) { return R.Id == FName(Row); }));
		}
	}
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FOpenStanceVersusControlsTest, "OpenStance.Versus.TwoPlayers", EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FOpenStanceVersusControlsTest::RunTest(const FString& Parameters)
{
	// Two independent pads: each fighter acts only on its own controls, in the same steps.
	FOpenStanceMatchSim Sim;
	Sim.SetMoveTable(FOpenStanceMoveData::CreateSeedTable(GetTransientPackage()));
	Sim.RoundRules.CeremonySeconds = 0.0f;
	Sim.PenaltyRules.PassivitySeconds = 0.0f;
	Sim.StartMatch(300.0f);
	FOpenStanceFighterControls Chung, Hong;
	const auto Run = [&](float Seconds)
	{
		for (int32 Step = 0; Step < FMath::RoundToInt(Seconds * 60.0f); ++Step)
		{
			Sim.Step(1.0f / 60.0f, Chung, Hong);
		}
	};

	// Chung steps in while Hong raises the guard: neither does the other's action.
	Chung.LeftStick = FVector2D(0.0, 1.0);
	Hong.bLT = true;
	const FVector2D HongStart = Sim.Fighters[1].Motion.Position;
	Run(0.5f);
	TestTrue(TEXT("Chung moved"), Sim.Fighters[0].Motion.Position.X > -150.0);
	TestTrue(TEXT("Hong did not"), (Sim.Fighters[1].Motion.Position - HongStart).Size() < 1.0);
	TestEqual(TEXT("Hong is guarding"), Sim.Fighters[1].State.CombatState, EOpenStanceCombatState::ActiveDefense);
	TestNotEqual(TEXT("Chung is not"), Sim.Fighters[0].State.CombatState, EOpenStanceCombatState::ActiveDefense);

	// Both kick on the same step: both techniques start.
	Chung = FOpenStanceFighterControls();
	Hong = FOpenStanceFighterControls();
	Run(0.5f);
	Chung.RightStick = Hong.RightStick = FVector2D(0.0, 1.0);
	Run(0.06f);
	Chung.RightStick = Hong.RightStick = FVector2D::ZeroVector;
	Run(0.15f);
	TestTrue(TEXT("Chung's kick started"), Sim.Fighters[0].State.IsAttacking());
	TestTrue(TEXT("Hong's kick started"), Sim.Fighters[1].State.IsAttacking());
	return true;
}

#endif
