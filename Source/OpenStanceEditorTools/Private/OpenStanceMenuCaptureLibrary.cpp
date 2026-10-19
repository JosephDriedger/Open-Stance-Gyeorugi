#include "OpenStanceMenuCaptureLibrary.h"

#include "Editor.h"
#include "Engine/LocalPlayer.h"
#include "Engine/TextureRenderTarget2D.h"
#include "ImageUtils.h"
#include "Menu/OpenStanceMatchModel.h"
#include "Menu/OpenStanceMenuContent.h"
#include "Menu/OpenStanceMenuSubsystem.h"
#include "Menu/OpenStanceScreen.h"
#include "Misc/FileHelper.h"
#include "Slate/WidgetRenderer.h"
#include "Widgets/SOverlay.h"
#include "UObject/StrongObjectPtr.h"

DEFINE_LOG_CATEGORY_STATIC(LogOpenStanceMenuCapture, Log, All);

namespace
{
	TMap<FString, FString> ParseState(const FString& State)
	{
		TMap<FString, FString> Pairs;
		TArray<FString> Entries;
		State.ParseIntoArray(Entries, TEXT(";"));
		for (const FString& Entry : Entries)
		{
			FString Key;
			FString Value;
			if (Entry.Split(TEXT("="), &Key, &Value))
			{
				Pairs.Add(Key.TrimStartAndEnd().ToLower(), Value.TrimStartAndEnd().ToLower());
			}
		}
		return Pairs;
	}

	/** The prototype's in-progress match: 7 to 4 in round 2 with 1:12 left, Chung's stamina 58% and Hong's 22%. */
	void ApplyHudSample(UOpenStanceMatchModel& Model)
	{
		const TArray<FOpenStanceFighterProfile>& Roster = OpenStanceMenuContent::GetRoster();
		Model.Reset(Roster[0].Name, Roster[1].Name);
		Model.SetClock(2, 72.0f);
		Model.AddPoints(EOpenStanceSide::Chung, 3, TEXT("Axe kick"), true);
		Model.AddPoints(EOpenStanceSide::Chung, 4, TEXT("Spinning hook"), false);
		Model.AddPoints(EOpenStanceSide::Hong, 4, TEXT("Back kick"), false);
		Model.SetStamina(EOpenStanceSide::Chung, 0.58f);
		Model.SetStamina(EOpenStanceSide::Hong, 0.22f);
		Model.SetCall(TEXT("Head kick"), TEXT("3 points"), TEXT(" · "));
	}
}

