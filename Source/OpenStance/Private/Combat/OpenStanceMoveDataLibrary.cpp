#include "Combat/OpenStanceMoveDataLibrary.h"

#include "Combat/OpenStanceMoveData.h"
#include "Engine/DataTable.h"
#include "Misc/FileHelper.h"

TArray<FString> UOpenStanceMoveDataLibrary::ValidateMoveTable(const UDataTable* Table, bool bRequireProductionAnimation, bool bCheckAssetsExist)
{
	TArray<FString> Lines;
	if (!Table || Table->RowStruct != FOpenStanceMoveRow::StaticStruct())
	{
		Lines.Add(TEXT("ERROR: not a MoveData table (row struct is not FOpenStanceMoveRow)."));
		return Lines;
	}

	FOpenStanceMoveCheckOptions Options;
	Options.bRequireProductionAnimation = bRequireProductionAnimation;
	Options.bCheckAssetsExist = bCheckAssetsExist;
	for (const FOpenStanceMoveIssue& Issue : FOpenStanceMoveData::Validate(*Table, Options))
	{
		Lines.Add(FString::Printf(TEXT("%s: %s: %s"), Issue.bError ? TEXT("ERROR") : TEXT("WARNING"), *Issue.RowName.ToString(), *Issue.Message));
	}
	return Lines;
}

bool UOpenStanceMoveDataLibrary::WriteSeedCsv(const FString& OutputPath)
{
	UDataTable* Table = FOpenStanceMoveData::CreateSeedTable(GetTransientPackage());
	return FFileHelper::SaveStringToFile(FOpenStanceMoveData::ExportCsv(*Table), *OutputPath, FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
}
