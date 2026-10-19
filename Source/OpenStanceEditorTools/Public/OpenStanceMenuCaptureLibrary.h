#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "Menu/OpenStanceMenuTypes.h"
#include "OpenStanceMenuCaptureLibrary.generated.h"

/**
 * Editor scripting for reviewing the menu (Python: unreal.OpenStanceMenuCaptureLibrary).
 *
 * Builds a menu screen without a viewport or a player and renders it to a PNG through the Slate widget renderer, so
 * every screen can be compared with the HTML prototype from a headless run (Tools/Unreal/capture_menu.py).
 */
UCLASS()
class UOpenStanceMenuCaptureLibrary : public UBlueprintFunctionLibrary
{
	GENERATED_BODY()

public:
	/**
	 * Render Screen at Width x Height and write it to OutputPath as a PNG. Returns true on success.
	 *
	 * State is a semicolon list of key=value pairs that sets up what the screen shows: hub, controls_tab and
	 * options_tab (indices), category (men or women), mode (sparring or tournament), sex (male or female) and
	 * gear (0 or 1) for the fighter creator, sample (hud or results, filling in the match model), dialog (pause,
	 * quit_game or quit_match, drawn over the screen; pass Screen None for the dialog alone) and focus (0 to
	 * draw no item as focused; default 1).
	 */
	UFUNCTION(BlueprintCallable, Category = "Open Stance|Menu")
	static bool CaptureScreen(EOpenStanceMenuScreen Screen, const FString& OutputPath, const FString& State, int32 Width = 1920, int32 Height = 1080);
};
