#include "Combat/OpenStanceMoveData.h"

#include "Animation/AnimMontage.h"
#include "Engine/DataTable.h"
#include "DataTableUtils.h"
#include "UObject/UnrealType.h"

namespace
{
	/** Placeholder montages live beside the captured ones and keep the AM_ prefix (GDD 16.5). */
	FSoftObjectPath PlaceholderPath(const TCHAR* Name)
	{
		return FSoftObjectPath(FString::Printf(TEXT("/Game/Animation/Moves/Placeholder/AM_Placeholder_%s.AM_Placeholder_%s"), Name, Name));
	}

	/** How long a placeholder animation keeps playing after the recovery ends: the cooldown before the next technique. */
	constexpr float PlaceholderAnimationTailSeconds = 0.15f;

	void AddIssue(TArray<FOpenStanceMoveIssue>& Issues, FName RowName, const FString& Message, bool bError = true)
	{
		FOpenStanceMoveIssue& Issue = Issues.AddDefaulted_GetRef();
		Issue.RowName = RowName;
		Issue.Message = Message;
		Issue.bError = bError;
	}

	FOpenStanceMoveRow MakeRow(
		const TCHAR* Display, EOpenStanceTechnique Technique, const TCHAR* Notation, EOpenStanceTarget Target,
		float Startup, float Active, float Recovery, float Cost, float Reach, float Impact,
		EOpenStanceReactionSeverity Reaction, float SelfFall, const TCHAR* PlaceholderName)
	{
		FOpenStanceMoveRow Row;
		Row.DisplayName = Display;
		Row.Technique = Technique;
		Row.GestureNotation = Notation;
		Row.Target = Target;
		Row.bSpinning = FOpenStanceMoveData::IsSpinning(Technique);
		Row.Limb = Technique == EOpenStanceTechnique::Punch ? EOpenStanceStrikeLimb::Glove : EOpenStanceStrikeLimb::FootGuard;
		Row.PlaceholderMontage = TSoftObjectPtr<UAnimMontage>(PlaceholderPath(PlaceholderName));
		Row.StartupSeconds = Startup;
		Row.ActiveSeconds = Active;
		Row.RecoverySeconds = Recovery;
		// Placeholder animations play a little past the phases; the real montage length replaces this with the mocap.
		Row.AnimationSeconds = Startup + Active + Recovery + PlaceholderAnimationTailSeconds;
		Row.StaminaCost = Cost;
		Row.Points = FOpenStanceMoveData::PointsFor(Technique, Target, Row.bSpinning);
		Row.ReachCm = Reach;
		Row.Impact = Impact;
		Row.Reaction = Reaction;
		Row.SelfFallChance = SelfFall;
		return Row;
	}
}

TSoftObjectPtr<UAnimMontage> FOpenStanceMoveRow::ResolveMontage(EOpenStanceLegSide ThrowingLeg, bool bAllowPlaceholder) const
{
	const TSoftObjectPtr<UAnimMontage>& ForLeg = ThrowingLeg == EOpenStanceLegSide::Left ? LeftLegMontage : RightLegMontage;
	if (!ForLeg.IsNull())
	{
		return ForLeg;
	}
	return bAllowPlaceholder ? PlaceholderMontage : TSoftObjectPtr<UAnimMontage>();
}

bool FOpenStanceMoveRow::HasProductionAnimation() const
{
	return !LeftLegMontage.IsNull() && !RightLegMontage.IsNull();
}

int32 FOpenStanceMoveData::PointsFor(EOpenStanceTechnique Technique, EOpenStanceTarget Target, bool bSpinning)
{
	if (Technique == EOpenStanceTechnique::None)
	{
		return 0;
	}
	if (Technique == EOpenStanceTechnique::Punch)
	{
		// Punches only score to the trunk protector; a punch to the head is a foul (GDD 8.3, 9.3).
		return Target == EOpenStanceTarget::Trunk ? 1 : 0;
	}
	if (Target == EOpenStanceTarget::Head)
	{
		return bSpinning ? 6 : 3;
	}
	return bSpinning ? 4 : 2;
}

bool FOpenStanceMoveData::IsSpinning(EOpenStanceTechnique Technique)
{
	return Technique == EOpenStanceTechnique::SpinSide
		|| Technique == EOpenStanceTechnique::SpinHook
		|| Technique == EOpenStanceTechnique::Tornado;
}

