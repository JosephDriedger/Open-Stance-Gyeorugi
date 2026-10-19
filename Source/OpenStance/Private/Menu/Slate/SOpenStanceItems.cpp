#include "Menu/Slate/SOpenStanceItems.h"

#include "Menu/OpenStanceMenuTheme.h"
#include "Menu/Slate/OpenStanceMenuWidgets.h"
#include "Menu/Slate/SOpenStanceArt.h"
#include "Menu/Slate/SOpenStanceFrame.h"
#include "Widgets/Images/SImage.h"
#include "Widgets/Input/SSlider.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SConstraintCanvas.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/SOverlay.h"
#include "Widgets/Text/STextBlock.h"

using namespace OpenStanceMenu;
using namespace OpenStanceMenuWidgets;
using OpenStanceMenuPaint::FGradient;

// SOpenStanceOption

void SOpenStanceOption::Construct(const FArguments& InArgs)
{
	InitInteraction(InArgs._Locked, InArgs._OnPressed, InArgs._OnStep, InArgs._OnActivated);
	Look = InArgs._Look;
	Current = InArgs._Current;

	// The prototype's 0.4u left border is part of the box, so the text starts that much further in
	FMargin Padding = InArgs._Padding != FMargin(0.0f) ? InArgs._Padding : FMargin(U(1.6f), U(1.05f));
	Padding.Left += U(0.4f);

	const TAttribute<FSlateColor> LabelColor = TAttribute<FSlateColor>::CreateSP(this, &SOpenStanceOption::GetLabelColor);

	TSharedRef<SHorizontalBox> Row = SNew(SHorizontalBox);
	if (InArgs._CenterLabel)
	{
		Row->AddSlot().FillWidth(1.0f)[SNullWidget::NullWidget];
	}
	Row->AddSlot().AutoWidth().VAlign(VAlign_Center)
	[
		MakeText(InArgs._Label, { EFont::DisplayItalic, InArgs._FontSize, 0.07f, true }, LabelColor)
	];
	if (InArgs._TagWidget.IsValid())
	{
		Row->AddSlot().AutoWidth().VAlign(VAlign_Center).Padding(U(1.0f), 0.0f, 0.0f, 0.0f)
		[
			InArgs._TagWidget.ToSharedRef()
		];
	}
	Row->AddSlot().FillWidth(1.0f)[SNullWidget::NullWidget];
	if (!InArgs._Small.IsEmpty())
	{
		Row->AddSlot().AutoWidth().VAlign(VAlign_Center).Padding(U(1.2f), 0.0f, 0.0f, 0.0f)
		[
			MakeText(InArgs._Small, { EFont::Body, 1.05f }, TAttribute<FSlateColor>::CreateSP(this, &SOpenStanceOption::GetSmallColor))
		];
	}
	if (InArgs._Value.IsSet())
	{
		const TAttribute<FString> Value = InArgs._Value;
		Row->AddSlot().AutoWidth().VAlign(VAlign_Center).Padding(U(1.2f), 0.0f, 0.0f, 0.0f)
		[
			MakeLiveText([Value]() { return Value.Get(FString()); }, { EFont::DisplayItalic, InArgs._FontSize, 0.07f, true },
				TAttribute<FSlateColor>::CreateSP(this, &SOpenStanceOption::GetValueColor))
		];
	}

	ChildSlot
	[
		SNew(SOpenStanceFrame)
		.Fill(TAttribute<FLinearColor>::CreateSP(this, &SOpenStanceOption::GetFill))
		.Gradient(TAttribute<FGradient>::CreateSP(this, &SOpenStanceOption::GetGradient))
		.AccentColor(TAttribute<FLinearColor>::CreateSP(this, &SOpenStanceOption::GetAccent))
		.AccentEdge(EOpenStanceFrameEdge::Left)
		.AccentThickness(U(0.4f))
		.CutCorner(U(0.9f))
		.Padding(Padding)
		[
			Row
		]
	];

	if (InArgs._Locked)
	{
		SetColorAndOpacity(FLinearColor(1.0f, 1.0f, 1.0f, 0.38f));
	}
}

