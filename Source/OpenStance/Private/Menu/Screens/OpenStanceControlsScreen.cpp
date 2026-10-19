#include "Menu/Screens/OpenStanceControlsScreen.h"

#include "Menu/OpenStanceMenuContent.h"
#include "Menu/OpenStanceMenuSubsystem.h"
#include "Menu/OpenStanceMenuTheme.h"
#include "Menu/Slate/SOpenStanceArt.h"
#include "Menu/Slate/SOpenStanceFrame.h"
#include "Menu/Slate/SOpenStanceInteractive.h"
#include "Menu/Slate/SOpenStanceItems.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/Layout/SWidgetSwitcher.h"
#include "Widgets/SBoxPanel.h"

using namespace OpenStanceMenu;
using namespace OpenStanceMenuWidgets;
using OpenStanceMenuPaint::FGradient;

namespace
{
	constexpr float ActionColumnUnits = 13.0f;
	constexpr float NotesColumnUnits = 11.5f;
	constexpr float ColumnGapUnits = 1.2f;

	/** One input in the list (.crow): the action, its input as chips and icons, and a note or point value. */
	class SControlRow : public SOpenStanceInteractive
	{
	public:
		SLATE_BEGIN_ARGS(SControlRow)
			: _PointsStyle(false)
			, _Locked(false)
		{
		}
			SLATE_ARGUMENT(FString, Action)
			SLATE_ARGUMENT(FString, Input)
			SLATE_ARGUMENT(FString, Notes)
			/** The third column holds point values, drawn in the accent colour. */
			SLATE_ARGUMENT(bool, PointsStyle)
			OPENSTANCE_INTERACTIVE_ARGUMENTS
		SLATE_END_ARGS()

		void Construct(const FArguments& InArgs)
		{
			InitInteraction(InArgs._Locked, InArgs._OnPressed, InArgs._OnStep, InArgs._OnActivated);
			SetForegroundColor(TAttribute<FSlateColor>::CreateSP(this, &SControlRow::GetForeground));

			const TAttribute<bool> Inverted = TAttribute<bool>::CreateSP(this, &SOpenStanceInteractive::IsActive);
			const TAttribute<FSlateColor> NotesColor = TAttribute<FSlateColor>::CreateSP(this, InArgs._PointsStyle ? &SControlRow::GetPointsColor : &SControlRow::GetNotesColor);
			const FTextSpec NotesSpec = InArgs._PointsStyle ? FTextSpec{ EFont::Display, 1.1f, 0.04f, false } : FTextSpec{ EFont::Body, 1.0f };

			ChildSlot
			[
				SNew(SBox)
				.MinDesiredHeight(U(3.1f))
				[
					SNew(SOpenStanceFrame)
					.Fill(Palette::Panel)
					.Gradient(TAttribute<FGradient>::CreateSP(this, &SControlRow::GetGradient))
					.Padding(FMargin(U(1.2f), U(0.4f)))
					[
						SNew(SHorizontalBox)
						+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
						[
							SNew(SBox).WidthOverride(U(ActionColumnUnits))
							[
								MakeText(InArgs._Action, { EFont::DisplayItalic, 1.35f, 0.05f, true }, TAttribute<FSlateColor>(FSlateColor::UseForeground()))
							]
						]
						+ SHorizontalBox::Slot().FillWidth(1.0f).VAlign(VAlign_Center).Padding(U(ColumnGapUnits), 0.0f)
						[
							InputLine(InArgs._Input, Inverted)
						]
						+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
						[
							SNew(SBox).WidthOverride(U(NotesColumnUnits))
							[
								SNew(STextBlock)
								.Text(FText::FromString(InArgs._Notes))
								.Font(MakeFont(NotesSpec.Font, NotesSpec.SizeUnits, NotesSpec.LetterSpacing))
								.ColorAndOpacity(NotesColor)
								.AutoWrapText(true)
							]
						]
					]
				]
			];
		}

	private:
		FSlateColor GetForeground() const
		{
			return IsActive() ? Palette::Ink : Palette::Bone;
		}

