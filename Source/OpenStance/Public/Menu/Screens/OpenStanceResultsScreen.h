#pragma once

#include "CoreMinimal.h"
#include "Menu/OpenStanceScreen.h"
#include "OpenStanceResultsScreen.generated.h"

/** End of a match: winner, final score, round scores, points by technique and penalties, then what to do next. */
UCLASS()
class OPENSTANCE_API UOpenStanceResultsScreen : public UOpenStanceScreen
{
	GENERATED_BODY()

protected:
	virtual TSharedRef<SWidget> BuildContent() override;
};