FLinearColor SOpenStanceOption::GetFill() const
{
	if (Look == EOpenStanceOptionLook::Primary)
	{
		return IsActive() ? Hex(0x5b93f2) : Palette::Chung;
	}
	if (Current.Get(false))
	{
		return IsActive() ? Palette::Bone : Palette::Panel2;
	}
	return Palette::Panel;
}

FGradient SOpenStanceOption::GetGradient() const
{
	if (Look != EOpenStanceOptionLook::Primary && IsActive() && !Current.Get(false))
	{
		return FGradient::TwoColor(90.0f, FLinearColor::White, Palette::FocusEnd);
	}
	return FGradient();
}

FLinearColor SOpenStanceOption::GetAccent() const
{
	if (Look == EOpenStanceOptionLook::Primary)
	{
		return IsActive() ? FLinearColor::White : FLinearColor::Transparent;
	}
	if (IsActive())
	{
		return Look == EOpenStanceOptionLook::Danger ? Palette::Hong : Palette::Chung;
	}
	return Current.Get(false) ? Palette::Chung : FLinearColor::Transparent;
}

FSlateColor SOpenStanceOption::GetLabelColor() const
{
	if (Look == EOpenStanceOptionLook::Primary)
	{
		return FLinearColor::White;
	}
	return IsActive() ? Palette::Ink : Palette::Bone;
}

FSlateColor SOpenStanceOption::GetSmallColor() const
{
	if (Look == EOpenStanceOptionLook::Primary)
	{
		return Palette::FocusEnd;
	}
	return IsActive() ? Palette::MuteOnFocus : Palette::Mute;
}

FSlateColor SOpenStanceOption::GetValueColor() const
{
	return IsActive() ? Palette::ChungDark : Palette::Chung;
}

// SOpenStanceTabButton

void SOpenStanceTabButton::Construct(const FArguments& InArgs)
{
	InitInteraction(InArgs._Locked, InArgs._OnPressed, InArgs._OnStep, InArgs._OnActivated);
	Selected = InArgs._Selected;

	const FMargin Padding = InArgs._Padding != FMargin(0.0f) ? InArgs._Padding : FMargin(U(1.6f), U(0.7f));

	TSharedRef<SHorizontalBox> Row = SNew(SHorizontalBox)
		+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
		[
			MakeText(InArgs._Label, { EFont::DisplayItalic, InArgs._FontSize, InArgs._LetterSpacing, true },
				TAttribute<FSlateColor>::CreateSP(this, &SOpenStanceTabButton::GetTextColor))
		];
	if (InArgs._TagWidget.IsValid())
	{
		Row->AddSlot().AutoWidth().VAlign(VAlign_Center).Padding(U(0.4f), 0.0f, 0.0f, 0.0f)
		[
			InArgs._TagWidget.ToSharedRef()
		];
	}

	const TAttribute<bool> IsSelected = Selected;
	ChildSlot
	[
		SNew(SOpenStanceFrame)
		.AccentColor(TAttribute<FLinearColor>::CreateLambda([IsSelected]()
		{
			return IsSelected.Get(false) ? Palette::Ice : FLinearColor::Transparent;
		}))
		.AccentEdge(EOpenStanceFrameEdge::Bottom)
		.AccentThickness(U(0.3f))
		.Padding(Padding)
		[
			Row
		]
	];

	if (InArgs._Dimmed || InArgs._Locked)
	{
		SetColorAndOpacity(FLinearColor(1.0f, 1.0f, 1.0f, 0.35f));
	}
}

FSlateColor SOpenStanceTabButton::GetTextColor() const
{
	if (Selected.Get(false))
	{
		return FLinearColor::White;
	}
	return IsActive() ? Palette::Bone : Palette::Mute;
}

// SOpenStanceHubTile

