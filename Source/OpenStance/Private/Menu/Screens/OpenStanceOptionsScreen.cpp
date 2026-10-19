#include "Menu/Screens/OpenStanceOptionsScreen.h"

#include "GameFramework/GameUserSettings.h"
#include "Menu/OpenStanceMenuSubsystem.h"
#include "Menu/OpenStanceMenuTheme.h"
#include "Menu/OpenStanceUserSettings.h"
#include "Menu/Slate/SOpenStanceFrame.h"
#include "Menu/Slate/SOpenStanceItems.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SWidgetSwitcher.h"
#include "Widgets/SBoxPanel.h"

using namespace OpenStanceMenu;
using namespace OpenStanceMenuWidgets;

namespace
{
	const TCHAR* const TabNames[] = { TEXT("Audio"), TEXT("Video"), TEXT("Controls"), TEXT("Accessibility") };

	const TArray<FIntPoint>& GetResolutions()
	{
		static const TArray<FIntPoint> Resolutions = { FIntPoint(1920, 1080), FIntPoint(2560, 1440), FIntPoint(3840, 2160) };
		return Resolutions;
	}

	/** Frame-rate caps in the prototype's order; zero means unlimited. */
	const TArray<float>& GetFrameRateCaps()
	{
		static const TArray<float> Caps = { 30.0f, 60.0f, 120.0f, 0.0f };
		return Caps;
	}

	const TArray<EWindowMode::Type>& GetWindowModes()
	{
		static const TArray<EWindowMode::Type> Modes = { EWindowMode::Fullscreen, EWindowMode::WindowedFullscreen, EWindowMode::Windowed };
		return Modes;
	}
}

TArray<FOpenStanceHint> UOpenStanceOptionsScreen::GetHints() const
{
	return SelectHints();
}

UOpenStanceUserSettings* UOpenStanceOptionsScreen::GetSettings() const
{
	const UOpenStanceMenuSubsystem* Menu = GetMenu();
	UOpenStanceUserSettings* Settings = Menu ? Menu->GetUserSettings() : nullptr;

	// Without the registered class (the settings are not wired in DefaultEngine.ini) the screen still works on defaults
	return Settings ? Settings : GetMutableDefault<UOpenStanceUserSettings>();
}

void UOpenStanceOptionsScreen::Commit(bool bVideoChanged) const
{
	UOpenStanceUserSettings* Settings = GetSettings();
	if (Settings && Settings == UGameUserSettings::GetGameUserSettings())
	{
		Settings->CommitChanges(bVideoChanged);
	}
}

void UOpenStanceOptionsScreen::RegisterFirstRow(const TSharedRef<SOpenStanceInteractive>& Row)
{
	// Every row registers; BuildContent keeps only the first one built for each tab
	FirstRows.Add(Row);
}

TSharedRef<SOpenStanceInteractive> UOpenStanceOptionsScreen::MakeChoiceRow(const FString& Label, const TArray<FString>& Values, TFunction<int32()> Get, TFunction<void(int32)> Set, bool bFuture, bool bVideo)
{
	const auto Cycle = [this, Values, Get, Set, bVideo](int32 Direction)
	{
		Set((Get() + Direction + Values.Num()) % Values.Num());
		Commit(bVideo);
	};
	return SNew(SOpenStanceOption)
		.Label(Label)
		.TagWidget(bFuture ? FutureTag() : TSharedPtr<SWidget>())
		.Value_Lambda([Values, Get]() { return Values.IsValidIndex(Get()) ? Values[Get()] : FString(); })
		.OnPressed(FSimpleDelegate::CreateWeakLambda(this, [Cycle]() { Cycle(1); }))
		.OnStep(FOpenStanceStepDelegate::CreateWeakLambda(this, [Cycle](int32 Direction) { Cycle(Direction); }));
}

