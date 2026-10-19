#pragma once

#include "CoreMinimal.h"
#include "Menu/OpenStanceScreen.h"
#include "OpenStanceSetupScreen.generated.h"

/**
 * Setup page for Sparring, Tournament and Referee Mode: a list of rows that cycle through values, a button that
 * continues, and cards of notes. Which one it is comes from the screen id; the rows are in OpenStanceMenuContent.
 */
UCLASS()
class OPENSTANCE_API UOpenStanceSetupScreen : public UOpenStanceScreen
{
	GENERATED_BODY()

protected:
	virtual TSharedRef<SWidget> BuildContent() override;
	virtual TArray<FOpenStanceHint> GetHints() const override;

private:
	void CycleRow(int32 RowIndex, int32 Direction);
	FString GetRowValue(int32 RowIndex) const;
	void Continue();
};
