#include "Menu/Screens/OpenStanceResultsScreen.h"

#include "Menu/OpenStanceMatchModel.h"
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
	/** "Chung 0 · Hong 1 (Gam-jeom: grabbing)" */
	FString DescribePenalties(const UOpenStanceMatchModel& Model)
	{
		FString Text = FString::Printf(TEXT("Chung %d · Hong %d"), Model.GetGamJeom(EOpenStanceSide::Chung), Model.GetGamJeom(EOpenStanceSide::Hong));
		TArray<FString> Reasons = Model.GetPenaltyReasons(EOpenStanceSide::Chung);
		Reasons.Append(Model.GetPenaltyReasons(EOpenStanceSide::Hong));
		if (!Reasons.IsEmpty())
		{
			Text += FString::Printf(TEXT(" (Gam-jeom: %s)"), *FString::Join(Reasons, TEXT(", ")).ToLower());
		}
		return Text;
	}
}

TSharedRef<SWidget> UOpenStanceResultsScreen::BuildContent()
{
	UOpenStanceMenuSubsystem* Menu = GetMenu();
	if (!Menu)
	{
		return SNullWidget::NullWidget;
	}
	const UOpenStanceMatchModel& Model = *Menu->GetMatchModel();

	const EOpenStanceSide Winner = Model.GetWinner();
	const bool bChungWon = Winner == EOpenStanceSide::Chung;
	const FLinearColor WinnerColour = bChungWon ? Palette::Chung : Palette::Hong;
	const FTextSpec BigSpec{ EFont::Display, 3.0f, 0.03f, false };

	// Left: winner and round scores
	TSharedRef<SVerticalBox> RoundRows = SNew(SVerticalBox);
	for (int32 Round = 1; Round <= UOpenStanceMatchModel::RoundCount; ++Round)
	{
		RoundRows->AddSlot().AutoHeight().Padding(0.0f, Round == 1 ? 0.0f : U(0.7f), 0.0f, 0.0f)
		[
			StatRow(FString::Printf(TEXT("Round %d"), Round), SNullWidget::NullWidget,
				FString::Printf(TEXT("%d–%d"), Model.GetRoundScore(EOpenStanceSide::Chung, Round), Model.GetRoundScore(EOpenStanceSide::Hong, Round)))
		];
	}

	const TSharedRef<SWidget> WinnerCard = Card(TEXT("Winner"),
		SNew(SVerticalBox)
		+ SVerticalBox::Slot().AutoHeight()
		[
			MakeText(Model.GetFighterName(Winner), BigSpec, WinnerColour)
		]
		+ SVerticalBox::Slot().AutoHeight().Padding(0.0f, U(0.7f), 0.0f, 0.0f)
		[
			SNew(SHorizontalBox)
			+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
			[
				MakeText(FString::FromInt(Model.GetScore(EOpenStanceSide::Chung)), BigSpec, Palette::Chung)
			]
			+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(U(1.6f), 0.0f)
			[
				MakeText(TEXT("–"), { EFont::Display, 2.4f }, Palette::Mute)
			]
			+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
			[
				MakeText(FString::FromInt(Model.GetScore(EOpenStanceSide::Hong)), BigSpec, Palette::Hong)
			]
		],
		WinnerColour);

	// Right: technique breakdown, penalties and the three next steps
	TSharedRef<SVerticalBox> Techniques = SNew(SVerticalBox);
	const TArray<TPair<FString, int32>> ByTechnique = Model.GetPointsByTechnique();
	const int32 MostPoints = ByTechnique.IsEmpty() ? 1 : ByTechnique[0].Value;
	for (int32 Index = 0; Index < FMath::Min(ByTechnique.Num(), 5); ++Index)
	{
		const float Fraction = static_cast<float>(ByTechnique[Index].Value) / MostPoints;
		Techniques->AddSlot().AutoHeight().Padding(0.0f, Index == 0 ? 0.0f : U(0.7f), 0.0f, 0.0f)
		[
			StatRow(ByTechnique[Index].Key, Bar(Fraction, Palette::Chung), FString::FromInt(ByTechnique[Index].Value))
		];
	}

	// In a tournament the next step is the bracket, which shows the result and the next pairing
	const bool bTournament = Menu->GetSession().Mode == EOpenStanceMatchMode::Tournament;
	TSharedRef<SOpenStanceOption> Rematch = SNew(SOpenStanceOption)
		.Label(bTournament ? TEXT("View bracket") : TEXT("Rematch"))
		.FontSize(1.6f)
		.OnPressed(FSimpleDelegate::CreateWeakLambda(this, [Menu, bTournament]()
		{
			if (bTournament)
			{
				Menu->ShowScreen(EOpenStanceMenuScreen::Bracket);
			}
			else
			{
				Menu->StartMatch();
			}
		}));
	SetDefaultFocus(Rematch);

	return SNew(SVerticalBox)
		+ SVerticalBox::Slot().AutoHeight()
		[
			Head(TEXT("Match over"), TEXT("Results"))
		]
		+ SVerticalBox::Slot().FillHeight(1.0f).Padding(0.0f, U(1.6f), 0.0f, 0.0f)
		[
			SNew(SHorizontalBox)
			+ SHorizontalBox::Slot().AutoWidth()
			[
				SNew(SBox).WidthOverride(U(40.0f))
				[
					SNew(SVerticalBox)
					+ SVerticalBox::Slot().AutoHeight()
					[
						WinnerCard
					]
					+ SVerticalBox::Slot().AutoHeight().Padding(0.0f, U(0.8f), 0.0f, 0.0f)
					[
						Card(TEXT("Round scores"), RoundRows)
					]
				]
			]
			+ SHorizontalBox::Slot().FillWidth(1.0f).Padding(U(2.4f), 0.0f, 0.0f, 0.0f)
			[
				SNew(SVerticalBox)
				+ SVerticalBox::Slot().AutoHeight()
				[
					Card(TEXT("Points by technique"), Techniques)
				]
				+ SVerticalBox::Slot().AutoHeight().Padding(0.0f, U(0.8f), 0.0f, 0.0f)
				[
					Card(TEXT("Penalties"), Paragraph(DescribePenalties(Model)))
				]
				+ SVerticalBox::Slot().FillHeight(1.0f)
				[
					SNew(SBox).VAlign(VAlign_Bottom)
					[
						SNew(SHorizontalBox)
						+ SHorizontalBox::Slot().FillWidth(1.0f)
						[
							Rematch
						]
						+ SHorizontalBox::Slot().FillWidth(1.0f).Padding(U(0.8f), 0.0f, 0.0f, 0.0f)
						[
							SNew(SOpenStanceOption)
							.Label(TEXT("Change fighters"))
							.FontSize(1.6f)
							.OnPressed(FSimpleDelegate::CreateWeakLambda(this, [Menu]() { Menu->ShowScreen(EOpenStanceMenuScreen::FighterSelect); }))
						]
						+ SHorizontalBox::Slot().FillWidth(1.0f).Padding(U(0.8f), 0.0f, 0.0f, 0.0f)
						[
							SNew(SOpenStanceOption)
							.Label(TEXT("Main menu"))
							.FontSize(1.6f)
							.OnPressed(FSimpleDelegate::CreateWeakLambda(this, [Menu]() { Menu->ReturnToMain(); }))
						]
					]
				]
			]
		];
}
