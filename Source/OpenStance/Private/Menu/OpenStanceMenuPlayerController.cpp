#include "Menu/OpenStanceMenuPlayerController.h"

#include "Engine/LocalPlayer.h"
#include "Menu/OpenStanceMenuSubsystem.h"

AOpenStanceMenuPlayerController::AOpenStanceMenuPlayerController()
{
	bShowMouseCursor = true;
}

void AOpenStanceMenuPlayerController::BeginPlay()
{
	Super::BeginPlay();

	if (ULocalPlayer* LocalPlayer = GetLocalPlayer())
	{
		if (UOpenStanceMenuSubsystem* Menu = LocalPlayer->GetSubsystem<UOpenStanceMenuSubsystem>())
		{
			Menu->StartMenuFlow();
		}
	}
}
