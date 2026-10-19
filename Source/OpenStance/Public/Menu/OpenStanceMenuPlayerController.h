#pragma once

#include "CoreMinimal.h"
#include "GameFramework/PlayerController.h"
#include "OpenStanceMenuPlayerController.generated.h"

/** Starts the menu flow for the local player when the menu level begins. */
UCLASS()
class OPENSTANCE_API AOpenStanceMenuPlayerController : public APlayerController
{
	GENERATED_BODY()

public:
	AOpenStanceMenuPlayerController();

protected:
	virtual void BeginPlay() override;
};
