#pragma once

#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "OpenStanceMenuGameMode.generated.h"

/**
 * Game mode for the menu level: no pawn, and a player controller that opens the title screen. The menu level is
 * an empty map (the menu draws itself); L_MainMenu sets this as its game mode override.
 */
UCLASS()
class OPENSTANCE_API AOpenStanceMenuGameMode : public AGameModeBase
{
	GENERATED_BODY()

public:
	AOpenStanceMenuGameMode();
};
