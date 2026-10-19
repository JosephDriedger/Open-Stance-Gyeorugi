#include "Menu/Screens/OpenStanceRefereeScreens.h"

#include "InputCoreTypes.h"
#include "Menu/OpenStanceMatchModel.h"
#include "Menu/OpenStanceMenuContent.h"
#include "Menu/OpenStanceMenuSubsystem.h"
#include "Menu/OpenStanceMenuTheme.h"
#include "Menu/Slate/SOpenStanceFrame.h"
#include "Menu/Slate/SOpenStanceItems.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SConstraintCanvas.h"
#include "Widgets/Layout/SWrapBox.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/SOverlay.h"

using namespace OpenStanceMenu;
using namespace OpenStanceMenuWidgets;

namespace
{
	struct FRefereeCommand
	{
		FString Input;
		FString Name;
	};

	/** Sets the model to the prototype's example: 7 to 4, round 2 with 1:12 left, referee about to call a break. */
	void ApplyExampleMatch(UOpenStanceMatchModel& Model)
	{
		const TArray<FOpenStanceFighterProfile>& Roster = OpenStanceMenuContent::GetRoster();
		Model.Reset(Roster[0].Name, Roster[1].Name);
		Model.SetClock(2, 72.0f);
		Model.AddPoints(EOpenStanceSide::Chung, 3, TEXT("Axe kick"), true);
		Model.AddPoints(EOpenStanceSide::Chung, 4, TEXT("Spinning hook"), false);
		Model.AddPoints(EOpenStanceSide::Hong, 4, TEXT("Back kick"), false);
		Model.SetCall(TEXT("You called"), TEXT("KAL-YEO · +2 correct call"), TEXT(" "));
	}

	/** One row of the rating table: a label, a count and a point change. */
	TSharedRef<SWidget> MakeRatingRow(const FString& Label, const FString& Count, const FString& Change, bool bTotal = false)
	{
		return SNew(SOpenStanceFrame)
			.AccentColor(Palette::Line)
			.AccentEdge(bTotal ? EOpenStanceFrameEdge::Top : EOpenStanceFrameEdge::None)
			.AccentThickness(1.5f)
			.Padding(FMargin(0.0f, bTotal ? U(0.5f) : 0.0f, 0.0f, 0.0f))
			[
				SNew(SHorizontalBox)
				+ SHorizontalBox::Slot().FillWidth(1.0f)
				[
					MakeText(Label, { EFont::Body, 1.05f }, Palette::Bone)
				]
				+ SHorizontalBox::Slot().AutoWidth()
				[
					SNew(SBox).WidthOverride(U(5.0f)).HAlign(HAlign_Right)
					[
						MakeText(Count, { EFont::Body, 1.05f }, Palette::Bone)
					]
				]
				+ SHorizontalBox::Slot().AutoWidth()
				[
					SNew(SBox).WidthOverride(U(6.0f)).HAlign(HAlign_Right)
					[
						MakeText(Change, { EFont::Body, 1.05f }, Palette::Bone)
					]
				]
			];
	}
}

// UOpenStanceRefereeMatchScreen

TArray<FOpenStanceHint> UOpenStanceRefereeMatchScreen::GetHints() const
{
	return
	{
		{ TEXT("A"), EOpenStanceGlyphLook::A, TEXT("End match (demo)") },
		{ TEXT("MENU"), EOpenStanceGlyphLook::Neutral, TEXT("Pause") }
	};
}

void UOpenStanceRefereeMatchScreen::NativeTick(const FGeometry& MyGeometry, float InDeltaTime)
{
	// The example match is static, so the HUD's demo clock stays off; only the animation in the base runs
	UOpenStanceScreen::NativeTick(MyGeometry, InDeltaTime);
}

FReply UOpenStanceRefereeMatchScreen::NativeOnKeyDown(const FGeometry& InGeometry, const FKeyEvent& InKeyEvent)
{
	const FKey Key = InKeyEvent.GetKey();
	if (Key == EKeys::Enter || Key == EKeys::SpaceBar || Key == EKeys::Gamepad_FaceButton_Bottom)
	{
		if (UOpenStanceMenuSubsystem* Menu = GetMenu())
		{
			Menu->ShowScreen(EOpenStanceMenuScreen::RefereeGrade);
		}
		return FReply::Handled();
	}
	return UOpenStanceScreen::NativeOnKeyDown(InGeometry, InKeyEvent);
}