TSharedRef<SOpenStanceInteractive> UOpenStanceOptionsScreen::MakeToggleRow(const FString& Label, bool UOpenStanceUserSettings::* Setting, bool bOnFirst, bool bFuture)
{
	TWeakObjectPtr<UOpenStanceOptionsScreen> WeakThis(this);
	const auto Settings = [WeakThis]() -> UOpenStanceUserSettings*
	{
		const UOpenStanceOptionsScreen* Screen = WeakThis.Get();
		return Screen ? Screen->GetSettings() : nullptr;
	};

	const TArray<FString> Values = bOnFirst ? TArray<FString>{ TEXT("On"), TEXT("Off") } : TArray<FString>{ TEXT("Off"), TEXT("On") };
	return MakeChoiceRow(Label, Values,
		[Settings, Setting, bOnFirst]()
		{
			const UOpenStanceUserSettings* Current = Settings();
			const bool bOn = Current && Current->*Setting;
			return bOn == bOnFirst ? 0 : 1;
		},
		[Settings, Setting, bOnFirst](int32 Index)
		{
			if (UOpenStanceUserSettings* Current = Settings())
			{
				Current->*Setting = (Index == 0) == bOnFirst;
			}
		},
		bFuture);
}

TSharedRef<SOpenStanceInteractive> UOpenStanceOptionsScreen::MakeSliderRow(const FString& Label, float UOpenStanceUserSettings::* Setting, float Min, float Max, float Step,
	TFunction<FString(float)> Format, bool bFuture)
{
	TWeakObjectPtr<UOpenStanceOptionsScreen> WeakThis(this);
	return SNew(SOpenStanceSliderRow)
		.Label(Label)
		.Min(Min)
		.Max(Max)
		.Step(Step)
		.Format(Format)
		.TagWidget(bFuture ? FutureTag() : TSharedPtr<SWidget>())
		.Value_Lambda([WeakThis, Setting]()
		{
			const UOpenStanceOptionsScreen* Screen = WeakThis.Get();
			const UOpenStanceUserSettings* Settings = Screen ? Screen->GetSettings() : nullptr;
			return Settings ? Settings->*Setting : 0.0f;
		})
		.OnValueChanged(SOpenStanceSliderRow::FOnValueChanged::CreateWeakLambda(this, [this, Setting, Step](float NewValue)
		{
			if (UOpenStanceUserSettings* Settings = GetSettings())
			{
				// Snap to the step so dragging lands on the values the readout shows
				Settings->*Setting = FMath::GridSnap(NewValue, Step);
				Commit(false);
			}
		}));
}

TSharedRef<SWidget> UOpenStanceOptionsScreen::BuildAudioTab()
{
	const auto Percent = [](float Value) { return FString::FromInt(FMath::RoundToInt(Value)); };
	TSharedRef<SVerticalBox> Rows = SNew(SVerticalBox);
	const auto Add = [this, &Rows](const TSharedRef<SOpenStanceInteractive>& Row)
	{
		RegisterFirstRow(Row);
		Rows->AddSlot().AutoHeight().Padding(0.0f, Rows->NumSlots() == 0 ? 0.0f : U(0.8f), 0.0f, 0.0f)[Row];
	};
	Add(MakeSliderRow(TEXT("Master"), &UOpenStanceUserSettings::MasterVolume, 0.0f, 100.0f, 5.0f, Percent));
	Add(MakeSliderRow(TEXT("Effects"), &UOpenStanceUserSettings::EffectsVolume, 0.0f, 100.0f, 5.0f, Percent));
	Add(MakeSliderRow(TEXT("Referee voice"), &UOpenStanceUserSettings::RefereeVoiceVolume, 0.0f, 100.0f, 5.0f, Percent));
	Add(MakeSliderRow(TEXT("Crowd"), &UOpenStanceUserSettings::CrowdVolume, 0.0f, 100.0f, 5.0f, Percent));
	Add(MakeSliderRow(TEXT("Music"), &UOpenStanceUserSettings::MusicVolume, 0.0f, 100.0f, 5.0f, Percent));
	Add(MakeSliderRow(TEXT("Commentary"), &UOpenStanceUserSettings::CommentaryVolume, 0.0f, 100.0f, 5.0f, Percent, true));
	return Rows;
}

