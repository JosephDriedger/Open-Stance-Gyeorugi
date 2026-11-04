#pragma once

#include "CoreMinimal.h"
#include "Menu/OpenStanceMenuTypes.h"
#include "Menu/OpenStanceScreen.h"
#include "OpenStanceFighterSelectScreen.generated.h"

/**
 * Pick the premade fighters for Sparring or Tournament: yours, on the side you chose on Side Select (Chung, blue and
 * left, by default), and your opponent's on the other. Y (or Tab, or the two buttons above the list) switches which one
 * a pick sets; each side's fighter is marked in its colour. X (or R, or the Random button) picks two different fighters
 * at random from the roster shown. LB and RB switch between the men's and women's rosters.
 */
UCLASS()
class OPENSTANCE_API UOpenStanceFighterSelectScreen : public UOpenStanceScreen
{
	GENERATED_BODY()

protected:
	virtual TSharedRef<SWidget> BuildContent() override;
	virtual TArray<FOpenStanceHint> GetHints() const override;
	virtual void HandleTabStep(int32 Direction) override;
	virtual FReply NativeOnKeyDown(const FGeometry& InGeometry, const FKeyEvent& InKeyEvent) override;

private:
	TSharedRef<SWidget> BuildSidePanel(EOpenStanceSide Side);
	TSharedRef<SWidget> BuildRosterList(EOpenStanceSex Sex);

	const FOpenStanceFighterProfile& GetFighter(EOpenStanceSide Side) const;
	void SetCategory(EOpenStanceSex Sex);
	void PickFighter(int32 RosterIndex);

	/** Both sides get a different random fighter from the roster shown. */
	void PickRandom();

	/** The side a pick sets: Chung or Hong, whichever is yours, or the opponent's while choosing the opponent. */
	EOpenStanceSide GetPickSide() const;

	/** While true, picks set the opponent's fighter instead of yours. */
	bool bChoosingOpponent = false;
};
