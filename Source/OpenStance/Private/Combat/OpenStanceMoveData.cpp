#include "Combat/OpenStanceMoveData.h"

#include "Animation/AnimMontage.h"
#include "Engine/DataTable.h"

namespace
{
	/** Placeholder montages live beside the captured ones and keep the AM_ prefix (GDD 16.5). */
	FSoftObjectPath PlaceholderPath(const TCHAR* Name)
	{
		return FSoftObjectPath(FString::Printf(TEXT("/Game/Animation/Moves/Placeholder/AM_Placeholder_%s.AM_Placeholder_%s"), Name, Name));
	}

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
	return Table.GetTableAsCSV();
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