void SOpenStanceHubTile::Construct(const FArguments& InArgs)
{
	InitInteraction(InArgs._Locked, InArgs._OnPressed, InArgs._OnStep, InArgs._OnActivated);
	bFuture = InArgs._Future;
	GradientFrom = InArgs._GradientFrom;
	GradientTo = InArgs._GradientTo;

	FGradient Glow;
	Glow.AngleDegrees = 0.0f;
	Glow.Stops = { { 0.0f, FLinearColor(0.0f, 0.0f, 0.0f, 0.78f) }, { 0.55f, FLinearColor(0.0f, 0.0f, 0.0f, 0.0f) } };

	const float Cut = U(2.0f);

	TSharedRef<SOverlay> Layers = SNew(SOverlay)
		+ SOverlay::Slot()
		[
			SNew(SConstraintCanvas)
			+ SConstraintCanvas::Slot()
			.Anchors(FAnchors(0.44f, 0.02f, 1.06f, 0.94f))
			.Offset(FMargin(0.0f))
			[
				SNew(SOpenStanceFighterFigure)
				.BodyColor(Hex(0xe7e5de))
				.TrimColor(Hex(0xbdb9ad))
				.GearOn(false)
				.Kick(InArgs._ShowKick)
			]
		]
		+ SOverlay::Slot()
		[
			SNew(SOpenStanceFrame).Gradient(Glow)
		]
		+ SOverlay::Slot().VAlign(VAlign_Bottom)
		[
			SNew(SVerticalBox)
			+ SVerticalBox::Slot().AutoHeight().Padding(U(1.6f), U(1.2f), U(1.6f), 0.0f)
			[
				SNew(STextBlock)
				.Text(FText::FromString(InArgs._Title))
				.Font(MakeFont(EFont::DisplayItalic, 2.5f, 0.03f))
				.ColorAndOpacity(FLinearColor::White)
				.TransformPolicy(ETextTransformPolicy::ToUpper)
				.AutoWrapText(true)
				.LineHeightPercentage(0.95f)
			]
			+ SVerticalBox::Slot().AutoHeight().Padding(U(1.6f), U(0.4f), U(1.6f), U(2.2f))
			[
				SNew(STextBlock)
				.Text(FText::FromString(InArgs._Subtitle))
				.Font(MakeFont(EFont::BodyMedium, 1.05f))
				.ColorAndOpacity(Hex(0xc9d6ee))
				.AutoWrapText(true)
			]
		];

	if (bFuture)
	{
		Layers->AddSlot().HAlign(HAlign_Left).VAlign(VAlign_Top).Padding(U(1.2f), U(1.0f), 0.0f, 0.0f)
		[
			SNew(SOpenStanceFrame)
			.Fill(FLinearColor(0.0f, 0.0f, 0.0f, 0.5f))
			[
				FutureTag()
			]
		];
	}

	// The prototype dims tiles that are not focused (brightness 0.72)
	Layers->AddSlot()
	[
		SNew(SOpenStanceFrame)
		.Fill(TAttribute<FLinearColor>::CreateSP(this, &SOpenStanceHubTile::GetDimming))
		.CutCorner(Cut)
	];

	ChildSlot
	[
		SNew(SOpenStanceFrame)
		.Fill(TAttribute<FLinearColor>::CreateSP(this, &SOpenStanceHubTile::GetFill))
		.Gradient(TAttribute<FGradient>::CreateSP(this, &SOpenStanceHubTile::GetGradient))
		.OutlineColor(TAttribute<FLinearColor>::CreateSP(this, &SOpenStanceHubTile::GetOutline))
		.OutlineThickness(U(0.28f))
		.CutCorner(Cut)
		.ClipContent(true)
		[
			Layers
		]
	];
}

void SOpenStanceHubTile::OnActiveChanged(bool bActive)
{
	const FVector2f Lift(0.0f, bActive ? -U(0.8f) : 0.0f);
	SetRenderTransform(TOptional<FSlateRenderTransform>(FSlateRenderTransform(Lift)));
}