TSharedRef<SWidget> UOpenStanceOptionsScreen::BuildVideoTab()
{
	TWeakObjectPtr<UOpenStanceOptionsScreen> WeakThis(this);
	const auto Settings = [WeakThis]() -> UOpenStanceUserSettings*
	{
		const UOpenStanceOptionsScreen* Screen = WeakThis.Get();
		return Screen ? Screen->GetSettings() : nullptr;
	};

	TSharedRef<SVerticalBox> Rows = SNew(SVerticalBox);
	const auto Add = [this, &Rows](const TSharedRef<SOpenStanceInteractive>& Row)
	{
		RegisterFirstRow(Row);
		Rows->AddSlot().AutoHeight().Padding(0.0f, Rows->NumSlots() == 0 ? 0.0f : U(0.8f), 0.0f, 0.0f)[Row];
	};

	Add(MakeChoiceRow(TEXT("Resolution"), { TEXT("1920×1080"), TEXT("2560×1440"), TEXT("3840×2160") },
		[Settings]()
		{
			const UOpenStanceUserSettings* Current = Settings();
			return Current ? FMath::Max(0, GetResolutions().IndexOfByKey(Current->GetScreenResolution())) : 0;
		},
		[Settings](int32 Index)
		{
			if (UOpenStanceUserSettings* Current = Settings())
			{
				Current->SetScreenResolution(GetResolutions()[Index]);
			}
		}, false, true));
	Add(MakeChoiceRow(TEXT("Window mode"), { TEXT("Fullscreen"), TEXT("Borderless"), TEXT("Windowed") },
		[Settings]()
		{
			const UOpenStanceUserSettings* Current = Settings();
			return Current ? FMath::Max(0, GetWindowModes().IndexOfByKey(Current->GetFullscreenMode())) : 0;
		},
		[Settings](int32 Index)
		{
			if (UOpenStanceUserSettings* Current = Settings())
			{
				Current->SetFullscreenMode(GetWindowModes()[Index]);
			}
		}, false, true));
	Add(MakeChoiceRow(TEXT("Quality preset"), { TEXT("Low"), TEXT("Medium"), TEXT("High"), TEXT("Epic") },
		[Settings]()
		{
			// A custom scalability mix reports -1; show it as High, the prototype's default
			const UOpenStanceUserSettings* Current = Settings();
			const int32 Level = Current ? Current->GetOverallScalabilityLevel() : 2;
			return Level < 0 ? 2 : FMath::Min(Level, 3);
		},
		[Settings](int32 Index)
		{
			if (UOpenStanceUserSettings* Current = Settings())
			{
				Current->SetOverallScalabilityLevel(Index);
			}
		}, false, true));
	Add(MakeChoiceRow(TEXT("Frame-rate cap"), { TEXT("30"), TEXT("60"), TEXT("120"), TEXT("Unlimited") },
		[Settings]()
		{
			const UOpenStanceUserSettings* Current = Settings();
			const int32 Found = Current ? GetFrameRateCaps().IndexOfByPredicate([Current](float Cap) { return FMath::IsNearlyEqual(Cap, Current->GetFrameRateLimit()); }) : INDEX_NONE;
			return Found == INDEX_NONE ? 1 : Found;
		},
		[Settings](int32 Index)
		{
			if (UOpenStanceUserSettings* Current = Settings())
			{
				Current->SetFrameRateLimit(GetFrameRateCaps()[Index]);
			}
		}, false, true));
	Add(MakeChoiceRow(TEXT("V-sync"), { TEXT("On"), TEXT("Off") },
		[Settings]()
		{
			const UOpenStanceUserSettings* Current = Settings();
			return Current && !Current->IsVSyncEnabled() ? 1 : 0;
		},
		[Settings](int32 Index)
		{
			if (UOpenStanceUserSettings* Current = Settings())
			{
				Current->SetVSyncEnabled(Index == 0);
			}
		}, false, true));
	return Rows;
}

