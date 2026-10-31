#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "OpenStanceMoveDataLibrary.generated.h"

class UDataTable;

/**
 * Editor scripting for the MoveData table (Python: unreal.OpenStanceMoveDataLibrary).
 *
 * Import and export use Unreal's own DataTableFunctionLibrary (fill_data_table_from_csv_file and
 * export_data_table_to_csv_file); this adds the checks and the seed (Tools/Unreal/create_move_data_table.py).
 */
UCLASS()
class OPENSTANCE_API UOpenStanceMoveDataLibrary : public UBlueprintFunctionLibrary
{
	GENERATED_BODY()

public:
	/**
	 * Checks every row for missing animation, impossible timing and a score that does not match its target.
	 * Returns one line per problem, "ERROR" or "WARNING" first; empty when the table is clean.
	 */
	UFUNCTION(BlueprintCallable, Category = "Open Stance|Combat")
	static TArray<FString> ValidateMoveTable(const UDataTable* Table, bool bRequireProductionAnimation, bool bCheckAssetsExist);

	/** Writes the Milestone 1 seed moves to a CSV file for review. Returns true on success. */
	UFUNCTION(BlueprintCallable, Category = "Open Stance|Combat")
	static bool WriteSeedCsv(const FString& OutputPath);
};