TArray<FOpenStanceMoveIssue> FOpenStanceMoveData::Validate(const TMap<FName, FOpenStanceMoveRow>& Rows, const FOpenStanceMoveCheckOptions& Options)
{
	TArray<FOpenStanceMoveIssue> Issues;
	TMap<uint32, FName> Keys;

	for (const TPair<FName, FOpenStanceMoveRow>& Pair : Rows)
	{
		const FName Name = Pair.Key;
		const FOpenStanceMoveRow& Row = Pair.Value;

		if (Row.Technique == EOpenStanceTechnique::None)
		{
			AddIssue(Issues, Name, TEXT("Technique is None."));
			continue;
		}

		const uint32 Key = (uint32(Row.Technique) << 2) | (uint32(Row.Target) << 1) | (Row.bJump ? 1u : 0u);
		if (const FName* Other = Keys.Find(Key))
		{
			AddIssue(Issues, Name, FString::Printf(TEXT("Same technique, target and jump as %s; the recognizer could not tell them apart."), *Other->ToString()));
		}
		else
		{
			Keys.Add(Key, Name);
		}

		// Timing: every phase needs a positive length, and a cancel window has to open inside the recovery.
		if (!FMath::IsFinite(Row.StartupSeconds) || Row.StartupSeconds <= 0.0f)
		{
			AddIssue(Issues, Name, TEXT("StartupSeconds must be greater than 0."));
		}
		if (!FMath::IsFinite(Row.ActiveSeconds) || Row.ActiveSeconds <= 0.0f)
		{
			AddIssue(Issues, Name, TEXT("ActiveSeconds must be greater than 0."));
		}
		if (!FMath::IsFinite(Row.RecoverySeconds) || Row.RecoverySeconds <= 0.0f)
		{
			AddIssue(Issues, Name, TEXT("RecoverySeconds must be greater than 0; a technique with no recovery cannot be punished."));
		}
		if (Row.CancelWindowSeconds >= 0.0f && Row.CancelWindowSeconds > Row.RecoverySeconds)
		{
			AddIssue(Issues, Name, TEXT("CancelWindowSeconds is later than the end of recovery."));
		}

		if (!FMath::IsFinite(Row.AnimationSeconds) || Row.AnimationSeconds < 0.0f)
		{
			AddIssue(Issues, Name, TEXT("AnimationSeconds cannot be negative."));
		}

		if (Row.StaminaCost < 0.0f)
		{
			AddIssue(Issues, Name, TEXT("StaminaCost cannot be negative."));
		}
		if (Row.ReachCm <= 0.0f)
		{
			AddIssue(Issues, Name, TEXT("ReachCm must be greater than 0."));
		}
		if (Row.Impact < 0.0f)
		{
			AddIssue(Issues, Name, TEXT("Impact cannot be negative."));
		}
		if (Row.SelfFallChance < 0.0f || Row.SelfFallChance > 1.0f)
		{
			AddIssue(Issues, Name, TEXT("SelfFallChance must be between 0 and 1."));
		}

		// Score and target: a punch never reaches the head, and the point value follows the PSS table.
		const bool bPunch = Row.Technique == EOpenStanceTechnique::Punch;
		if (bPunch && Row.Target == EOpenStanceTarget::Head)
		{
			AddIssue(Issues, Name, TEXT("A punch to the head is illegal and cannot score."));
		}
		else if (Row.Points != PointsFor(Row.Technique, Row.Target, Row.bSpinning))
		{
			AddIssue(Issues, Name, FString::Printf(TEXT("Points is %d but the scoring table gives %d for this technique and target."),
				Row.Points, PointsFor(Row.Technique, Row.Target, Row.bSpinning)));
		}
		if (Row.bSpinning != IsSpinning(Row.Technique))
		{
			AddIssue(Issues, Name, TEXT("bSpinning does not match the technique."));
		}
		if (bPunch != (Row.Limb == EOpenStanceStrikeLimb::Glove))
		{
			AddIssue(Issues, Name, TEXT("Punches trace the glove and kicks trace the foot guard."));
		}

		// Animation: a row with nothing to play cannot run at all.
		const bool bHasPlaceholder = !Row.PlaceholderMontage.IsNull();
		if (!bHasPlaceholder && !Row.HasProductionAnimation())
		{
			AddIssue(Issues, Name, TEXT("No animation: set a placeholder montage or both legs' montages."));
		}
		else if (!Row.HasProductionAnimation())
		{
			AddIssue(Issues, Name, TEXT("Still on placeholder animation."), Options.bRequireProductionAnimation);
		}

		if (Options.bCheckAssetsExist)
		{
			for (const TSoftObjectPtr<UAnimMontage>* Montage : { &Row.LeftLegMontage, &Row.RightLegMontage, &Row.PlaceholderMontage })
			{
				if (!Montage->IsNull() && !Montage->LoadSynchronous())
				{
					AddIssue(Issues, Name, FString::Printf(TEXT("Montage %s does not exist."), *Montage->ToString()));
				}
			}
		}
	}
	return Issues;
}

