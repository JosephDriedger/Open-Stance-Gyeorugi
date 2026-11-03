#include "Menu/Screens/OpenStanceSideSelectScreen.h"

#include "InputCoreTypes.h"
#include "Menu/OpenStanceMenuContent.h"
#include "Menu/OpenStanceMenuSubsystem.h"
#include "Menu/OpenStanceMenuTheme.h"
#include "Menu/Slate/SOpenStanceArt.h"
#include "Menu/Slate/SOpenStanceFrame.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/SBoxPanel.h"

using namespace OpenStanceMenu;
using namespace OpenStanceMenuWidgets;

namespace
{
	/** The Sparring setup's Players row: 0 is "1P vs AI", 1 is "1P vs 2P". */
	constexpr int32 TwoPlayerIndex = 1;

	FOpenStanceFighterProfile GetFighterOnSide(const UOpenStanceMenuSubsystem* Menu, EOpenStanceSide Side)
	{
		const TArray<FOpenStanceFighterProfile>& Roster = OpenStanceMenuContent::GetRoster();
		const int32 Index = Menu ? (Side == EOpenStanceSide::Chung ? Menu->GetSession().ChungFighter : Menu->GetSession().HongFighter) : 0;
		return Roster.IsValidIndex(Index) ? Roster[Index] : FOpenStanceFighterProfile();
	}

	bool IsLeftKey(const FKey& Key)
	{
		return Key == EKeys::Gamepad_DPad_Left || Key == EKeys::Gamepad_LeftStick_Left || Key == EKeys::Left || Key == EKeys::A;
	}

	bool IsRightKey(const FKey& Key)
	{
		return Key == EKeys::Gamepad_DPad_Right || Key == EKeys::Gamepad_LeftStick_Right || Key == EKeys::Right || Key == EKeys::D;
	}

	bool IsConfirmKey(const FKey& Key)
	{
		return Key == EKeys::Gamepad_FaceButton_Bottom || Key == EKeys::Enter || Key == EKeys::SpaceBar;
	}
}

UOpenStanceSideSelectScreen::UOpenStanceSideSelectScreen(const FObjectInitializer& ObjectInitializer)
	: Super(ObjectInitializer)
{
	// Nothing here takes menu focus: the screen reads left, right and A itself, like the match HUD reads its keys.
	SetIsFocusable(true);
}

TArray<FOpenStanceHint> UOpenStanceSideSelectScreen::GetHints() const
{
	return
	{
		{ TEXT("LS"), EOpenStanceGlyphLook::Neutral, TEXT("Choose Side") },
		{ TEXT("A"), EOpenStanceGlyphLook::A, TEXT("Continue") },
		{ TEXT("B"), EOpenStanceGlyphLook::B, TEXT("Back") }
	};
}

bool UOpenStanceSideSelectScreen::IsTwoPlayer() const
{
	const UOpenStanceMenuSubsystem* Menu = GetMenu();
	return Menu && Menu->GetChoiceIndex(EOpenStanceMenuScreen::Sparring, TEXT("Players"), 0) == TwoPlayerIndex;
}

void UOpenStanceSideSelectScreen::ChooseSide(EOpenStanceSide Side)
{
	if (UOpenStanceMenuSubsystem* Menu = GetMenu())
	{
		Menu->GetSession().PlayerSide = Side;
	}
}

FReply UOpenStanceSideSelectScreen::NativeOnKeyDown(const FGeometry& InGeometry, const FKeyEvent& InKeyEvent)
{
	const FKey Key = InKeyEvent.GetKey();
	if (IsLeftKey(Key))
	{
		ChooseSide(EOpenStanceSide::Chung);
		return FReply::Handled();
	}
	if (IsRightKey(Key))
	{
		ChooseSide(EOpenStanceSide::Hong);
		return FReply::Handled();
	}
	if (IsConfirmKey(Key))
	{
		if (UOpenStanceMenuSubsystem* Menu = GetMenu())
		{
			Menu->ShowScreen(EOpenStanceMenuScreen::FighterSelect);
		}
		return FReply::Handled();
	}
	return Super::NativeOnKeyDown(InGeometry, InKeyEvent);
}

