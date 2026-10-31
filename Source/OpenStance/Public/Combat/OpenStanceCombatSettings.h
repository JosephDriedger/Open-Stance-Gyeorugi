#pragma once

#include "CoreMinimal.h"
#include "Combat/OpenStanceFootwork.h"
#include "Engine/DeveloperSettings.h"
#include "OpenStanceCombatSettings.generated.h"

/**
 * Combat tuning that designers edit without code: Project Settings > Game > Open Stance Combat, saved to
 * Config/DefaultGame.ini. Per-technique numbers live in the MoveData table instead (Docs/Combat_Data.md).
 */
UCLASS(Config = Game, DefaultConfig, meta = (DisplayName = "Open Stance Combat"))
class OPENSTANCE_API UOpenStanceCombatSettings : public UDeveloperSettings
{
	GENERATED_BODY()

public:
	UOpenStanceCombatSettings()
	{
		CategoryName = TEXT("Game");
	}

	UPROPERTY(Config, EditAnywhere, Category = "Footwork")
	FOpenStanceMovementTuning Movement;

	static const FOpenStanceMovementTuning& GetMovement()
	{
		return GetDefault<UOpenStanceCombatSettings>()->Movement;
	}
};
