#include "Menu/Screens/OpenStanceTitleScreen.h"

#include "InputCoreTypes.h"
#include "Menu/OpenStanceMenuSubsystem.h"
#include "Menu/OpenStanceMenuTheme.h"
#include "Misc/App.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/SBoxPanel.h"

using namespace OpenStanceMenu;
using namespace OpenStanceMenuWidgets;

UOpenStanceTitleScreen::UOpenStanceTitleScreen(const FObjectInitializer& ObjectInitializer)
	: Super(ObjectInitializer)
{
	// The title has nothing to focus, so the screen itself takes the key presses
	SetIsFocusable(true);
}

TArray<FOpenStanceHint> UOpenStanceTitleScreen::GetHints() const
{
	return TArray<FOpenStanceHint>();
}

TSharedRef<SWidget> UOpenStanceTitleScreen::BuildContent()
{
	const FTextSpec LogoSpec{ EFont::DisplayItalic, 11.0f, 0.06f, true };
	const FTextSpec OpenSpec{ EFont::Display, 11.0f, 0.06f, true };

	// The prompt blinks: bright for the first half of every 1.6 s, dim for the second
	const TAttribute<FSlateColor> PromptColor = TAttribute<FSlateColor>::CreateLambda([]()
	{
		const bool bBright = FMath::Fmod(FApp::GetCurrentTime(), 1.6) < 0.8;
		return FSlateColor(FLinearColor(Palette::Bone.R, Palette::Bone.G, Palette::Bone.B, bBright ? 1.0f : 0.25f));
	});

	return SNew(SBox)
		.HAlign(HAlign_Center)
		.VAlign(VAlign_Center)
		[
			SNew(SVerticalBox)
			+ SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Center)
			[
				SNew(SHorizontalBox)
				+ SHorizontalBox::Slot().AutoWidth()
				[
					MakeText(TEXT("Open"), OpenSpec, Palette::Chung)
				]
				+ SHorizontalBox::Slot().AutoWidth().Padding(U(2.0f), 0.0f, 0.0f, 0.0f)
				[
					MakeText(TEXT("Stance"), LogoSpec, Palette::Hong)
				]
				+ SHorizontalBox::Slot().AutoWidth()
				[
					MakeText(TEXT(":"), LogoSpec, Palette::Bone)
				]
			]
			+ SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Center).Padding(0.0f, U(1.0f), 0.0f, 0.0f)
			[
				MakeText(TEXT("Gyeorugi"), { EFont::DisplayItalic, 6.2f, 0.26f, true }, Palette::Bone)
			]
			+ SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Center).Padding(0.0f, U(4.2f), 0.0f, 0.0f)
			[
				MakeText(TEXT("Press any button to start"), { EFont::Display, 1.7f, 0.4f, true }, PromptColor)
			]
		];
}

FReply UOpenStanceTitleScreen::NativeOnKeyDown(const FGeometry& InGeometry, const FKeyEvent& InKeyEvent)
{
	const FKey Key = InKeyEvent.GetKey();
	if (Key == EKeys::Tab || Key.IsModifierKey())
	{
		return FReply::Unhandled();
	}
	Proceed();
	return FReply::Handled();
}

FReply UOpenStanceTitleScreen::NativeOnMouseButtonDown(const FGeometry& InGeometry, const FPointerEvent& InMouseEvent)
{
	Proceed();
	return FReply::Handled();
}

void UOpenStanceTitleScreen::Proceed()
{
	if (UOpenStanceMenuSubsystem* Menu = GetMenu())
	{
		Menu->ShowScreen(EOpenStanceMenuScreen::Main);
	}
}
