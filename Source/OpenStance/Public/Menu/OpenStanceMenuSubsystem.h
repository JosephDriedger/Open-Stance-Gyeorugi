#pragma once

#include "CoreMinimal.h"
#include "Menu/OpenStanceMenuTypes.h"
#include "Subsystems/LocalPlayerSubsystem.h"
#include "OpenStanceMenuSubsystem.generated.h"

class SWidget;
class UOpenStanceDialogScreen;
class UOpenStanceMatchModel;
class UOpenStanceScreen;
class UOpenStanceUserSettings;

/** One button in a dialog or the pause menu. OnPressed runs after the dialog has closed. */
struct FOpenStanceDialogButton
{
	FString Label;
	TFunction<void()> OnPressed;
	/** Focus rule in red, for quit and other destructive choices. */
	bool bDanger = false;
};

struct FOpenStanceDialogRequest
{
	FString Title;
	FString Message;
	TArray<FOpenStanceDialogButton> Buttons;
	/** What B or Escape does. Empty just closes the dialog. */
	TFunction<void()> OnBack;
};

DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FOpenStanceMatchRequested, const FOpenStanceMatchSetup&, Setup);

/**
 * Runs the menu flow for a local player: which screen is showing, the back stack, dialogs and the pause menu,
 * and what the player has chosen so far. Screens ask it to navigate and never open each other directly.
 *
 * It does not start gameplay. When a match is chosen it raises OnMatchRequested with the setup, and shows the
 * match HUD, so gameplay can bind to it and load the arena without the menu knowing how.
 */
UCLASS()
class OPENSTANCE_API UOpenStanceMenuSubsystem : public ULocalPlayerSubsystem
{
	GENERATED_BODY()

public:
	/** Opens the title screen, the start of the menu flow. */
	UFUNCTION(BlueprintCallable, Category = "Open Stance|Menu")
	void StartMenuFlow();

	/** Shows a screen and remembers the current one so Back returns to it. */
	UFUNCTION(BlueprintCallable, Category = "Open Stance|Menu")
	void ShowScreen(EOpenStanceMenuScreen Screen);

	/** Shows a screen without remembering the current one. */
	UFUNCTION(BlueprintCallable, Category = "Open Stance|Menu")
	void ReplaceScreen(EOpenStanceMenuScreen Screen);

	/** Clears the back stack and shows the main menu. */
	UFUNCTION(BlueprintCallable, Category = "Open Stance|Menu")
	void ReturnToMain();

	/** Back: to the previous screen, to the main menu if there is none, and to the pause menu from a match. */
	UFUNCTION(BlueprintCallable, Category = "Open Stance|Menu")
	void GoBack();

	/** Opens a screen from the pause menu; Back returns to the match. */
	void ShowScreenFromMatch(EOpenStanceMenuScreen Screen);

	/** Starts a match with the current choices: resets the HUD model, raises OnMatchRequested and shows the HUD. */
	UFUNCTION(BlueprintCallable, Category = "Open Stance|Menu")
	void StartMatch(bool bRememberCurrent = true);

	void ShowDialog(FOpenStanceDialogRequest Request);

	/** The pause menu and quit confirmations as dialog requests, so tools can render them without a viewport. */
	FOpenStanceDialogRequest MakePauseRequest();
	FOpenStanceDialogRequest MakeQuitGameRequest();
	FOpenStanceDialogRequest MakeQuitMatchRequest();
	void CloseDialog();
	bool IsDialogOpen() const;

	/** Pauses the match and opens the pause menu. */
	void ShowPauseMenu();
	void ShowQuitGameDialog();
	void ShowQuitMatchDialog();

	/** Raised when a match starts; gameplay binds this to load the arena and spawn the fighters. */
	UPROPERTY(BlueprintAssignable, Category = "Open Stance|Menu")
	FOpenStanceMatchRequested OnMatchRequested;

	/** The choices made on the setup and fighter select screens, as gameplay needs them. */
	UFUNCTION(BlueprintCallable, Category = "Open Stance|Menu")
	FOpenStanceMatchSetup BuildMatchSetup() const;

	FOpenStanceMenuSession& GetSession()
	{
		return Session;
	}

	const FOpenStanceMenuSession& GetSession() const
	{
		return Session;
	}

	/** The state the match HUD and results page show. Created on first use. */
	UOpenStanceMatchModel* GetMatchModel();

	/** The player's settings, or null when the project has not registered UOpenStanceUserSettings. */
	UOpenStanceUserSettings* GetUserSettings() const;

	EOpenStanceMenuScreen GetCurrentScreen() const
	{
		return CurrentScreen;
	}

	UOpenStanceScreen* GetActiveScreen() const
	{
		return ActiveScreen;
	}

	/** Remembered value of a row on a setup screen. */
	int32 GetChoiceIndex(EOpenStanceMenuScreen Screen, FName RowId, int32 DefaultIndex) const;
	void SetChoiceIndex(EOpenStanceMenuScreen Screen, FName RowId, int32 Index);

	/**
	 * Builds a screen without showing it, for tools that capture it (Tools/Unreal/capture_menu.py). Needs a
	 * world only for widget creation; the screen is not added to a viewport.
	 */
	UOpenStanceScreen* CreateScreenForCapture(UWorld* World, EOpenStanceMenuScreen Screen);

	/** Same for a dialog, which sits over a screen. */
	UOpenStanceScreen* CreateDialogForCapture(UWorld* World, FOpenStanceDialogRequest Request);

private:
	static TSubclassOf<UOpenStanceScreen> GetScreenClass(EOpenStanceMenuScreen Screen);

	/** Builds and shows a screen, replacing the current one in the viewport. */
	void Present(EOpenStanceMenuScreen Screen);
	void ApplyInputMode(EOpenStanceMenuScreen Screen);
	APlayerController* GetOwningController() const;

	/** Takes the dialog off screen without touching pause or focus; CloseDialog and Present build on it. */
	void RemoveDialog();
	void RememberFocus();
	static FName MakeChoiceKey(EOpenStanceMenuScreen Screen, FName RowId);

	UPROPERTY(Transient)
	TObjectPtr<UOpenStanceScreen> ActiveScreen;

	UPROPERTY(Transient)
	TObjectPtr<UOpenStanceDialogScreen> DialogScreen;

	UPROPERTY(Transient)
	TObjectPtr<UOpenStanceMatchModel> MatchModel;

	/** What had focus when the dialog opened, so closing it puts the player back where they were. */
	TWeakPtr<SWidget> FocusBeforeDialog;

	FOpenStanceMenuSession Session;
	TArray<EOpenStanceMenuScreen> BackStack;
	EOpenStanceMenuScreen CurrentScreen = EOpenStanceMenuScreen::None;

	static constexpr int32 ScreenZOrder = 10;
	static constexpr int32 DialogZOrder = 100;
};
