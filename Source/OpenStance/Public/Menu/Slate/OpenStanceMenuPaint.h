#pragma once

#include "CoreMinimal.h"
#include "Fonts/SlateFontInfo.h"
#include "Layout/Geometry.h"
#include "Styling/WidgetStyle.h"

class FSlateWindowElementList;

/**
 * Low-level drawing for the menu's custom widgets: filled polygons with per-vertex colour (so cut corners and
 * angled gradients work), radial glows, outlines and centred text. Shapes are given in widget-local space.
 *
 * Slate batches elements of different types separately, so overlapping shapes must be on different layers;
 * every call here moves Layer on by one.
 */
namespace OpenStanceMenuPaint
{
	/** What one paint pass draws into. Tint carries the widget's opacity, so shapes fade with their screen. */
	struct OPENSTANCE_API FPaintTarget
	{
		FPaintTarget(FSlateWindowElementList& InElements, const FGeometry& InGeometry, const FWidgetStyle& InStyle, int32 InLayer);

		FSlateWindowElementList& Elements;
		const FGeometry& Geometry;
		FLinearColor Tint;
		int32 Layer;
	};

	struct FGradientStop
	{
		/** 0 at the start of the gradient line, 1 at the end. */
		float Position = 0.0f;
		FLinearColor Color = FLinearColor::Transparent;
	};

	/** A CSS-style linear gradient: Angle 0 points up, 90 right, 180 down. Colours blend straight, without premultiplying. */
	struct OPENSTANCE_API FGradient
	{
		float AngleDegrees = 180.0f;
		TArray<FGradientStop> Stops;

		FLinearColor Evaluate(float Position) const;
		static FGradient TwoColor(float AngleDegrees, const FLinearColor& From, const FLinearColor& To);
	};

	/**
	 * A flattened vector path built from SVG-style commands, so the prototype's inline SVG artwork can be
	 * ported with its own coordinates. Curves are flattened to straight segments.
	 */
	class OPENSTANCE_API FPath
	{
	public:
		FPath& MoveTo(float X, float Y);
		FPath& LineTo(float X, float Y);
		FPath& QuadTo(float ControlX, float ControlY, float X, float Y);

		static FPath Rect(float X, float Y, float Width, float Height);
		static FPath RoundedRect(float X, float Y, float Width, float Height, float Radius);
		static FPath Ellipse(float CenterX, float CenterY, float RadiusX, float RadiusY, int32 Segments = 32);

		/** A copy scaled about the origin, then moved by Offset. */
		FPath Placed(const FVector2f& Offset, float Scale) const;
		FPath Rotated(float Degrees, const FVector2f& Pivot) const;

		TConstArrayView<FVector2f> GetPoints() const
		{
			return Points;
		}

	private:
		static constexpr int32 CurveSegments = 10;
		TArray<FVector2f> Points;
	};

	OPENSTANCE_API void FillPolygon(FPaintTarget& Target, TConstArrayView<FVector2f> Points, const FLinearColor& Color);

	/** Fills a convex polygon with a gradient laid over a box of BoxSize (the widget, or the shape's bounds). */
	OPENSTANCE_API void FillPolygonGradient(FPaintTarget& Target, TConstArrayView<FVector2f> Points, const FVector2f& BoxSize, const FGradient& Gradient);

	OPENSTANCE_API void FillRect(FPaintTarget& Target, const FVector2f& TopLeft, const FVector2f& Size, const FLinearColor& Color);

	/** A soft elliptical glow: CenterColor at the middle fading linearly to EdgeColor at the radii. */
	OPENSTANCE_API void FillGlow(FPaintTarget& Target, const FVector2f& Center, const FVector2f& Radii, const FLinearColor& CenterColor, const FLinearColor& EdgeColor);

	OPENSTANCE_API void StrokePolyline(FPaintTarget& Target, TConstArrayView<FVector2f> Points, const FLinearColor& Color, float Thickness, bool bClosed);

	OPENSTANCE_API void DrawCenteredText(FPaintTarget& Target, const FString& Text, const FSlateFontInfo& Font, const FVector2f& Center, const FLinearColor& Color);
}