TArray<FOpenStanceMoveIssue> FOpenStanceMoveData::Validate(const UDataTable& Table, const FOpenStanceMoveCheckOptions& Options)
{
	TMap<FName, FOpenStanceMoveRow> Rows;
	for (const TPair<FName, uint8*>& Pair : Table.GetRowMap())
	{
		Rows.Add(Pair.Key, *reinterpret_cast<const FOpenStanceMoveRow*>(Pair.Value));
	}
	return Validate(Rows, Options);
}

TMap<FName, FOpenStanceMoveRow> FOpenStanceMoveData::BuildSeedRows()
{
	using T = EOpenStanceTechnique;
	using G = EOpenStanceTarget;
	using R = EOpenStanceReactionSeverity;

	// Starting values for the Milestone 1 greybox, tuned in playtests (GDD 8.9, 8.10). Costs are the GDD's
	// basic-kick and spinning tiers; head rows are a little slower to start and hit harder.
	TMap<FName, FOpenStanceMoveRow> Rows;
	Rows.Add(TEXT("SideKick_Trunk"), MakeRow(TEXT("Side Kick"), T::SideKick, TEXT("RS Up"), G::Trunk, 0.25f, 0.10f, 0.45f, 8.0f, 105.0f, 60.0f, R::Normal, 0.0f, TEXT("SideKick")));
	Rows.Add(TEXT("SideKick_Head"), MakeRow(TEXT("Side Kick (Head)"), T::SideKick, TEXT("RB + RS Up"), G::Head, 0.28f, 0.10f, 0.48f, 8.0f, 105.0f, 60.0f, R::Heavy, 0.0f, TEXT("SideKick")));
	Rows.Add(TEXT("Roundhouse_Trunk"), MakeRow(TEXT("Roundhouse Kick"), T::Roundhouse, TEXT("RS toward the lead leg"), G::Trunk, 0.20f, 0.10f, 0.40f, 8.0f, 110.0f, 55.0f, R::Normal, 0.0f, TEXT("Roundhouse")));
	Rows.Add(TEXT("Roundhouse_Head"), MakeRow(TEXT("Roundhouse Kick (Head)"), T::Roundhouse, TEXT("RB + RS toward the lead leg"), G::Head, 0.23f, 0.10f, 0.43f, 8.0f, 110.0f, 55.0f, R::Heavy, 0.0f, TEXT("Roundhouse")));
	Rows.Add(TEXT("SpinSide_Trunk"), MakeRow(TEXT("Spin Side Kick"), T::SpinSide, TEXT("RS Down, Up"), G::Trunk, 0.40f, 0.12f, 0.60f, 20.0f, 120.0f, 80.0f, R::Heavy, 0.05f, TEXT("SpinSide")));
	Rows.Add(TEXT("SpinSide_Head"), MakeRow(TEXT("Spin Side Kick (Head)"), T::SpinSide, TEXT("RB + RS Down, Up"), G::Head, 0.43f, 0.12f, 0.63f, 20.0f, 120.0f, 80.0f, R::Knockdown, 0.05f, TEXT("SpinSide")));
	Rows.Add(TEXT("Hook_Trunk"), MakeRow(TEXT("Hook Kick"), T::Hook, TEXT("RS toward the other side"), G::Trunk, 0.22f, 0.10f, 0.42f, 8.0f, 110.0f, 55.0f, R::Normal, 0.0f, TEXT("Hook")));
	Rows.Add(TEXT("Hook_Head"), MakeRow(TEXT("Hook Kick (Head)"), T::Hook, TEXT("RB + RS toward the other side"), G::Head, 0.25f, 0.10f, 0.45f, 8.0f, 110.0f, 55.0f, R::Heavy, 0.0f, TEXT("Hook")));
	Rows.Add(TEXT("Axe_Head"), MakeRow(TEXT("Axe Kick"), T::Axe, TEXT("RS Left/Right quarter circle forward, Down"), G::Head, 0.32f, 0.12f, 0.50f, 12.0f, 115.0f, 70.0f, R::Heavy, 0.02f, TEXT("Axe")));

	// X throws a punch with the glove: trunk only (a punch to the head is a foul), one point, light and quick (GDD 8.3, 9.3).
	Rows.Add(TEXT("Punch_Trunk"), MakeRow(TEXT("Punch"), T::Punch, TEXT("X"), G::Trunk, 0.10f, 0.06f, 0.20f, 3.0f, 70.0f, 40.0f, R::Normal, 0.0f, TEXT("Punch")));

	Rows.Add(TEXT("SpinHook_Trunk"), MakeRow(TEXT("Spin Hook Kick"), T::SpinHook, TEXT("RT + RS Left/Right half circle down"), G::Trunk, 0.42f, 0.12f, 0.62f, 20.0f, 115.0f, 75.0f, R::Heavy, 0.05f, TEXT("SpinHook")));
	Rows.Add(TEXT("SpinHook_Head"), MakeRow(TEXT("Spin Hook Kick (Head)"), T::SpinHook, TEXT("RB + RT + RS Left/Right half circle down"), G::Head, 0.45f, 0.12f, 0.65f, 20.0f, 115.0f, 75.0f, R::Knockdown, 0.05f, TEXT("SpinHook")));

	// The tornado kick is always airborne, so its rows are the jump rows the recognizer's Find asks for. Highest cost and
	// fall chance of the set: GDD 9.2 makes it the hardest input and 8.9 gives non-grounded kicks a failure chance.
	FOpenStanceMoveRow TornadoTrunk = MakeRow(TEXT("Tornado Kick"), T::Tornado, TEXT("Y, RS Left/Right half circle down, half circle up"), G::Trunk, 0.50f, 0.14f, 0.75f, 30.0f, 125.0f, 90.0f, R::Heavy, 0.12f, TEXT("Tornado"));
	TornadoTrunk.bJump = true;
	Rows.Add(TEXT("Tornado_Trunk"), TornadoTrunk);
	FOpenStanceMoveRow TornadoHead = MakeRow(TEXT("Tornado Kick (Head)"), T::Tornado, TEXT("Y, RB + RS Left/Right half circle down, half circle up"), G::Head, 0.53f, 0.14f, 0.78f, 30.0f, 125.0f, 90.0f, R::Knockdown, 0.12f, TEXT("Tornado"));
	TornadoHead.bJump = true;
	Rows.Add(TEXT("Tornado_Head"), TornadoHead);

	// Jump kicks (GDD 9.2): the grounded kick thrown after a tap of Y, same target and points, at the Jump cost tier. They start a
	// little slower and can fail their own landing. The tornado is already airborne; there is no jump punch.
	const auto Jump = [&Rows](const TCHAR* BaseName, const TCHAR* Display, const TCHAR* Notation)
	{
		FOpenStanceMoveRow Row = Rows[BaseName];
		Row.DisplayName = Display;
		Row.GestureNotation = Notation;
		Row.bJump = true;
		Row.StartupSeconds += 0.05f;
		Row.AnimationSeconds += 0.05f;
		Row.StaminaCost += 6.0f;
		Row.SelfFallChance = FMath::Max(Row.SelfFallChance, 0.03f);
		return Row;
	};
	Rows.Add(TEXT("SideKick_Trunk_Jump"), Jump(TEXT("SideKick_Trunk"), TEXT("Jump Side Kick"), TEXT("Y, RS Up")));
	Rows.Add(TEXT("SideKick_Head_Jump"), Jump(TEXT("SideKick_Head"), TEXT("Jump Side Kick (Head)"), TEXT("Y, RB + RS Up")));
	Rows.Add(TEXT("Roundhouse_Trunk_Jump"), Jump(TEXT("Roundhouse_Trunk"), TEXT("Jump Roundhouse"), TEXT("Y, RS toward the lead leg")));
	Rows.Add(TEXT("Roundhouse_Head_Jump"), Jump(TEXT("Roundhouse_Head"), TEXT("Jump Roundhouse (Head)"), TEXT("Y, RB + RS toward the lead leg")));
	Rows.Add(TEXT("Hook_Trunk_Jump"), Jump(TEXT("Hook_Trunk"), TEXT("Jump Hook Kick"), TEXT("Y, RS toward the other side")));
	Rows.Add(TEXT("Hook_Head_Jump"), Jump(TEXT("Hook_Head"), TEXT("Jump Hook Kick (Head)"), TEXT("Y, RB + RS toward the other side")));
	Rows.Add(TEXT("Axe_Head_Jump"), Jump(TEXT("Axe_Head"), TEXT("Jump Axe Kick"), TEXT("Y, RS Left/Right quarter circle forward, Down")));
	Rows.Add(TEXT("SpinHook_Trunk_Jump"), Jump(TEXT("SpinHook_Trunk"), TEXT("Jump Spin Hook Kick"), TEXT("Y, RT + RS Left/Right half circle down")));
	Rows.Add(TEXT("SpinHook_Head_Jump"), Jump(TEXT("SpinHook_Head"), TEXT("Jump Spin Hook Kick (Head)"), TEXT("Y, RB + RT + RS Left/Right half circle down")));
	return Rows;
}

