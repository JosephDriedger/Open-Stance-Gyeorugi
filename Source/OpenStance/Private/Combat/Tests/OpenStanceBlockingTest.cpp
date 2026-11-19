#include "Combat/OpenStanceMatchModelSync.h"
#include "Combat/OpenStanceMatchSim.h"
#include "Combat/OpenStanceMoveData.h"
#include "Menu/OpenStanceMatchModel.h"
#include "Misc/AutomationTest.h"

#if WITH_DEV_AUTOMATION_TESTS

namespace
{
	/** Chung attacks, Hong defends with whatever its controls hold. In range, no ceremony, no passivity timer. */
	struct FBlockRig
	{
		FOpenStanceMatchSim Sim;
		FOpenStanceFighterControls Chung;
		FOpenStanceFighterControls Hong;

		FBlockRig()
		{
			Sim.SetMoveTable(FOpenStanceMoveData::CreateSeedTable(GetTransientPackage()));
			Sim.RoundRules.CeremonySeconds = 0.0f;
			Sim.PenaltyRules.PassivitySeconds = 0.0f;
			Sim.StartMatch(90.0f);
		}

		void Run(float Seconds)
		{
			const int32 Count = FMath::Max(1, FMath::RoundToInt(Seconds * 60.0f));
			for (int32 Index = 0; Index < Count; ++Index)
			{
				Sim.Step(1.0f / 60.0f, Chung, Hong);
			}
		}

		/** Chung throws Row and the exchange plays out; returns the points it scored. */
		int32 Throw(const TCHAR* Row)
		{
			const int32 Before = Sim.Fighters[0].State.Score;
			Sim.ThrowMove(0, Row, EOpenStanceLegSide::Right);
			Run(1.6f);
			return Sim.Fighters[0].State.Score - Before;
		}

		/** Hong picks a guard posture with the D-pad: Up high, Left cross, Right mixed, Down low (GDD 7.3). */
		void Posture(EOpenStanceDPad DPad)
		{
			Hong.DPad = DPad;
			Run(0.05f);
			Hong.DPad = EOpenStanceDPad::None;
			Run(0.3f);
		}

		/** Puts Hong into a guard: LT, then the stick, held long enough to settle. */
		void Guard(FVector2D Stick)
		{
			Hong.bLT = true;
			Hong.RightStick = Stick;
			Run(0.1f);
		}

