#include "Combat/OpenStanceMatchModelSync.h"
#include "Combat/OpenStanceMatchRules.h"
#include "Combat/OpenStanceMatchSim.h"
#include "Combat/OpenStanceMoveData.h"
#include "Menu/OpenStanceMatchModel.h"
#include "Misc/AutomationTest.h"

#if WITH_DEV_AUTOMATION_TESTS

namespace
{
	/** A match on the M1 seed table with WT rules, a short break and no ceremony unless a test asks for them. */
	struct FRulesRig
	{
		FOpenStanceMatchSim Sim;
		FOpenStanceFighterControls Chung;
		FOpenStanceFighterControls Hong;

		explicit FRulesRig(TFunctionRef<void(FOpenStanceRoundTuning&)> Configure = [](FOpenStanceRoundTuning&) {})
		{
			Sim.SetMoveTable(FOpenStanceMoveData::CreateSeedTable(GetTransientPackage()));
			Sim.RoundRules.CeremonySeconds = 0.0f;
			Sim.RoundRules.BreakSeconds = 1.0f;
			Configure(Sim.RoundRules);
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

		/** Ends the current round on the clock with this score, then waits out the break if the match goes on. */
		void PlayRound(int32 ChungPoints, int32 HongPoints)
		{
			Sim.SetScore(ChungPoints, HongPoints);
			Sim.SetClock(0.05f);
			Run(0.1f);
			if (Sim.Match.State == EOpenStanceMatchState::RoundBreak)
			{
				Sim.SkipBreak();
				Run(0.05f);
			}
		}

		bool LogHas(const TCHAR* Text) const
		{
			return Sim.Log.ContainsByPredicate([Text](const FOpenStanceMatchLogEntry& Entry) { return Entry.Text == Text; });
		}
	};

