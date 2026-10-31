#pragma once

#include "CoreMinimal.h"
#include "Combat/OpenStanceCombatTypes.h"
#include "Engine/DataTable.h"
#include "OpenStanceMoveData.generated.h"

class UAnimMontage;
class UDataTable;

/**
 * One technique aimed at one target (GDD 16.3). The row name is the move's id, for example SideKick_Trunk.
 *
 * Animation, tuning and combat logic stay apart: the combat code reads timing, cost, points and reach from here and
 * asks for a montage only through ResolveMontage, so a placeholder swaps for final mocap by editing the row.
 * Distances are centimetres (Unreal units); times are seconds.
 */
USTRUCT(BlueprintType)
struct OPENSTANCE_API FOpenStanceMoveRow : public FTableRowBase
{
	GENERATED_BODY()

	/** Name shown in the move list and the debug overlay. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Open Stance|Move")
	FString DisplayName;

	/** The Skill Stick gesture this row answers (GDD 7.2). Together with Target and bJump it is the row's key. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Open Stance|Move")
	EOpenStanceTechnique Technique = EOpenStanceTechnique::SideKick;

	/** The gesture as the controls reference writes it, for review, for example "RS Up". Not read by the game. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Open Stance|Move")
	FString GestureNotation;

	/** RB aims a kick at the head; every other kick and every punch aims at the trunk (GDD 8.6). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Open Stance|Move")
	EOpenStanceTarget Target = EOpenStanceTarget::Trunk;

	/** Thrown airborne after a leading tap of Y (GDD 7.4). Jump rows belong to Milestone 3. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Open Stance|Move")
	bool bJump = false;

	/** Spinning techniques score the higher values (GDD 8.3). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Open Stance|Move")
	bool bSpinning = false;

	/** The limb whose trace is checked during Attack Active. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Open Stance|Move")
	EOpenStanceStrikeLimb Limb = EOpenStanceStrikeLimb::FootGuard;

	/** Montage authored for the left leg throwing this technique. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Open Stance|Animation")
	TSoftObjectPtr<UAnimMontage> LeftLegMontage;

	/** Montage authored for the right leg throwing this technique. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Open Stance|Animation")
	TSoftObjectPtr<UAnimMontage> RightLegMontage;

	/** Stand-in for either leg until the captured montage exists (GDD 16.4). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Open Stance|Animation")
	TSoftObjectPtr<UAnimMontage> PlaceholderMontage;

	/** Seconds from the input to the first active frame. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Open Stance|Timing")
	float StartupSeconds = 0.2f;

	/** Seconds the trace can score. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Open Stance|Timing")
	float ActiveSeconds = 0.1f;

	/** Seconds from the last active frame until the fighter is free again; the punishable window. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Open Stance|Timing")
	float RecoverySeconds = 0.4f;

	/** Seconds into the recovery from which the technique may be cancelled; negative means it cannot be cancelled. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Open Stance|Timing")
	float CancelWindowSeconds = -1.0f;

	/** Stamina spent when the technique starts (GDD 8.9). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Open Stance|Cost")
	float StaminaCost = 8.0f;

	/** Points for a valid contact; 1, 2, 3, 4 or 6 (GDD 8.3). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Open Stance|Scoring")
	int32 Points = 2;

	/** How far the trace can reach from the attacker's centre line at a 175 cm fighter; reach scales with height. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Open Stance|Scoring")
	float ReachCm = 110.0f;

	/** Strength of the contact, compared with the protector's impact threshold (GDD 8.3). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Open Stance|Scoring")
	float Impact = 50.0f;

	/** How the defender reacts when the technique lands (GDD 8.10). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Open Stance|Reaction")
	EOpenStanceReactionSeverity Reaction = EOpenStanceReactionSeverity::Normal;

	/** Chance, 0 to 1, that Attack Recovery ends in a fall instead of Idle (GDD 8.10). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Open Stance|Reaction")
	float SelfFallChance = 0.0f;

	/** Seconds of the whole technique from startup to the end of recovery. */
	float GetTotalSeconds() const { return StartupSeconds + ActiveSeconds + RecoverySeconds; }

	/** The montage for the leg that throws it, falling back to the placeholder when allowed. Null if none exists. */
	TSoftObjectPtr<UAnimMontage> ResolveMontage(EOpenStanceLegSide ThrowingLeg, bool bAllowPlaceholder) const;

	/** True when a captured montage exists for both legs. */
	bool HasProductionAnimation() const;
};

/** One problem found while checking a MoveData table. */
struct OPENSTANCE_API FOpenStanceMoveIssue
{
	FName RowName;
	FString Message;
	bool bError = true;
};

/** What the checker should insist on. */
struct OPENSTANCE_API FOpenStanceMoveCheckOptions
{
	/** Production builds need captured montages; the M1 greybox accepts placeholders. */
	bool bRequireProductionAnimation = false;

	/** Loads each montage path and reports the ones that do not exist. Editor only; leave off for pure data checks. */
	bool bCheckAssetsExist = false;
};

/** Reads, checks and seeds the MoveData table (GDD 16.6). */
struct OPENSTANCE_API FOpenStanceMoveData
{
	/** Points the PSS awards for a technique (GDD 8.3): 0 where the combination cannot score. */
	static int32 PointsFor(EOpenStanceTechnique Technique, EOpenStanceTarget Target, bool bSpinning);

	static bool IsSpinning(EOpenStanceTechnique Technique);

	/** Checks every row for missing animation, impossible timing and a score that does not match its target. */
	static TArray<FOpenStanceMoveIssue> Validate(const TMap<FName, FOpenStanceMoveRow>& Rows, const FOpenStanceMoveCheckOptions& Options);

	/** Checks the rows of a data table. */
	static TArray<FOpenStanceMoveIssue> Validate(const UDataTable& Table, const FOpenStanceMoveCheckOptions& Options);

	/** The Milestone 1 moves: side, roundhouse and spin side, each to the trunk and the head, with placeholder animation. */
	static TMap<FName, FOpenStanceMoveRow> BuildSeedRows();

	/** A table of the seed rows, in memory. */
	static UDataTable* CreateSeedTable(UObject* Outer);

	/** The CSV text of a table, for review outside Unreal. */
	static FString ExportCsv(const UDataTable& Table);

	/** Replaces the table's rows from CSV text; returns the problems the importer reported. */
	static TArray<FString> ImportCsv(UDataTable& Table, const FString& Csv);

	/** The row for a gesture, or null if the move list has none (the technique is not mapped yet). */
	static const FOpenStanceMoveRow* Find(const UDataTable& Table, EOpenStanceTechnique Technique, EOpenStanceTarget Target, bool bJump, FName* OutRowName = nullptr);
};
