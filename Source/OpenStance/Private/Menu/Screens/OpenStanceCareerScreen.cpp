#include "Menu/Screens/OpenStanceCareerScreen.h"

#include "Menu/OpenStanceMenuContent.h"
#include "Menu/OpenStanceMenuSubsystem.h"
#include "Menu/OpenStanceMenuTheme.h"
#include "Menu/Slate/SOpenStanceFrame.h"
#include "Menu/Slate/SOpenStanceItems.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/SOverlay.h"

using namespace OpenStanceMenu;
using namespace OpenStanceMenuWidgets;

namespace
{
	enum class EWeekKind : uint8
	{
		Training,
		Event,
		Grading
	};

	struct FWeek
	{
		FString Label;
		EWeekKind Kind;
		FString Name;
	};

	/** One week in the season calendar (.wk). */
	TSharedRef<SWidget> MakeWeek(const FWeek& Week, bool bCurrent)
	{
		FLinearColor Fill = Palette::Panel2;
		FLinearColor TextColor = Palette::Bone;
		if (Week.Kind == EWeekKind::Event)
		{
			Fill = Palette::HongDark;
			TextColor = FLinearColor::White;
		}
		else if (Week.Kind == EWeekKind::Grading)
		{
			Fill = Palette::ChungDark;
			TextColor = FLinearColor::White;
		}

		return SNew(SOpenStanceFrame)
			.Fill(Palette::Panel)
			.OutlineColor(bCurrent ? Palette::Warn : FLinearColor::Transparent)
			.OutlineThickness(U(0.25f))
			.Padding(FMargin(U(0.8f)))
			[
				SNew(SVerticalBox)
				+ SVerticalBox::Slot().AutoHeight()
				[
					MakeText(Week.Label, { EFont::Display, 1.2f, 0.1f, false }, Palette::Bone)
				]
				+ SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Left).Padding(0.0f, U(0.4f), 0.0f, 0.0f)
				[
					SNew(SOpenStanceFrame)
					.Fill(Fill)
					.Padding(FMargin(U(0.5f), U(0.3f)))
					[
						MakeText(Week.Name, { EFont::Body, 1.0f }, TextColor)
					]
				]
			];
	}
}

TArray<FOpenStanceHint> UOpenStanceCareerScreen::GetHints() const
{
	return
	{
		{ TEXT("A"), EOpenStanceGlyphLook::A, TEXT("Select") },
		{ TEXT("B"), EOpenStanceGlyphLook::B, TEXT("Back") },
		{ TEXT("Y"), EOpenStanceGlyphLook::Y, TEXT("Advance week") }
	};
}

