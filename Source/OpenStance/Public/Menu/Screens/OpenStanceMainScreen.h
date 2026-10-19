#pragma once

#include "CoreMinimal.h"
#include "Menu/OpenStanceScreen.h"
#include "OpenStanceMainScreen.generated.h"

class SOpenStanceInteractive;

/** Main menu: four hubs (Play, Progress, Connected, Options) as tab strips of tall tiles, with LB and RB to switch hub. */
UCLASS()
class OPENSTANCE_API UOpenStanceMainScreen : public UOpenStanceScreen
{
	GENERATED_BODY()

protected:
	virtual TSharedRef<SWidget> BuildContent() override;
	virtual TArray<FOpenStanceHint> GetHints() const override;
	virtual void HandleTabStep(int32 Direction) override;

private:
	void SelectHub(int32 HubIndex);
	void OpenTile(int32 HubIndex, int32 TileIndex);

	/** The first tile of each hub, so a tab change can move focus onto the new strip. */
	TArray<TWeakPtr<SOpenStanceInteractive>> FirstTiles;
};
