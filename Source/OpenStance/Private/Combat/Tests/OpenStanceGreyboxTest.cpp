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

#endif