TSharedRef<SWidget> UOpenStanceRefereeMatchScreen::BuildContent()
{
	const TWeakObjectPtr<UOpenStanceMatchModel> Model = GetModel();
	if (Model.IsValid())
	{
		ApplyExampleMatch(*Model);
	}

	const TArray<FRefereeCommand> Commands =
	{
		{ TEXT("A"), TEXT("SHI-JAK / KYE-SOK") },
		{ TEXT("B"), TEXT("KAL-YEO") },
		{ TEXT("Hold X, RS"), TEXT("GAM-JEOM") },
		{ TEXT("Y"), TEXT("KEU-MAN") },
		{ TEXT("Hold LT"), TEXT("Knockdown count") },
		{ TEXT("RT"), TEXT("Raise hand") },
		{ TEXT("D-pad ↑"), TEXT("CHARYEOT") },
		{ TEXT("D-pad ↓"), TEXT("JOON-BI") }
	};

	TSharedRef<SWrapBox> CommandBar = SNew(SWrapBox).UseAllottedSize(true).HAlign(HAlign_Center).InnerSlotPadding(FVector2D(U(1.4f), U(0.6f)));
	for (const FRefereeCommand& Command : Commands)
	{
		CommandBar->AddSlot()
		[
			SNew(SOpenStanceFrame)
			.Fill(Hex(0x05070b, 0.8f))
			.Padding(FMargin(U(0.8f), U(0.4f)))
			[
				SNew(SHorizontalBox)
				+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
				[
					InputLine(Command.Input, false, false)
				]
				+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(U(0.5f), 0.0f, 0.0f, 0.0f)
				[
					MakeText(Command.Name, { EFont::Display, 1.05f, 0.06f, true }, Palette::Bone)
				]
			]
		];
	}

	const TSharedRef<SWidget> RatingPanel = SNew(SBox)
		.WidthOverride(U(24.0f))
		[
			SNew(SVerticalBox)
			+ SVerticalBox::Slot().AutoHeight()
			[
				SNew(SHorizontalBox)
				+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
				[
					MakeText(TEXT("Referee rating"), { EFont::Display, 1.2f, 0.1f, true }, Palette::Bone)
				]
				+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(U(0.6f), 0.0f, 0.0f, 0.0f)
				[
					FutureTag()
				]
			]
			+ SVerticalBox::Slot().AutoHeight().Padding(0.0f, U(0.5f), 0.0f, 0.0f)
			[
				Bar(0.86f, Palette::Ok)
			]
			+ SVerticalBox::Slot().AutoHeight().Padding(0.0f, U(0.5f), 0.0f, 0.0f)
			[
				MakeText(TEXT("86"), { EFont::Display, 2.4f }, Palette::Ok)
			]
		];

	return SNew(SOverlay)
		+ SOverlay::Slot()
		[
			SNew(SConstraintCanvas)
			+ PlaceAt(0.5f, 0.0f, U(2.0f), 0.5f)[BuildScoreboard(Model)]
			+ PlaceAt(0.0f, U(4.0f), U(13.0f), 0.0f)[RatingPanel]
			+ PlaceAt(0.0f, U(26.0f), U(17.75f), 0.0f)[BuildFighter(EOpenStanceSide::Chung)]
			+ PlaceAt(0.0f, U(54.0f), U(17.75f), 0.0f)[BuildFighter(EOpenStanceSide::Hong)]
			+ PlaceAt(0.5f, 0.0f, -U(14.0f), 0.5f, 1.0f, 1.0f)[BuildCallBanner(Model)]
		]
		+ SOverlay::Slot().VAlign(VAlign_Bottom).Padding(U(4.0f), 0.0f, U(4.0f), U(5.0f))
		[
			CommandBar
		];
}

// UOpenStanceRefereeGradeScreen