UDataTable* FOpenStanceMoveData::CreateSeedTable(UObject* Outer)
{
	UDataTable* Table = NewObject<UDataTable>(Outer);
	Table->RowStruct = FOpenStanceMoveRow::StaticStruct();
	for (const TPair<FName, FOpenStanceMoveRow>& Pair : BuildSeedRows())
	{
		Table->AddRow(Pair.Key, Pair.Value);
	}
	return Table;
}

FString FOpenStanceMoveData::ExportCsv(const UDataTable& Table)
{
	// UDataTable::GetTableAsCSV is editor-only. Keep the Blueprint export path
	// available in game builds using the runtime property serializers.
	if (!Table.RowStruct)
	{
		return FString();
	}
	const auto CsvField = [](const FString& Value)
	{
		return TEXT("\"") + Value.Replace(TEXT("\""), TEXT("\"\"")) + TEXT("\"");
	};
	TArray<const FProperty*> Columns;
	FString Csv = CsvField(Table.ImportKeyField.IsEmpty() ? TEXT("---") : Table.ImportKeyField);
	for (TFieldIterator<FProperty> Property(Table.RowStruct); Property; ++Property)
	{
		const FString Name = DataTableUtils::GetPropertyExportName(*Property);
		if (!Table.ImportKeyField.IsEmpty() && Name == Table.ImportKeyField)
		{
			continue;
		}
		Columns.Add(*Property);
		Csv += TEXT(",") + CsvField(Name);
	}
	Csv += TEXT("\n");
	for (const auto& Row : Table.GetRowMap())
	{
		Csv += CsvField(Row.Key.ToString());
		for (const FProperty* Property : Columns)
		{
			Csv += TEXT(",") + CsvField(DataTableUtils::GetPropertyValueAsString(Property, Row.Value, EDataTableExportFlags::None));
		}
		Csv += TEXT("\n");
	}
	return Csv;
}

TArray<FString> FOpenStanceMoveData::ImportCsv(UDataTable& Table, const FString& Csv)
{
	Table.RowStruct = FOpenStanceMoveRow::StaticStruct();
	return Table.CreateTableFromCSVString(Csv);
}

const FOpenStanceMoveRow* FOpenStanceMoveData::Find(const UDataTable& Table, EOpenStanceTechnique Technique, EOpenStanceTarget Target, bool bJump, FName* OutRowName)
{
	for (const TPair<FName, uint8*>& Pair : Table.GetRowMap())
	{
		const FOpenStanceMoveRow* Row = reinterpret_cast<const FOpenStanceMoveRow*>(Pair.Value);
		if (Row->Technique == Technique && Row->Target == Target && Row->bJump == bJump)
		{
			if (OutRowName)
			{
				*OutRowName = Pair.Key;
			}
			return Row;
		}
	}
	return nullptr;
}
