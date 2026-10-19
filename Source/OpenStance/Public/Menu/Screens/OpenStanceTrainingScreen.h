#pragma once

#include "CoreMinimal.h"
#include "Menu/OpenStanceScreen.h"
#include "OpenStanceTrainingScreen.generated.h"

/** Training hub: lessons, drills and free practice, with the current lesson and coach feedback beside them. */
UCLASS()
class OPENSTANCE_API UOpenStanceTrainingScreen : public UOpenStanceScreen
{
	GENERATED_BODY()

protected:
	virtual TSharedRef<SWidget> BuildContent() override;
};
