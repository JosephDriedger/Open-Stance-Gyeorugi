#include "Menu/OpenStanceMenuSubsystem.h"

#include "Blueprint/UserWidget.h"
#include "Engine/LocalPlayer.h"
#include "Framework/Application/SlateUser.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "HAL/IConsoleManager.h"
#include "Menu/OpenStanceMatchModel.h"
#include "Menu/OpenStanceMenuContent.h"
#include "Menu/OpenStanceUserSettings.h"
#include "Menu/Screens/OpenStanceBracketScreen.h"
#include "Menu/Screens/OpenStanceCareerScreen.h"
#include "Menu/Screens/OpenStanceControlsScreen.h"
#include "Menu/Screens/OpenStanceCustomizeScreen.h"
#include "Menu/Screens/OpenStanceDialogScreen.h"
#include "Menu/Screens/OpenStanceFighterSelectScreen.h"
#include "Menu/Screens/OpenStanceInfoScreen.h"
#include "Menu/Screens/OpenStanceMainScreen.h"
#include "Menu/Screens/OpenStanceMatchScreen.h"
#include "Menu/Screens/OpenStanceOptionsScreen.h"
#include "Menu/Screens/OpenStanceRefereeScreens.h"
#include "Menu/Screens/OpenStanceResultsScreen.h"
#include "Menu/Screens/OpenStanceSetupScreen.h"
#include "Menu/Screens/OpenStanceTitleScreen.h"
#include "Menu/Screens/OpenStanceTrainingScreen.h"

DEFINE_LOG_CATEGORY_STATIC(LogOpenStanceMenu, Log, All);

TSubclassOf<UOpenStanceScreen> UOpenStanceMenuSubsystem::GetScreenClass(EOpenStanceMenuScreen Screen)
{
	switch (Screen)
	{
	case EOpenStanceMenuScreen::Title:
		return UOpenStanceTitleScreen::StaticClass();
	case EOpenStanceMenuScreen::Main:
		return UOpenStanceMainScreen::StaticClass();
	case EOpenStanceMenuScreen::Sparring:
	case EOpenStanceMenuScreen::Tournament:
	case EOpenStanceMenuScreen::RefereeSetup:
		return UOpenStanceSetupScreen::StaticClass();
	case EOpenStanceMenuScreen::FighterSelect:
		return UOpenStanceFighterSelectScreen::StaticClass();
	case EOpenStanceMenuScreen::Match:
		return UOpenStanceMatchScreen::StaticClass();
	case EOpenStanceMenuScreen::Results:
		return UOpenStanceResultsScreen::StaticClass();
	case EOpenStanceMenuScreen::Bracket:
		return UOpenStanceBracketScreen::StaticClass();
	case EOpenStanceMenuScreen::Training:
		return UOpenStanceTrainingScreen::StaticClass();
	case EOpenStanceMenuScreen::Career:
		return UOpenStanceCareerScreen::StaticClass();
	case EOpenStanceMenuScreen::Customize:
		return UOpenStanceCustomizeScreen::StaticClass();
	case EOpenStanceMenuScreen::Options:
		return UOpenStanceOptionsScreen::StaticClass();
	case EOpenStanceMenuScreen::Controls:
		return UOpenStanceControlsScreen::StaticClass();
	case EOpenStanceMenuScreen::Team:
	case EOpenStanceMenuScreen::Challenges:
	case EOpenStanceMenuScreen::Online:
	case EOpenStanceMenuScreen::Replays:
	case EOpenStanceMenuScreen::Broadcast:
	case EOpenStanceMenuScreen::LongTerm:
		return UOpenStanceInfoScreen::StaticClass();
	case EOpenStanceMenuScreen::RefereeMatch:
		return UOpenStanceRefereeMatchScreen::StaticClass();
	case EOpenStanceMenuScreen::RefereeGrade:
		return UOpenStanceRefereeGradeScreen::StaticClass();
	default:
		return nullptr;
	}
}

APlayerController* UOpenStanceMenuSubsystem::GetOwningController() const
{
	const ULocalPlayer* LocalPlayer = GetLocalPlayer();
	return LocalPlayer ? LocalPlayer->GetPlayerController(GetWorld()) : nullptr;
}

void UOpenStanceMenuSubsystem::StartMenuFlow()
{
	BackStack.Reset();
	Present(EOpenStanceMenuScreen::Title);
}

void UOpenStanceMenuSubsystem::ShowScreen(EOpenStanceMenuScreen Screen)
{
	if (CurrentScreen != EOpenStanceMenuScreen::None && CurrentScreen != Screen)
	{
		BackStack.Add(CurrentScreen);
	}
	Present(Screen);
}

void UOpenStanceMenuSubsystem::ReplaceScreen(EOpenStanceMenuScreen Screen)
{
	Present(Screen);
}

