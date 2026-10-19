#pragma once

#include "CoreMinimal.h"
#include "Menu/OpenStanceScreen.h"
#include "Menu/Screens/OpenStanceMatchScreen.h"
#include "OpenStanceRefereeScreens.generated.h"

/**
 * Referee Mode in the match (Future, GDD 7.7): the match HUD seen from the referee, with a rating panel and the
 * commands on the controller along the bottom. It shows the prototype's example match until Referee Mode exists.
 * A ends the match and goes to the grade.
 */
UCLASS()
class OPENSTANCE_API UOpenStanceRefereeMatchScreen : public UOpenStanceMatchScreen
{
	GENERATED_BODY()

protected:
	virtual TSharedRef<SWidget> BuildContent() override;
	virtual TArray<FOpenStanceHint> GetHints() const override;
	virtual void NativeTick(const FGeometry& MyGeometry, float InDeltaTime) override;
	virtual FReply NativeOnKeyDown(const FGeometry& InGeometry, const FKeyEvent& InKeyEvent) override;
};

/** The referee's grade after a match: rating, what changed it, and the thresholds for a warning or removal. */
UCLASS()
class OPENSTANCE_API UOpenStanceRefereeGradeScreen : public UOpenStanceScreen
{
	GENERATED_BODY()

protected:
	virtual TSharedRef<SWidget> BuildContent() override;
};
