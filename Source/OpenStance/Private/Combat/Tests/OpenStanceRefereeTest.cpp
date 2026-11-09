#include "Combat/OpenStanceCameraDirector.h"
#include "Combat/OpenStanceMatchModelSync.h"
#include "Combat/OpenStanceMatchSim.h"
#include "Combat/OpenStanceMoveData.h"
#include "Combat/OpenStanceReferee.h"
#include "Menu/OpenStanceMatchModel.h"
#include "Misc/AutomationTest.h"

#if WITH_DEV_AUTOMATION_TESTS

namespace
{
	/** A match with the referee following it at 60 Hz. Every call the referee makes is kept, in order. */
	struct FRefereeRig
	{
		FOpenStanceMatchSim Sim;
		FOpenStanceReferee Referee;
		FOpenStanceFighterControls Chung;
		FOpenStanceFighterControls Hong;
		TArray<FOpenStanceRefereeCall> Calls;
		TArray<EOpenStanceRefereePose> Poses;

		explicit FRefereeRig(bool bCeremony = false, float Distance = 200.0f)
		{
			Sim.SetMoveTable(FOpenStanceMoveData::CreateSeedTable(GetTransientPackage()));
			Sim.RoundRules.CeremonySeconds = bCeremony ? 4.0f : 0.0f;
			Sim.RoundRules.BreakSeconds = 1.0f;
			Sim.PenaltyRules.PassivitySeconds = 0.0f;
			Sim.StartMatch(Distance);
			Referee.Reset(Sim, 0, 3);
		}

		void Run(float Seconds)
		{
			for (int32 Step = 0; Step < FMath::Max(1, FMath::RoundToInt(Seconds * 60.0f)); ++Step)
			{
				Sim.Step(1.0f / 60.0f, Chung, Hong);
				Referee.Update(1.0f / 60.0f, Sim, 0);
				Calls.Append(Referee.GetNewCalls());
				if (Poses.IsEmpty() || Poses.Last() != Referee.GetPose())
				{
					Poses.Add(Referee.GetPose());
				}
			}
		}

		TArray<FString> Terms() const
		{
			TArray<FString> Out;
			for (const FOpenStanceRefereeCall& Call : Calls)
			{
				Out.Add(Call.Term);
			}
			return Out;
		}

		float DistanceTo(int32 Fighter) const
		{
			return static_cast<float>((Referee.GetPosition() - Sim.Fighters[Fighter].Motion.Position).Size());
		}
	};