void UOpenStanceMenuSubsystem::ReturnToMain()
{
	BackStack.Reset();
	Present(EOpenStanceMenuScreen::Main);
}

void UOpenStanceMenuSubsystem::GoBack()
{
	if (CurrentScreen == EOpenStanceMenuScreen::Title || CurrentScreen == EOpenStanceMenuScreen::None)
	{
		return;
	}
	if (CurrentScreen == EOpenStanceMenuScreen::Match)
	{
		ShowPauseMenu();
		return;
	}
	Present(BackStack.IsEmpty() ? EOpenStanceMenuScreen::Main : BackStack.Pop());
}

void UOpenStanceMenuSubsystem::ShowScreenFromMatch(EOpenStanceMenuScreen Screen)
{
	BackStack.Add(EOpenStanceMenuScreen::Match);
	Present(Screen);

	// The match is still on hold behind this screen; the match screen reopens the pause menu when Back returns to it
	GetMatchModel()->SetPaused(true);
}

void UOpenStanceMenuSubsystem::StartMatch(bool bRememberCurrent)
{
	const TArray<FOpenStanceFighterProfile>& Roster = OpenStanceMenuContent::GetRoster();
	const FOpenStanceMenuSession& Current = Session;
	const FString ChungName = Roster.IsValidIndex(Current.ChungFighter) ? Roster[Current.ChungFighter].Name : FString();
	const FString HongName = Roster.IsValidIndex(Current.HongFighter) ? Roster[Current.HongFighter].Name : FString();
	GetMatchModel()->Reset(ChungName, HongName);

	OnMatchRequested.Broadcast(BuildMatchSetup());
	if (bRememberCurrent)
	{
		ShowScreen(EOpenStanceMenuScreen::Match);
	}
	else
	{
		ReplaceScreen(EOpenStanceMenuScreen::Match);
	}
}

void UOpenStanceMenuSubsystem::Present(EOpenStanceMenuScreen Screen)
{
	RemoveDialog();

	APlayerController* Controller = GetOwningController();
	const TSubclassOf<UOpenStanceScreen> ScreenClass = GetScreenClass(Screen);
	if (!Controller || !ScreenClass)
	{
		UE_LOG(LogOpenStanceMenu, Warning, TEXT("Cannot show menu screen %s: no player controller or screen class"), *UEnum::GetValueAsString(Screen));
		return;
	}

	if (ActiveScreen)
	{
		ActiveScreen->RemoveFromParent();
		ActiveScreen = nullptr;
	}

	UE_LOG(LogOpenStanceMenu, Log, TEXT("Showing menu screen %s"), *UEnum::GetValueAsString(Screen));
	CurrentScreen = Screen;
	UOpenStanceScreen* NewScreen = CreateWidget<UOpenStanceScreen>(Controller, ScreenClass);
	if (!NewScreen)
	{
		return;
	}
	NewScreen->InitScreen(this, Screen);
	NewScreen->AddToPlayerScreen(ScreenZOrder);
	NewScreen->FocusDefault();
	ActiveScreen = NewScreen;
	ApplyInputMode(Screen);
}

void UOpenStanceMenuSubsystem::ApplyInputMode(EOpenStanceMenuScreen Screen)
{
	APlayerController* Controller = GetOwningController();
	if (!Controller)
	{
		return;
	}

	Controller->bShowMouseCursor = true;
	if (Screen == EOpenStanceMenuScreen::Match || Screen == EOpenStanceMenuScreen::RefereeMatch)
	{
		// The HUD takes menu keys first; everything else falls through to gameplay input
		FInputModeGameAndUI InputMode;
		InputMode.SetHideCursorDuringCapture(false);
		Controller->SetInputMode(InputMode);
	}
	else
	{
		Controller->SetInputMode(FInputModeUIOnly());
	}
}

void UOpenStanceMenuSubsystem::ShowDialog(FOpenStanceDialogRequest Request)
{
	if (!DialogScreen)
	{
		RememberFocus();
	}
	RemoveDialog();

	APlayerController* Controller = GetOwningController();
	if (!Controller)
	{
		return;
	}

	UOpenStanceDialogScreen* Dialog = CreateWidget<UOpenStanceDialogScreen>(Controller, UOpenStanceDialogScreen::StaticClass());
	Dialog->InitScreen(this, EOpenStanceMenuScreen::None);
	Dialog->SetRequest(MoveTemp(Request));
	Dialog->AddToPlayerScreen(DialogZOrder);
	Dialog->FocusDefault();
	DialogScreen = Dialog;
}

void UOpenStanceMenuSubsystem::RemoveDialog()
{
	if (DialogScreen)
	{
		DialogScreen->RemoveFromParent();
		DialogScreen = nullptr;
	}
}

