#include "Menu/OpenStanceScreen.h"

#include "Engine/LocalPlayer.h"
#include "InputCoreTypes.h"
#include "Menu/OpenStanceMenuSubsystem.h"
#include "Menu/OpenStanceMenuTheme.h"
#include "Menu/Slate/SOpenStanceArt.h"
#include "Menu/Slate/SOpenStanceFrame.h"
#include "Menu/Slate/SOpenStanceInteractive.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SScaleBox.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/SOverlay.h"

using namespace OpenStanceMenu;

namespace
{
	/** The prototype's screen-in animation: 0.22 s of fade and a 1u slide from the left. */
	constexpr float SlideSeconds = 0.22f;

	bool IsBackKey(const FKey& Key)
	{
		return Key == EKeys::Gamepad_FaceButton_Right || Key == EKeys::Escape || Key == EKeys::BackSpace;
	}

	bool IsPreviousTabKey(const FKey& Key)
	{
		return Key == EKeys::Gamepad_LeftShoulder || Key == EKeys::Q || Key == EKeys::PageUp || Key == EKeys::LeftBracket;
	}

	bool IsNextTabKey(const FKey& Key)
	{
		return Key == EKeys::Gamepad_RightShoulder || Key == EKeys::E || Key == EKeys::PageDown || Key == EKeys::RightBracket;
	}
}

void UOpenStanceScreen::InitScreen(UOpenStanceMenuSubsystem* InMenu, EOpenStanceMenuScreen InScreenId)
{
	OwningMenu = InMenu;
	ScreenId = InScreenId;
}

TSharedRef<SWidget> UOpenStanceScreen::RebuildWidget()
{
	DefaultFocus.Reset();
	const TSharedRef<SWidget> Content = BuildContent();

	TSharedRef<SOverlay> Canvas = SNew(SOverlay)
		+ SOverlay::Slot().Padding(GetContentPadding())
		[
			Content
		];

	const TArray<FOpenStanceHint> Hints = GetHints();
	if (!Hints.IsEmpty())
	{
		Canvas->AddSlot().VAlign(VAlign_Bottom)
		[
			SNew(SBox)
			.HeightOverride(U(4.4f))
			[
				SNew(SOpenStanceFrame)
				.Gradient(OpenStanceMenuPaint::FGradient::TwoColor(0.0f, Palette::Shade, FLinearColor(Palette::Shade.R, Palette::Shade.G, Palette::Shade.B, 0.0f)))
				.Padding(FMargin(U(4.0f), 0.0f))
				[
					SNew(SHorizontalBox)
					+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
					[
						OpenStanceMenuWidgets::HintBar(Hints)
					]
				]
			]
		];
	}

	return SNew(SOverlay)
		+ SOverlay::Slot()
		[
			BuildBackground()
		]
		+ SOverlay::Slot()
		[
			SNew(SScaleBox)
			.Stretch(EStretch::ScaleToFit)
			[
				SNew(SBox)
				.WidthOverride(DesignWidth)
				.HeightOverride(DesignHeight)
				[
					Canvas
				]
			]
		];
}

void UOpenStanceScreen::ReleaseSlateResources(bool bReleaseChildren)
{
	Super::ReleaseSlateResources(bReleaseChildren);
	DefaultFocus.Reset();
}

void UOpenStanceScreen::NativeConstruct()
{
	Super::NativeConstruct();
	TimeOnScreen = bAnimateIn ? 0.0f : SlideSeconds;
	if (bAnimateIn)
	{
		SetRenderOpacity(0.0f);
	}
}

void UOpenStanceScreen::NativeTick(const FGeometry& MyGeometry, float InDeltaTime)
{
	Super::NativeTick(MyGeometry, InDeltaTime);
	if (!bAnimateIn || TimeOnScreen >= SlideSeconds)
	{
		return;
	}

	TimeOnScreen += InDeltaTime;
	const float Alpha = FMath::InterpEaseOut(0.0f, 1.0f, FMath::Clamp(TimeOnScreen / SlideSeconds, 0.0f, 1.0f), 2.0f);
	SetRenderOpacity(Alpha);
	SetRenderTranslation(FVector2D(-U(1.0f) * (1.0f - Alpha), 0.0f));
}

