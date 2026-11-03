#include "Combat/OpenStanceMatchModelSync.h"
#include "Combat/OpenStanceMatchSim.h"
#include "Combat/OpenStanceMoveData.h"
#include "Engine/DataTable.h"
#include "Menu/OpenStanceMatchModel.h"
#include "Misc/AutomationTest.h"

#if WITH_DEV_AUTOMATION_TESTS

namespace
{
	/** A simulation on the seed moves, mirrored into a HUD model. */
	struct FSyncRig
	{
		FOpenStanceMatchSim Sim;
		FOpenStanceFighterControls Chung;
		FOpenStanceFighterControls Hong;
		FOpenStanceMatchModelSync Sync;
		UOpenStanceMatchModel* Model = nullptr;

		explicit FSyncRig(float Distance = 90.0f)
		{
			const UDataTable* Table = FOpenStanceMoveData::CreateSeedTable(GetTransientPackage());
			Sim.SetMoveTable(Table);
			Sim.StartMatch(Distance);
			Model = NewObject<UOpenStanceMatchModel>(GetTransientPackage());
			Sync.Begin(Sim, *Model, TEXT("Min-jun Park"), TEXT("Dae-ho Kim"), Table);
		}

		void Run(float Seconds)
		{
			const int32 Count = FMath::Max(1, FMath::RoundToInt(Seconds * 60.0f));
			for (int32 Index = 0; Index < Count; ++Index)
			{
				Sim.Step(1.0f / 60.0f, Chung, Hong);
				Sync.Update(Sim, *Model);
			}
		}
	};
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FOpenStanceMatchModelSyncTest, "OpenStance.Greybox.MatchModelSync", EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FOpenStanceMatchModelSyncTest::RunTest(const FString& Parameters)
{
	// Taking the model over turns the demo off and names the fighters.
	{
		FSyncRig Rig;
		TestFalse(TEXT("the HUD is out of its demo"), Rig.Model->bDemoMode);
		TestEqual(TEXT("Chung's name"), Rig.Model->GetFighterName(EOpenStanceSide::Chung), FString(TEXT("Min-jun Park")));
		TestEqual(TEXT("Hong's name"), Rig.Model->GetFighterName(EOpenStanceSide::Hong), FString(TEXT("Dae-ho Kim")));
		TestEqual(TEXT("round 1"), Rig.Model->GetRound(), 1);
	}

	// A scored kick shows in the score, the results list and the stamina bar.
	{
		FSyncRig Rig(90.0f);
		Rig.Chung.RightStick = FVector2D(0.0, 1.0);
		Rig.Run(0.06f);
		Rig.Chung.RightStick = FVector2D::ZeroVector;
		Rig.Run(0.1f);
		const float StaminaAfterKick = Rig.Model->GetStamina(EOpenStanceSide::Chung);
		Rig.Run(1.4f);
		const int32 SimScore = Rig.Sim.Fighters[0].State.Score;
		TestTrue(TEXT("the side kick scored in the simulation"), SimScore > 0);
		TestEqual(TEXT("the HUD shows the same score"), Rig.Model->GetScore(EOpenStanceSide::Chung), SimScore);
		if (TestEqual(TEXT("one scoring event"), Rig.Model->GetEvents().Num(), 1))
		{
			TestEqual(TEXT("with the move's name"), Rig.Model->GetEvents()[0].Technique, FString(TEXT("Side Kick")));
			TestEqual(TEXT("filed under Chung"), Rig.Model->GetEvents()[0].Side, EOpenStanceSide::Chung);
		}
		TestTrue(TEXT("the kick cost stamina, and the bar shows it"), StaminaAfterKick < 1.0f);
		TestEqual(TEXT("the other fighter's bar is full"), Rig.Model->GetStamina(EOpenStanceSide::Hong), 1.0f);
	}

	// The referee's call names the scoring category the points decide (GDD 8.3).
	{
		UOpenStanceMatchModel* Model = NewObject<UOpenStanceMatchModel>(GetTransientPackage());
		Model->Reset(TEXT("A"), TEXT("B"));
		bool bChungScores = true; // alternate the fighters so the 12-point gap does not end the match mid-test
		const auto Check = [&](int32 Points, bool bHead, const TCHAR* Technique, const TCHAR* Term, const TCHAR* Meaning)
		{
			Model->AddPoints(bChungScores ? EOpenStanceSide::Chung : EOpenStanceSide::Hong, Points, Technique, bHead);
			bChungScores = !bChungScores;
			TestEqual(*FString::Printf(TEXT("%d points: call"), Points), Model->GetCallTerm(), FString(Term));
			TestEqual(*FString::Printf(TEXT("%d points: meaning"), Points), Model->GetCallMeaning(), FString(Meaning));
		};
		Check(6, true, TEXT("Spin Hook Kick"), TEXT("Spin Head Kick"), TEXT("6 Points"));
		Check(4, false, TEXT("Spin Side Kick"), TEXT("Spin Body Kick"), TEXT("4 Points"));
		Check(3, true, TEXT("Roundhouse Kick"), TEXT("Head Kick"), TEXT("3 Points"));
		Check(2, false, TEXT("Side Kick"), TEXT("Body Kick"), TEXT("2 Points"));
		Check(1, false, TEXT("Punch"), TEXT("Punch"), TEXT("1 Point"));
	}

	// A penalty: the gam-jeom, the other fighter's point, the reason and the referee's call.
	{
		FSyncRig Rig;
		Rig.Sim.AddGamJeom(1, TEXT("Grabbing"));
		Rig.Run(0.05f);
		TestEqual(TEXT("Hong has a gam-jeom"), Rig.Model->GetGamJeom(EOpenStanceSide::Hong), 1);
		TestEqual(TEXT("Chung gets the point"), Rig.Model->GetScore(EOpenStanceSide::Chung), 1);
		TestTrue(TEXT("the reason is kept for the results page"), Rig.Model->GetPenaltyReasons(EOpenStanceSide::Hong).Contains(TEXT("Grabbing")));
		TestEqual(TEXT("the referee calls gam-jeom"), Rig.Model->GetCallTerm(), FString(TEXT("GAM-JEOM")));
	}

	// The clinch's referee calls reach the HUD: kal-yeo, then kye-sok.
	{
		FSyncRig Rig(150.0f);
		Rig.Chung.bB = true;
		Rig.Chung.LeftStick = FVector2D(0.0, 1.0);
		Rig.Run(0.45f);
		Rig.Chung.bB = false;
		Rig.Chung.LeftStick = FVector2D::ZeroVector;
		Rig.Run(0.9f);
		TestEqual(TEXT("kal-yeo"), Rig.Model->GetCallTerm(), FString(TEXT("KAL-YEO")));
		Rig.Run(1.2f);
		TestEqual(TEXT("then kye-sok"), Rig.Model->GetCallTerm(), FString(TEXT("KYE-SOK")));
	}

	// The clock, the round and the break between rounds.
	{
		FSyncRig Rig;
		Rig.Sim.SetClock(30.0f);
		Rig.Run(0.05f);
		TestEqual(TEXT("the HUD clock follows the simulation"), Rig.Model->GetTimeRemaining(), 30.0f, 0.5f);
		Rig.Sim.SetClock(0.1f);
		Rig.Run(0.5f);
		TestEqual(TEXT("keu-man at the end of the round"), Rig.Model->GetCallTerm(), FString(TEXT("KEU-MAN")));
		Rig.Run(2.4f);
		TestEqual(TEXT("round 2 on the HUD"), Rig.Model->GetRound(), 2);
		TestEqual(TEXT("with shi-jak"), Rig.Model->GetCallTerm(), FString(TEXT("SHI-JAK")));
		TestFalse(TEXT("the match is not over"), Rig.Model->IsFinished());
	}

	// The simulation ending the match ends the HUD's.
	{
		FSyncRig Rig;
		Rig.Sim.SetScore(12, 0);
		Rig.Run(0.2f);
		TestTrue(TEXT("the 12-point gap finishes the HUD's match"), Rig.Model->IsFinished());
	}
	return true;
}

#endif
