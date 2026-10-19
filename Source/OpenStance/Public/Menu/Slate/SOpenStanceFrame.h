#pragma once

#include "CoreMinimal.h"
#include "Menu/Slate/OpenStanceMenuPaint.h"
#include "Widgets/SCompoundWidget.h"

enum class EOpenStanceFrameEdge : uint8
{
	None,
	Left,
	Top,
	Bottom
};

/**
 * The menu's box: a flat or gradient fill, an optional accent bar on one edge, an optional outline and the cut
 * bottom-right corner the prototype's buttons and tiles use (CSS clip-path). Every panel, button and tag is one of
 * these with different arguments, so the visual language lives in one place.
 */
class OPENSTANCE_API SOpenStanceFrame : public SCompoundWidget
{
public:
	SLATE_BEGIN_ARGS(SOpenStanceFrame)
		: _Fill(FLinearColor::Transparent)
		, _Gradient()
		, _OutlineColor(FLinearColor::Transparent)
		, _OutlineThickness(0.0f)
		, _AccentColor(FLinearColor::Transparent)
		, _AccentEdge(EOpenStanceFrameEdge::None)
		, _AccentThickness(0.0f)
		, _CutCorner(0.0f)
		, _Padding(FMargin(0.0f))
		, _ClipContent(false)
	{
	}
		/** Flat fill. Ignored while Gradient has stops. */
		SLATE_ATTRIBUTE(FLinearColor, Fill)
		SLATE_ATTRIBUTE(OpenStanceMenuPaint::FGradient, Gradient)
		SLATE_ATTRIBUTE(FLinearColor, OutlineColor)
		SLATE_ARGUMENT(float, OutlineThickness)
		SLATE_ATTRIBUTE(FLinearColor, AccentColor)
		SLATE_ARGUMENT(EOpenStanceFrameEdge, AccentEdge)
		SLATE_ARGUMENT(float, AccentThickness)
		/** Size of the diagonal cut on the bottom-right corner, in canvas pixels. */
		SLATE_ARGUMENT(float, CutCorner)
		SLATE_ATTRIBUTE(FMargin, Padding)
		/** Clip children to the frame, for artwork that overhangs the edge. */
		SLATE_ARGUMENT(bool, ClipContent)
		SLATE_DEFAULT_SLOT(FArguments, Content)
	SLATE_END_ARGS()

	void Construct(const FArguments& InArgs);

	virtual int32 OnPaint(const FPaintArgs& Args, const FGeometry& AllottedGeometry, const FSlateRect& MyCullingRect,
		FSlateWindowElementList& OutDrawElements, int32 LayerId, const FWidgetStyle& InWidgetStyle, bool bParentEnabled) const override;

private:
	TAttribute<FLinearColor> Fill;
	TAttribute<OpenStanceMenuPaint::FGradient> Gradient;
	TAttribute<FLinearColor> OutlineColor;
	TAttribute<FLinearColor> AccentColor;
	float OutlineThickness = 0.0f;
	EOpenStanceFrameEdge AccentEdge = EOpenStanceFrameEdge::None;
	float AccentThickness = 0.0f;
	float CutCorner = 0.0f;
};
