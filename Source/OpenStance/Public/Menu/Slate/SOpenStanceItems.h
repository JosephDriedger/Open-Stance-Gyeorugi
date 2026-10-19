#pragma once

#include "CoreMinimal.h"
#include "Menu/Slate/OpenStanceMenuPaint.h"
#include "Menu/Slate/SOpenStanceInteractive.h"
#include "Styling/SlateTypes.h"
#include "Widgets/DeclarativeSyntaxSupport.h"

class SOpenStanceFrame;

enum class EOpenStanceOptionLook : uint8
{
	Standard,
	/** Solid Chung blue, for the call-to-action at the bottom of a setup page. */
	Primary,
	/** Focus rule in Hong red instead of blue, for quit and destructive choices. */
	Danger
};

/**
 * The prototype's .opt: an italic caps button with a label, and optionally a tag, a small note and a value on
 * the right (value rows cycle with left and right). Focus turns it white with a blue rule on the left.
 */
class OPENSTANCE_API SOpenStanceOption : public SOpenStanceInteractive
{
public:
	SLATE_BEGIN_ARGS(SOpenStanceOption)
		: _Look(EOpenStanceOptionLook::Standard)
		, _Current(false)
		, _FontSize(1.9f)
		, _Padding(FMargin(0.0f))
		, _CenterLabel(false)
		, _Locked(false)
	{
	}
		SLATE_ARGUMENT(FString, Label)
		SLATE_ATTRIBUTE(FString, Value)
		SLATE_ARGUMENT(FString, Small)
		SLATE_ARGUMENT(TSharedPtr<SWidget>, TagWidget)
		SLATE_ARGUMENT(EOpenStanceOptionLook, Look)
		/** Marks the entry as the current one in a strip of options, as the selected tab is. */
		SLATE_ATTRIBUTE(bool, Current)
		SLATE_ARGUMENT(float, FontSize)
		/** Overrides the default padding when non-zero, in canvas pixels. */
		SLATE_ARGUMENT(FMargin, Padding)
		SLATE_ARGUMENT(bool, CenterLabel)
		OPENSTANCE_INTERACTIVE_ARGUMENTS
	SLATE_END_ARGS()

	void Construct(const FArguments& InArgs);

private:
	FLinearColor GetFill() const;
	OpenStanceMenuPaint::FGradient GetGradient() const;
	FLinearColor GetAccent() const;
	FSlateColor GetLabelColor() const;
	FSlateColor GetSmallColor() const;
	FSlateColor GetValueColor() const;

	EOpenStanceOptionLook Look = EOpenStanceOptionLook::Standard;
	TAttribute<bool> Current;
};

/** Hub and controls tab: caps text with an ice underline when selected. */
class OPENSTANCE_API SOpenStanceTabButton : public SOpenStanceInteractive
{
public:
	SLATE_BEGIN_ARGS(SOpenStanceTabButton)
		: _Selected(false)
		, _FontSize(1.7f)
		, _LetterSpacing(0.1f)
		, _Padding(FMargin(0.0f))
		, _Dimmed(false)
		, _Locked(false)
	{
	}
		SLATE_ARGUMENT(FString, Label)
		SLATE_ATTRIBUTE(bool, Selected)
		SLATE_ARGUMENT(float, FontSize)
		SLATE_ARGUMENT(float, LetterSpacing)
		SLATE_ARGUMENT(FMargin, Padding)
		SLATE_ARGUMENT(TSharedPtr<SWidget>, TagWidget)
		/** Faded, for tabs that show Future content but still open. */
		SLATE_ARGUMENT(bool, Dimmed)
		OPENSTANCE_INTERACTIVE_ARGUMENTS
	SLATE_END_ARGS()

	void Construct(const FArguments& InArgs);

private:
	FSlateColor GetTextColor() const;

	TAttribute<bool> Selected;
};