	FOpenStanceRoundTally Tally(int32 Points)
	{
		FOpenStanceRoundTally Result;
		Result.Points = Points;
		return Result;
	}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FOpenStanceMatchRulesTieBreakTest, "OpenStance.Match.TieBreak", EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FOpenStanceMatchRulesTieBreakTest::RunTest(const FString& Parameters)
{
	// Points first, then WT Article 15 in order: turning kicks, head, trunk, punch, gam-jeom, protector hits, the referee.
	const auto Decide = [](const FOpenStanceRoundTally& A, const FOpenStanceRoundTally& B, EOpenStanceRoundEnd& OutReason)
	{
		const FOpenStanceRoundTally Pair[2] = { A, B };
		EOpenStanceSide Winner;
		FOpenStanceMatchRules::DecideAtTime(Pair, EOpenStanceSide::Chung, Winner, OutReason);
		return Winner;
	};
	EOpenStanceRoundEnd Reason;

	TestEqual(TEXT("more points win"), Decide(Tally(3), Tally(5), Reason), EOpenStanceSide::Hong);
	TestEqual(TEXT("on points"), Reason, EOpenStanceRoundEnd::Points);

	// Level on 6: Hong's came from a spinning kick.
	{
		FOpenStanceRoundTally Chung, Hong;
		Chung.AddScore(3, true, false, false);
		Chung.AddScore(3, true, false, false);
		Hong.AddScore(6, true, false, true);
		TestEqual(TEXT("turning kicks break a tie"), Decide(Chung, Hong, Reason), EOpenStanceSide::Hong);
		TestEqual(TEXT("as the first tie-break"), Reason, EOpenStanceRoundEnd::TieBreakTurning);
	}
	// Level on 3, no turning kicks: a head kick beats a body kick and a punch.
	{
		FOpenStanceRoundTally Chung, Hong;
		Chung.AddScore(3, true, false, false);
		Hong.AddScore(2, false, false, false);
		Hong.AddScore(1, false, true, false);
		TestEqual(TEXT("head points next"), Decide(Chung, Hong, Reason), EOpenStanceSide::Chung);
		TestEqual(TEXT("the head tie-break"), Reason, EOpenStanceRoundEnd::TieBreakHead);
	}
	// Level on 2: two punches lose to a body kick on trunk points.
	{
		FOpenStanceRoundTally Chung, Hong;
		Chung.AddScore(1, false, true, false);
		Chung.AddScore(1, false, true, false);
		Hong.AddScore(2, false, false, false);
		TestEqual(TEXT("trunk points next"), Decide(Chung, Hong, Reason), EOpenStanceSide::Hong);
		TestEqual(TEXT("the trunk tie-break"), Reason, EOpenStanceRoundEnd::TieBreakTrunk);
	}
	// Level on 1: a punch beats a point from the opponent's gam-jeom.
	{
		FOpenStanceRoundTally Chung, Hong;
		Chung.AddScore(1, false, true, false);
		Hong.Points = 1;
		Hong.GamJeomPoints = 1;
		TestEqual(TEXT("punch points next"), Decide(Chung, Hong, Reason), EOpenStanceSide::Chung);
		TestEqual(TEXT("the punch tie-break"), Reason, EOpenStanceRoundEnd::TieBreakPunch);
	}
	// Level on 0: the protector registered Hong's glancing kick.
	{
		FOpenStanceRoundTally Chung, Hong;
		Hong.ProtectorHits = 1;
		TestEqual(TEXT("protector hits next"), Decide(Chung, Hong, Reason), EOpenStanceSide::Hong);
		TestEqual(TEXT("the protector tie-break"), Reason, EOpenStanceRoundEnd::TieBreakProtectorHits);
	}
	// Everything level: the referee decides, on techniques brought to their active phase, then the coin.
	{
		FOpenStanceRoundTally Chung, Hong;
		Chung.ActiveAttacks = 4;
		Hong.ActiveAttacks = 2;
		TestEqual(TEXT("the referee favours the busier fighter"), Decide(Chung, Hong, Reason), EOpenStanceSide::Chung);
		TestEqual(TEXT("the referee's decision"), Reason, EOpenStanceRoundEnd::RefereeDecision);
		const FOpenStanceRoundTally Level[2] = { FOpenStanceRoundTally(), FOpenStanceRoundTally() };
		EOpenStanceSide Winner;
		FOpenStanceMatchRules::DecideAtTime(Level, EOpenStanceSide::Hong, Winner, Reason);
		TestEqual(TEXT("and with nothing to go on, the coin"), Winner, EOpenStanceSide::Hong);
	}

	// Stops before time: the gap, the gap turned off, and the round's gam-jeom limit before the score.
	{
		FOpenStanceRoundTuning Rules;
		EOpenStanceSide Winner;
		const FOpenStanceRoundTally Gap[2] = { Tally(0), Tally(12) };
		TestTrue(TEXT("a 12-point lead stops the round"), FOpenStanceMatchRules::CheckRoundStop(Rules, Gap, Winner, Reason) && Winner == EOpenStanceSide::Hong && Reason == EOpenStanceRoundEnd::PointGap);
		const FOpenStanceRoundTally Short[2] = { Tally(0), Tally(11) };
		TestFalse(TEXT("an 11-point lead does not"), FOpenStanceMatchRules::CheckRoundStop(Rules, Short, Winner, Reason));
		Rules.GapToEnd = 0;
		TestFalse(TEXT("with the gap off nothing does"), FOpenStanceMatchRules::CheckRoundStop(Rules, Gap, Winner, Reason));
		Rules.GapToEnd = 20;
		TestFalse(TEXT("a 20-point gap needs 20"), FOpenStanceMatchRules::CheckRoundStop(Rules, Gap, Winner, Reason));
		FOpenStanceRoundTally Fouled[2] = { Tally(0), Tally(15) };
		Fouled[1].GamJeom = 5;
		TestTrue(TEXT("five gam-jeom lose the round, even far ahead"), FOpenStanceMatchRules::CheckRoundStop(Rules, Fouled, Winner, Reason) && Winner == EOpenStanceSide::Chung && Reason == EOpenStanceRoundEnd::PenaltyLimit);
	}
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FOpenStanceMatchRulesFlowTest, "OpenStance.Match.BestOfThree", EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FOpenStanceMatchRulesFlowTest::RunTest(const FString& Parameters)
{
	// 2-0: two rounds won on the clock end a best of three without a third.
	{
		FRulesRig Rig;
		Rig.PlayRound(3, 1);
		TestEqual(TEXT("round 1 to Chung"), Rig.Sim.Fighters[0].RoundWins, 1);
		TestEqual(TEXT("round 2 is on"), Rig.Sim.Match.Round, 2);
		TestEqual(TEXT("with the score back to zero"), Rig.Sim.Fighters[0].State.Score, 0);
		Rig.PlayRound(5, 2);
		TestEqual(TEXT("2-0 finishes the match"), Rig.Sim.Match.State, EOpenStanceMatchState::Finished);
		TestEqual(TEXT("for Chung"), Rig.Sim.MatchWinner, EOpenStanceSide::Chung);
		TestEqual(TEXT("after two rounds"), Rig.Sim.RoundHistory.Num(), 2);
		TestTrue(TEXT("the winner's call and the final bow"), Rig.LogHas(TEXT("chung seung")) && Rig.LogHas(TEXT("kyeongrye")));
		TestEqual(TEXT("and the fighters are finished"), Rig.Sim.Fighters[1].State.CombatState, EOpenStanceCombatState::MatchFinished);
	}

	// 2-1, and more total points do not beat two round wins: Hong scores 13 to Chung's 2 and still loses.
	{
		FRulesRig Rig;
		Rig.PlayRound(1, 0);
		Rig.PlayRound(0, 11);
		TestEqual(TEXT("1-1 goes to a third round"), Rig.Sim.Match.Round, 3);
		Rig.PlayRound(1, 0);
		TestEqual(TEXT("the third round ends it"), Rig.Sim.Match.State, EOpenStanceMatchState::Finished);
		TestEqual(TEXT("Chung wins on rounds"), Rig.Sim.MatchWinner, EOpenStanceSide::Chung);
		const int32 ChungTotal = Rig.Sim.RoundHistory[0].Tally[0].Points + Rig.Sim.RoundHistory[1].Tally[0].Points + Rig.Sim.RoundHistory[2].Tally[0].Points;
		const int32 HongTotal = Rig.Sim.RoundHistory[0].Tally[1].Points + Rig.Sim.RoundHistory[1].Tally[1].Points + Rig.Sim.RoundHistory[2].Tally[1].Points;
		TestTrue(TEXT("though Hong has more points in all"), HongTotal > ChungTotal);
	}

	// The 12-point gap wins the round at once, not the match, and the next round starts level.
	{
		FRulesRig Rig;
		Rig.Sim.SetScore(12, 0);
		Rig.Run(0.05f);
		TestEqual(TEXT("the gap stops round 1"), Rig.Sim.Match.State, EOpenStanceMatchState::RoundBreak);
		TestEqual(TEXT("with the gap as the reason"), Rig.Sim.RoundHistory.Num() ? Rig.Sim.RoundHistory[0].Reason : EOpenStanceRoundEnd::None, EOpenStanceRoundEnd::PointGap);
		TestTrue(TEXT("the clock had time left"), Rig.Sim.Match.ClockSeconds > 100.0f);
		Rig.Run(1.1f);
		TestEqual(TEXT("the break runs out into round 2"), Rig.Sim.Match.Round, 2);
		Rig.Sim.SetScore(0, 12);
		Rig.Run(0.05f);
		Rig.Sim.SkipBreak();
		Rig.Run(0.05f);
		Rig.Sim.SetScore(20, 0);
		Rig.Run(0.05f);
		TestEqual(TEXT("three gap rounds finish the match 2-1"), Rig.Sim.Match.State, EOpenStanceMatchState::Finished);
		TestEqual(TEXT("for Chung"), Rig.Sim.MatchWinner, EOpenStanceSide::Chung);
		TestEqual(TEXT("the reason is the gap"), Rig.Sim.MatchEnd, EOpenStanceRoundEnd::PointGap);
	}

	// Match setup's options: a single round, a 1:00 round, the gap off and a 20-point gap.
	{
		FRulesRig Rig([](FOpenStanceRoundTuning& Rules) { Rules.RoundCount = 1; Rules.RoundSeconds = 60.0f; });
		TestEqual(TEXT("a 1:00 round"), Rig.Sim.Match.ClockSeconds, 60.0f);
		Rig.PlayRound(0, 2);
		TestEqual(TEXT("a single round ends the match"), Rig.Sim.Match.State, EOpenStanceMatchState::Finished);
		TestEqual(TEXT("for its winner"), Rig.Sim.MatchWinner, EOpenStanceSide::Hong);
	}
	{
		FRulesRig Rig([](FOpenStanceRoundTuning& Rules) { Rules.GapToEnd = 0; Rules.RoundSeconds = 90.0f; });
		Rig.Sim.SetScore(30, 0);
		Rig.Run(0.2f);
		TestEqual(TEXT("with the gap off a big lead plays on"), Rig.Sim.Match.State, EOpenStanceMatchState::Running);
	}
	{
		FRulesRig Rig([](FOpenStanceRoundTuning& Rules) { Rules.GapToEnd = 20; });
		Rig.Sim.SetScore(15, 0);
		Rig.Run(0.2f);
		TestEqual(TEXT("15 is not a 20-point gap"), Rig.Sim.Match.State, EOpenStanceMatchState::Running);
		Rig.Sim.SetScore(20, 0);
		Rig.Run(0.05f);
		TestEqual(TEXT("20 is"), Rig.Sim.Match.State, EOpenStanceMatchState::RoundBreak);
	}

	// A tie at time goes through the tie-break: Chung's protector registered a glancing kick.
	{
		FRulesRig Rig;
		Rig.Sim.Fighters[0].Round.ProtectorHits = 1;
		Rig.PlayRound(4, 4);
		TestEqual(TEXT("the tied round has a winner"), Rig.Sim.Fighters[0].RoundWins, 1);
		TestEqual(TEXT("by the protector tie-break"), Rig.Sim.RoundHistory[0].Reason, EOpenStanceRoundEnd::TieBreakProtectorHits);
	}
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FOpenStanceMatchRulesPenaltyTest, "OpenStance.Match.PenaltyLimits", EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FOpenStanceMatchRulesPenaltyTest::RunTest(const FString& Parameters)
{
	// Five gam-jeom in a round lose it, though each gave the other fighter a point.
	{
		FRulesRig Rig;
		Rig.Sim.SetScore(0, 10);
		for (int32 Index = 0; Index < 4; ++Index)
		{
			Rig.Sim.AddGamJeom(1, TEXT("Boundary"));
		}
		Rig.Run(0.05f);
		TestEqual(TEXT("four do not"), Rig.Sim.Match.State, EOpenStanceMatchState::Running);
		Rig.Sim.AddGamJeom(1, TEXT("Boundary"));
		Rig.Run(0.05f);
		TestEqual(TEXT("the fifth loses Hong the round"), Rig.Sim.RoundHistory.Num() ? Rig.Sim.RoundHistory[0].Winner : EOpenStanceSide::Hong, EOpenStanceSide::Chung);
		TestEqual(TEXT("on the penalty limit"), Rig.Sim.RoundHistory.Num() ? Rig.Sim.RoundHistory[0].Reason : EOpenStanceRoundEnd::None, EOpenStanceRoundEnd::PenaltyLimit);
		Rig.Sim.SkipBreak();
		Rig.Run(0.05f);
		TestEqual(TEXT("round 2 starts with no gam-jeom"), Rig.Sim.Fighters[1].State.GamJeom, 0);
		TestEqual(TEXT("but the match count is kept"), Rig.Sim.Fighters[1].MatchGamJeom, 5);
		TestEqual(TEXT("and every reason"), Rig.Sim.Fighters[1].PenaltyReasons.Num(), 5);
	}

	// The tenth gam-jeom of the match loses the match at once, in any round.
	{
		FRulesRig Rig;
		Rig.Sim.Fighters[0].MatchGamJeom = 9;
		Rig.Sim.AddGamJeom(0, TEXT("Falling"));
		Rig.Run(0.05f);
		TestEqual(TEXT("ten gam-jeom finish the match"), Rig.Sim.Match.State, EOpenStanceMatchState::Finished);
		TestEqual(TEXT("for the other fighter"), Rig.Sim.MatchWinner, EOpenStanceSide::Hong);
		TestEqual(TEXT("on the match limit"), Rig.Sim.MatchEnd, EOpenStanceRoundEnd::MatchPenaltyLimit);
	}
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FOpenStanceMatchRulesClockTest, "OpenStance.Match.CeremonyAndBreak", EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FOpenStanceMatchRulesClockTest::RunTest(const FString& Parameters)
{
	// The opening ceremony: no attack starts and the clock holds until shi-jak.
	{
		FRulesRig Rig([](FOpenStanceRoundTuning& Rules) { Rules = FOpenStanceRoundTuning(); });
		TestEqual(TEXT("the match opens Ready"), Rig.Sim.Match.State, EOpenStanceMatchState::Ready);
		Rig.Chung.RightStick = FVector2D(0.0, 1.0);
		Rig.Run(0.1f);
		Rig.Chung.RightStick = FVector2D::ZeroVector;
		Rig.Run(1.0f);
		TestEqual(TEXT("no attack in the ceremony"), Rig.Sim.Fighters[0].State.Stamina, FOpenStanceFighterState::FullStamina);
		TestEqual(TEXT("the clock holds"), Rig.Sim.Match.ClockSeconds, 120.0f);
		Rig.Run(3.0f);
		TestEqual(TEXT("shi-jak starts play"), Rig.Sim.Match.State, EOpenStanceMatchState::Running);
		TestTrue(TEXT("after attention, bow and ready"), Rig.LogHas(TEXT("charyeot")) && Rig.LogHas(TEXT("kyeongrye")) && Rig.LogHas(TEXT("joon-bi")) && Rig.LogHas(TEXT("shi-jak")));
	}

	// A referee stop holds the clock.
	{
		FRulesRig Rig;
		Rig.Sim.SetClock(50.0f);
		Rig.Sim.Match.State = EOpenStanceMatchState::Stopped;
		Rig.Run(2.0f);
		TestEqual(TEXT("the clock holds in a stop"), Rig.Sim.Match.ClockSeconds, 50.0f);
	}

	// The full 1:00 break runs on its own, local play may skip it, and the next round starts fresh.
	{
		FRulesRig Rig([](FOpenStanceRoundTuning& Rules) { Rules.BreakSeconds = 60.0f; });
		Rig.Sim.Fighters[0].State.Stamina = 10.0f;
		Rig.Sim.Fighters[0].Motion.Position = FVector2D(250.0, 80.0);
		Rig.Sim.SetScore(2, 0);
		Rig.Sim.SetClock(0.05f);
		Rig.Run(30.0f);
		TestEqual(TEXT("half a minute into the break it is still on"), Rig.Sim.Match.State, EOpenStanceMatchState::RoundBreak);
		TestEqual(TEXT("with half a minute left"), Rig.Sim.GetPauseSecondsLeft(), 30.0f, 0.2f);
		TestTrue(TEXT("skipping it"), Rig.Sim.SkipBreak());
		Rig.Run(0.05f);
		TestEqual(TEXT("starts round 2"), Rig.Sim.Match.Round, 2);
		TestEqual(TEXT("with full stamina"), Rig.Sim.Fighters[0].State.Stamina, FOpenStanceFighterState::FullStamina, 1.0f);
		TestEqual(TEXT("and the fighters on their marks"), static_cast<float>(Rig.Sim.Fighters[0].Motion.Position.X), -100.0f, 1.0f);
		TestFalse(TEXT("nothing to skip in play"), Rig.Sim.SkipBreak());
	}
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FOpenStanceMatchRulesModelTest, "OpenStance.Match.ModelFollowsRounds", EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FOpenStanceMatchRulesModelTest::RunTest(const FString& Parameters)
{
	// The HUD's model shows the round's score and the rounds won, and names the simulation's winner, not the most points.
	FRulesRig Rig;
	UOpenStanceMatchModel* Model = NewObject<UOpenStanceMatchModel>(GetTransientPackage());
	FOpenStanceMatchModelSync Sync;
	Sync.Begin(Rig.Sim, *Model, TEXT("Min-jun Park"), TEXT("Dae-ho Kim"), nullptr);
	TestFalse(TEXT("the model is out of its demo"), Model->bDemoMode);

	const auto Step = [&](float Seconds)
	{
		const int32 Count = FMath::Max(1, FMath::RoundToInt(Seconds * 60.0f));
		for (int32 Index = 0; Index < Count; ++Index)
		{
			Rig.Sim.Step(1.0f / 60.0f, Rig.Chung, Rig.Hong);
			Sync.Update(Rig.Sim, *Model);
		}
	};

	// Round 1 to Chung on a gam-jeom point; round 2 to Hong by the gap.
	Rig.Sim.AddGamJeom(1, TEXT("Boundary"));
	Rig.Sim.SetClock(0.05f);
	Step(0.1f);
	TestTrue(TEXT("the break shows on the HUD"), Model->IsInBreak());
	TestEqual(TEXT("round 1 recorded for Chung"), Model->GetRoundOutcome(1) ? Model->GetRoundOutcome(1)->Winner : EOpenStanceSide::Hong, EOpenStanceSide::Chung);
	Rig.Sim.SkipBreak();
	Step(0.05f);
	TestEqual(TEXT("round 2 on the HUD"), Model->GetRound(), 2);
	TestEqual(TEXT("the HUD's score is the round's"), Model->GetScore(EOpenStanceSide::Chung), 0);
	TestEqual(TEXT("and so is its gam-jeom"), Model->GetGamJeom(EOpenStanceSide::Hong), 0);
	TestEqual(TEXT("the match keeps it"), Model->GetMatchGamJeom(EOpenStanceSide::Hong), 1);
	TestEqual(TEXT("one round each, after this one"), Model->GetRoundWins(EOpenStanceSide::Chung), 1);

	Rig.Sim.SetScore(0, 12);
	Step(0.05f);
	TestEqual(TEXT("round 2 to Hong by the gap"), Model->GetRoundOutcome(2) ? Model->GetRoundOutcome(2)->Reason : FString(), FString(TEXT("Point gap")));
	Rig.Sim.SkipBreak();
	Step(0.05f);
	Rig.Sim.SetScore(1, 0);
	Rig.Sim.SetClock(0.05f);
	Step(0.1f);
	TestTrue(TEXT("the match is over on the HUD"), Model->IsFinished());
	TestEqual(TEXT("Chung wins 2-1"), Model->GetWinner(), EOpenStanceSide::Chung);
	TestEqual(TEXT("two rounds to one"), Model->GetRoundWins(EOpenStanceSide::Chung) * 10 + Model->GetRoundWins(EOpenStanceSide::Hong), 21);
	TestEqual(TEXT("the referee names the winner"), Model->GetCallTerm(), FString(TEXT("CHUNG SEUNG")));
	return true;
}

#endif