void UOpenStanceMenuSubsystem::RememberFocus()
{
	const ULocalPlayer* LocalPlayer = GetLocalPlayer();
	const TSharedPtr<const FSlateUser> SlateUser = LocalPlayer ? LocalPlayer->GetSlateUser() : nullptr;
	FocusBeforeDialog = SlateUser ? SlateUser->GetFocusedWidget() : nullptr;
}

void UOpenStanceMenuSubsystem::CloseDialog()
{
	if (!DialogScreen)
	{
		return;
	}
	RemoveDialog();

	if (CurrentScreen == EOpenStanceMenuScreen::Match && MatchModel)
	{
		MatchModel->SetPaused(false);
	}

	// Back to the item that opened the dialog, or the screen's first item if it is gone
	ULocalPlayer* LocalPlayer = GetLocalPlayer();
	const TSharedPtr<SWidget> Previous = FocusBeforeDialog.Pin();
	if (LocalPlayer && Previous.IsValid())
	{
		LocalPlayer->GetSlateOperations().SetUserFocus(Previous.ToSharedRef());
	}
	else if (ActiveScreen)
	{
		ActiveScreen->FocusDefault();
	}
}

bool UOpenStanceMenuSubsystem::IsDialogOpen() const
{
	return DialogScreen != nullptr;
}

FOpenStanceDialogRequest UOpenStanceMenuSubsystem::MakePauseRequest()
{
	FOpenStanceDialogRequest Request;
	Request.Title = TEXT("Paused");
	Request.Buttons =
	{
		{ TEXT("Resume"), nullptr, false },
		{ TEXT("Move list"), [this]()
			{
				Session.ControlsTabIndex = FMath::Max(0, OpenStanceMenuContent::FindControlTab(TEXT("Standing kicks")));
				ShowScreenFromMatch(EOpenStanceMenuScreen::Controls);
			}, false },
		{ TEXT("Controls"), [this]()
			{
				Session.ControlsTabIndex = 0;
				ShowScreenFromMatch(EOpenStanceMenuScreen::Controls);
			}, false },
		{ TEXT("Options"), [this]() { ShowScreenFromMatch(EOpenStanceMenuScreen::Options); }, false },
		{ TEXT("Restart"), [this]() { StartMatch(false); }, false },
		{ TEXT("Quit match"), [this]() { ShowQuitMatchDialog(); }, true }
	};
	return Request;
}

FOpenStanceDialogRequest UOpenStanceMenuSubsystem::MakeQuitGameRequest()
{
	FOpenStanceDialogRequest Request;
	Request.Title = TEXT("Quit game?");
	Request.Message = TEXT("Settings and created fighters are already saved.");
	Request.Buttons =
	{
		{ TEXT("Quit to title"), [this]() { StartMenuFlow(); }, true },
		{ TEXT("Cancel"), nullptr, false }
	};
	return Request;
}

FOpenStanceDialogRequest UOpenStanceMenuSubsystem::MakeQuitMatchRequest()
{
	FOpenStanceDialogRequest Request;
	Request.Title = TEXT("Quit match?");
	Request.Message = TEXT("The match will not be saved.");
	Request.Buttons =
	{
		{ TEXT("Quit to main menu"), [this]() { ReturnToMain(); }, true },
		{ TEXT("Cancel"), [this]() { ShowPauseMenu(); }, false }
	};
	return Request;
}

void UOpenStanceMenuSubsystem::ShowPauseMenu()
{
	if (IsDialogOpen())
	{
		return;
	}
	ShowDialog(MakePauseRequest());
	GetMatchModel()->SetPaused(true);
}

void UOpenStanceMenuSubsystem::ShowQuitGameDialog()
{
	ShowDialog(MakeQuitGameRequest());
}

void UOpenStanceMenuSubsystem::ShowQuitMatchDialog()
{
	ShowDialog(MakeQuitMatchRequest());
	GetMatchModel()->SetPaused(true);
}

FOpenStanceMatchSetup UOpenStanceMenuSubsystem::BuildMatchSetup() const
{
	const TArray<FOpenStanceFighterProfile>& Roster = OpenStanceMenuContent::GetRoster();

	FOpenStanceMatchSetup Setup;
	Setup.Mode = Session.Mode;
	if (Roster.IsValidIndex(Session.ChungFighter))
	{
		Setup.Chung = Roster[Session.ChungFighter];
	}
	if (Roster.IsValidIndex(Session.HongFighter))
	{
		Setup.Hong = Roster[Session.HongFighter];
	}

	const EOpenStanceMenuScreen SetupScreen = Session.Mode == EOpenStanceMatchMode::Tournament ? EOpenStanceMenuScreen::Tournament
		: Session.Mode == EOpenStanceMatchMode::Referee ? EOpenStanceMenuScreen::RefereeSetup
		: EOpenStanceMenuScreen::Sparring;
	if (const OpenStanceMenuContent::FSetupDefinition* Definition = OpenStanceMenuContent::FindSetup(SetupScreen))
	{
		for (const OpenStanceMenuContent::FChoiceRow& Row : Definition->Rows)
		{
			const int32 Index = GetChoiceIndex(SetupScreen, Row.Id, Row.DefaultIndex);
			if (Row.Values.IsValidIndex(Index))
			{
				Setup.Choices.Add(Row.Id, Row.Values[Index]);
			}
		}
	}
	return Setup;
}