// The prototype's .tile focus rule swaps the colour gradient for a flat panel, so a focused tile is dark with a white frame
FLinearColor SOpenStanceHubTile::GetFill() const
{
	return IsActive() ? Palette::Panel2 : FLinearColor::Transparent;
}

FGradient SOpenStanceHubTile::GetGradient() const
{
	return IsActive() ? FGradient() : FGradient::TwoColor(155.0f, GradientFrom, GradientTo);
}

FLinearColor SOpenStanceHubTile::GetDimming() const
{
	return IsActive() ? FLinearColor::Transparent : FLinearColor(0.0f, 0.0f, 0.0f, 0.28f);
}

FLinearColor SOpenStanceHubTile::GetOutline() const
{
	return IsActive() ? FLinearColor::White : FLinearColor::Transparent;
}

// SOpenStanceFighterTile

void SOpenStanceFighterTile::Construct(const FArguments& InArgs)
{
	InitInteraction(InArgs._Locked, InArgs._OnPressed, InArgs._OnStep, InArgs._OnActivated);
	Selected = InArgs._Selected;
	bHong = InArgs._Hong;

	ChildSlot
	[
		SNew(SOpenStanceFrame)
		.Fill(TAttribute<FLinearColor>::CreateSP(this, &SOpenStanceFighterTile::GetFill))
		.AccentColor(TAttribute<FLinearColor>::CreateSP(this, &SOpenStanceFighterTile::GetRule))
		.AccentEdge(EOpenStanceFrameEdge::Bottom)
		.AccentThickness(U(0.3f))
		.Padding(FMargin(U(1.2f), U(1.0f)))
		[
			SNew(SVerticalBox)
			+ SVerticalBox::Slot().AutoHeight()
			[
				MakeText(InArgs._Name, { EFont::Display, 1.7f, 0.06f, true }, Palette::Bone)
			]
			+ SVerticalBox::Slot().AutoHeight().Padding(0.0f, U(0.3f), 0.0f, 0.0f)
			[
				MakeText(InArgs._Detail, { EFont::Body, 1.0f }, Palette::Mute)
			]
		]
	];
}

FLinearColor SOpenStanceFighterTile::GetFill() const
{
	return IsActive() || Selected.Get(false) ? Palette::Panel2 : Palette::Panel;
}

FLinearColor SOpenStanceFighterTile::GetRule() const
{
	if (IsActive() || Selected.Get(false))
	{
		return bHong ? Palette::Hong : Palette::Chung;
	}
	return FLinearColor::Transparent;
}

// SOpenStanceSwatch

void SOpenStanceSwatch::Construct(const FArguments& InArgs)
{
	InitInteraction(InArgs._Locked, InArgs._OnPressed, InArgs._OnStep, InArgs._OnActivated);
	Selected = InArgs._Selected;

	ChildSlot
	[
		SNew(SBox)
		.WidthOverride(U(2.6f))
		.HeightOverride(U(2.6f))
		[
			SNew(SOpenStanceFrame)
			.Fill(InArgs._Color)
			.OutlineColor(TAttribute<FLinearColor>::CreateSP(this, &SOpenStanceSwatch::GetOutline))
			.OutlineThickness(U(0.2f))
		]
	];
}

FLinearColor SOpenStanceSwatch::GetOutline() const
{
	if (Selected.Get(false))
	{
		return Palette::Bone;
	}
	return IsActive() ? Palette::Ice : FLinearColor::Transparent;
}

// SOpenStanceSliderRow