bool UOpenStanceMenuCaptureLibrary::CaptureScreen(EOpenStanceMenuScreen Screen, const FString& OutputPath, const FString& State, int32 Width, int32 Height)
{
	UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
	if (!World)
	{
		UE_LOG(LogOpenStanceMenuCapture, Error, TEXT("No editor world to create the widget in"));
		return false;
	}

	// A subsystem on a local player that was never added to a game is enough: it only holds the menu session and the match model
	TStrongObjectPtr<ULocalPlayer> LocalPlayer(NewObject<ULocalPlayer>(GEngine, GEngine->LocalPlayerClass));
	TStrongObjectPtr<UOpenStanceMenuSubsystem> Menu(NewObject<UOpenStanceMenuSubsystem>(LocalPlayer.Get()));
	const TMap<FString, FString> Options = ParseState(State);

	FOpenStanceMenuSession& Session = Menu->GetSession();
	if (const FString* Value = Options.Find(TEXT("hub")))
	{
		Session.MainHubIndex = FCString::Atoi(**Value);
	}
	if (const FString* Value = Options.Find(TEXT("controls_tab")))
	{
		Session.ControlsTabIndex = FCString::Atoi(**Value);
	}
	if (const FString* Value = Options.Find(TEXT("options_tab")))
	{
		Session.OptionsTabIndex = FCString::Atoi(**Value);
	}
	if (const FString* Value = Options.Find(TEXT("category")))
	{
		const EOpenStanceSex Sex = *Value == TEXT("women") ? EOpenStanceSex::Female : EOpenStanceSex::Male;
		const TArray<int32> Indices = OpenStanceMenuContent::GetRosterIndices(Sex);
		Session.Category = Sex;
		Session.ChungFighter = Indices[0];
		Session.HongFighter = Indices[1];
	}
	if (const FString* Value = Options.Find(TEXT("sex")))
	{
		Session.CareerAppearance.Sex = *Value == TEXT("female") ? EOpenStanceSex::Female : EOpenStanceSex::Male;
	}
	if (const FString* Value = Options.Find(TEXT("gear")))
	{
		Session.CareerAppearance.bGearOn = *Value != TEXT("0");
	}
	if (const FString* Value = Options.Find(TEXT("mode")))
	{
		Session.Mode = *Value == TEXT("tournament") ? EOpenStanceMatchMode::Tournament : EOpenStanceMatchMode::Sparring;
	}
	if (const FString* Value = Options.Find(TEXT("sample")))
	{
		UOpenStanceMatchModel* Model = Menu->GetMatchModel();
		const TArray<FOpenStanceFighterProfile>& Roster = OpenStanceMenuContent::GetRoster();
		if (*Value == TEXT("results"))
		{
			Model->Reset(Roster[0].Name, Roster[1].Name);
			Model->PopulateSample();
		}
		else
		{
			ApplyHudSample(*Model);
		}
	}

	const FString* FocusOption = Options.Find(TEXT("focus"));
	const bool bShowFocus = !FocusOption || *FocusOption != TEXT("0");

	// A screen, a dialog over a screen (dialog=pause, quit_game or quit_match), or a dialog alone (Screen None)
	TStrongObjectPtr<UOpenStanceScreen> Widget;
	TStrongObjectPtr<UOpenStanceScreen> Dialog;
	TSharedRef<SOverlay> Composite = SNew(SOverlay);
	if (Screen != EOpenStanceMenuScreen::None)
	{
		Widget.Reset(Menu->CreateScreenForCapture(World, Screen));
		if (!Widget.IsValid())
		{
			UE_LOG(LogOpenStanceMenuCapture, Error, TEXT("No screen class for %s"), *UEnum::GetValueAsString(Screen));
			return false;
		}
		Composite->AddSlot()[Widget->TakeWidget()];
		if (bShowFocus)
		{
			Widget->PreviewFocus();
		}
	}
	if (const FString* DialogOption = Options.Find(TEXT("dialog")))
	{
		FOpenStanceDialogRequest Request = *DialogOption == TEXT("quit_game") ? Menu->MakeQuitGameRequest()
			: *DialogOption == TEXT("quit_match") ? Menu->MakeQuitMatchRequest()
			: Menu->MakePauseRequest();
		Dialog.Reset(Menu->CreateDialogForCapture(World, MoveTemp(Request)));
		Composite->AddSlot()[Dialog->TakeWidget()];
		if (bShowFocus)
		{
			Dialog->PreviewFocus();
		}
	}
	const TSharedRef<SWidget> SlateWidget = Composite;

	// Slate applies the display gamma itself, so the target is linear: a gamma-tagged target would encode twice
	TStrongObjectPtr<UTextureRenderTarget2D> Target(NewObject<UTextureRenderTarget2D>());
	Target->InitCustomFormat(Width, Height, PF_B8G8R8A8, true);

	FWidgetRenderer Renderer(true);

	// Wrapped text and flow layouts size themselves from the width they were given the frame before, so draw a few
	// frames and keep the last, as a running game would show
	for (int32 Frame = 0; Frame < 3; ++Frame)
	{
		Renderer.DrawWidget(Target.Get(), SlateWidget, FVector2D(Width, Height), 0.0f);
	}
	FlushRenderingCommands();

	IFileManager::Get().MakeDirectory(*FPaths::GetPath(OutputPath), true);
	const TUniquePtr<FArchive> Archive(IFileManager::Get().CreateFileWriter(*OutputPath));
	if (!Archive.IsValid() || !FImageUtils::ExportRenderTarget2DAsPNG(Target.Get(), *Archive))
	{
		UE_LOG(LogOpenStanceMenuCapture, Error, TEXT("Could not write %s"), *OutputPath);
		return false;
	}
	return true;
}
