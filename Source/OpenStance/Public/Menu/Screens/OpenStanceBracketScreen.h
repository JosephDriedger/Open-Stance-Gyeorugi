#pragma once

#include "CoreMinimal.h"
#include "Menu/OpenStanceScreen.h"
#include "OpenStanceBracketScreen.generated.h"

/**
 * Tournament bracket shown between matches: finished pairings with their scores, the next pairing outlined, and the
 * rounds still to play. The pairings are the prototype's example eight-fighter bracket until the tournament flow
 * supplies real ones.
 */
UCLASS()
class OPENSTANCE_API UOpenStanceBracketScreen : public UOpenStanceScreen
{
	GENERATED_BODY()

protected:
	virtual TSharedRef<SWidget> BuildContent() override;
};