		EOpenStanceContactType LastContact() const
		{
			return Sim.Contacts.Num() ? Sim.Contacts.Last().Type : EOpenStanceContactType::Score;
		}
	};
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FOpenStanceBlockingGuardsTest, "OpenStance.Defense.Blocks", EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FOpenStanceBlockingGuardsTest::RunTest(const FString& Parameters)
{
	// Natural blocking from the guard posture alone, no LT. Chung kicks with the right leg, so a roundhouse swings in on
	// Hong's left, Hong's rear side in Right Lead. The middle is open in every posture, so straight kicks get through.
	{
		FBlockRig Rig;
		TestEqual(TEXT("High: the hands beside the head"), Rig.Sim.Fighters[1].State.Guard, EOpenStanceGuard::High);
		TestEqual(TEXT("stop the roundhouse to the head"), Rig.Throw(TEXT("Roundhouse_Head")), 0);
		TestEqual(TEXT("as a block"), Rig.LastContact(), EOpenStanceContactType::Blocked);
		TestEqual(TEXT("but leave the body open"), Rig.Throw(TEXT("Roundhouse_Trunk")), 2);
		TestEqual(TEXT("and the punch"), Rig.Throw(TEXT("Punch_Trunk")), 1);
		TestEqual(TEXT("and the middle: a straight spinning kick to the face"), Rig.Throw(TEXT("SpinSide_Head")), 6);
	}
	{
		FBlockRig Rig;
		Rig.Posture(EOpenStanceDPad::Down);
		TestEqual(TEXT("Low: the forearms at the flanks"), Rig.Sim.Fighters[1].State.Guard, EOpenStanceGuard::Low);
		TestEqual(TEXT("stop the roundhouse to the body"), Rig.Throw(TEXT("Roundhouse_Trunk")), 0);
		TestEqual(TEXT("not the straight side kick"), Rig.Throw(TEXT("SideKick_Trunk")), 2);
		TestEqual(TEXT("and not the head kick"), Rig.Throw(TEXT("Roundhouse_Head")), 3);
	}
	{
		FBlockRig Rig;
		Rig.Posture(EOpenStanceDPad::Right);
		TestEqual(TEXT("Mixed"), Rig.Sim.Fighters[1].State.Guard, EOpenStanceGuard::Mixed);
		TestEqual(TEXT("the rear hand high stops the head kick on the rear side"), Rig.Throw(TEXT("Roundhouse_Head")), 0);
		TestEqual(TEXT("and the lead hand low leaves the rear body open"), Rig.Throw(TEXT("Roundhouse_Trunk")), 2);
	}
	{
		FBlockRig Rig;
		Rig.Posture(EOpenStanceDPad::Left);
		TestEqual(TEXT("Cross"), Rig.Sim.Fighters[1].State.Guard, EOpenStanceGuard::Cross);
		TestEqual(TEXT("the rear arm across the body stops the straight side kick"), Rig.Throw(TEXT("SideKick_Trunk")), 0);
		TestEqual(TEXT("and the punch"), Rig.Throw(TEXT("Punch_Trunk")), 0);
	}

	// Attacking drops the guard: a fighter in a technique has no arms in the way.
	{
		FBlockRig Rig;
		Rig.Posture(EOpenStanceDPad::Down);
		TestTrue(TEXT("in guard the arms are there"), Rig.Sim.Fighters[1].GetBody().Guard.Num() > 0);
		Rig.Sim.ThrowMove(1, TEXT("SideKick_Trunk"), EOpenStanceLegSide::Right);
		Rig.Run(1.0f / 60.0f);
		TestEqual(TEXT("mid-technique they are not"), Rig.Sim.Fighters[1].GetBody().Guard.Num(), 0);
	}

	// LT alone: the closed guard stops punches and body kicks; the head stays open.
	{
		FBlockRig Rig;
		Rig.Guard(FVector2D::ZeroVector);
		TestEqual(TEXT("LT raises Active Defense"), Rig.Sim.Fighters[1].State.CombatState, EOpenStanceCombatState::ActiveDefense);
		TestEqual(TEXT("the closed guard blocks the body kick"), Rig.Throw(TEXT("Roundhouse_Trunk")), 0);
		TestEqual(TEXT("as a block"), Rig.LastContact(), EOpenStanceContactType::Blocked);
		TestEqual(TEXT("and the defender is not hurt"), Rig.Sim.Fighters[1].State.CombatState, EOpenStanceCombatState::ActiveDefense);
		TestEqual(TEXT("it blocks the punch"), Rig.Throw(TEXT("Punch_Trunk")), 0);
		TestEqual(TEXT("the side kick"), Rig.Throw(TEXT("SideKick_Trunk")), 0);
		TestEqual(TEXT("but not the head kick"), Rig.Throw(TEXT("Roundhouse_Head")), 3);
		TestEqual(TEXT("three blocks counted"), Rig.Sim.Fighters[1].Blocks, 3);
		TestEqual(TEXT("and no protector hits for the attacker"), Rig.Sim.Fighters[0].Round.ProtectorHits, 1);
	}

	// LT + RS Up: the high block stops head kicks; the trunk is open.
	{
		FBlockRig Rig;
		Rig.Guard(FVector2D(0.0, 1.0));
		TestEqual(TEXT("the high block stops the head kick"), Rig.Throw(TEXT("Roundhouse_Head")), 0);
		TestEqual(TEXT("as a block"), Rig.LastContact(), EOpenStanceContactType::Blocked);
		TestEqual(TEXT("and the spinning head kick"), Rig.Throw(TEXT("SpinSide_Head")), 0);
		TestEqual(TEXT("but the body kick gets under it"), Rig.Throw(TEXT("Roundhouse_Trunk")), 2);
	}

	// LT + RS Down: the leg check stops body kicks, not punches, and the raised leg is watched for leg lifting.
	{
		FBlockRig Rig;
		Rig.Guard(FVector2D(0.0, -1.0));
		TestTrue(TEXT("the leg is up"), Rig.Sim.Fighters[1].Motion.bLegRaised);
		TestEqual(TEXT("the leg check stops the straight body kick"), Rig.Throw(TEXT("SideKick_Trunk")), 0);
		TestEqual(TEXT("but not the punch"), Rig.Throw(TEXT("Punch_Trunk")), 1);
		// The punch knocked Hong out of defense, so the leg came down and the 3 s count starts again from there.
		Rig.Run(3.2f);
		TestEqual(TEXT("held past 3 s it is leg lifting"), Rig.Sim.Fighters[1].PenaltyReasons.Contains(TEXT("Leg lifting")), true);
		Rig.Hong.RightStick = FVector2D::ZeroVector;
		Rig.Run(0.1f);
		TestFalse(TEXT("back to the closed guard, the leg comes down"), Rig.Sim.Fighters[1].Motion.bLegRaised);
	}
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FOpenStanceBlockingSwayTest, "OpenStance.Defense.SwayAndHud", EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FOpenStanceBlockingSwayTest::RunTest(const FString& Parameters)
{
	// A sway in time evades anything, head or body.
	{
		FBlockRig Rig;
		Rig.Guard(FVector2D::ZeroVector);
		const FVector2D Before = Rig.Sim.Fighters[1].Motion.Position;
		Rig.Hong.RightStick = FVector2D(1.0, 0.0);
		Rig.Sim.ThrowMove(0, TEXT("Roundhouse_Head"), EOpenStanceLegSide::Right);
		Rig.Run(1.6f);
		TestEqual(TEXT("the sway evades the head kick"), Rig.Sim.Fighters[0].State.Score, 0);
		TestTrue(TEXT("by stepping off the line"), (Rig.Sim.Fighters[1].Motion.Position - Before).Size() > 20.0);
	}

	// Swayed too early: standing off line with no guard up, the kick lands or misses, but is never evaded.
	{
		FBlockRig Rig;
		Rig.Guard(FVector2D(1.0, 0.0));
		Rig.Run(1.0f);
		const int32 ContactsBefore = Rig.Sim.Contacts.Num();
		Rig.Throw(TEXT("Roundhouse_Head"));
		bool bEvaded = false;
		for (int32 Index = ContactsBefore; Index < Rig.Sim.Contacts.Num(); ++Index)
		{
			bEvaded |= Rig.Sim.Contacts[Index].Type == EOpenStanceContactType::Evaded;
		}
		TestFalse(TEXT("a sway held too long evades nothing"), bEvaded);
	}

	// os.AIMode block holds LT alone: the body kick is blocked and the HUD says so.
	{
		FBlockRig Rig;
		UOpenStanceMatchModel* Model = NewObject<UOpenStanceMatchModel>(GetTransientPackage());
		FOpenStanceMatchModelSync Sync;
		Sync.Begin(Rig.Sim, *Model, TEXT("A"), TEXT("B"), nullptr);
		Rig.Guard(FVector2D::ZeroVector);
		Rig.Sim.ThrowMove(0, TEXT("Roundhouse_Trunk"), EOpenStanceLegSide::Right);
		for (int32 Step = 0; Step < 60; ++Step)
		{
			Rig.Run(1.0f / 60.0f);
			Sync.Update(Rig.Sim, *Model);
			if (Model->GetCallTerm() == TEXT("Blocked"))
			{
				break;
			}
		}
		TestEqual(TEXT("the HUD calls the block"), Model->GetCallTerm(), FString(TEXT("Blocked")));
		TestEqual(TEXT("and shows no points"), Model->GetScore(EOpenStanceSide::Chung), 0);
	}
	return true;
}

#endif
