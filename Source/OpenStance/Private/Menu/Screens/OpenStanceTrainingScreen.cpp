#include "Menu/Screens/OpenStanceTrainingScreen.h"

#include "Menu/OpenStanceMenuTheme.h"
#include "Menu/Slate/SOpenStanceFrame.h"
#include "Menu/Slate/SOpenStanceItems.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SWrapBox.h"
#include "Widgets/SBoxPanel.h"

using namespace OpenStanceMenu;
using namespace OpenStanceMenuWidgets;

namespace
{
	struct FLesson
	{
		FString Title;
		FString Status;
		bool bLocked = false;
	};

	struct FDrill
	{
		FString Title;
		/** Best grade so far, or a dash when not tried. */
		FString Grade;
	};

	/** The lesson text with the X button drawn inline, as the prototype does. */
	TSharedRef<SWidget> MakeLessonText()
	{
		TSharedRef<SWrapBox> Line = SNew(SWrapBox).UseAllottedSize(true).InnerSlotPadding(FVector2D(U(0.3f), 0.0f));
		const FString Lead = TEXT("Turn your back to the target, look over your shoulder, then drive the heel through. Skill Stick down, then");
		TArray<FString> Words;
		Lead.ParseIntoArrayWS(Words);
		for (const FString& Word : Words)
		{
			Line->AddSlot()[MakeText(Word, { EFont::Body, 1.2f }, Palette::Bone)];
		}
		Line->AddSlot().VAlign(VAlign_Center)[Glyph(TEXT("X"), EOpenStanceGlyphLook::X, 1.6f)];
		Line->AddSlot()[MakeText(TEXT("."), { EFont::Body, 1.2f }, Palette::Bone)];
		return Line;
	}
}

TSharedRef<SWidget> UOpenStanceTrainingScreen::BuildContent()
{
	const TArray<FLesson> Lessons =
	{
		{ TEXT("1 · Stance and footwork"), TEXT("Done"), false },
		{ TEXT("2 · Roundhouse kick"), TEXT("Done"), false },
		{ TEXT("3 · Back kick"), TEXT("Next"), false },
		{ TEXT("4 · Active defence"), TEXT("Locked"), true }
	};
	const TArray<FDrill> Drills =
	{
		{ TEXT("Kick accuracy"), TEXT("B") },
		{ TEXT("Counter timing"), TEXT("C") },
		{ TEXT("Stamina management"), TEXT("—") }
	};

	TSharedPtr<SOpenStanceInteractive> FirstItem;
	TSharedRef<SVerticalBox> LessonColumn = SNew(SVerticalBox)
		+ SVerticalBox::Slot().AutoHeight().Padding(0.0f, 0.0f, 0.0f, U(0.8f))
		[
			Kicker(TEXT("Lessons"))
		];
	for (const FLesson& Lesson : Lessons)
	{
		TSharedRef<SOpenStanceOption> Item = SNew(SOpenStanceOption)
			.Label(Lesson.Title)
			.Locked(Lesson.bLocked)
			.TagWidget(Tag(Lesson.Status));
		if (!FirstItem.IsValid() && !Lesson.bLocked)
		{
			FirstItem = Item;
		}
		LessonColumn->AddSlot().AutoHeight().Padding(0.0f, 0.0f, 0.0f, U(0.8f))
		[
			Item
		];
	}

	TSharedRef<SVerticalBox> DrillColumn = SNew(SVerticalBox)
		+ SVerticalBox::Slot().AutoHeight().Padding(0.0f, 0.0f, 0.0f, U(0.8f))
		[
			Kicker(TEXT("Drills"))
		];
	for (const FDrill& Drill : Drills)
	{
		DrillColumn->AddSlot().AutoHeight().Padding(0.0f, 0.0f, 0.0f, U(0.8f))
		[
			SNew(SOpenStanceOption)
			.Label(Drill.Title)
			.Value(Drill.Grade)
		];
	}
	DrillColumn->AddSlot().AutoHeight().Padding(0.0f, U(0.8f), 0.0f, U(0.8f))
	[
		Kicker(TEXT("Practice"))
	];
	DrillColumn->AddSlot().AutoHeight()
	[
		SNew(SOpenStanceOption)
		.Label(TEXT("Free practice"))
		.Small(TEXT("AI partner"))
	];
	SetDefaultFocus(FirstItem);

	return SNew(SVerticalBox)
		+ SVerticalBox::Slot().AutoHeight()
		[
			Head(TEXT("Progress"), TEXT("Training"))
		]
		+ SVerticalBox::Slot().FillHeight(1.0f).Padding(0.0f, U(1.6f), 0.0f, 0.0f)
		[
			SNew(SHorizontalBox)
			+ SHorizontalBox::Slot().AutoWidth()
			[
				SNew(SBox).WidthOverride(U(30.0f))
				[
					LessonColumn
				]
			]
			+ SHorizontalBox::Slot().AutoWidth().Padding(U(2.4f), 0.0f, 0.0f, 0.0f)
			[
				SNew(SBox).WidthOverride(U(30.0f))
				[
					DrillColumn
				]
			]
			+ SHorizontalBox::Slot().FillWidth(1.0f).Padding(U(2.4f), 0.0f, 0.0f, 0.0f)
			[
				SNew(SVerticalBox)
				+ SVerticalBox::Slot().AutoHeight()
				[
					Card(TEXT("Lesson 3 · Back kick"),
						SNew(SVerticalBox)
						+ SVerticalBox::Slot().AutoHeight().Padding(0.0f, 0.0f, 0.0f, U(0.7f))
						[
							Paragraph(TEXT("Step-by-step prompts show controller icons and wait for the correct input."))
						]
						+ SVerticalBox::Slot().AutoHeight()
						[
							MakeLessonText()
						])
				]
				+ SVerticalBox::Slot().AutoHeight().Padding(0.0f, U(0.8f), 0.0f, 0.0f)
				[
					TextCard(TEXT("Coach feedback"), { TEXT("Your last three matches lost most points to counters. Try the Counter timing drill.") })
				]
			]
		];
}