UOpenStanceMatchModel* UOpenStanceMenuSubsystem::GetMatchModel()
{
	if (!MatchModel)
	{
		MatchModel = NewObject<UOpenStanceMatchModel>(this);
		MatchModel->Reset(FString(), FString());
	}
	return MatchModel;
}

UOpenStanceUserSettings* UOpenStanceMenuSubsystem::GetUserSettings() const
{
	return UOpenStanceUserSettings::Get();
}

FName UOpenStanceMenuSubsystem::MakeChoiceKey(EOpenStanceMenuScreen Screen, FName RowId)
{
	return FName(*FString::Printf(TEXT("%s.%s"), *UEnum::GetValueAsString(Screen), *RowId.ToString()));
}

int32 UOpenStanceMenuSubsystem::GetChoiceIndex(EOpenStanceMenuScreen Screen, FName RowId, int32 DefaultIndex) const
{
	const int32* Found = Session.Choices.Find(MakeChoiceKey(Screen, RowId));
	return Found ? *Found : DefaultIndex;
}

void UOpenStanceMenuSubsystem::SetChoiceIndex(EOpenStanceMenuScreen Screen, FName RowId, int32 Index)
{
	Session.Choices.Add(MakeChoiceKey(Screen, RowId), Index);
}

UOpenStanceScreen* UOpenStanceMenuSubsystem::CreateScreenForCapture(UWorld* World, EOpenStanceMenuScreen Screen)
{
	const TSubclassOf<UOpenStanceScreen> ScreenClass = GetScreenClass(Screen);
	if (!World || !ScreenClass)
	{
		return nullptr;
	}
	UOpenStanceScreen* Widget = CreateWidget<UOpenStanceScreen>(World, ScreenClass);
	Widget->InitScreen(this, Screen);
	Widget->SetAnimateIn(false);
	return Widget;
}

UOpenStanceScreen* UOpenStanceMenuSubsystem::CreateDialogForCapture(UWorld* World, FOpenStanceDialogRequest Request)
{
	if (!World)
	{
		return nullptr;
	}
	UOpenStanceDialogScreen* Dialog = CreateWidget<UOpenStanceDialogScreen>(World, UOpenStanceDialogScreen::StaticClass());
	Dialog->InitScreen(this, EOpenStanceMenuScreen::None);
	Dialog->SetRequest(MoveTemp(Request));
	return Dialog;
}

namespace
{
	UOpenStanceMenuSubsystem* FindMenu(UWorld* World)
	{
		const ULocalPlayer* LocalPlayer = World ? World->GetFirstLocalPlayerFromController() : nullptr;
		return LocalPlayer ? LocalPlayer->GetSubsystem<UOpenStanceMenuSubsystem>() : nullptr;
	}

	// Console shortcuts for jumping around the menu while developing and for scripted checks of the flow
	FAutoConsoleCommandWithWorldAndArgs ShowScreenCommand(
		TEXT("OpenStance.Menu.Show"),
		TEXT("Opens a menu screen by name, e.g. OpenStance.Menu.Show Controls"),
		FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
		{
			UOpenStanceMenuSubsystem* Menu = FindMenu(World);
			const int64 Value = Args.IsEmpty() ? INDEX_NONE : StaticEnum<EOpenStanceMenuScreen>()->GetValueByNameString(Args[0]);
			if (Menu && Value != INDEX_NONE)
			{
				Menu->ShowScreen(static_cast<EOpenStanceMenuScreen>(Value));
			}
			else
			{
				UE_LOG(LogOpenStanceMenu, Warning, TEXT("OpenStance.Menu.Show needs a screen name (Title, Main, Sparring, ...) and a local player"));
			}
		}));

	FAutoConsoleCommandWithWorldAndArgs BackScreenCommand(
		TEXT("OpenStance.Menu.Back"),
		TEXT("Goes back one menu screen, as the B button does"),
		FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
		{
			if (UOpenStanceMenuSubsystem* Menu = FindMenu(World))
			{
				Menu->GoBack();
			}
		}));
}
