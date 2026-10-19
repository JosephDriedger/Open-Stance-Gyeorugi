#pragma once

#include "CoreMinimal.h"
#include "Menu/OpenStanceScreen.h"
#include "OpenStanceInfoScreen.generated.h"

/**
 * The information pages for features the design lists as Future (Team Championship, Challenges, Online, Replays,
 * Broadcast, Long-term career): a list of what each will offer, with notes beside it. The screen id picks the page.
 */
UCLASS()
class OPENSTANCE_API UOpenStanceInfoScreen : public UOpenStanceScreen
{
	GENERATED_BODY()

protected:
	virtual TSharedRef<SWidget> BuildContent() override;
};
