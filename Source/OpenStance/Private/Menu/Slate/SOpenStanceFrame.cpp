#include "Menu/Slate/SOpenStanceFrame.h"

void SOpenStanceFrame::Construct(const FArguments& InArgs)
{
	Fill = InArgs._Fill;
	Gradient = InArgs._Gradient;
	OutlineColor = InArgs._OutlineColor;
	AccentColor = InArgs._AccentColor;
	OutlineThickness = InArgs._OutlineThickness;
	AccentEdge = InArgs._AccentEdge;
	AccentThickness = InArgs._AccentThickness;
	CutCorner = InArgs._CutCorner;

	if (InArgs._ClipContent)
	{
		SetClipping(EWidgetClipping::ClipToBounds);
	}

	ChildSlot
	.Padding(InArgs._Padding)
	[
		InArgs._Content.Widget
	];
}

int32 SOpenStanceFrame::OnPaint(const FPaintArgs& Args, const FGeometry& AllottedGeometry, const FSlateRect& MyCullingRect,
	FSlateWindowElementList& OutDrawElements, int32 LayerId, const FWidgetStyle& InWidgetStyle, bool bParentEnabled) const
{
	using namespace OpenStanceMenuPaint;

	const FVector2f Size = AllottedGeometry.GetLocalSize();
	const float Cut = FMath::Clamp(CutCorner, 0.0f, FMath::Min(Size.X, Size.Y) * 0.5f);

	TArray<FVector2f, TInlineAllocator<5>> Shape;
	Shape.Add(FVector2f(0.0f, 0.0f));
	Shape.Add(FVector2f(Size.X, 0.0f));
	if (Cut > 0.0f)
	{
		Shape.Add(FVector2f(Size.X, Size.Y - Cut));
		Shape.Add(FVector2f(Size.X - Cut, Size.Y));
	}
	else
	{
		Shape.Add(FVector2f(Size.X, Size.Y));
	}
	Shape.Add(FVector2f(0.0f, Size.Y));

	FPaintTarget Target(OutDrawElements, AllottedGeometry, InWidgetStyle, LayerId);

	const FGradient GradientValue = Gradient.Get(FGradient());
	if (!GradientValue.Stops.IsEmpty())
	{
		FillPolygonGradient(Target, Shape, Size, GradientValue);
	}
	else
	{
		FillPolygon(Target, Shape, Fill.Get(FLinearColor::Transparent));
	}

	if (AccentEdge != EOpenStanceFrameEdge::None && AccentThickness > 0.0f)
	{
		const FLinearColor Accent = AccentColor.Get(FLinearColor::Transparent);
		switch (AccentEdge)
		{
		case EOpenStanceFrameEdge::Left:
			FillRect(Target, FVector2f::ZeroVector, FVector2f(AccentThickness, Size.Y), Accent);
			break;
		case EOpenStanceFrameEdge::Top:
			FillRect(Target, FVector2f::ZeroVector, FVector2f(Size.X, AccentThickness), Accent);
			break;
		case EOpenStanceFrameEdge::Bottom:
			FillRect(Target, FVector2f(0.0f, Size.Y - AccentThickness), FVector2f(Size.X, AccentThickness), Accent);
			break;
		default:
			break;
		}
	}

	const int32 ContentLayer = SCompoundWidget::OnPaint(Args, AllottedGeometry, MyCullingRect, OutDrawElements, Target.Layer, InWidgetStyle, bParentEnabled);

	const FLinearColor Outline = OutlineColor.Get(FLinearColor::Transparent);
	if (OutlineThickness > 0.0f && Outline.A > 0.0f)
	{
		// Inset by half the stroke so it stays inside the frame; a 45 degree cut moves in by (2 - sqrt 2) of the inset
		const float Half = OutlineThickness * 0.5f;
		const float InsetCut = Cut > 0.0f ? FMath::Max(Cut - Half * 0.586f, 0.0f) : 0.0f;
		TArray<FVector2f, TInlineAllocator<5>> Border;
		Border.Add(FVector2f(Half, Half));
		Border.Add(FVector2f(Size.X - Half, Half));
		if (InsetCut > 0.0f)
		{
			Border.Add(FVector2f(Size.X - Half, Size.Y - Half - InsetCut));
			Border.Add(FVector2f(Size.X - Half - InsetCut, Size.Y - Half));
		}
		else
		{
			Border.Add(FVector2f(Size.X - Half, Size.Y - Half));
		}
		Border.Add(FVector2f(Half, Size.Y - Half));

		FPaintTarget OutlineTarget(OutDrawElements, AllottedGeometry, InWidgetStyle, ContentLayer + 1);
		StrokePolyline(OutlineTarget, Border, Outline, OutlineThickness, true);
		return OutlineTarget.Layer;
	}
	return ContentLayer;
}
