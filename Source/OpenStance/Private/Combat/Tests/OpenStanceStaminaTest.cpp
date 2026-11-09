#include "Combat/OpenStanceMatchModelSync.h"
#include "Combat/OpenStanceMatchSim.h"
#include "Combat/OpenStanceMoveData.h"
#include "Engine/DataTable.h"
#include "Menu/OpenStanceMatchModel.h"
#include "Misc/AutomationTest.h"

#if WITH_DEV_AUTOMATION_TESTS

namespace
{
	/** A match two metres apart, so techniques miss and only stamina changes. No ceremony. */
	struct FStaminaRig
	{
		FOpenStanceMatchSim Sim;
		FOpenStanceFighterControls Chung;
		FOpenStanceFighterControls Hong;
		const UDataTable* Table = nullptr;

		explicit FStaminaRig(TFunctionRef<void(FOpenStanceMatchSim&)> Configure = [](FOpenStanceMatchSim&) {})
		{
			Table = FOpenStanceMoveData::CreateSeedTable(GetTransientPackage());
			Sim.SetMoveTable(Table);
			Sim.RoundRules.CeremonySeconds = 0.0f;
			Sim.RoundRules.BreakSeconds = 1.0f;
			Configure(Sim);
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

		FOpenStanceFighterSim& Fighter() { return Sim.Fighters[0]; }

		/** Throws a row and plays it out; returns the seconds it spent in Attack Recovery. */
		float ThrowAndRecover(FName Row)
		{
			Sim.ThrowMove(0, Row, EOpenStanceLegSide::Right);
			float Recovery = 0.0f;
			for (int32 Step = 0; Step < 600 && Fighter().State.CombatState != EOpenStanceCombatState::IdleMovement; ++Step)
			{
				Sim.Step(1.0f / 60.0f, Chung, Hong);
				Recovery += Fighter().State.CombatState == EOpenStanceCombatState::AttackRecovery ? 1.0f / 60.0f : 0.0f;
			}
			// Let the rest of the animation play so the next technique is not refused on its cooldown.
			for (int32 Step = 0; Step < 120 && Fighter().Machine.GetCooldownLeft() > 0.0f; ++Step)
			{
				Sim.Step(1.0f / 60.0f, Chung, Hong);
			}
			return Recovery;
		}

		float Cost(const TCHAR* Row) const
		{
			const FOpenStanceMoveRow* Found = Table->FindRow<FOpenStanceMoveRow>(Row, TEXT("StaminaTest"), false);
			return Found ? Found->StaminaCost : -1.0f;
		}
	};
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FOpenStanceStaminaCostsTest, "OpenStance.Stamina.Costs", EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FOpenStanceStaminaCostsTest::RunTest(const FString& Parameters)
{
	// The GDD 8.9 table: punch 3, basic kick 8, dash 12, axe 12, jump kick 14, jump axe 18, spin 20, jump spin hook 26,
	// tornado 30; footwork is free.
	FStaminaRig Rig;
	TestEqual(TEXT("punch"), Rig.Cost(TEXT("Punch_Trunk")), 3.0f);
	TestEqual(TEXT("basic kick"), Rig.Cost(TEXT("Roundhouse_Trunk")), 8.0f);
	TestEqual(TEXT("axe kick"), Rig.Cost(TEXT("Axe_Head")), 12.0f);
	TestEqual(TEXT("jump kick"), Rig.Cost(TEXT("SideKick_Trunk_Jump")), 14.0f);
	TestEqual(TEXT("jump axe kick"), Rig.Cost(TEXT("Axe_Head_Jump")), 18.0f);
	TestEqual(TEXT("spinning kick"), Rig.Cost(TEXT("SpinSide_Trunk")), 20.0f);
	TestEqual(TEXT("jump spin hook kick"), Rig.Cost(TEXT("SpinHook_Trunk_Jump")), 26.0f);
	TestEqual(TEXT("tornado kick"), Rig.Cost(TEXT("Tornado_Trunk")), 30.0f);
	TestEqual(TEXT("dash"), Rig.Sim.Movement.DashStaminaCost, 12.0f);

	Rig.Chung.LeftStick = FVector2D(0.0, -1.0);
	Rig.Run(1.0f);
	Rig.Chung.LeftStick = FVector2D(1.0, 0.0);
	Rig.Run(1.0f);
	TestEqual(TEXT("stepping and circling are free"), Rig.Fighter().State.Stamina, 100.0f);

	// A fake costs its technique's share: all of it by default, or what the setting says.
	{
		FStaminaRig Fakes([](FOpenStanceMatchSim& Sim) { Sim.StaminaRules.FakeCostScale = 0.5f; });
		Fakes.Chung.bLB = true;
		Fakes.Chung.RightStick = FVector2D(0.0, 1.0);
		Fakes.Run(0.05f);
		Fakes.Chung.RightStick = FVector2D::ZeroVector;
		Fakes.Run(0.5f);
		TestEqual(TEXT("a fake at half cost"), Fakes.Fighter().State.Stamina, 96.0f, 0.01f);
	}
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FOpenStanceStaminaRegenTest, "OpenStance.Stamina.Regeneration", EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FOpenStanceStaminaRegenTest::RunTest(const FString& Parameters)
{
	// 15 per second, starting after a full second without spending.
	FStaminaRig Rig;
	Rig.Fighter().State.Stamina = 40.0f; // as if just spent
	Rig.Run(0.9f);
	TestEqual(TEXT("nothing comes back within the first second"), Rig.Fighter().State.Stamina, 40.0f);
	Rig.Run(0.5f);
	TestTrue(TEXT("regeneration has started by 1.4 s"), Rig.Fighter().State.Stamina > 44.0f);
	const float Before = Rig.Fighter().State.Stamina;
	Rig.Run(1.0f);
	TestEqual(TEXT("at 15 per second"), Rig.Fighter().State.Stamina - Before, 15.0f, 0.3f);
	Rig.Run(5.0f);
	TestEqual(TEXT("up to the pool and no further"), Rig.Fighter().State.Stamina, 100.0f);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FOpenStanceStaminaLowTest, "OpenStance.Stamina.LowNeverLocks", EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FOpenStanceStaminaLowTest::RunTest(const FString& Parameters)
{
	// Repeated spinning kicks drain the pool and slow recovery, but every control still works (GDD 8.9, E6).
	FStaminaRig Rig;
	const float FreshRecovery = Rig.ThrowAndRecover(TEXT("SpinSide_Trunk"));
	int32 Kicks = 1;
	while (Kicks < 12 && Rig.Fighter().State.Stamina >= 5.0f)
	{
		Rig.ThrowAndRecover(TEXT("SpinSide_Trunk"));
		++Kicks;
	}
	TestTrue(TEXT("back-to-back spinning kicks run the pool nearly dry"), Rig.Fighter().State.Stamina < 5.0f);
	TestTrue(TEXT("the fighter is on low stamina"), Rig.Fighter().State.IsLowStamina());
	const float TiredRecovery = Rig.ThrowAndRecover(TEXT("SpinSide_Trunk"));
	TestTrue(TEXT("an empty pool still throws a spinning kick"), TiredRecovery > 0.0f);
	TestEqual(TEXT("with a 30% longer recovery"), TiredRecovery, FreshRecovery * 1.3f, 0.05f);
	TestEqual(TEXT("and 20% less impact"), Rig.Fighter().Machine.GetImpactScale(Rig.Fighter().State), 0.8f);

	// Dash, switch sides and step all still work on an empty pool.
	Rig.Fighter().State.Stamina = 0.0f;
	const FVector2D Start = Rig.Fighter().Motion.Position;
	Rig.Chung.bB = true;
	Rig.Chung.LeftStick = FVector2D(0.0, -1.0);
	Rig.Run(0.4f);
	Rig.Chung.bB = false;
	Rig.Chung.LeftStick = FVector2D::ZeroVector;
	TestTrue(TEXT("the dash goes on an empty pool"), (Rig.Fighter().Motion.Position - Start).Size() > 60.0);
	TestEqual(TEXT("and leaves it at zero"), Rig.Fighter().State.Stamina, 0.0f, 0.5f);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FOpenStanceStaminaAttributesTest, "OpenStance.Stamina.Attributes", EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FOpenStanceStaminaAttributesTest::RunTest(const FString& Parameters)
{
	// Career: Stamina 100 is a 10% bigger pool, Recovery 40 a 10% slower regeneration (GDD 5.4).
	FStaminaRig Career([](FOpenStanceMatchSim& Sim)
	{
		Sim.bEqualTerms = false;
		Sim.Fighters[0].StaminaAttribute = 100;
		Sim.Fighters[0].RecoveryAttribute = 40;
	});
	TestEqual(TEXT("Stamina 100: a pool of 110"), Career.Fighter().State.MaxStamina, 110.0f, 0.01f);
	TestEqual(TEXT("starting full"), Career.Fighter().State.Stamina, 110.0f, 0.01f);
	TestEqual(TEXT("Recovery 40: 13.5 per second"), Career.Fighter().RegenPerSecond, 13.5f, 0.01f);
	TestEqual(TEXT("low stamina is still below 25, not a share of the pool"), Career.Fighter().State.LowStaminaThreshold, 25.0f);

	// A round break refills to the fighter's own pool.
	Career.ThrowAndRecover(TEXT("Tornado_Trunk"));
	Career.Sim.SetScore(2, 0);
	Career.Sim.SetClock(0.05f);
	Career.Run(0.1f);
	Career.Sim.SkipBreak();
	Career.Run(0.05f);
	TestEqual(TEXT("round 2 starts at the full 110"), Career.Fighter().State.Stamina, 110.0f, 0.5f);

	// Equal Terms ignores the attributes.
	FStaminaRig Equal([](FOpenStanceMatchSim& Sim)
	{
		Sim.Fighters[0].StaminaAttribute = 100;
		Sim.Fighters[0].RecoveryAttribute = 40;
	});
	TestEqual(TEXT("Equal Terms: a pool of 100"), Equal.Fighter().State.MaxStamina, 100.0f);
	TestEqual(TEXT("and 15 per second"), Equal.Fighter().RegenPerSecond, 15.0f);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FOpenStanceStaminaDefenseTest, "OpenStance.Stamina.DefenseAndHud", EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FOpenStanceStaminaDefenseTest::RunTest(const FString& Parameters)
{
	// Raising Active Defense costs stamina, and releasing it leaves a short opening before a technique can start.
	FStaminaRig Rig;
	Rig.Chung.bLT = true;
	Rig.Run(0.5f);
	TestEqual(TEXT("LT raised the guard"), Rig.Fighter().State.CombatState, EOpenStanceCombatState::ActiveDefense);
	TestEqual(TEXT("for 3 stamina"), Rig.Fighter().State.Stamina, 97.0f, 0.01f);
	Rig.Run(0.5f);
	TestEqual(TEXT("holding it costs nothing more"), Rig.Fighter().State.Stamina, 97.0f, 0.01f);
	Rig.Chung.bLT = false;
	Rig.Run(1.0f / 60.0f);
	TestTrue(TEXT("released: the defense recovery runs"), Rig.Fighter().Machine.GetCooldownLeft() > 0.1f);
	Rig.Sim.ThrowMove(0, TEXT("Roundhouse_Trunk"), EOpenStanceLegSide::Right);
	TestEqual(TEXT("so a kick straight out of the guard is refused"), Rig.Fighter().State.CombatState, EOpenStanceCombatState::IdleMovement);
	Rig.Run(0.25f);
	Rig.Sim.ThrowMove(0, TEXT("Roundhouse_Trunk"), EOpenStanceLegSide::Right);
	TestEqual(TEXT("and starts once it has run"), Rig.Fighter().State.CombatState, EOpenStanceCombatState::AttackStartup);

	// The HUD's bar and low-stamina warning follow the simulation, with the threshold an absolute 25.
	FStaminaRig Hud([](FOpenStanceMatchSim& Sim) { Sim.bEqualTerms = false; Sim.Fighters[0].StaminaAttribute = 100; });
	UOpenStanceMatchModel* Model = NewObject<UOpenStanceMatchModel>(GetTransientPackage());
	FOpenStanceMatchModelSync Sync;
	Sync.Begin(Hud.Sim, *Model, TEXT("A"), TEXT("B"), Hud.Table);
	Hud.Fighter().State.Stamina = 26.0f; // 24% of 110, but not below 25
	Hud.Fighter().PreviousStamina = 26.0f;
	Sync.Update(Hud.Sim, *Model);
	TestEqual(TEXT("the bar shows the share of the pool"), Model->GetStamina(EOpenStanceSide::Chung), 26.0f / 110.0f, 0.001f);
	TestFalse(TEXT("26 is not low"), Model->IsLowStamina(EOpenStanceSide::Chung));
	Hud.Fighter().State.Stamina = 24.0f;
	Sync.Update(Hud.Sim, *Model);
	TestTrue(TEXT("24 is"), Model->IsLowStamina(EOpenStanceSide::Chung));
	return true;
}

#endif