	FOpenStanceMatchLogEntry Entry(const TCHAR* Text, EOpenStanceSide Side = EOpenStanceSide::Chung)
	{
		FOpenStanceMatchLogEntry Out;
		Out.Text = Text;
		Out.Side = Side;
		return Out;
	}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FOpenStanceRefereeCallsTest, "OpenStance.Referee.Calls", EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FOpenStanceRefereeCallsTest::RunTest(const FString& Parameters)
{
	// GDD 8.5: every command with its English meaning, the side named where a fighter is.
	FOpenStanceRefereeCall Call;
	const auto Check = [&](const FOpenStanceMatchLogEntry& In, const TCHAR* Term, const TCHAR* Meaning, EOpenStanceRefereePose Pose)
	{
		if (TestTrue(*FString::Printf(TEXT("'%s' is a call"), *In.Text), FOpenStanceReferee::CallFor(In, Call)))
		{
			TestEqual(*FString::Printf(TEXT("'%s' term"), *In.Text), Call.Term, FString(Term));
			TestEqual(*FString::Printf(TEXT("'%s' meaning"), *In.Text), Call.Meaning, FString(Meaning));
			TestEqual(*FString::Printf(TEXT("'%s' gesture"), *In.Text), Call.Pose, Pose);
			TestFalse(*FString::Printf(TEXT("'%s' has a voice line"), *In.Text), Call.Cue.IsNone());
		}
	};
	using P = EOpenStanceRefereePose;
	Check(Entry(TEXT("charyeot")), TEXT("CHARYEOT"), TEXT("Attention"), P::Attention);
	Check(Entry(TEXT("kyeongrye")), TEXT("KYEONGRYE"), TEXT("Bow"), P::Bow);
	Check(Entry(TEXT("joon-bi")), TEXT("JOON-BI"), TEXT("Ready"), P::Ready);
	Check(Entry(TEXT("shi-jak")), TEXT("SHI-JAK"), TEXT("Begin"), P::Start);
	Check(Entry(TEXT("kal-yeo")), TEXT("KAL-YEO"), TEXT("Break"), P::Separate);
	Check(Entry(TEXT("kye-sok")), TEXT("KYE-SOK"), TEXT("Continue"), P::Start);
	Check(Entry(TEXT("keu-man")), TEXT("KEU-MAN"), TEXT("Stop"), P::Stop);
	Check(Entry(TEXT("gong-gyeok")), TEXT("GONG-GYEOK"), TEXT("Attack"), P::Start);
	Check(Entry(TEXT("gam-jeom: holding or pushing"), EOpenStanceSide::Hong), TEXT("GAM-JEOM"), TEXT("Hong, Holding or pushing"), P::Point);
	TestTrue(TEXT("the penalty names Hong"), Call.bNamesSide && Call.Side == EOpenStanceSide::Hong);
	Check(Entry(TEXT("count 1")), TEXT("HANA"), TEXT("One"), P::Count);
	Check(Entry(TEXT("count 8")), TEXT("YEODEOL"), TEXT("Eight"), P::Count);
	Check(Entry(TEXT("hong seung"), EOpenStanceSide::Hong), TEXT("HONG SEUNG"), TEXT("Hong wins"), P::RaiseWinner);
	TestFalse(TEXT("a score is not a referee call"), FOpenStanceReferee::CallFor(Entry(TEXT("score +2 SideKick_Trunk to the trunk")), Call));

	// A referee is picked at random from the six.
	TSet<int32> Picked;
	FRefereeRig Rig;
	for (int32 Seed = 0; Seed < 30; ++Seed)
	{
		Rig.Referee.Reset(Rig.Sim, 0, Seed);
		Picked.Add(Rig.Referee.GetRefereeIndex());
	}
	TestTrue(TEXT("different matches get different referees"), Picked.Num() >= 4);
	bool bInRange = true;
	for (const int32 Index : Picked)
	{
		bInRange &= Index >= 0 && Index < FOpenStanceReferee::RefereeCount;
	}
	TestTrue(TEXT("and only the six"), bInRange);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FOpenStanceRefereeCeremonyTest, "OpenStance.Referee.CeremonyAndPosition", EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FOpenStanceRefereeCeremonyTest::RunTest(const FString& Parameters)
{
	// The opening ceremony in order, with its gestures.
	FRefereeRig Rig(true);
	Rig.Run(4.5f);
	TestEqual(TEXT("attention, bow, ready, start"), FString::Join(Rig.Terms(), TEXT(" ")), FString(TEXT("CHARYEOT KYEONGRYE JOON-BI SHI-JAK")));
	TestTrue(TEXT("with the attention, bow, ready and start gestures"),
		Rig.Poses.Contains(EOpenStanceRefereePose::Bow) && Rig.Poses.Contains(EOpenStanceRefereePose::Ready) && Rig.Poses.Contains(EOpenStanceRefereePose::Start));

	// In play: clear of both fighters, on the far side of the line from the combat camera, and never between the camera
	// and a fighter, while the fighters circle.
	FOpenStanceCameraDirector Director;
	for (int32 Step = 0; Step < 8; ++Step)
	{
		const FVector2D Dir(FMath::Cos(Step * UE_PI / 4.0), FMath::Sin(Step * UE_PI / 4.0));
		Rig.Sim.Fighters[0].Motion.Position = -Dir * 110.0;
		Rig.Sim.Fighters[1].Motion.Position = Dir * 110.0;
		Rig.Run(3.0f); // time to walk round
		TestTrue(*FString::Printf(TEXT("step %d: clear of Chung"), Step), Rig.DistanceTo(0) >= 115.0f);
		TestTrue(*FString::Printf(TEXT("step %d: clear of Hong"), Step), Rig.DistanceTo(1) >= 115.0f);
		const FOpenStanceCameraFrame Camera = Director.FrameCombat(Rig.Sim, 0);
		const FVector2D Cam(Camera.Position.X, Camera.Position.Y);
		for (int32 Fighter = 0; Fighter < 2; ++Fighter)
		{
			const FVector2D F = Rig.Sim.Fighters[Fighter].Motion.Position;
			const FVector2D Closest = FMath::ClosestPointOnSegment2D(Rig.Referee.GetPosition(), Cam, F);
			TestTrue(*FString::Printf(TEXT("step %d: not in the camera's view of fighter %d"), Step, Fighter), (Closest - Rig.Referee.GetPosition()).Size() > 50.0);
		}
	}
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FOpenStanceRefereeStopsTest, "OpenStance.Referee.Stops", EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FOpenStanceRefereeStopsTest::RunTest(const FString& Parameters)
{
	// A clinch: the referee steps in between for kal-yeo, then kye-sok.
	{
		FRefereeRig Rig(false, 150.0f);
		Rig.Chung.bB = true;
		Rig.Chung.LeftStick = FVector2D(0.0, 1.0);
		Rig.Run(0.45f);
		Rig.Chung.bB = false;
		Rig.Chung.LeftStick = FVector2D::ZeroVector;
		Rig.Run(0.9f);
		TestEqual(TEXT("kal-yeo"), Rig.Referee.GetPose(), EOpenStanceRefereePose::Separate);
		const FVector2D Mid = (Rig.Sim.Fighters[0].Motion.Position + Rig.Sim.Fighters[1].Motion.Position) * 0.5;
		Rig.Run(0.3f);
		TestTrue(TEXT("the referee has stepped in toward the fighters"), (Rig.Referee.GetPosition() - Mid).Size() < 120.0);
		Rig.Run(1.5f);
		TestTrue(TEXT("then kye-sok"), Rig.Terms().Contains(TEXT("KYE-SOK")));
	}

	// A penalty: the referee names the side and points at that fighter.
	{
		FRefereeRig Rig;
		Rig.Run(0.5f);
		Rig.Sim.AddGamJeom(1, TEXT("Boundary"));
		Rig.Run(0.1f);
		TestEqual(TEXT("kal-yeo, then gam-jeom"), FString::Join(Rig.Terms(), TEXT(" ")).Right(16), FString(TEXT("KAL-YEO GAM-JEOM")));
		Rig.Run(0.5f);
		TestEqual(TEXT("pointing"), Rig.Referee.GetPose(), EOpenStanceRefereePose::Point);
		const FVector2D Facing = Rig.Referee.GetFacing();
		const FVector2D RefRight(-Facing.Y, Facing.X);
		const bool bHongOnRight = FVector2D::DotProduct(Rig.Sim.Fighters[1].Motion.Position - Rig.Referee.GetPosition(), RefRight) >= 0.0;
		TestEqual(TEXT("with the arm on Hong's side"), Rig.Referee.IsGestureRight(), bHongOnRight);
	}

	// A knockdown: kal-yeo, the clock stops, HANA to YEODEOL a second apart beside the fighter on the floor, nothing scores,
	// then kye-sok and the clock runs again (GDD 8.5, 8.10).
	{
		FRefereeRig Rig(false, 90.0f);
		Rig.Hong.DPad = EOpenStanceDPad::Down; // Low guard: the head is open
		Rig.Run(0.4f);
		Rig.Hong.DPad = EOpenStanceDPad::None;
		Rig.Sim.Fighters[1].State.Stamina = 10.0f;
		Rig.Sim.Fighters[1].PreviousStamina = 10.0f;
		Rig.Sim.ThrowMove(0, TEXT("Roundhouse_Head"), EOpenStanceLegSide::Right);
		for (int32 Step = 0; Step < 90 && !Rig.Sim.IsCounting(); ++Step)
		{
			Rig.Run(1.0f / 60.0f);
		}
		TestTrue(TEXT("the knockdown starts a count"), Rig.Sim.IsCounting());
		TestEqual(TEXT("over Hong"), Rig.Sim.GetCountedFighter(), 1);
		const float Clock = Rig.Sim.Match.ClockSeconds;
		const int32 Score = Rig.Sim.Fighters[0].State.Score;
		Rig.Run(4.0f);
		TestEqual(TEXT("the clock holds through the count"), Rig.Sim.Match.ClockSeconds, Clock);
		TestTrue(TEXT("the referee stands over the fighter on the floor"), Rig.DistanceTo(1) < 140.0f);
		Rig.Sim.ThrowMove(0, TEXT("Roundhouse_Trunk"), EOpenStanceLegSide::Right);
		Rig.Run(1.0f);
		TestEqual(TEXT("nothing scores during the count"), Rig.Sim.Fighters[0].State.Score, Score);
		Rig.Run(4.5f);
		const TArray<FString> Terms = Rig.Terms();
		const int32 First = Terms.Find(TEXT("HANA"));
		const int32 Last = Terms.Find(TEXT("YEODEOL"));
		TestTrue(TEXT("HANA to YEODEOL, in order"), First != INDEX_NONE && Last == First + 7);
		TestEqual(TEXT("then kye-sok"), Terms.Last(), FString(TEXT("KYE-SOK")));
		TestEqual(TEXT("and play runs"), Rig.Sim.Match.State, EOpenStanceMatchState::Running);
		Rig.Run(0.5f);
		TestTrue(TEXT("the clock runs again"), Rig.Sim.Match.ClockSeconds < Clock);
	}

	// The end: KEU-MAN, the winner's hand raised with the side named, the bow.
	{
		FRefereeRig Rig;
		Rig.Sim.RoundRules.RoundCount = 1;
		Rig.Sim.StartMatch(200.0f);
		Rig.Referee.Reset(Rig.Sim, 0, 3);
		Rig.Sim.SetScore(0, 3);
		Rig.Sim.SetClock(0.05f);
		Rig.Run(4.0f);
		const TArray<FString> Terms = Rig.Terms();
		TestTrue(TEXT("keu-man, hong seung, kyeongrye"), Terms.Contains(TEXT("KEU-MAN")) && Terms.Contains(TEXT("HONG SEUNG")) && Terms.Last() == TEXT("KYEONGRYE"));
		TestTrue(TEXT("the winner's hand went up"), Rig.Poses.Contains(EOpenStanceRefereePose::RaiseWinner));

		// The HUD shows the same calls, with their meanings.
		UOpenStanceMatchModel* Model = NewObject<UOpenStanceMatchModel>(GetTransientPackage());
		FOpenStanceMatchModelSync Sync;
		FRefereeRig Count(false, 90.0f);
		Sync.Begin(Count.Sim, *Model, TEXT("A"), TEXT("B"), nullptr);
		Count.Sim.AddLog(EOpenStanceSide::Hong, TEXT("count 3"));
		Sync.Update(Count.Sim, *Model);
		TestEqual(TEXT("the HUD shows SET"), Model->GetCallTerm(), FString(TEXT("SET")));
		TestEqual(TEXT("meaning three"), Model->GetCallMeaning(), FString(TEXT("Three")));
	}
	return true;
}

#endif