void SOpenStanceSliderRow::Construct(const FArguments& InArgs)
{
	InitInteraction(InArgs._Locked, FSimpleDelegate(), FOpenStanceStepDelegate::CreateSP(this, &SOpenStanceSliderRow::StepValue), InArgs._OnActivated);
	Min = InArgs._Min;
	Max = InArgs._Max;
	Step = InArgs._Step;
	Value = InArgs._Value;
	OnValueChanged = InArgs._OnValueChanged;
	Format = InArgs._Format ? InArgs._Format : [](float Raw) { return FString::FromInt(FMath::RoundToInt(Raw)); };

	BarBrush = *Brushes::White();
	BarBrush.TintColor = FSlateColor(Palette::Line);
	ThumbBrush = *Brushes::Circle();
	ThumbBrush.TintColor = FSlateColor(Palette::Chung);
	ThumbBrush.ImageSize = FVector2f(U(1.4f), U(1.4f));

	SliderStyle = FSliderStyle()
		.SetNormalBarImage(BarBrush)
		.SetHoveredBarImage(BarBrush)
		.SetDisabledBarImage(BarBrush)
		.SetNormalThumbImage(ThumbBrush)
		.SetHoveredThumbImage(ThumbBrush)
		.SetDisabledThumbImage(ThumbBrush)
		.SetBarThickness(U(0.3f));

	TSharedRef<SHorizontalBox> Row = SNew(SHorizontalBox)
		+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
		[
			SNew(SBox).WidthOverride(U(20.0f))
			[
				SNew(SHorizontalBox)
				+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
				[
					MakeText(InArgs._Label, { EFont::Display, 1.5f, 0.07f, true }, Palette::Bone)
				]
				+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(U(0.8f), 0.0f, 0.0f, 0.0f)
				[
					InArgs._TagWidget.IsValid() ? InArgs._TagWidget.ToSharedRef() : SNullWidget::NullWidget
				]
			]
		]
		+ SHorizontalBox::Slot().FillWidth(1.0f).VAlign(VAlign_Center).Padding(U(1.2f), 0.0f)
		[
			SNew(SSlider)
			.Style(&SliderStyle)
			.IsFocusable(false)
			.StepSize(Max > Min ? Step / (Max - Min) : 0.0f)
			.Value(TAttribute<float>::CreateSP(this, &SOpenStanceSliderRow::GetNormalized))
			.OnValueChanged(FOnFloatValueChanged::CreateSP(this, &SOpenStanceSliderRow::HandleSliderChanged))
		]
		+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
		[
			SNew(SBox).WidthOverride(U(5.0f)).HAlign(HAlign_Right)
			[
				MakeLiveText([this]() { return Format(Value.Get(0.0f)); }, { EFont::Display, 1.5f, 0.07f, false }, Palette::Chung)
			]
		];

	ChildSlot
	[
		SNew(SOpenStanceFrame)
		.Fill(TAttribute<FLinearColor>::CreateSP(this, &SOpenStanceSliderRow::GetFill))
		.AccentColor(TAttribute<FLinearColor>::CreateSP(this, &SOpenStanceSliderRow::GetAccent))
		.AccentEdge(EOpenStanceFrameEdge::Left)
		.AccentThickness(U(0.4f))
		.Padding(FMargin(U(2.0f), U(0.9f), U(1.6f), U(0.9f)))
		[
			Row
		]
	];
}

void SOpenStanceSliderRow::StepValue(int32 Direction)
{
	const float Next = FMath::Clamp(Value.Get(Min) + Direction * Step, Min, Max);
	OnValueChanged.ExecuteIfBound(Next);
}

void SOpenStanceSliderRow::HandleSliderChanged(float NormalizedValue)
{
	OnValueChanged.ExecuteIfBound(FMath::Lerp(Min, Max, NormalizedValue));
}

float SOpenStanceSliderRow::GetNormalized() const
{
	return Max > Min ? FMath::Clamp((Value.Get(Min) - Min) / (Max - Min), 0.0f, 1.0f) : 0.0f;
}

FLinearColor SOpenStanceSliderRow::GetFill() const
{
	return IsActive() ? Palette::Panel2 : Palette::Panel;
}

FLinearColor SOpenStanceSliderRow::GetAccent() const
{
	return IsActive() ? Palette::Chung : FLinearColor::Transparent;
}
