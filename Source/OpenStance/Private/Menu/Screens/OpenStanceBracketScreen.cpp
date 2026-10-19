#include "Menu/Screens/OpenStanceBracketScreen.h"

#include "Menu/OpenStanceMenuSubsystem.h"
#include "Menu/OpenStanceMenuTheme.h"
#include "Menu/Slate/SOpenStanceFrame.h"
#include "Menu/Slate/SOpenStanceItems.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/SBoxPanel.h"

using namespace OpenStanceMenu;
using namespace OpenStanceMenuWidgets;

namespace
{
	/** One fighter in a pairing. Score is a dash while the match is still to play. */
	struct FBracketSlot
	{
		FString Name;
		FString Score;
		bool bWon = false;
		bool bLost = false;
	};

	struct FBracketMatch
	{
		FBracketSlot Top;
		FBracketSlot Bottom;
		bool bNext = false;
	};

	FBracketMatch Played(const TCHAR* TopName, int32 TopScore, const TCHAR* BottomName, int32 BottomScore)
	{
		FBracketMatch Match;
		Match.Top = { TopName, FString::FromInt(TopScore), TopScore > BottomScore, TopScore < BottomScore };
		Match.Bottom = { BottomName, FString::FromInt(BottomScore), BottomScore > TopScore, BottomScore < TopScore };
		return Match;
	}

	FBracketMatch ToPlay(const TCHAR* TopName, const TCHAR* BottomName, bool bNext = false)
	{
		FBracketMatch Match;
		Match.Top = { TopName, TEXT("—"), false, false };
		Match.Bottom = { BottomName, TEXT("—"), false, false };
		Match.bNext = bNext;
		return Match;
	}

	TSharedRef<SWidget> MakeSlot(const FBracketSlot& Slot, bool bFirst)
	{
		return SNew(SOpenStanceFrame)
			.Fill(Slot.bWon ? Palette::Panel2 : Palette::Panel)
			.AccentColor(Palette::Line)
			.AccentEdge(bFirst ? EOpenStanceFrameEdge::None : EOpenStanceFrameEdge::Top)
			.AccentThickness(1.5f)
			.Padding(FMargin(U(0.9f), U(0.5f)))
			[
				SNew(SHorizontalBox)
				+ SHorizontalBox::Slot().FillWidth(1.0f)
				[
					MakeText(Slot.Name, { EFont::BodyBold, 1.15f }, Slot.bLost ? Palette::Mute : Palette::Bone)
				]
				+ SHorizontalBox::Slot().AutoWidth()
				[
					MakeText(Slot.Score, { EFont::BodyBold, 1.15f }, Slot.bLost ? Palette::Mute : Palette::Bone)
				]
			];
	}

	TSharedRef<SWidget> MakeRound(const TArray<FBracketMatch>& Matches)
	{
		TSharedRef<SVerticalBox> Round = SNew(SVerticalBox);
		for (const FBracketMatch& Match : Matches)
		{
			// Equal cells with the pairing centred in each space the rounds out evenly, as the prototype does
			Round->AddSlot().FillHeight(1.0f).VAlign(VAlign_Center)
			[
				SNew(SOpenStanceFrame)
				.OutlineColor(Match.bNext ? Palette::Warn : FLinearColor::Transparent)
				.OutlineThickness(U(0.25f))
				[
					SNew(SVerticalBox)
					+ SVerticalBox::Slot().AutoHeight()
					[
						MakeSlot(Match.Top, true)
					]
					+ SVerticalBox::Slot().AutoHeight()
					[
						MakeSlot(Match.Bottom, false)
					]
				]
			];
		}
		return Round;
	}
}

TSharedRef<SWidget> UOpenStanceBracketScreen::BuildContent()
{
	const TArray<FBracketMatch> QuarterFinals =
	{
		Played(TEXT("Min-jun Park"), 2, TEXT("Joon Lee"), 0),
		Played(TEXT("Sofia Reyes"), 3, TEXT("Tomas Silva"), 1),
		Played(TEXT("Dae-ho Kim"), 1, TEXT("Aiko Tanaka"), 2),
		Played(TEXT("Amara Okafor"), 2, TEXT("Leo Martin"), 0)
	};
	const TArray<FBracketMatch> SemiFinals = { ToPlay(TEXT("Min-jun Park"), TEXT("Sofia Reyes"), true), ToPlay(TEXT("Aiko Tanaka"), TEXT("Amara Okafor")) };
	const TArray<FBracketMatch> Final = { ToPlay(TEXT("TBD"), TEXT("TBD")) };

	TSharedRef<SOpenStanceOption> NextMatch = SNew(SOpenStanceOption)
		.Label(TEXT("Next match: Park vs Reyes"))
		.Look(EOpenStanceOptionLook::Primary)
		.OnPressed(FSimpleDelegate::CreateWeakLambda(this, [this]()
		{
			if (UOpenStanceMenuSubsystem* Menu = GetMenu())
			{
				Menu->StartMatch();
			}
		}));
	SetDefaultFocus(NextMatch);

	return SNew(SVerticalBox)
		+ SVerticalBox::Slot().AutoHeight()
		[
			Head(TEXT("Tournament · 8 fighters · World Taekwondo"), TEXT("Bracket"))
		]
		+ SVerticalBox::Slot().FillHeight(1.0f).Padding(0.0f, U(1.6f), 0.0f, 0.0f)
		[
			SNew(SHorizontalBox)
			+ SHorizontalBox::Slot().FillWidth(1.0f)
			[
				MakeRound(QuarterFinals)
			]
			+ SHorizontalBox::Slot().FillWidth(1.0f).Padding(U(2.0f), 0.0f)
			[
				MakeRound(SemiFinals)
			]
			+ SHorizontalBox::Slot().FillWidth(1.0f)
			[
				MakeRound(Final)
			]
		]
		+ SVerticalBox::Slot().AutoHeight().Padding(0.0f, U(1.6f), 0.0f, 0.0f)
		[
			SNew(SHorizontalBox)
			+ SHorizontalBox::Slot().AutoWidth()
			[
				NextMatch
			]
		];
}