TSharedRef<SWidget> UOpenStanceSideSelectScreen::BuildSide(EOpenStanceSide Side)
{
	const bool bChung = Side == EOpenStanceSide::Chung;
	const FLinearColor Colour = bChung ? Palette::Chung : Palette::Hong;
	const FLinearColor Dark = bChung ? Palette::ChungDark : Palette::HongDark;
	TWeakObjectPtr<UOpenStanceSideSelectScreen> WeakThis(this);

	const auto Fighter = [WeakThis, Side]()
	{
		const UOpenStanceSideSelectScreen* Screen = WeakThis.Get();
		return GetFighterOnSide(Screen ? Screen->GetMenu() : nullptr, Side);
	};

	// A controller marker under the fighter it drives: P1 on the chosen side, P2 on the other when there are two players.
	const auto Marker = [WeakThis, Side](const TCHAR* Label, bool bPlayerTwo)
	{
		return SNew(SBox)
			.Visibility_Lambda([WeakThis, Side, bPlayerTwo]()
			{
				const UOpenStanceSideSelectScreen* Screen = WeakThis.Get();
				const UOpenStanceMenuSubsystem* Menu = Screen ? Screen->GetMenu() : nullptr;
				if (!Menu)
				{
					return EVisibility::Hidden;
				}
				const bool bPlayerOneHere = Menu->GetSession().PlayerSide == Side;
				const bool bShow = bPlayerTwo ? (Screen->IsTwoPlayer() && !bPlayerOneHere) : bPlayerOneHere;
				return bShow ? EVisibility::Visible : EVisibility::Hidden;
			})
			[
				SNew(SOpenStanceFrame)
				.Fill(Palette::Bone)
				.Padding(FMargin(U(2.0f), U(0.7f)))
				[
					MakeText(Label, { EFont::Display, 2.2f, 0.1f, true }, Hex(0x0b1424))
				]
			];
	};

	return SNew(SBox)
		.WidthOverride(U(25.0f))
		[
			SNew(SVerticalBox)
			+ SVerticalBox::Slot().AutoHeight()
			[
				MakeText(bChung ? TEXT("Chung") : TEXT("Hong"), { EFont::Display, 2.4f, 0.1f, false }, Colour)
			]
			+ SVerticalBox::Slot().AutoHeight().Padding(0.0f, U(0.3f), 0.0f, 0.0f)
			[
				MakeText(bChung ? TEXT("Blue · Left") : TEXT("Red · Right"), { EFont::BodyBold, 1.05f, 0.2f, true }, Palette::Mute)
			]
			+ SVerticalBox::Slot().FillHeight(1.0f).MaxHeight(U(26.0f)).Padding(0.0f, U(0.8f), 0.0f, 0.0f)
			[
				SNew(SOpenStanceFrame)
				.Fill(Palette::Panel)
				.Padding(FMargin(U(1.0f)))
				[
					SNew(SOpenStanceFighterFigure)
					.BodyColor(Colour)
					.TrimColor(Dark)
					.GearOn(true)
					.Kick(bChung)
					.Sex_Lambda([Fighter]() { return Fighter().Sex; })
				]
			]
			+ SVerticalBox::Slot().AutoHeight().Padding(0.0f, U(0.8f), 0.0f, 0.0f)
			[
				MakeLiveText([Fighter]() { return Fighter().Name; }, { EFont::Display, 2.0f, 0.03f, false }, Palette::Bone)
			]
			+ SVerticalBox::Slot().AutoHeight().Padding(0.0f, U(1.0f), 0.0f, 0.0f).HAlign(HAlign_Center)
			[
				SNew(SHorizontalBox)
				+ SHorizontalBox::Slot().AutoWidth().Padding(0.0f, 0.0f, U(0.6f), 0.0f)
				[
					Marker(TEXT("P1"), false)
				]
				+ SHorizontalBox::Slot().AutoWidth()
				[
					Marker(TEXT("P2"), true)
				]
			]
		];
}

TSharedRef<SWidget> UOpenStanceSideSelectScreen::BuildContent()
{
	const UOpenStanceMenuSubsystem* Menu = GetMenu();
	const FString ModeName = Menu && Menu->GetSession().Mode == EOpenStanceMatchMode::Tournament ? TEXT("Tournament") : TEXT("Sparring");

	const TSharedRef<SWidget> Centre = SNew(SVerticalBox)
		+ SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Center)
		[
			MakeText(TEXT("←   →"), { EFont::Display, 4.0f, 0.0f, false }, Palette::Bone)
		]
		+ SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Center).Padding(0.0f, U(1.0f), 0.0f, 0.0f)
		[
			MakeText(TEXT("Move Your Controller to Pick a Side"), { EFont::BodyBold, 1.2f, 0.15f, true }, Palette::Bone)
		]
		+ SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Center).Padding(0.0f, U(0.6f), 0.0f, 0.0f)
		[
			MakeLiveText([WeakThis = TWeakObjectPtr<UOpenStanceSideSelectScreen>(this)]()
			{
				const UOpenStanceSideSelectScreen* Screen = WeakThis.Get();
				return Screen && Screen->IsTwoPlayer() ? FString(TEXT("Player 2 Takes the Other Side")) : FString(TEXT("The AI Takes the Other Side"));
			}, { EFont::Body, 1.1f, 0.0f, false }, Palette::Mute)
		];

	return SNew(SVerticalBox)
		+ SVerticalBox::Slot().AutoHeight()
		[
			Head(ModeName, TEXT("Choose Your Side"))
		]
		+ SVerticalBox::Slot().FillHeight(1.0f).Padding(0.0f, U(1.6f), 0.0f, 0.0f)
		[
			SNew(SHorizontalBox)
			+ SHorizontalBox::Slot().AutoWidth()
			[
				BuildSide(EOpenStanceSide::Chung)
			]
			+ SHorizontalBox::Slot().FillWidth(1.0f).Padding(U(2.4f), 0.0f)
			[
				SNew(SBox).VAlign(VAlign_Center)
				[
					Centre
				]
			]
			+ SHorizontalBox::Slot().AutoWidth()
			[
				BuildSide(EOpenStanceSide::Hong)
			]
		];
}
