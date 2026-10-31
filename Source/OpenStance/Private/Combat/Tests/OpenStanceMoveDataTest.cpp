#include "Combat/OpenStanceFighterState.h"
#include "Combat/OpenStanceMoveData.h"
#include "Engine/DataTable.h"
#include "Misc/AutomationTest.h"

#if WITH_DEV_AUTOMATION_TESTS

namespace
{
	int32 CountErrors(const TArray<FOpenStanceMoveIssue>& Issues)
	{
		int32 Count = 0;
		for (const FOpenStanceMoveIssue& Issue : Issues)
		{
			Count += Issue.bError ? 1 : 0;
		}
		return Count;
	}

	bool HasMessage(const TArray<FOpenStanceMoveIssue>& Issues, FName Row, const TCHAR* Fragment)
	{
		for (const FOpenStanceMoveIssue& Issue : Issues)
		{
			if (Issue.RowName == Row && Issue.Message.Contains(Fragment))
			{
				return true;
			}
		}
		return false;
	}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FOpenStanceMoveDataSeedTest, "OpenStance.MoveData.Seed", EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FOpenStanceMoveDataSeedTest::RunTest(const FString& Parameters)
{
	const TMap<FName, FOpenStanceMoveRow> Rows = FOpenStanceMoveData::BuildSeedRows();
	TestEqual(TEXT("six seed rows: side, roundhouse and spin side, each to trunk and head"), Rows.Num(), 6);

	TArray<FOpenStanceMoveIssue> Issues = FOpenStanceMoveData::Validate(Rows, FOpenStanceMoveCheckOptions());
	TestEqual(TEXT("the seed passes with placeholder animation"), CountErrors(Issues), 0);

	FOpenStanceMoveCheckOptions Production;
	Production.bRequireProductionAnimation = true;
	Issues = FOpenStanceMoveData::Validate(Rows, Production);
	TestEqual(TEXT("every seed row fails a production check while it is on placeholders"), CountErrors(Issues), Rows.Num());

	TestEqual(TEXT("side kick trunk"), Rows[TEXT("SideKick_Trunk")].Points, 2);
	TestEqual(TEXT("side kick head"), Rows[TEXT("SideKick_Head")].Points, 3);
	TestEqual(TEXT("spin side trunk"), Rows[TEXT("SpinSide_Trunk")].Points, 4);
	TestEqual(TEXT("spin side head"), Rows[TEXT("SpinSide_Head")].Points, 6);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FOpenStanceMoveDataPointsTest, "OpenStance.MoveData.Points", EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FOpenStanceMoveDataPointsTest::RunTest(const FString& Parameters)
{
	using T = EOpenStanceTechnique;
	using G = EOpenStanceTarget;
	TestEqual(TEXT("punch"), FOpenStanceMoveData::PointsFor(T::Punch, G::Trunk, false), 1);
	TestEqual(TEXT("punch to the head cannot score"), FOpenStanceMoveData::PointsFor(T::Punch, G::Head, false), 0);
	TestEqual(TEXT("body kick"), FOpenStanceMoveData::PointsFor(T::Roundhouse, G::Trunk, false), 2);
	TestEqual(TEXT("head kick"), FOpenStanceMoveData::PointsFor(T::Roundhouse, G::Head, false), 3);
	TestEqual(TEXT("spinning body kick"), FOpenStanceMoveData::PointsFor(T::SpinHook, G::Trunk, true), 4);
	TestEqual(TEXT("spinning head kick"), FOpenStanceMoveData::PointsFor(T::SpinHook, G::Head, true), 6);
	TestTrue(TEXT("tornado is spinning"), FOpenStanceMoveData::IsSpinning(T::Tornado));
	TestFalse(TEXT("axe is not"), FOpenStanceMoveData::IsSpinning(T::Axe));
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FOpenStanceMoveDataValidateTest, "OpenStance.MoveData.Validate", EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FOpenStanceMoveDataValidateTest::RunTest(const FString& Parameters)
{
	const FOpenStanceMoveCheckOptions Options;
	TMap<FName, FOpenStanceMoveRow> Rows = FOpenStanceMoveData::BuildSeedRows();

	// Missing animation.
	{
		TMap<FName, FOpenStanceMoveRow> Bad = Rows;
		Bad[TEXT("SideKick_Trunk")].PlaceholderMontage.Reset();
		TestTrue(TEXT("a row with nothing to play is reported"), HasMessage(FOpenStanceMoveData::Validate(Bad, Options), TEXT("SideKick_Trunk"), TEXT("No animation")));
	}

	// Impossible timing.
	{
		TMap<FName, FOpenStanceMoveRow> Bad = Rows;
		Bad[TEXT("Roundhouse_Trunk")].ActiveSeconds = 0.0f;
		Bad[TEXT("Roundhouse_Head")].RecoverySeconds = -0.1f;
		Bad[TEXT("SpinSide_Trunk")].CancelWindowSeconds = 5.0f;
		const TArray<FOpenStanceMoveIssue> Issues = FOpenStanceMoveData::Validate(Bad, Options);
		TestTrue(TEXT("zero active phase"), HasMessage(Issues, TEXT("Roundhouse_Trunk"), TEXT("ActiveSeconds")));
		TestTrue(TEXT("negative recovery"), HasMessage(Issues, TEXT("Roundhouse_Head"), TEXT("RecoverySeconds")));
		TestTrue(TEXT("cancel window after recovery"), HasMessage(Issues, TEXT("SpinSide_Trunk"), TEXT("CancelWindowSeconds")));
	}

	// Score and target.
	{
		TMap<FName, FOpenStanceMoveRow> Bad = Rows;
		Bad[TEXT("SideKick_Head")].Points = 2;
		FOpenStanceMoveRow& Punch = Bad.Add(TEXT("Punch_Head"), Rows[TEXT("SideKick_Trunk")]);
		Punch.Technique = EOpenStanceTechnique::Punch;
		Punch.Target = EOpenStanceTarget::Head;
		Punch.Limb = EOpenStanceStrikeLimb::Glove;
		Punch.Points = 1;
		const TArray<FOpenStanceMoveIssue> Issues = FOpenStanceMoveData::Validate(Bad, Options);
		TestTrue(TEXT("head kick worth the body value"), HasMessage(Issues, TEXT("SideKick_Head"), TEXT("scoring table")));
		TestTrue(TEXT("punch to the head"), HasMessage(Issues, TEXT("Punch_Head"), TEXT("illegal")));
	}

	// Two rows for one gesture.
	{
		TMap<FName, FOpenStanceMoveRow> Bad = Rows;
		Bad.Add(TEXT("SideKick_Trunk_Copy"), Rows[TEXT("SideKick_Trunk")]);
		const TArray<FOpenStanceMoveIssue> Issues = FOpenStanceMoveData::Validate(Bad, Options);
		TestTrue(TEXT("duplicate gesture key"), CountErrors(Issues) > 0);
	}
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FOpenStanceMoveDataMontageTest, "OpenStance.MoveData.Montage", EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FOpenStanceMoveDataMontageTest::RunTest(const FString& Parameters)
{
	FOpenStanceMoveRow Row = FOpenStanceMoveData::BuildSeedRows()[TEXT("SideKick_Trunk")];
	TestEqual(TEXT("placeholder stands in for either leg"), Row.ResolveMontage(EOpenStanceLegSide::Left, true).ToSoftObjectPath(), Row.PlaceholderMontage.ToSoftObjectPath());
	TestTrue(TEXT("no placeholder when it is not allowed"), Row.ResolveMontage(EOpenStanceLegSide::Left, false).IsNull());

	Row.RightLegMontage = TSoftObjectPtr<UAnimMontage>(FSoftObjectPath(TEXT("/Game/Test/AM_Right.AM_Right")));
	TestEqual(TEXT("the right-leg montage wins for the right leg"), Row.ResolveMontage(EOpenStanceLegSide::Right, true).ToSoftObjectPath(), Row.RightLegMontage.ToSoftObjectPath());
	TestEqual(TEXT("the left leg still falls back"), Row.ResolveMontage(EOpenStanceLegSide::Left, true).ToSoftObjectPath(), Row.PlaceholderMontage.ToSoftObjectPath());
	TestFalse(TEXT("one leg is not production animation"), Row.HasProductionAnimation());
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FOpenStanceMoveDataCsvTest, "OpenStance.MoveData.Csv", EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FOpenStanceMoveDataCsvTest::RunTest(const FString& Parameters)
{
	UDataTable* Source = FOpenStanceMoveData::CreateSeedTable(GetTransientPackage());
	const FString Csv = FOpenStanceMoveData::ExportCsv(*Source);
	TestTrue(TEXT("the export has a header and a row per move"), Csv.Contains(TEXT("SideKick_Trunk")) && Csv.Contains(TEXT("StartupSeconds")));

	UDataTable* Copy = NewObject<UDataTable>(GetTransientPackage());
	const TArray<FString> Problems = FOpenStanceMoveData::ImportCsv(*Copy, Csv);
	TestEqual(TEXT("import reports no problems"), Problems.Num(), 0);
	TestEqual(TEXT("same row count"), Copy->GetRowMap().Num(), Source->GetRowMap().Num());

	FName RowName;
	const FOpenStanceMoveRow* Spin = FOpenStanceMoveData::Find(*Copy, EOpenStanceTechnique::SpinSide, EOpenStanceTarget::Head, false, &RowName);
	if (TestNotNull(TEXT("find the spin side head row"), Spin))
	{
		TestEqual(TEXT("row name survives"), RowName, FName(TEXT("SpinSide_Head")));
		TestEqual(TEXT("points survive"), Spin->Points, 6);
		TestEqual(TEXT("timing survives"), Spin->StartupSeconds, 0.43f);
		TestEqual(TEXT("placeholder path survives"), Spin->PlaceholderMontage.ToSoftObjectPath(), FOpenStanceMoveData::BuildSeedRows()[TEXT("SpinSide_Head")].PlaceholderMontage.ToSoftObjectPath());
	}
	TestNull(TEXT("an unmapped technique has no row"), FOpenStanceMoveData::Find(*Copy, EOpenStanceTechnique::Tornado, EOpenStanceTarget::Head, false));
	TestEqual(TEXT("the copy still validates"), CountErrors(FOpenStanceMoveData::Validate(*Copy, FOpenStanceMoveCheckOptions())), 0);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FOpenStanceFighterStateTest, "OpenStance.FighterState.Legs", EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FOpenStanceFighterStateTest::RunTest(const FString& Parameters)
{
	FOpenStanceFighterState State;
	State.Stance = EOpenStanceStance::RightLead;
	TestEqual(TEXT("right lead: right leg is forward"), State.GetLeadLeg(), EOpenStanceLegSide::Right);
	TestEqual(TEXT("right lead: left leg is back"), State.GetBackLeg(), EOpenStanceLegSide::Left);
	TestEqual(TEXT("no RT throws with the lead leg"), State.GetThrowingLeg(), EOpenStanceLegSide::Right);
	State.bBackLegHeld = true;
	TestEqual(TEXT("RT throws with the back leg"), State.GetThrowingLeg(), EOpenStanceLegSide::Left);
	State.Stance = EOpenStanceStance::LeftLead;
	TestEqual(TEXT("after switching sides the same RT kick uses the other leg"), State.GetThrowingLeg(), EOpenStanceLegSide::Right);
	TestFalse(TEXT("a fresh fighter is not attacking"), State.IsAttacking());
	State.CombatState = EOpenStanceCombatState::AttackRecovery;
	TestTrue(TEXT("recovery counts as attacking"), State.IsAttacking());
	State.Stamina = 24.0f;
	TestTrue(TEXT("below 25 is low stamina"), State.IsLowStamina());
	return true;
}

#endif