TSharedRef<SWidget> UOpenStanceOptionsScreen::BuildControlsTab()
{
	TSharedRef<SVerticalBox> Rows = SNew(SVerticalBox);
	const auto Add = [this, &Rows](const TSharedRef<SOpenStanceInteractive>& Row, float TopGap = U(0.8f))
	{
		RegisterFirstRow(Row);
		Rows->AddSlot().AutoHeight().Padding(0.0f, Rows->NumSlots() == 0 ? 0.0f : TopGap, 0.0f, 0.0f)[Row];
	};

	Add(MakeToggleRow(TEXT("Vibration"), &UOpenStanceUserSettings::bVibration, true));
	Add(MakeSliderRow(TEXT("Skill Stick dead zone"), &UOpenStanceUserSettings::SkillStickDeadZone, 0.0f, 40.0f, 1.0f,
		[](float Value) { return FString::Printf(TEXT("%d%%"), FMath::RoundToInt(Value)); }));
	Add(MakeSliderRow(TEXT("Stick input window"), &UOpenStanceUserSettings::StickInputWindow, 0.20f, 0.40f, 0.01f,
		[](float Value) { return FString::Printf(TEXT("%.2f s"), Value); }));
	Add(SNew(SOpenStanceOption)
		.Label(TEXT("Open controls reference"))
		.Small(TEXT("All inputs, by group"))
		.OnPressed(FSimpleDelegate::CreateWeakLambda(this, [this]()
		{
			if (UOpenStanceMenuSubsystem* Menu = GetMenu())
			{
				Menu->ShowScreen(EOpenStanceMenuScreen::Controls);
			}
		})), U(1.4f));
	Rows->AddSlot().AutoHeight().Padding(0.0f, U(0.8f), 0.0f, 0.0f)
	[
		MakeText(TEXT("Sticks and triggers are fixed in v1.0."), { EFont::Body, 1.0f }, Palette::Mute)
	];
	Add(SNew(SOpenStanceOption)
		.Label(TEXT("Button remapping"))
		.TagWidget(FutureTag())
		.Small(TEXT("Remap every button")));
	Add(MakeToggleRow(TEXT("Hold-to-toggle for held modifiers"), &UOpenStanceUserSettings::bHoldToToggleModifiers, false, true));
	return Rows;
}

TSharedRef<SWidget> UOpenStanceOptionsScreen::BuildAccessibilityTab()
{
	TSharedRef<SVerticalBox> Rows = SNew(SVerticalBox);
	const auto Add = [this, &Rows](const TSharedRef<SOpenStanceInteractive>& Row)
	{
		RegisterFirstRow(Row);
		Rows->AddSlot().AutoHeight().Padding(0.0f, Rows->NumSlots() == 0 ? 0.0f : U(0.8f), 0.0f, 0.0f)[Row];
	};

	Add(MakeToggleRow(TEXT("Subtitles for referee commands"), &UOpenStanceUserSettings::bRefereeSubtitles, true));
	Add(MakeToggleRow(TEXT("Reduced camera motion"), &UOpenStanceUserSettings::bReducedCameraMotion, false, true));
	Add(MakeToggleRow(TEXT("Reduced screen shake"), &UOpenStanceUserSettings::bReducedScreenShake, false, true));
	Add(MakeToggleRow(TEXT("Audio cues for incoming attacks"), &UOpenStanceUserSettings::bAudioCuesIncomingAttacks, false, true));
	Add(MakeToggleRow(TEXT("Audio cues for stamina state"), &UOpenStanceUserSettings::bAudioCuesStaminaState, false, true));
	Add(SNew(SOpenStanceOption)
		.Label(TEXT("Button remapping"))
		.TagWidget(FutureTag())
		.Small(TEXT("Remap every button")));
	return Rows;
}