TSharedRef<SWidget> UOpenStanceCareerScreen::BuildContent()
{
	const UOpenStanceMenuSubsystem* Menu = GetMenu();
	const FString Name = Menu ? Menu->GetSession().CareerName : FString(TEXT("Jae-won Choi"));

	const auto Open = [this](EOpenStanceMenuScreen Screen)
	{
		return FSimpleDelegate::CreateWeakLambda(this, [this, Screen]()
		{
			if (UOpenStanceMenuSubsystem* MenuSubsystem = GetMenu())
			{
				MenuSubsystem->ShowScreen(Screen);
			}
		});
	};

	TSharedPtr<SOpenStanceInteractive> FirstItem;
	TSharedRef<SVerticalBox> Actions = SNew(SVerticalBox);
	const auto AddAction = [&Actions, &FirstItem](const TSharedRef<SOpenStanceOption>& Item)
	{
		if (!FirstItem.IsValid())
		{
			FirstItem = Item;
		}
		Actions->AddSlot().AutoHeight().Padding(0.0f, U(0.8f), 0.0f, 0.0f)
		[
			Item
		];
	};
	AddAction(SNew(SOpenStanceOption).Label(TEXT("Training slots")));
	AddAction(SNew(SOpenStanceOption).Label(TEXT("Enter event")).Small(TEXT("City Open")));
	AddAction(SNew(SOpenStanceOption).Label(TEXT("Grading")));
	AddAction(SNew(SOpenStanceOption).Label(TEXT("Post-match review")));
	AddAction(SNew(SOpenStanceOption).Label(TEXT("Fighter creator")).Small(TEXT("Look and gear")).OnPressed(Open(EOpenStanceMenuScreen::Customize)));
	AddAction(SNew(SOpenStanceOption).Label(TEXT("Long-term career")).TagWidget(FutureTag()).OnPressed(Open(EOpenStanceMenuScreen::LongTerm)));
	SetDefaultFocus(FirstItem);

	const TArray<FWeek> Weeks =
	{
		{ TEXT("Wk 1"), EWeekKind::Training, TEXT("Footwork block") },
		{ TEXT("Wk 2"), EWeekKind::Training, TEXT("Sparring block") },
		{ TEXT("Wk 3"), EWeekKind::Event, TEXT("City Open") },
		{ TEXT("Wk 4"), EWeekKind::Training, TEXT("Rest") },
		{ TEXT("Wk 5"), EWeekKind::Training, TEXT("Kick power") },
		{ TEXT("Wk 6"), EWeekKind::Grading, TEXT("Grading: blue belt") },
		{ TEXT("Wk 7"), EWeekKind::Training, TEXT("Counter drills") },
		{ TEXT("Wk 8"), EWeekKind::Event, TEXT("Regional Cup") }
	};
	const int32 CurrentWeek = 2;

	TSharedRef<SVerticalBox> Calendar = SNew(SVerticalBox);
	for (int32 Row = 0; Row < 2; ++Row)
	{
		TSharedRef<SHorizontalBox> RowBox = SNew(SHorizontalBox);
		for (int32 Column = 0; Column < 4; ++Column)
		{
			const int32 WeekIndex = Row * 4 + Column;
			RowBox->AddSlot().FillWidth(1.0f).Padding(Column == 0 ? 0.0f : U(0.6f), 0.0f, 0.0f, 0.0f)
			[
				MakeWeek(Weeks[WeekIndex], WeekIndex == CurrentWeek)
			];
		}
		Calendar->AddSlot().FillHeight(1.0f).Padding(0.0f, Row == 0 ? 0.0f : U(0.6f), 0.0f, 0.0f)
		[
			RowBox
		];
	}

	TSharedRef<SWidget> Body = SNew(SVerticalBox)
		+ SVerticalBox::Slot().AutoHeight()
		[
			Head(TEXT("Progress"), TEXT("Career"))
		]
		+ SVerticalBox::Slot().FillHeight(1.0f).Padding(0.0f, U(1.6f), 0.0f, 0.0f)
		[
			SNew(SHorizontalBox)
			+ SHorizontalBox::Slot().AutoWidth()
			[
				SNew(SBox).WidthOverride(U(26.0f))
				[
					SNew(SVerticalBox)
					+ SVerticalBox::Slot().AutoHeight()
					[
						Card(Name,
							SNew(SVerticalBox)
							+ SVerticalBox::Slot().AutoHeight()
							[
								SNew(SHorizontalBox)
								+ SHorizontalBox::Slot().AutoWidth().Padding(0.0f, 0.0f, U(0.8f), 0.0f)[Tag(TEXT("Your fighter"))]
								+ SHorizontalBox::Slot().AutoWidth().Padding(0.0f, 0.0f, U(0.8f), 0.0f)[Tag(TEXT("Green belt"))]
								+ SHorizontalBox::Slot().AutoWidth()[Tag(TEXT("OVR 74"))]
							]
							+ SVerticalBox::Slot().AutoHeight().Padding(0.0f, U(0.7f), 0.0f, 0.0f)
							[
								StatRow(TEXT("Season"), Bar(0.35f, Palette::Ok), TEXT("3/8"))
							])
					]
					+ SVerticalBox::Slot().AutoHeight()
					[
						Actions
					]
				]
			]
			+ SHorizontalBox::Slot().FillWidth(1.0f).Padding(U(2.4f), 0.0f, 0.0f, 0.0f)
			[
				SNew(SVerticalBox)
				+ SVerticalBox::Slot().AutoHeight().Padding(0.0f, 0.0f, 0.0f, U(0.8f))
				[
					Kicker(TEXT("Season calendar · sample"))
				]
				+ SVerticalBox::Slot().FillHeight(1.0f)
				[
					Calendar
				]
			]
		];

	return SNew(SOverlay)
		+ SOverlay::Slot()
		[
			Body
		]
		+ SOverlay::Slot().HAlign(HAlign_Right).VAlign(VAlign_Top)
		[
			PlayerBar(Name, TEXT("Your fighter · Green belt · OVR 74"), TEXT("JC"))
		];
}
