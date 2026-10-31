#include "Combat/OpenStanceGreyboxProof.h"

namespace
{
	constexpr float Tick = 1.0f / 60.0f;

	struct FProofRun
	{
		FOpenStanceMatchSim& Sim;
		FOpenStanceFighterControls Chung;
		FOpenStanceFighterControls Hong;
		TArray<FOpenStanceGreyboxProof::FStage> Stages;

		explicit FProofRun(FOpenStanceMatchSim& InSim) : Sim(InSim) {}

		void Hold(float Seconds)
		{
			const int32 Count = FMath::Max(1, FMath::RoundToInt(Seconds / Tick));
			for (int32 Index = 0; Index < Count; ++Index)
			{
				Sim.Step(Tick, Chung, Hong);
			}
		}

		/** Pushes the right stick one way for a few frames, then back to centre. */
		void Flick(const FVector2D& Stick)
		{
			Chung.RightStick = Stick;
			Hold(0.05f);
			Chung.RightStick = FVector2D::ZeroVector;
			Hold(0.1f);
		}

		/** Lets both fighters finish whatever they are doing. */
		void Settle()
		{
			for (int32 Index = 0; Index < 400; ++Index)
			{
				Sim.Step(Tick, Chung, Hong);
				if (Sim.Fighters[0].State.CombatState == EOpenStanceCombatState::IdleMovement
					&& Sim.Fighters[1].State.CombatState == EOpenStanceCombatState::IdleMovement)
				{
					return;
				}
			}
		}

		void Stage(const TCHAR* Name, bool bPassed, const FString& Detail)
		{
			FOpenStanceGreyboxProof::FStage& Entry = Stages.AddDefaulted_GetRef();
			Entry.Name = Name;
			Entry.bPassed = bPassed;
			Entry.Detail = Detail;
		}

		int32 ChungScore() const { return Sim.Fighters[0].State.Score; }
		const FOpenStanceFighterSim& Chung0() const { return Sim.Fighters[0]; }
	};
}