TSharedRef<SWidget> UOpenStanceOptionsScreen::BuildContent()
{
	FirstRows.Reset();

	// Each tab builds its rows in turn; RegisterFirstRow keeps the first row of each
	const auto BuildTab = [this](int32 TabIndex) -> TSharedRef<SWidget>
	{
		const int32 Before = FirstRows.Num();
		TSharedRef<SWidget> Tab = SNullWidget::NullWidget;
		switch (TabIndex)
		{
		case 0:
			Tab = BuildAudioTab();
			break;
		case 1:
			Tab = BuildVideoTab();
			break;
		case 2:
			Tab = BuildControlsTab();
			break;
		default:
			Tab = BuildAccessibilityTab();
			break;
		}
		// Only the first registration of a tab is kept, so drop the rest
		if (FirstRows.Num() > Before + 1)
		{
			FirstRows.SetNum(Before + 1);
		}
		return Tab;
	};

	TWeakObjectPtr<UOpenStanceOptionsScreen> WeakThis(this);
	const auto GetTab = [WeakThis]()
	{
		const UOpenStanceOptionsScreen* Screen = WeakThis.Get();
		const UOpenStanceMenuSubsystem* Menu = Screen ? Screen->GetMenu() : nullptr;
		return Menu ? FMath::Clamp(Menu->GetSession().OptionsTabIndex, 0, UE_ARRAY_COUNT(TabNames) - 1) : 0;
	};

	TSharedRef<SWidgetSwitcher> Tabs = SNew(SWidgetSwitcher).WidgetIndex_Lambda(GetTab);
	for (int32 TabIndex = 0; TabIndex < UE_ARRAY_COUNT(TabNames); ++TabIndex)
	{
		Tabs->AddSlot()[BuildTab(TabIndex)];
	}

	TSharedRef<SHorizontalBox> Strip = SNew(SHorizontalBox);
	for (int32 TabIndex = 0; TabIndex < UE_ARRAY_COUNT(TabNames); ++TabIndex)
	{
		Strip->AddSlot().AutoWidth().Padding(TabIndex == 0 ? 0.0f : U(0.4f), 0.0f, 0.0f, 0.0f)
		[
			SNew(SOpenStanceOption)
			.Label(TabNames[TabIndex])
			.Padding(FMargin(U(2.0f), U(0.8f)))
			.Current_Lambda([GetTab, TabIndex]() { return GetTab() == TabIndex; })
			.OnPressed(FSimpleDelegate::CreateWeakLambda(this, [this, TabIndex]() { SelectTab(TabIndex); }))
		];
	}

	SetDefaultFocus(FirstRows.IsValidIndex(GetTab()) ? FirstRows[GetTab()].Pin() : nullptr);

	return SNew(SVerticalBox)
		+ SVerticalBox::Slot().AutoHeight()
		[
			Head(TEXT("Settings save automatically"), TEXT("Options"))
		]
		+ SVerticalBox::Slot().AutoHeight().Padding(0.0f, U(1.6f), 0.0f, 0.0f)
		[
			Strip
		]
		+ SVerticalBox::Slot().FillHeight(1.0f).Padding(0.0f, U(1.6f), 0.0f, 0.0f)
		[
			SNew(SHorizontalBox)
			+ SHorizontalBox::Slot().AutoWidth()
			[
				SNew(SBox)
				.WidthOverride(U(60.0f))
				[
					Tabs
				]
			]
		];
}

void UOpenStanceOptionsScreen::SelectTab(int32 TabIndex)
{
	UOpenStanceMenuSubsystem* Menu = GetMenu();
	if (!Menu || !FirstRows.IsValidIndex(TabIndex))
	{
		return;
	}
	Menu->GetSession().OptionsTabIndex = TabIndex;
	FocusWidget(FirstRows[TabIndex].Pin());
}

void UOpenStanceOptionsScreen::HandleTabStep(int32 Direction)
{
	const UOpenStanceMenuSubsystem* Menu = GetMenu();
	if (Menu)
	{
		const int32 Count = UE_ARRAY_COUNT(TabNames);
		SelectTab((Menu->GetSession().OptionsTabIndex + Direction + Count) % Count);
	}
}