		FSlateColor GetNotesColor() const
		{
			return IsActive() ? Hex(0x3b465a) : Palette::Mute;
		}

		FSlateColor GetPointsColor() const
		{
			return IsActive() ? Palette::ChungDark : Palette::Ice;
		}

		FGradient GetGradient() const
		{
			return IsActive() ? FGradient::TwoColor(90.0f, FLinearColor::White, Palette::FocusEnd) : FGradient();
		}
	};

	/** Column titles above a tab's rows, laid out on the same widths. */
	TSharedRef<SWidget> MakeHeader(const OpenStanceMenuContent::FControlTab& Tab)
	{
		const FTextSpec Spec{ EFont::BodyBold, 0.95f, 0.16f, true };
		return SNew(SOpenStanceFrame)
			.Fill(Palette::Ink)
			.Padding(FMargin(U(1.2f), U(0.55f)))
			[
				SNew(SHorizontalBox)
				+ SHorizontalBox::Slot().AutoWidth()
				[
					SNew(SBox).WidthOverride(U(ActionColumnUnits))
					[
						MakeText(Tab.Columns[0], Spec, Palette::Mute)
					]
				]
				+ SHorizontalBox::Slot().FillWidth(1.0f).Padding(U(ColumnGapUnits), 0.0f)
				[
					MakeText(Tab.Columns[1], Spec, Palette::Mute)
				]
				+ SHorizontalBox::Slot().AutoWidth()
				[
					SNew(SBox).WidthOverride(U(NotesColumnUnits))
					[
						MakeText(Tab.Columns[2], Spec, Palette::Mute)
					]
				]
			];
	}
}

TArray<FOpenStanceHint> UOpenStanceControlsScreen::GetHints() const
{
	return TabHints(TEXT("Previous tab"), TEXT("Next tab"));
}

