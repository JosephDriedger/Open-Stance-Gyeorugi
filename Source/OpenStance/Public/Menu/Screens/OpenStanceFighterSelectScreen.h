#pragma once

#include "CoreMinimal.h"
#include "Menu/OpenStanceMenuTypes.h"
#include "Menu/OpenStanceScreen.h"
#include "OpenStanceFighterSelectScreen.generated.h"

/**
 * Pick a premade fighter for Sparring or Tournament. The fighter you pick takes the side you chose on Side Select (Chung,
 * blue and left, by default); the other side is the opponent. LB and RB switch between the men's and women's rosters.
 */
UCLASS()
class OPENSTANCE_API UOpenStanceFighterSelectScreen : public UOpenStanceScreen
{
	GENERATED_BODY()

protected:
	virtual TSharedRef<SWidget> BuildContent() override;
	virtual TArray<FOpenStanceHint> GetHints() const override;
	virtual void HandleTabStep(int32 Direction) override;

private:
	TSharedRef<SWidget> BuildSidePanel(EOpenStanceSide Side);
	TSharedRef<SWidget> BuildRosterList(EOpenStanceSex Sex);

	const FOpenStanceFighterProfile& GetFighter(EOpenStanceSide Side) const;
	void SetCategory(EOpenStanceSex Sex);
	void PickFighter(int32 RosterIndex);
};
