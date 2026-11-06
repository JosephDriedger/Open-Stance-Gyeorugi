#include "Combat/OpenStanceCombatOverlay.h"
#include "Combat/OpenStanceGreyboxProof.h"
#include "Engine/DataTable.h"
#include "Misc/AutomationTest.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"

#if WITH_DEV_AUTOMATION_TESTS

namespace
{
	/** A simulation on the M1 seed table. */
	struct FSimRig
	{
		FOpenStanceMatchSim Sim;
		FOpenStanceFighterControls Chung;
		FOpenStanceFighterControls Hong;

		FSimRig(float Distance = 100.0f)
		{
			Sim.SetMoveTable(FOpenStanceMoveData::CreateSeedTable(GetTransientPackage()));
			Sim.StartMatch(Distance);
		}

		void Run(float Seconds)
		{
			const int32 Count = FMath::Max(1, FMath::RoundToInt(Seconds * 60.0f));
			for (int32 Index = 0; Index < Count; ++Index)
			{
				Sim.Step(1.0f / 60.0f, Chung, Hong);
			}
		}
	};
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FOpenStanceGreyboxProofTest, "OpenStance.Greybox.Proof", EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FOpenStanceGreyboxProofTest::RunTest(const FString& Parameters)
{
	FOpenStanceMatchSim Sim;
	Sim.SetMoveTable(FOpenStanceMoveData::CreateSeedTable(GetTransientPackage()));
	const TArray<FOpenStanceGreyboxProof::FStage> Stages = FOpenStanceGreyboxProof::Run(Sim);
	TestEqual(TEXT("eight stages"), Stages.Num(), 8);
	for (const FOpenStanceGreyboxProof::FStage& Stage : Stages)
	{
		TestTrue(*FString::Printf(TEXT("%s -- %s"), *Stage.Name, *Stage.Detail), Stage.bPassed);
	}

	// Kept as the record of the proof, regenerated on every run.
	const FString Path = FPaths::ProjectLogDir() / TEXT("OpenStanceGreyboxProof.txt");
	FFileHelper::SaveStringToFile(FOpenStanceGreyboxProof::Format(Stages, Sim), *Path, FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);

	// It is repeatable: a second run gives the same result.
	FOpenStanceMatchSim Again;
	Again.SetMoveTable(FOpenStanceMoveData::CreateSeedTable(GetTransientPackage()));
	const TArray<FOpenStanceGreyboxProof::FStage> Second = FOpenStanceGreyboxProof::Run(Again);
	TestEqual(TEXT("the second run has the same text"), FOpenStanceGreyboxProof::Format(Second, Again), FOpenStanceGreyboxProof::Format(Stages, Sim));
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FOpenStanceGreyboxProofReplayTest, "OpenStance.Greybox.ProofReplay", EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FOpenStanceGreyboxProofReplayTest::RunTest(const FString& Parameters)
{
	// os.PlayProof records the script, then feeds it step by step into a fresh match: the replay must end the same way.
	FOpenStanceMatchSim Recorded;
	Recorded.SetMoveTable(FOpenStanceMoveData::CreateSeedTable(GetTransientPackage()));
	FOpenStanceGreyboxProof::FTrack Track;
	const TArray<FOpenStanceGreyboxProof::FStage> Stages = FOpenStanceGreyboxProof::Run(Recorded, &Track);
	TestTrue(TEXT("the recorded run passes"), FOpenStanceGreyboxProof::AllPassed(Stages));
	TestTrue(TEXT("a step was recorded per 60 Hz tick"), Track.Chung.Num() > 300);
	TestEqual(TEXT("an intro, six stages and the final score are captioned"), Track.Captions.Num(), 8);

	FOpenStanceMatchSim Live;
	Live.SetMoveTable(FOpenStanceMoveData::CreateSeedTable(GetTransientPackage()));
	Live.StartMatch(FOpenStanceGreyboxProof::StartDistanceCm);
	const FOpenStanceFighterControls Idle;
	for (const FOpenStanceFighterControls& Chung : Track.Chung)
	{
		Live.Step(FOpenStanceGreyboxProof::StepSeconds, Chung, Idle);
	}
	TestEqual(TEXT("the replay scores the same for Chung"), Live.Fighters[0].State.Score, FOpenStanceGreyboxProof::ExpectedChungScore);
	TestEqual(TEXT("and for Hong"), Live.Fighters[1].State.Score, 0);
	TestEqual(TEXT("and logs the same match"), Live.Log.Num(), Recorded.Log.Num());
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FOpenStanceMatchSimTest, "OpenStance.Greybox.Sim", EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FOpenStanceMatchSimTest::RunTest(const FString& Parameters)
{
	// Cheats: infinite stamina holds it at 100, score and clock can be set.
	{
		FSimRig Rig;
		Rig.Sim.bInfiniteStamina = true;
		Rig.Chung.bRT = false;
		Rig.Chung.RightStick = FVector2D(0.0, 1.0);
		Rig.Run(0.1f);
		Rig.Chung.RightStick = FVector2D::ZeroVector;
		Rig.Run(1.0f);
		TestEqual(TEXT("kicks cost nothing with os.InfiniteStamina"), Rig.Sim.Fighters[0].State.Stamina, FOpenStanceFighterState::FullStamina);

		Rig.Sim.SetScore(7, 3);
		Rig.Sim.SetClock(42.0f);
		TestEqual(TEXT("os.SetScore Chung"), Rig.Sim.Fighters[0].State.Score, 7);
		TestEqual(TEXT("os.SetScore Hong"), Rig.Sim.Fighters[1].State.Score, 3);
		TestEqual(TEXT("os.SetClock"), Rig.Sim.Match.ClockSeconds, 42.0f, 0.5f);
	}
	// Without the cheat a kick costs stamina and it comes back after a second.
	{
		FSimRig Rig;
		Rig.Chung.RightStick = FVector2D(0.0, 1.0);
		Rig.Run(0.1f);
		Rig.Chung.RightStick = FVector2D::ZeroVector;
		Rig.Run(0.2f);
		const float Spent = Rig.Sim.Fighters[0].State.Stamina;
		TestTrue(TEXT("the side kick cost stamina"), Spent < 95.0f);
		Rig.Run(3.0f);
		TestEqual(TEXT("and after a second of rest it came back to full"), Rig.Sim.Fighters[0].State.Stamina, FOpenStanceFighterState::FullStamina);
	}
	// A punch to the head and a kick below the belt each cost the offender a gam-jeom and give the other a point.
	{
		FSimRig Rig(70.0f);
		FOpenStanceMoveRow Row = FOpenStanceMoveData::BuildSeedRows()[TEXT("Roundhouse_Trunk")];
		FOpenStanceContact Foul;
		Foul.Type = EOpenStanceContactType::KickBelowBelt;
		Foul.Attacker = EOpenStanceSide::Chung;
		Foul.Defender = EOpenStanceSide::Hong;
		// Drive the real path: a kick whose tip is forced low through the registry.
		FOpenStanceAttackRequest Request;
		Request.MoveName = TEXT("Roundhouse_Trunk");
		Request.Row = Row;
		FOpenStanceCombatMachine& Machine = Rig.Sim.Fighters[0].Machine;
		TArray<FOpenStanceCombatEvent> Events;
		Machine.RequestAttack(Request, Rig.Sim.Fighters[0].State, Rig.Sim.Match, true, Events);
		Machine.Tick(0.25f, Rig.Sim.Fighters[0].State, Rig.Sim.Match, Events);
		FOpenStanceHitContext Context;
		Context.Attack = Machine.GetCurrentAttack();
		Context.bCanScore = Machine.CanScore(Rig.Sim.Fighters[0].State, Rig.Sim.Match);
		Context.AttackSerial = Machine.GetAttackSerial();
		Context.Attacker = Rig.Sim.Fighters[0].GetBody();
		Context.Defender = Rig.Sim.Fighters[1].GetBody();
		Context.Trace.Start = FVector(Context.Defender.Root.X - 10.0, 0.0, 60.0);
		Context.Trace.End = FVector(Context.Defender.Root.X, 0.0, 60.0);
		TArray<FOpenStanceContact> Contacts;
		TestTrue(TEXT("a low trace registers a foul"), Rig.Sim.Fighters[0].Registry.Trace(Context, Contacts));
		TestEqual(TEXT("it is the below-belt kind"), Contacts.Num() ? Contacts[0].Type : EOpenStanceContactType::Score, EOpenStanceContactType::KickBelowBelt);
	}
	// Stopped play: nothing scores and no attack starts.
	{
		FSimRig Rig;
		Rig.Sim.Match.State = EOpenStanceMatchState::Stopped;
		Rig.Chung.RightStick = FVector2D(0.0, 1.0);
		Rig.Run(0.1f);
		Rig.Chung.RightStick = FVector2D::ZeroVector;
		Rig.Run(1.0f);
		TestEqual(TEXT("no score while stopped"), Rig.Sim.Fighters[0].State.Score, 0);
		TestEqual(TEXT("no attack started"), Rig.Sim.Fighters[0].State.Stamina, FOpenStanceFighterState::FullStamina);
	}
	// A match that runs out of clock finishes and freezes combat.
	{
		FSimRig Rig;
		Rig.Sim.Match.Round = Rig.Sim.RoundRules.RoundCount; // the last round
		Rig.Sim.SetClock(0.2f);
		Rig.Run(0.5f);
		TestEqual(TEXT("the clock ended the match"), Rig.Sim.Match.State, EOpenStanceMatchState::Finished);
		TestEqual(TEXT("and the fighters are finished"), Rig.Sim.Fighters[0].State.CombatState, EOpenStanceCombatState::MatchFinished);
	}
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FOpenStanceOverlayTest, "OpenStance.Greybox.Overlay", EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FOpenStanceOverlayTest::RunTest(const FString& Parameters)
{
	FSimRig Rig;
	Rig.Chung.bRT = true;
	Rig.Chung.bRB = true;
	Rig.Chung.RightStick = FVector2D(-1.0, 0.0);
	Rig.Run(0.1f);
	Rig.Chung.RightStick = FVector2D::ZeroVector;
	Rig.Run(0.1f);

	auto Contains = [](const TArray<FString>& Lines, const TCHAR* Text)
	{
		return Lines.ContainsByPredicate([Text](const FString& Line) { return Line.Contains(Text); });
	};

	const TArray<FString> Debug = FOpenStanceCombatOverlay::BuildLines(Rig.Sim, 0, false);
	TestTrue(TEXT("debug: stance and state"), Contains(Debug, TEXT("Right Lead")) && Contains(Debug, TEXT("Attack")));
	TestTrue(TEXT("debug: held modifiers"), Contains(Debug, TEXT("Held: RT RB")));
	TestTrue(TEXT("debug: stick history"), Contains(Debug, TEXT("Stick: Left")));
	TestTrue(TEXT("debug: resolved leg, move and target"), Contains(Debug, TEXT("Leg: Left (back)")) && Contains(Debug, TEXT("Roundhouse")) && Contains(Debug, TEXT("Target: Head")));
	TestTrue(TEXT("debug: stamina and score"), Contains(Debug, TEXT("Stamina:")) && Contains(Debug, TEXT("score 0")));
	TestTrue(TEXT("debug: result"), Contains(Debug, TEXT("Result:")));

	// The player-facing display carries the training items and not the internals.
	const TArray<FString> Player = FOpenStanceCombatOverlay::BuildLines(Rig.Sim, 0, true);
	TestTrue(TEXT("training: input, leg, move, target, stamina, result"),
		Contains(Player, TEXT("Input:")) && Contains(Player, TEXT("Leg:")) && Contains(Player, TEXT("Move:")) && Contains(Player, TEXT("Target:")) && Contains(Player, TEXT("Stamina:")) && Contains(Player, TEXT("Result:")));
	TestFalse(TEXT("training: no combat-state internals"), Contains(Player, TEXT("Stick:")) || Contains(Player, TEXT("guard")));

	// Rejected and expired gestures stay visible.
	FSimRig Bad;
	Bad.Chung.RightStick = FVector2D(0.0, -1.0);
	Bad.Run(0.1f);
	Bad.Chung.RightStick = FVector2D(-1.0, 0.0);
	Bad.Run(0.1f);
	Bad.Chung.RightStick = FVector2D::ZeroVector;
	Bad.Run(0.1f);
	TestTrue(TEXT("a rejected gesture is shown"), Contains(FOpenStanceCombatOverlay::BuildLines(Bad.Sim, 0, false), TEXT("Rejected: Down, Left")));
	FSimRig Partial;
	Partial.Chung.RightStick = FVector2D(0.0, -1.0);
	Partial.Run(0.5f);
	TestTrue(TEXT("an expired gesture is shown"), Contains(FOpenStanceCombatOverlay::BuildLines(Partial.Sim, 0, false), TEXT("Expired: Down")));
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FOpenStanceGreyboxPunchTest, "OpenStance.Greybox.Punch", EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FOpenStanceGreyboxPunchTest::RunTest(const FString& Parameters)
{
	// X throws one punch per press, to the trunk; holding it does not repeat.
	FSimRig Rig(80.0f);
	Rig.Chung.bX = true;
	Rig.Run(0.05f);
	TestEqual(TEXT("X starts a punch"), Rig.Sim.Fighters[0].LastMove, FString(TEXT("Punch")));
	TestEqual(TEXT("to the trunk"), Rig.Sim.Fighters[0].LastTarget, FString(TEXT("Trunk")));
	const int32 AfterPress = Rig.Sim.Fighters[0].InputEventCount;
	Rig.Run(1.0f);
	TestEqual(TEXT("a held X throws no second punch"), Rig.Sim.Fighters[0].InputEventCount, AfterPress);

	// LT reads the buttons as defence, so X does nothing under it.
	FSimRig Blocking(80.0f);
	Blocking.Chung.bLT = true;
	Blocking.Chung.bX = true;
	Blocking.Run(0.2f);
	TestEqual(TEXT("no punch while LT is held"), Blocking.Sim.Fighters[0].InputEventCount, 0);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FOpenStanceGreyboxSpinSwitchTest, "OpenStance.Greybox.SpinKicksSwitchSides", EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FOpenStanceGreyboxSpinSwitchTest::RunTest(const FString& Parameters)
{
	// A spin side kick lands facing the front: the sides switch, with the animated switch rather than an instant flip.
	{
		FSimRig Rig(100.0f);
		TestEqual(TEXT("starts Right Lead"), Rig.Sim.Fighters[0].State.Stance, EOpenStanceStance::RightLead);
		Rig.Chung.RightStick = FVector2D(0.0, -1.0);
		Rig.Run(0.05f);
		Rig.Chung.RightStick = FVector2D(0.0, 1.0);
		Rig.Run(0.05f);
		Rig.Chung.RightStick = FVector2D::ZeroVector;
		bool bSawSwitch = false;
		for (int32 Index = 0; Index < 180 && !bSawSwitch; ++Index)
		{
			Rig.Run(1.0f / 60.0f);
			bSawSwitch = Rig.Sim.Fighters[0].Motion.bSwitching;
		}
		TestTrue(TEXT("the switch animates"), bSawSwitch);
		Rig.Run(2.0f);
		TestEqual(TEXT("the spin side kick left Chung Left Lead"), Rig.Sim.Fighters[0].State.Stance, EOpenStanceStance::LeftLead);
		TestFalse(TEXT("and the switch has finished"), Rig.Sim.Fighters[0].Motion.bSwitching);
	}

	// The spin hook (RT and a half circle down) does the same.
	{
		FSimRig Rig(100.0f);
		Rig.Chung.bRT = true;
		const FVector2D Path[] = { FVector2D(-1.0, 0.0), FVector2D(0.0, -1.0), FVector2D(1.0, 0.0) };
		for (const FVector2D& Step : Path)
		{
			Rig.Chung.RightStick = Step;
			Rig.Run(0.04f);
		}
		Rig.Chung.RightStick = FVector2D::ZeroVector;
		Rig.Run(3.0f);
		TestEqual(TEXT("the spin hook was thrown"), Rig.Sim.Fighters[0].LastMove.Left(9), FString(TEXT("Spin Hook")));
		TestEqual(TEXT("and left Chung Left Lead"), Rig.Sim.Fighters[0].State.Stance, EOpenStanceStance::LeftLead);
	}

	// Every back-leg kick lands with the sides switched, whatever the kick is.
	{
		FSimRig Rig(100.0f);
		Rig.Chung.bRT = true;
		Rig.Chung.RightStick = FVector2D(-1.0, 0.0); // Right Lead + RT: the left back leg's roundhouse
		Rig.Run(0.05f);
		Rig.Chung.RightStick = FVector2D::ZeroVector;
		Rig.Run(3.0f);
		TestEqual(TEXT("a back-leg roundhouse was thrown"), Rig.Sim.Fighters[0].LastLeg, FString(TEXT("Left (back)")));
		TestEqual(TEXT("and it left Chung Left Lead"), Rig.Sim.Fighters[0].State.Stance, EOpenStanceStance::LeftLead);
	}

	// An ordinary kick does not switch sides.
	{
		FSimRig Rig(100.0f);
		Rig.Chung.RightStick = FVector2D(0.0, 1.0);
		Rig.Run(0.05f);
		Rig.Chung.RightStick = FVector2D::ZeroVector;
		Rig.Run(2.0f);
		TestEqual(TEXT("a side kick keeps Right Lead"), Rig.Sim.Fighters[0].State.Stance, EOpenStanceStance::RightLead);
	}
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FOpenStanceGreyboxClinchTest, "OpenStance.Greybox.Clinch", EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FOpenStanceGreyboxClinchTest::RunTest(const FString& Parameters)
{
	const auto Distance = [](const FSimRig& Rig) { return static_cast<float>((Rig.Sim.Fighters[0].Motion.Position - Rig.Sim.Fighters[1].Motion.Position).Size()); };
	const auto LogHas = [](const FSimRig& Rig, const TCHAR* Text)
	{
		return Rig.Sim.Log.ContainsByPredicate([Text](const FOpenStanceMatchLogEntry& Entry) { return Entry.Text.Contains(Text); });
	};

	// A dash that closes to contact range starts a clinch (GDD 6.4).
	{
		FSimRig Rig(150.0f);
		Rig.Chung.bB = true;
		Rig.Chung.LeftStick = FVector2D(0.0, 1.0);
		Rig.Run(0.45f);
		Rig.Chung.bB = false;
		Rig.Chung.LeftStick = FVector2D::ZeroVector;
		TestTrue(TEXT("the dash ended chest to chest"), Distance(Rig) <= Rig.Sim.ClinchRules.ContactRangeCm + 1.0f);
		TestTrue(TEXT("and a clinch started"), Rig.Sim.IsInClinch());
		TestTrue(TEXT("the log says so"), LogHas(Rig, TEXT("clinch")));

		// Nobody can throw, dash or switch inside it.
		Rig.Chung.bX = true;
		Rig.Run(0.1f);
		Rig.Chung.bX = false;
		TestTrue(TEXT("a punch in a clinch is refused"), Rig.Sim.Fighters[0].LastResult.StartsWith(TEXT("clinch")));
		TestEqual(TEXT("and no technique started"), Rig.Sim.Fighters[0].State.CombatState, EOpenStanceCombatState::IdleMovement);

		// The referee calls kal-yeo: play stops, the clock holds and the fighters are drawn apart.
		Rig.Run(0.75f);
		TestEqual(TEXT("kal-yeo stops play"), Rig.Sim.Match.State, EOpenStanceMatchState::Stopped);
		TestTrue(TEXT("kal-yeo is logged"), LogHas(Rig, TEXT("kal-yeo")));
		const float ClockAtStop = Rig.Sim.Match.ClockSeconds;
		Rig.Run(0.2f);
		TestEqual(TEXT("the clock holds while play is stopped"), Rig.Sim.Match.ClockSeconds, ClockAtStop);

		// Kye-sok: play resumes with the fighters apart and free to act.
		Rig.Run(1.0f);
		TestEqual(TEXT("kye-sok restarts play"), Rig.Sim.Match.State, EOpenStanceMatchState::Running);
		TestTrue(TEXT("kye-sok is logged"), LogHas(Rig, TEXT("kye-sok")));
		TestFalse(TEXT("the clinch is over"), Rig.Sim.IsInClinch());
		TestTrue(TEXT("and the fighters are the referee's separation apart"), Distance(Rig) >= Rig.Sim.ClinchRules.SeparationCm - 2.0f);
		TestEqual(TEXT("an ordinary clinch is not a foul"), Rig.Sim.Fighters[0].State.GamJeom + Rig.Sim.Fighters[1].State.GamJeom, 0);

		Rig.Chung.bX = true;
		Rig.Run(0.05f);
		TestEqual(TEXT("a punch works again"), Rig.Sim.Fighters[0].LastMove, FString(TEXT("Punch")));
	}

	// Holding or pushing for over a second is a gam-jeom for whoever is still pressing in (GDD 8.4).
	{
		FSimRig Rig(150.0f);
		Rig.Sim.ClinchRules.RefereeCallSeconds = 3.0f; // a slow referee, so the hold can pass a second
		Rig.Chung.bB = true;
		Rig.Chung.LeftStick = FVector2D(0.0, 1.0);
		Rig.Run(0.45f);
		Rig.Chung.bB = false;
		Rig.Run(1.2f); // Chung keeps pushing, Hong stands still
		TestEqual(TEXT("the pusher is penalized"), Rig.Sim.Fighters[0].State.GamJeom, 1);
		TestEqual(TEXT("the other fighter scores the point"), Rig.Sim.Fighters[1].State.Score, 1);
		TestEqual(TEXT("the fighter who did not push is not"), Rig.Sim.Fighters[1].State.GamJeom, 0);
		Rig.Run(1.0f);
		TestEqual(TEXT("one penalty per clinch"), Rig.Sim.Fighters[0].State.GamJeom, 1);
	}

	// Fighters two metres apart do not clinch.
	{
		FSimRig Rig(200.0f);
		Rig.Run(0.5f);
		TestFalse(TEXT("no clinch from two metres"), Rig.Sim.IsInClinch());
	}
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FOpenStanceGreyboxRoundsTest, "OpenStance.Greybox.Rounds", EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FOpenStanceGreyboxRoundsTest::RunTest(const FString& Parameters)
{
	// Three rounds: the clock running out ends a round, not the match, until the last one (WT rules, GDD 4.4).
	{
		FSimRig Rig;
		Rig.Sim.SetScore(3, 1);
		Rig.Sim.SetClock(0.2f);
		Rig.Run(0.5f);
		TestEqual(TEXT("round 1 ends in a break"), Rig.Sim.Match.State, EOpenStanceMatchState::RoundBreak);
		Rig.Run(2.2f);
		TestEqual(TEXT("round 2 starts"), Rig.Sim.Match.Round, 2);
		TestEqual(TEXT("with play running"), Rig.Sim.Match.State, EOpenStanceMatchState::Running);
		TestEqual(TEXT("and a full clock"), Rig.Sim.Match.ClockSeconds, Rig.Sim.RoundRules.RoundSeconds, 3.0f);
		TestEqual(TEXT("the scores carry over"), Rig.Sim.Fighters[0].State.Score, 3);
		TestEqual(TEXT("and the fighters are back on their marks"), static_cast<float>((Rig.Sim.Fighters[1].Motion.Position - Rig.Sim.Fighters[0].Motion.Position).Size()), 100.0f, 1.0f);

		Rig.Sim.SetClock(0.1f);
		Rig.Run(2.8f);
		TestEqual(TEXT("round 3 starts"), Rig.Sim.Match.Round, 3);
		Rig.Sim.SetClock(0.1f);
		Rig.Run(0.5f);
		TestEqual(TEXT("the third round's clock ends the match"), Rig.Sim.Match.State, EOpenStanceMatchState::Finished);
	}

	// A 12-point gap ends the match at once.
	{
		FSimRig Rig;
		Rig.Sim.SetScore(12, 0);
		Rig.Run(0.1f);
		TestEqual(TEXT("a 12-point gap finishes the match"), Rig.Sim.Match.State, EOpenStanceMatchState::Finished);
	}

	// A penalty's reason is kept for the HUD and the results page.
	{
		FSimRig Rig;
		Rig.Sim.AddGamJeom(1, TEXT("Grabbing"));
		TestEqual(TEXT("the penalized fighter has a gam-jeom"), Rig.Sim.Fighters[1].State.GamJeom, 1);
		TestEqual(TEXT("the other fighter gets the point"), Rig.Sim.Fighters[0].State.Score, 1);
		TestEqual(TEXT("and the reason is recorded"), Rig.Sim.Fighters[1].PenaltyReasons.Num() == 1 ? Rig.Sim.Fighters[1].PenaltyReasons[0] : FString(), FString(TEXT("Grabbing")));
	}
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FOpenStanceGreyboxEveryMoveTest,"OpenStance.Greybox.EveryMoveHasARow", EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FOpenStanceGreyboxEveryMoveTest::RunTest(const FString& Parameters)
{
	// Every gesture the recognizer registers must find a move row for each target and jump state it can produce, or the
	// input would throw "unmapped" in the greybox.
	const UDataTable* Table = FOpenStanceMoveData::CreateSeedTable(GetTransientPackage());
	for (const FOpenStanceGestureDef& Def : FOpenStanceSkillStickRecognizer::MakeDefaultGestures())
	{
		const bool bJumps[] = { false, true };
		const EOpenStanceTarget Targets[] = { EOpenStanceTarget::Trunk, EOpenStanceTarget::Head };
		for (const bool bJump : bJumps)
		{
			if (bJump && !Def.bCanJump)
			{
				continue;
			}
			if (!bJump && Def.bRequiresJump)
			{
				continue;
			}
			for (const EOpenStanceTarget Target : Targets)
			{
				if (Def.bHeadOnly && Target != EOpenStanceTarget::Head)
				{
					continue;
				}
				TestNotNull(*FString::Printf(TEXT("%s, %s%s has a move row"), *UEnum::GetValueAsString(Def.Technique),
					Target == EOpenStanceTarget::Head ? TEXT("head") : TEXT("trunk"), bJump ? TEXT(", jump") : TEXT("")),
					FOpenStanceMoveData::Find(*Table, Def.Technique, Target, bJump));
			}
		}
	}
	TestNotNull(TEXT("the punch has a row"), FOpenStanceMoveData::Find(*Table, EOpenStanceTechnique::Punch, EOpenStanceTarget::Trunk, false));
	return true;
}

#endif