TSharedRef<SWidget> UOpenStanceRefereeGradeScreen::BuildContent()
{
	struct FRatingEvent
	{
		FString Label;
		FString Count;
		FString Change;
	};
	const TArray<FRatingEvent> Events =
	{
		{ TEXT("Correct call"), TEXT("3"), TEXT("+6") },
		{ TEXT("Late call"), TEXT("2"), TEXT("−6") },
		{ TEXT("Missed penalty"), TEXT("1"), TEXT("−6") },
		{ TEXT("Wrong penalty"), TEXT("1"), TEXT("−10") },
		{ TEXT("Blocked the camera"), TEXT("2"), TEXT("−4") }
	};

	TSharedRef<SVerticalBox> Changes = SNew(SVerticalBox);
	for (const FRatingEvent& Event : Events)
	{
		Changes->AddSlot().AutoHeight().Padding(0.0f, 0.0f, 0.0f, U(0.7f))
		[
			MakeRatingRow(Event.Label, Event.Count, Event.Change)
		];
	}
	Changes->AddSlot().AutoHeight()
	[
		MakeRatingRow(TEXT("Rating"), FString(), TEXT("100 → 80"), true)
	];

	const TSharedRef<SWidget> GradeBody = SNew(SVerticalBox)
		+ SVerticalBox::Slot().AutoHeight()
		[
			SNew(SHorizontalBox)
			+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
			[
				MakeText(TEXT("B"), { EFont::Display, 9.0f }, Palette::Bone)
			]
			+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(U(1.4f), 0.0f, 0.0f, 0.0f)
			[
				SNew(SVerticalBox)
				+ SVerticalBox::Slot().AutoHeight()
				[
					MakeText(TEXT("Rating 80"), { EFont::Display, 2.6f }, Palette::Bone)
				]
				+ SVerticalBox::Slot().AutoHeight()
				[
					MakeText(TEXT("Started at 100"), { EFont::Body, 1.1f }, Palette::Mute)
				]
			]
		]
		+ SVerticalBox::Slot().AutoHeight().Padding(0.0f, U(0.7f), 0.0f, 0.0f)
		[
			Bar(0.8f, Palette::Ok)
		]
		+ SVerticalBox::Slot().AutoHeight().Padding(0.0f, U(0.7f), 0.0f, 0.0f)
		[
			StatRow(TEXT("Call accuracy"), SNullWidget::NullWidget, TEXT("B"))
		]
		+ SVerticalBox::Slot().AutoHeight().Padding(0.0f, U(0.7f), 0.0f, 0.0f)
		[
			StatRow(TEXT("Call timing"), SNullWidget::NullWidget, TEXT("C"))
		]
		+ SVerticalBox::Slot().AutoHeight().Padding(0.0f, U(0.7f), 0.0f, 0.0f)
		[
			StatRow(TEXT("Positioning"), SNullWidget::NullWidget, TEXT("B"))
		];

	TSharedRef<SOpenStanceOption> PlayAgain = SNew(SOpenStanceOption)
		.Label(TEXT("Play again"))
		.OnPressed(FSimpleDelegate::CreateWeakLambda(this, [this]()
		{
			if (UOpenStanceMenuSubsystem* Menu = GetMenu())
			{
				Menu->ShowScreen(EOpenStanceMenuScreen::RefereeSetup);
			}
		}));
	SetDefaultFocus(PlayAgain);

	return SNew(SVerticalBox)
		+ SVerticalBox::Slot().AutoHeight()
		[
			Head(TEXT("Referee Mode"), TEXT("Referee grade"), true)
		]
		+ SVerticalBox::Slot().FillHeight(1.0f).Padding(0.0f, U(1.6f), 0.0f, 0.0f)
		[
			SNew(SHorizontalBox)
			+ SHorizontalBox::Slot().AutoWidth()
			[
				SNew(SBox).WidthOverride(U(34.0f))
				[
					SNew(SVerticalBox)
					+ SVerticalBox::Slot().AutoHeight()
					[
						Card(TEXT("Grade"), GradeBody)
					]
					+ SVerticalBox::Slot().AutoHeight().Padding(0.0f, U(0.8f), 0.0f, 0.0f)
					[
						TextCard(TEXT("Thresholds"), { TEXT("Below 40: a warning from the technical delegate. Below 20: removal at the next break and a grade of F.") })
					]
				]
			]
			+ SHorizontalBox::Slot().FillWidth(1.0f).Padding(U(2.4f), 0.0f, 0.0f, 0.0f)
			[
				SNew(SVerticalBox)
				+ SVerticalBox::Slot().AutoHeight()
				[
					Card(TEXT("Rating changes"), Changes)
				]
				+ SVerticalBox::Slot().FillHeight(1.0f)
				[
					SNew(SBox).VAlign(VAlign_Bottom)
					[
						SNew(SHorizontalBox)
						+ SHorizontalBox::Slot().FillWidth(1.0f)
						[
							PlayAgain
						]
						+ SHorizontalBox::Slot().FillWidth(1.0f).Padding(U(0.8f), 0.0f, 0.0f, 0.0f)
						[
							SNew(SOpenStanceOption)
							.Label(TEXT("Main menu"))
							.OnPressed(FSimpleDelegate::CreateWeakLambda(this, [this]()
							{
								if (UOpenStanceMenuSubsystem* Menu = GetMenu())
								{
									Menu->ReturnToMain();
								}
							}))
						]
					]
				]
			]
		];
}