/** A tall main-menu tile with a gradient, fighter artwork and a lift and white frame when focused. */
class OPENSTANCE_API SOpenStanceHubTile : public SOpenStanceInteractive
{
public:
	SLATE_BEGIN_ARGS(SOpenStanceHubTile)
		: _GradientFrom(FLinearColor::Black)
		, _GradientTo(FLinearColor::Black)
		, _ShowKick(false)
		, _Future(false)
		, _Locked(false)
	{
	}
		SLATE_ARGUMENT(FString, Title)
		SLATE_ARGUMENT(FString, Subtitle)
		SLATE_ARGUMENT(FLinearColor, GradientFrom)
		SLATE_ARGUMENT(FLinearColor, GradientTo)
		/** Artwork pose: a kick or a ready stance. */
		SLATE_ARGUMENT(bool, ShowKick)
		/** Shows the amber Future tag; the tile still opens its information page. */
		SLATE_ARGUMENT(bool, Future)
		OPENSTANCE_INTERACTIVE_ARGUMENTS
	SLATE_END_ARGS()

	void Construct(const FArguments& InArgs);

protected:
	virtual void OnActiveChanged(bool bActive) override;

private:
	FLinearColor GetFill() const;
	OpenStanceMenuPaint::FGradient GetGradient() const;
	FLinearColor GetDimming() const;
	FLinearColor GetOutline() const;

	FLinearColor GradientFrom;
	FLinearColor GradientTo;
	bool bFuture = false;
};

/** A premade fighter in the select list (.tile). Hong tiles use a red rule. */
class OPENSTANCE_API SOpenStanceFighterTile : public SOpenStanceInteractive
{
public:
	SLATE_BEGIN_ARGS(SOpenStanceFighterTile)
		: _Selected(false)
		, _Hong(false)
		, _Locked(false)
	{
	}
		SLATE_ARGUMENT(FString, Name)
		SLATE_ARGUMENT(FString, Detail)
		SLATE_ATTRIBUTE(bool, Selected)
		SLATE_ARGUMENT(bool, Hong)
		OPENSTANCE_INTERACTIVE_ARGUMENTS
	SLATE_END_ARGS()

	void Construct(const FArguments& InArgs);

private:
	FLinearColor GetFill() const;
	FLinearColor GetRule() const;

	TAttribute<bool> Selected;
	bool bHong = false;
};

/** A colour choice in the fighter creator. */
class OPENSTANCE_API SOpenStanceSwatch : public SOpenStanceInteractive
{
public:
	SLATE_BEGIN_ARGS(SOpenStanceSwatch)
		: _Color(FLinearColor::White)
		, _Selected(false)
		, _Locked(false)
	{
	}
		SLATE_ARGUMENT(FLinearColor, Color)
		SLATE_ATTRIBUTE(bool, Selected)
		OPENSTANCE_INTERACTIVE_ARGUMENTS
	SLATE_END_ARGS()

	void Construct(const FArguments& InArgs);

private:
	FLinearColor GetOutline() const;

	TAttribute<bool> Selected;
};

/** Label, slider and value on one row (.sl). Left and right step the value; the slider also takes the pointer. */
class OPENSTANCE_API SOpenStanceSliderRow : public SOpenStanceInteractive
{
public:
	DECLARE_DELEGATE_OneParam(FOnValueChanged, float);

	SLATE_BEGIN_ARGS(SOpenStanceSliderRow)
		: _Min(0.0f)
		, _Max(100.0f)
		, _Step(5.0f)
		, _Value(0.0f)
		, _Locked(false)
	{
	}
		SLATE_ARGUMENT(FString, Label)
		SLATE_ARGUMENT(float, Min)
		SLATE_ARGUMENT(float, Max)
		SLATE_ARGUMENT(float, Step)
		SLATE_ATTRIBUTE(float, Value)
		/** Formats the value for the right-hand readout; defaults to a rounded integer. */
		SLATE_ARGUMENT(TFunction<FString(float)>, Format)
		SLATE_ARGUMENT(TSharedPtr<SWidget>, TagWidget)
		SLATE_EVENT(FOnValueChanged, OnValueChanged)
		SLATE_EVENT(FSimpleDelegate, OnActivated)
		SLATE_ARGUMENT(bool, Locked)
	SLATE_END_ARGS()

	void Construct(const FArguments& InArgs);

private:
	void StepValue(int32 Direction);
	void HandleSliderChanged(float NormalizedValue);
	float GetNormalized() const;
	FLinearColor GetFill() const;
	FLinearColor GetAccent() const;

	float Min = 0.0f;
	float Max = 100.0f;
	float Step = 5.0f;
	TAttribute<float> Value;
	TFunction<FString(float)> Format;
	FOnValueChanged OnValueChanged;
	FSliderStyle SliderStyle;
	FSlateBrush BarBrush;
	FSlateBrush ThumbBrush;
};
