#include "Menu/OpenStanceMenuGameMode.h"

#include "Menu/OpenStanceMenuPlayerController.h"

AOpenStanceMenuGameMode::AOpenStanceMenuGameMode()
{
	PlayerControllerClass = AOpenStanceMenuPlayerController::StaticClass();
	DefaultPawnClass = nullptr;
}