TSharedRef<SWidget> UOpenStanceControlsScreen::BuildContent()
{
	const TArray<OpenStanceMenuContent::FControlTab>& Tabs = OpenStanceMenuContent::GetControlTabs();
	TWeakObjectPtr<UOpenStanceControlsScreen> WeakThis(this);
	const auto GetTab = [WeakThis]()
	{
		const UOpenStanceControlsScreen* Screen = WeakThis.Get();
		const UOpenStanceMenuSubsystem* Menu = Screen ? Screen->GetMenu() : nullptr;
		return Menu ? FMath::Clamp(Menu->GetSession().ControlsTabIndex, 0, OpenStanceMenuContent::GetControlTabs().Num() - 1) : 0;
	};

	// The controller diagram, lit by whichever row has focus
	const TSharedRef<SOpenStanceGamepadDiagram> GamepadDiagram = SNew(SOpenStanceGamepadDiagram);
	Diagram = GamepadDiagram;

	FirstRows.Reset();
	TSharedRef<SWidgetSwitcher> Pages = SNew(SWidgetSwitcher).WidgetIndex_Lambda(GetTab);
	for (const OpenStanceMenuContent::FControlTab& Tab : Tabs)
	{
		TSharedRef<SScrollBox> Rows = SNew(SScrollBox).ScrollBarVisibility(EVisibility::Collapsed);
		TWeakPtr<SOpenStanceInteractive> FirstRow;
		for (const OpenStanceMenuContent::FControlRow& Row : Tab.Rows)
		{
			const TArray<FName> Parts = GetInputParts(Row.Input);
			TSharedRef<SControlRow> RowWidget = SNew(SControlRow)
				.Action(Row.Action)
				.Input(Row.Input)
				.Notes(Row.Notes)
				.PointsStyle(Tab.Columns[2] == TEXT("Points"))
				.OnActivated(FSimpleDelegate::CreateWeakLambda(this, [this, Parts]() { HighlightParts(Parts); }));
			if (!FirstRow.IsValid())
			{
				FirstRow = RowWidget;
			}
			Rows->AddSlot().Padding(0.0f, 0.0f, 0.0f, U(0.35f))[RowWidget];
		}
		FirstRows.Add(FirstRow);

		Pages->AddSlot()
		[
			SNew(SVerticalBox)
			+ SVerticalBox::Slot().AutoHeight().Padding(0.0f, 0.0f, 0.0f, U(0.35f))
			[
				MakeHeader(Tab)
			]
			+ SVerticalBox::Slot().FillHeight(1.0f)
			[
				Rows
			]
		];
	}
	SetDefaultFocus(FirstRows.IsValidIndex(GetTab()) ? FirstRows[GetTab()].Pin() : nullptr);

	// Tab strip: LB, the tabs, RB
	TSharedRef<SHorizontalBox> Strip = SNew(SHorizontalBox)
		+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(0.0f, 0.0f, U(0.4f), 0.0f)
		[
			Glyph(TEXT("LB"), EOpenStanceGlyphLook::Key)
		];
	for (int32 TabIndex = 0; TabIndex < Tabs.Num(); ++TabIndex)
	{
		Strip->AddSlot().AutoWidth().VAlign(VAlign_Center).Padding(0.0f, 0.0f, U(0.4f), 0.0f)
		[
			SNew(SOpenStanceTabButton)
			.Label(Tabs[TabIndex].Name)
			.FontSize(1.15f)
			.LetterSpacing(0.05f)
			.Padding(FMargin(U(0.8f), U(0.6f)))
			.TagWidget(Tabs[TabIndex].bFuture ? FutureTag() : TSharedPtr<SWidget>())
			.Selected_Lambda([GetTab, TabIndex]() { return GetTab() == TabIndex; })
			.OnPressed(FSimpleDelegate::CreateWeakLambda(this, [this, TabIndex]() { SelectTab(TabIndex); }))
		];
	}
	Strip->AddSlot().AutoWidth().VAlign(VAlign_Center)
	[
		Glyph(TEXT("RB"), EOpenStanceGlyphLook::Key)
	];

	return SNew(SVerticalBox)
		+ SVerticalBox::Slot().AutoHeight()
		[
			Head(TEXT("Options · Controls"), TEXT("Controls"))
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
				SNew(SBox).WidthOverride(U(30.0f))
				[
					SNew(SVerticalBox)
					+ SVerticalBox::Slot().AutoHeight()
					[
						SNew(SOpenStanceFrame)
						.Fill(Palette::Panel)
						.Padding(FMargin(U(0.8f)))
						[
							SNew(SBox).HeightOverride(U(18.0f))
							[
								GamepadDiagram
							]
						]
					]
					+ SVerticalBox::Slot().AutoHeight().Padding(0.0f, U(0.8f), 0.0f, 0.0f)
					[
						Paragraph(TEXT("Point at a row and its buttons light up. Stick icons start at the dot and turn the way the arrow points. The icons show the → side; mirror them for ←."), 1.05f, Palette::Mute)
					]
				]
			]
			+ SHorizontalBox::Slot().FillWidth(1.0f).Padding(U(2.0f), 0.0f, 0.0f, 0.0f)
			[
				Pages
			]
		];
}

void UOpenStanceControlsScreen::HighlightParts(const TArray<FName>& Parts)
{
	if (const TSharedPtr<SOpenStanceGamepadDiagram> Pad = Diagram.Pin())
	{
		Pad->SetHighlighted(Parts);
	}
}

void UOpenStanceControlsScreen::SelectTab(int32 TabIndex)
{
	UOpenStanceMenuSubsystem* Menu = GetMenu();
	if (!Menu || !FirstRows.IsValidIndex(TabIndex))
	{
		return;
	}
	Menu->GetSession().ControlsTabIndex = TabIndex;
	FocusWidget(FirstRows[TabIndex].Pin());
}

void UOpenStanceControlsScreen::HandleTabStep(int32 Direction)
{
	const UOpenStanceMenuSubsystem* Menu = GetMenu();
	const int32 Count = OpenStanceMenuContent::GetControlTabs().Num();
	if (Menu && Count > 0)
	{
		SelectTab((Menu->GetSession().ControlsTabIndex + Direction + Count) % Count);
	}
}
