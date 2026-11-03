#pragma once

#include "CoreMinimal.h"
#include "Menu/OpenStanceMenuTypes.h"
#include "Menu/OpenStanceScreen.h"
#include "OpenStanceSideSelectScreen.generated.h"

/**
 * Pick the side you play, the way sports games pick home and away: both fighters are shown, and a controller marker
 * (P1, and P2 in a two-player match) sits under one of them. Left or right on the D-pad or the left stick moves the
 * marker, A continues to Fighter Select. Chung is blue on the left and Hong is red on the right whichever side you take;
 * the marker only says which one your controller drives (GDD 4.1).
 */
UCLASS()
class OPENSTANCE_API UOpenStanceSideSelectScreen : public UOpenStanceScreen
{
	GENERATED_BODY()

public:
	UOpenStanceSideSelectScreen(const FObjectInitializer& ObjectInitializer);

protected:
	virtual TSharedRef<SWidget> BuildContent() override;
	virtual TArray<FOpenStanceHint> GetHints() const override;
	virtual FReply NativeOnKeyDown(const FGeometry& InGeometry, const FKeyEvent& InKeyEvent) override;

private:
	TSharedRef<SWidget> BuildSide(EOpenStanceSide Side);

	/** Moves player 1's marker to a side. Player 2, when there is one, takes the other. */
	void ChooseSide(EOpenStanceSide Side);

	/** True for the Sparring setup's "1P vs 2P". */
	bool IsTwoPlayer() const;
};
