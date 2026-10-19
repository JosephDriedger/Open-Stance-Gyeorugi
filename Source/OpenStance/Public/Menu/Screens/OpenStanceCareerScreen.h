#pragma once

#include "CoreMinimal.h"
#include "Menu/OpenStanceScreen.h"
#include "OpenStanceCareerScreen.generated.h"

/**
 * Career hub for the created fighter: season progress, the weekly calendar, and entries for training slots, events,
 * grading, reviews, the fighter creator and the Future long-term career. The calendar is the prototype's example.
 */
UCLASS()
class OPENSTANCE_API UOpenStanceCareerScreen : public UOpenStanceScreen
{
	GENERATED_BODY()

protected:
	virtual TSharedRef<SWidget> BuildContent() override;
	virtual TArray<FOpenStanceHint> GetHints() const override;
};
