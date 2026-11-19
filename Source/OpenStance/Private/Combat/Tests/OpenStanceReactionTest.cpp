#include "Combat/OpenStanceMatchSim.h"
#include "Combat/OpenStanceMoveData.h"
#include "Engine/DataTable.h"
#include "Misc/AutomationTest.h"

#if WITH_DEV_AUTOMATION_TESTS

namespace
{
	/** Chung attacks Hong in range, no ceremony, no passivity timer. The move table is the rig's own so a test can edit a row. */
	struct FReactionRig
	{
		FOpenStanceMatchSim Sim;
		FOpenStanceFighterControls Chung;
		FOpenStanceFighterControls Hong;
		UDataTable* Table = nullptr;

		explicit FReactionRig(float Distance = 90.0f)
		{
			Table = FOpenStanceMoveData::CreateSeedTable(GetTransientPackage());
			Sim.SetMoveTable(Table);
			Sim.RoundRules.CeremonySeconds = 0.0f;
			Sim.PenaltyRules.PassivitySeconds = 0.0f;
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

		void Posture(int32 Index, EOpenStanceDPad DPad)
		{
			FOpenStanceFighterControls& Controls = Index == 0 ? Chung : Hong;
			Controls.DPad = DPad;
			Run(1.0f / 60.0f);
			Controls.DPad = EOpenStanceDPad::None;
			Run(0.4f);
		}

		/** Seconds from the throw to the active phase. */
		float StartupOf(const TCHAR* Row)
		{
			Sim.ThrowMove(0, Row, EOpenStanceLegSide::Right);
			float Seconds = 0.0f;
			for (int32 Step = 0; Step < 120 && Sim.Fighters[0].State.CombatState == EOpenStanceCombatState::AttackStartup; ++Step)
			{
				Sim.Step(1.0f / 60.0f, Chung, Hong);
				Seconds += 1.0f / 60.0f;
			}
			Run(2.0f);
			return Seconds;
		}
	};
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FOpenStanceGuardReadinessTest, "OpenStance.Guards.Readiness", EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FOpenStanceGuardReadinessTest::RunTest(const FString& Parameters)
{
	// High is quicker to the head than to the body; Low the other way round (GDD 8.7). Far apart, so nothing lands.
	{
		FReactionRig Rig(300.0f);
		Rig.Posture(0, EOpenStanceDPad::Up);
		const float HighHead = Rig.StartupOf(TEXT("Roundhouse_Head"));
		const float HighBody = Rig.StartupOf(TEXT("Roundhouse_Trunk"));
		Rig.Posture(0, EOpenStanceDPad::Down);
		const float LowHead = Rig.StartupOf(TEXT("Roundhouse_Head"));
		const float LowBody = Rig.StartupOf(TEXT("Roundhouse_Trunk"));
		Rig.Posture(0, EOpenStanceDPad::Right);
		const float MixedBody = Rig.StartupOf(TEXT("Roundhouse_Trunk"));
		TestTrue(TEXT("High throws to the head sooner than Low"), HighHead < LowHead);
		TestTrue(TEXT("Low starts a body kick sooner than High"), LowBody < HighBody);
		TestTrue(TEXT("Mixed is in between for the body"), LowBody < MixedBody && MixedBody < HighBody);
	}

	// Changing guard: Mixed is the quickest to change from, High and Low the slowest, and moving hands cover nothing.
	{
		FReactionRig Rig;
		Rig.Posture(1, EOpenStanceDPad::Right);
		Rig.Hong.DPad = EOpenStanceDPad::Down;
		Rig.Run(1.0f / 60.0f);
		Rig.Hong.DPad = EOpenStanceDPad::None;
		TestEqual(TEXT("from Mixed the change takes 0.15 s"), Rig.Sim.Fighters[1].Motion.GuardTransitionLeft, 0.15f - 1.0f / 60.0f, 0.02f);
		TestEqual(TEXT("mid-change the hands cover nothing"), Rig.Sim.Fighters[1].GetBody().Guard.Num(), 0);
		Rig.Run(0.3f);
		TestTrue(TEXT("then the Low guard's arms are there"), Rig.Sim.Fighters[1].GetBody().Guard.Num() > 0);
		Rig.Hong.DPad = EOpenStanceDPad::Up;
		Rig.Run(1.0f / 60.0f);
		Rig.Hong.DPad = EOpenStanceDPad::None;
		TestEqual(TEXT("from Low it takes 0.25 s"), Rig.Sim.Fighters[1].Motion.GuardTransitionLeft, 0.25f - 1.0f / 60.0f, 0.02f);

		// A body kick that arrives while the hands move lands; the same kick into the settled Low guard is blocked.
		FReactionRig Kick;
		Kick.Posture(1, EOpenStanceDPad::Down);
		Kick.Sim.ThrowMove(0, TEXT("Roundhouse_Trunk"), EOpenStanceLegSide::Right);
		Kick.Run(1.5f);
		TestEqual(TEXT("the settled Low guard blocks it"), Kick.Sim.Fighters[0].State.Score, 0);
		Kick.Sim.ThrowMove(0, TEXT("Roundhouse_Trunk"), EOpenStanceLegSide::Right);
		Kick.Run(0.15f); // the kick's startup, nearly done
		Kick.Hong.DPad = EOpenStanceDPad::Up;
		Kick.Run(1.0f / 60.0f);
		Kick.Hong.DPad = EOpenStanceDPad::Down;
		Kick.Run(1.0f / 60.0f);
		Kick.Hong.DPad = EOpenStanceDPad::None;
		Kick.Run(1.5f);
		TestEqual(TEXT("caught changing guard, it scores"), Kick.Sim.Fighters[0].State.Score, 2);
	}

	// The high block comes up slower from Low, the slowest guard to defend a head kick from.
	{
		FReactionRig Rig;
		Rig.Posture(1, EOpenStanceDPad::Down);
		Rig.Hong.bLT = true;
		Rig.Hong.RightStick = FVector2D(0.0, 1.0);
		Rig.Run(0.1f);
		const int32 Early = Rig.Sim.Fighters[1].GetBody().Guard.Num();
		Rig.Run(0.2f);
		const int32 Raised = Rig.Sim.Fighters[1].GetBody().Guard.Num();
		TestEqual(TEXT("0.1 s in, Low still shows only its own two arms"), Early, 2);
		TestEqual(TEXT("then the high block's four"), Raised, 4);

		FReactionRig Mixed;
		Mixed.Posture(1, EOpenStanceDPad::Right);
		Mixed.Hong.bLT = true;
		Mixed.Hong.RightStick = FVector2D(0.0, 1.0);
		Mixed.Run(0.1f);
		TestEqual(TEXT("from Mixed it is up within 0.1 s"), Mixed.Sim.Fighters[1].GetBody().Guard.Num(), 4);
	}
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FOpenStanceSeverityTest, "OpenStance.Reactions.Severity", EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FOpenStanceSeverityTest::RunTest(const FString& Parameters)
{
	using Sev = EOpenStanceReactionSeverity;
	const FOpenStanceSeverityTuning Tuning;
	const auto Resolve = [&](Sev Authored, float Impact, int32 Composure, bool bTired)
	{
		return FOpenStanceMatchSim::ResolveSeverity(Authored, Impact, 60.0f, Composure, bTired, Tuning);
	};
	TestEqual(TEXT("full impact on a fresh baseline defender: as authored"), Resolve(Sev::Heavy, 60.0f, 70, false), Sev::Heavy);
	TestEqual(TEXT("a tired attacker's 20% weaker kick: a step lighter"), Resolve(Sev::Heavy, 48.0f, 70, false), Sev::Normal);
	TestEqual(TEXT("a tired defender: a step heavier"), Resolve(Sev::Heavy, 60.0f, 70, true), Sev::Knockdown);
	TestEqual(TEXT("both tired: about even"), Resolve(Sev::Heavy, 48.0f, 70, true), Sev::Heavy);
	TestEqual(TEXT("high Composure keeps a tired defender standing"), Resolve(Sev::Heavy, 60.0f, 100, true), Sev::Heavy);
	TestEqual(TEXT("low Composure on a fresh defender: still as authored"), Resolve(Sev::Normal, 60.0f, 40, false), Sev::Normal);
	TestEqual(TEXT("never lighter than Minor"), Resolve(Sev::Minor, 30.0f, 70, false), Sev::Minor);
	TestEqual(TEXT("never heavier than Knockdown"), Resolve(Sev::Knockdown, 60.0f, 40, true), Sev::Knockdown);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FOpenStanceKnockdownPathsTest, "OpenStance.Reactions.KnockdownPaths", EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FOpenStanceKnockdownPathsTest::RunTest(const FString& Parameters)
{
	// A landed hit knocks down a tired defender: the referee counts, no penalty (GDD 8.10).
	{
		FReactionRig Rig;
		Rig.Posture(1, EOpenStanceDPad::Down); // Low: the head is open
		Rig.Sim.Fighters[1].State.Stamina = 10.0f;
		Rig.Sim.Fighters[1].PreviousStamina = 10.0f;
		Rig.Sim.ThrowMove(0, TEXT("Roundhouse_Head"), EOpenStanceLegSide::Right);
		bool bDown = false;
		for (int32 Step = 0; Step < 90 && !bDown; ++Step)
		{
			Rig.Run(1.0f / 60.0f);
			bDown = Rig.Sim.Fighters[1].State.CombatState == EOpenStanceCombatState::KnockedDown;
		}
		TestTrue(TEXT("the tired defender goes down"), bDown);
		TestEqual(TEXT("knocked down by the hit"), Rig.Sim.Fighters[1].Machine.GetKnockdownCause(), EOpenStanceKnockdownCause::Hit);
		TestEqual(TEXT("which is no penalty"), Rig.Sim.Fighters[1].MatchGamJeom, 0);
		TestEqual(TEXT("and the head kick scored"), Rig.Sim.Fighters[0].State.Score, 3);
	}

	// A fresh defender takes the same kick standing: Heavy, a stagger.
	{
		FReactionRig Rig;
		Rig.Posture(1, EOpenStanceDPad::Down);
		Rig.Sim.ThrowMove(0, TEXT("Roundhouse_Head"), EOpenStanceLegSide::Right);
		bool bStaggered = false;
		for (int32 Step = 0; Step < 90; ++Step)
		{
			Rig.Run(1.0f / 60.0f);
			bStaggered |= Rig.Sim.Fighters[1].State.CombatState == EOpenStanceCombatState::Staggered;
		}
		TestTrue(TEXT("a fresh defender is staggered, not dropped"), bStaggered);
	}

	// A failed landing with no hit is a fall: the Falling gam-jeom (GDD 8.4).
	{
		FReactionRig Rig(300.0f);
		Rig.Table->FindRow<FOpenStanceMoveRow>(TEXT("SpinSide_Trunk"), TEXT("Test"))->SelfFallChance = 1.0f;
		Rig.Sim.ThrowMove(0, TEXT("SpinSide_Trunk"), EOpenStanceLegSide::Right);
		Rig.Run(1.5f);
		TestEqual(TEXT("the kicker fell on its own"), Rig.Sim.Fighters[0].Machine.GetKnockdownCause(), EOpenStanceKnockdownCause::FailedLanding);
		TestEqual(TEXT("which is the Falling gam-jeom"), Rig.Sim.Fighters[0].PenaltyReasons.Contains(TEXT("Falling")), true);
	}
	return true;
}

#endif