FReply UOpenStanceScreen::NativeOnKeyDown(const FGeometry& InGeometry, const FKeyEvent& InKeyEvent)
{
	const FKey Key = InKeyEvent.GetKey();
	if (IsBackKey(Key))
	{
		HandleBack();
		return FReply::Handled();
	}
	if (IsPreviousTabKey(Key))
	{
		HandleTabStep(-1);
		return FReply::Handled();
	}
	if (IsNextTabKey(Key))
	{
		HandleTabStep(1);
		return FReply::Handled();
	}
	return Super::NativeOnKeyDown(InGeometry, InKeyEvent);
}

TSharedRef<SWidget> UOpenStanceScreen::BuildBackground()
{
	return SNew(SOpenStanceBackdrop);
}

TArray<FOpenStanceHint> UOpenStanceScreen::GetHints() const
{
	return StandardHints();
}

FMargin UOpenStanceScreen::GetContentPadding() const
{
	return FMargin(U(4.0f), U(3.2f), U(4.0f), U(6.5f));
}

void UOpenStanceScreen::HandleBack()
{
	if (UOpenStanceMenuSubsystem* MenuSubsystem = GetMenu())
	{
		MenuSubsystem->GoBack();
	}
}

void UOpenStanceScreen::SetDefaultFocus(const TSharedPtr<SOpenStanceInteractive>& Widget)
{
	DefaultFocus = Widget;
}

void UOpenStanceScreen::FocusDefault()
{
	// Screens with nothing to focus (the title, the HUD) take the keys themselves
	if (const TSharedPtr<SOpenStanceInteractive> Item = DefaultFocus.Pin())
	{
		FocusWidget(Item);
	}
	else
	{
		FocusWidget(GetCachedWidget());
	}
}

void UOpenStanceScreen::PreviewFocus()
{
	if (const TSharedPtr<SOpenStanceInteractive> Item = DefaultFocus.Pin())
	{
		Item->SetPreviewActive(true);
	}
}

void UOpenStanceScreen::FocusWidget(const TSharedPtr<SWidget>& Widget) const
{
	ULocalPlayer* LocalPlayer = GetOwningLocalPlayer();
	if (LocalPlayer && Widget.IsValid())
	{
		// Queued rather than immediate: the screen may have been added to the viewport this same frame
		LocalPlayer->GetSlateOperations().SetUserFocus(Widget.ToSharedRef());
	}
}

TArray<FOpenStanceHint> UOpenStanceScreen::StandardHints()
{
	return
	{
		{ TEXT("A"), EOpenStanceGlyphLook::A, TEXT("Select") },
		{ TEXT("B"), EOpenStanceGlyphLook::B, TEXT("Back") }
	};
}

TArray<FOpenStanceHint> UOpenStanceScreen::SelectHints()
{
	return
	{
		{ TEXT("A"), EOpenStanceGlyphLook::A, TEXT("Select") },
		{ TEXT("B"), EOpenStanceGlyphLook::B, TEXT("Back") },
		{ TEXT("↔"), EOpenStanceGlyphLook::Neutral, TEXT("Change value") }
	};
}

TArray<FOpenStanceHint> UOpenStanceScreen::TabHints(const FString& PreviousCaption, const FString& NextCaption)
{
	return
	{
		{ TEXT("A"), EOpenStanceGlyphLook::A, TEXT("Select") },
		{ TEXT("B"), EOpenStanceGlyphLook::B, TEXT("Back") },
		{ TEXT("LB"), EOpenStanceGlyphLook::Neutral, PreviousCaption },
		{ TEXT("RB"), EOpenStanceGlyphLook::Neutral, NextCaption }
	};
}