TArray<FOpenStanceGreyboxProof::FStage> FOpenStanceGreyboxProof::Run(FOpenStanceMatchSim& Sim)
{
	FProofRun Run(Sim);
	Sim.StartMatch(100.0f);
	Run.Hold(0.2f);

	const FVector2D Up(0.0, 1.0), Down(0.0, -1.0), Left(-1.0, 0.0), Right(1.0, 0.0);
	auto Scored = [&](const TCHAR* Name, int32 Before, int32 Points, const TCHAR* LegContains, const TCHAR* MoveContains)
	{
		const FOpenStanceFighterSim& F = Run.Chung0();
		const bool bPassed = Run.ChungScore() == Before + Points && F.LastLeg.Contains(LegContains) && F.LastMove.Contains(MoveContains);
		Run.Stage(Name, bPassed, FString::Printf(TEXT("%s with the %s, %s; score %d -> %d"), *F.LastMove, *F.LastLeg, *F.LastResult, Before, Run.ChungScore()));
	};

	// 1. RS Up: the side kick with the lead leg.
	int32 Before = Run.ChungScore();
	Run.Flick(Up);
	Run.Settle();
	Scored(TEXT("Side kick (RS Up)"), Before, 2, TEXT("Right (lead)"), TEXT("Side Kick"));

	// 2. RS toward the lead leg: the roundhouse.
	Before = Run.ChungScore();
	Run.Flick(Right);
	Run.Settle();
	Scored(TEXT("Roundhouse (RS toward the lead leg)"), Before, 2, TEXT("Right (lead)"), TEXT("Roundhouse"));

	// 3. RS Down then Up: the spin side kick, 4 points.
	Before = Run.ChungScore();
	Run.Chung.RightStick = Down;
	Run.Hold(0.05f);
	Run.Chung.RightStick = Up;
	Run.Hold(0.05f);
	Run.Chung.RightStick = FVector2D::ZeroVector;
	Run.Hold(0.1f);
	Run.Settle();
	Scored(TEXT("Spin side kick (RS Down, Up)"), Before, 4, TEXT("Right (lead)"), TEXT("Spin Side"));

	// 4. A switches sides: a visible switch, then the other leg leads.
	Run.Chung.bA = true;
	Run.Hold(0.1f);
	const bool bMidSwitch = Run.Chung0().Motion.bSwitching && Run.Chung0().State.Stance == EOpenStanceStance::RightLead;
	Run.Chung.bA = false;
	Run.Hold(0.6f);
	Run.Stage(TEXT("Switch sides (A)"), bMidSwitch && Run.Chung0().State.Stance == EOpenStanceStance::LeftLead && !Run.Chung0().Motion.bSwitching,
		FString::Printf(TEXT("switching without an instant mirror, then %s"), Run.Chung0().State.Stance == EOpenStanceStance::LeftLead ? TEXT("Left Lead") : TEXT("Right Lead")));

	// 5. The same RT roundhouse from the other side: the back leg is now the right one and RS Right throws it.
	Run.Chung.bRT = true;
	Before = Run.ChungScore();
	Run.Flick(Right);
	Run.Chung.bRT = false;
	Run.Settle();
	Scored(TEXT("Back-leg roundhouse after switching (RT + RS toward the back leg)"), Before, 2, TEXT("Right (back)"), TEXT("Roundhouse"));

	// 6. Step back out of range and kick: a clean miss.
	Run.Chung.LeftStick = FVector2D(0.0, -1.0);
	Run.Hold(1.0f);
	Run.Chung.LeftStick = FVector2D::ZeroVector;
	Run.Hold(0.2f);
	Before = Run.ChungScore();
	Run.Flick(Up);
	Run.Settle();
	Run.Stage(TEXT("Side kick from too far: a miss"), Run.ChungScore() == Before && Run.Chung0().LastResult == TEXT("MISS"),
		FString::Printf(TEXT("%s, %s; score stays %d"), *Run.Chung0().LastMove, *Run.Chung0().LastResult, Run.ChungScore()));

	// 7. Close in and score a spinning head kick: 6 points.
	Run.Chung.LeftStick = FVector2D(0.0, 1.0);
	Run.Hold(0.8f);
	Run.Chung.LeftStick = FVector2D::ZeroVector;
	Run.Hold(0.2f);
	Run.Chung.bRB = true;
	Before = Run.ChungScore();
	Run.Chung.RightStick = Down;
	Run.Hold(0.05f);
	Run.Chung.RightStick = Up;
	Run.Hold(0.05f);
	Run.Chung.RightStick = FVector2D::ZeroVector;
	Run.Hold(0.1f);
	Run.Chung.bRB = false;
	Run.Settle();
	Scored(TEXT("Spin side kick to the head (RB, RS Down, Up)"), Before, 6, TEXT("Left"), TEXT("Spin Side"));

	const bool bTotals = Run.ChungScore() == 16 && Sim.Fighters[1].State.Score == 0;
	Run.Stage(TEXT("Final score"), bTotals, FString::Printf(TEXT("Chung %d, Hong %d (expected 16 to 0)"), Run.ChungScore(), Sim.Fighters[1].State.Score));
	return Run.Stages;
}

bool FOpenStanceGreyboxProof::AllPassed(const TArray<FStage>& Stages)
{
	for (const FStage& Stage : Stages)
	{
		if (!Stage.bPassed)
		{
			return false;
		}
	}
	return Stages.Num() > 0;
}

FString FOpenStanceGreyboxProof::Format(const TArray<FStage>& Stages, const FOpenStanceMatchSim& Sim)
{
	FString Text = TEXT("Open Stance M1 greybox proof\n");
	for (const FStage& Stage : Stages)
	{
		Text += FString::Printf(TEXT("[%s] %s: %s\n"), Stage.bPassed ? TEXT("PASS") : TEXT("FAIL"), *Stage.Name, *Stage.Detail);
	}
	Text += TEXT("\nMatch log\n");
	for (const FOpenStanceMatchLogEntry& Entry : Sim.Log)
	{
		Text += FString::Printf(TEXT("%7.2f s  %s  %s\n"), Entry.Time, Entry.Side == EOpenStanceSide::Chung ? TEXT("Chung") : TEXT("Hong "), *Entry.Text);
	}
	return Text;
}
