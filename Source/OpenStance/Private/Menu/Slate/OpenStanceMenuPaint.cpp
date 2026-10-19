#include "Menu/Slate/OpenStanceMenuPaint.h"

#include "Fonts/FontMeasure.h"
#include "Framework/Application/SlateApplication.h"
#include "Menu/OpenStanceMenuTheme.h"
#include "Rendering/DrawElements.h"
#include "Rendering/RenderingCommon.h"
#include "Rendering/SlateRenderer.h"

namespace OpenStanceMenuPaint
{
	namespace
	{
		FSlateVertex MakeVertex(const FPaintTarget& Target, const FVector2f& Local, const FLinearColor& Color)
		{
			// Custom vertices are drawn untransformed, so move them to window space here
			const FVector2f Window(Target.Geometry.GetAccumulatedRenderTransform().TransformPoint(Local));
			return FSlateVertex::Make<ESlateVertexRounding::Disabled>(FSlateRenderTransform(), Window, FVector2f(0.5f, 0.5f), (Color * Target.Tint).ToFColor(true));
		}

		void Submit(FPaintTarget& Target, const TArray<FSlateVertex>& Vertices, const TArray<SlateIndex>& Indices)
		{
			if (Vertices.IsEmpty() || Indices.IsEmpty() || !FSlateApplication::IsInitialized())
			{
				return;
			}
			FSlateRenderer* Renderer = FSlateApplication::Get().GetRenderer();
			if (!Renderer)
			{
				return;
			}
			// Any texture will do: the vertices carry the colour and the white tile leaves it unchanged
			const FSlateResourceHandle White = Renderer->GetResourceHandle(*OpenStanceMenu::Brushes::White());
			FSlateDrawElement::MakeCustomVerts(Target.Elements, Target.Layer++, White, Vertices, Indices, nullptr, 0, 0);
		}

		float Cross(const FVector2f& A, const FVector2f& B, const FVector2f& C)
		{
			return (B.X - A.X) * (C.Y - A.Y) - (B.Y - A.Y) * (C.X - A.X);
		}

		bool IsInsideTriangle(const FVector2f& P, const FVector2f& A, const FVector2f& B, const FVector2f& C)
		{
			const float D1 = Cross(A, B, P);
			const float D2 = Cross(B, C, P);
			const float D3 = Cross(C, A, P);
			const bool bHasNegative = D1 < 0.0f || D2 < 0.0f || D3 < 0.0f;
			const bool bHasPositive = D1 > 0.0f || D2 > 0.0f || D3 > 0.0f;
			return !(bHasNegative && bHasPositive);
		}

		/** Ear clipping, so concave artwork such as the controller body and the hair caps fills correctly. */
		void Triangulate(TConstArrayView<FVector2f> Points, TArray<SlateIndex>& OutIndices)
		{
			const int32 Num = Points.Num();
			if (Num < 3)
			{
				return;
			}

			float DoubleArea = 0.0f;
			for (int32 Index = 0; Index < Num; ++Index)
			{
				const FVector2f& A = Points[Index];
				const FVector2f& B = Points[(Index + 1) % Num];
				DoubleArea += A.X * B.Y - B.X * A.Y;
			}
			const float Winding = DoubleArea >= 0.0f ? 1.0f : -1.0f;

			TArray<int32> Remaining;
			Remaining.Reserve(Num);
			for (int32 Index = 0; Index < Num; ++Index)
			{
				Remaining.Add(Index);
			}

			int32 Guard = Num * Num;
			while (Remaining.Num() > 3 && Guard-- > 0)
			{
				bool bClipped = false;
				for (int32 Corner = 0; Corner < Remaining.Num(); ++Corner)
				{
					const int32 Previous = Remaining[(Corner + Remaining.Num() - 1) % Remaining.Num()];
					const int32 Current = Remaining[Corner];
					const int32 Next = Remaining[(Corner + 1) % Remaining.Num()];
					if (Cross(Points[Previous], Points[Current], Points[Next]) * Winding <= 0.0f)
					{
						continue;
					}

					bool bContainsPoint = false;
					for (const int32 Other : Remaining)
					{
						if (Other != Previous && Other != Current && Other != Next && IsInsideTriangle(Points[Other], Points[Previous], Points[Current], Points[Next]))
						{
							bContainsPoint = true;
							break;
						}
					}
					if (bContainsPoint)
					{
						continue;
					}

					OutIndices.Add(static_cast<SlateIndex>(Previous));
					OutIndices.Add(static_cast<SlateIndex>(Current));
					OutIndices.Add(static_cast<SlateIndex>(Next));
					Remaining.RemoveAt(Corner);
					bClipped = true;
					break;
				}
				if (!bClipped)
				{
					break;
				}
			}

			// Whatever is left is a convex fan; also the fallback for degenerate input
			for (int32 Index = 1; Index + 1 < Remaining.Num(); ++Index)
			{
				OutIndices.Add(static_cast<SlateIndex>(Remaining[0]));
				OutIndices.Add(static_cast<SlateIndex>(Remaining[Index]));
				OutIndices.Add(static_cast<SlateIndex>(Remaining[Index + 1]));
			}
		}

		/** Keeps the part of a convex polygon where Signed(point) >= 0. */
		TArray<FVector2f> ClipByPlane(TConstArrayView<FVector2f> In, TFunctionRef<float(const FVector2f&)> Signed)
		{
			TArray<FVector2f> Out;
			const int32 Num = In.Num();
			for (int32 Index = 0; Index < Num; ++Index)
			{
				const FVector2f& A = In[Index];
				const FVector2f& B = In[(Index + 1) % Num];
				const float DistanceA = Signed(A);
				const float DistanceB = Signed(B);
				if (DistanceA >= 0.0f)
				{
					Out.Add(A);
				}
				if ((DistanceA >= 0.0f) != (DistanceB >= 0.0f))
				{
					Out.Add(A + (B - A) * (DistanceA / (DistanceA - DistanceB)));
				}
			}
			return Out;
		}
	}

	FPaintTarget::FPaintTarget(FSlateWindowElementList& InElements, const FGeometry& InGeometry, const FWidgetStyle& InStyle, int32 InLayer)
		: Elements(InElements)
		, Geometry(InGeometry)
		, Tint(InStyle.GetColorAndOpacityTint())
		, Layer(InLayer)
	{
	}

	FLinearColor FGradient::Evaluate(float Position) const
	{
		if (Stops.IsEmpty())
		{
			return FLinearColor::Transparent;
		}
		if (Position <= Stops[0].Position)
		{
			return Stops[0].Color;
		}
		for (int32 Index = 1; Index < Stops.Num(); ++Index)
		{
			if (Position <= Stops[Index].Position)
			{
				const float Span = Stops[Index].Position - Stops[Index - 1].Position;
				const float Alpha = Span > UE_SMALL_NUMBER ? (Position - Stops[Index - 1].Position) / Span : 1.0f;
				return FMath::Lerp(Stops[Index - 1].Color, Stops[Index].Color, Alpha);
			}
		}
		return Stops.Last().Color;
	}

	FGradient FGradient::TwoColor(float AngleDegrees, const FLinearColor& From, const FLinearColor& To)
	{
		FGradient Result;
		Result.AngleDegrees = AngleDegrees;
		Result.Stops = { { 0.0f, From }, { 1.0f, To } };
		return Result;
	}

	FPath& FPath::MoveTo(float X, float Y)
	{
		Points.Emplace(X, Y);
		return *this;
	}

	FPath& FPath::LineTo(float X, float Y)
	{
		Points.Emplace(X, Y);
		return *this;
	}

	FPath& FPath::QuadTo(float ControlX, float ControlY, float X, float Y)
	{
		const FVector2f Start = Points.IsEmpty() ? FVector2f(X, Y) : Points.Last();
		const FVector2f Control(ControlX, ControlY);
		const FVector2f End(X, Y);
		for (int32 Step = 1; Step <= CurveSegments; ++Step)
		{
			const float T = static_cast<float>(Step) / CurveSegments;
			const float Inverse = 1.0f - T;
			Points.Add(Start * (Inverse * Inverse) + Control * (2.0f * Inverse * T) + End * (T * T));
		}
		return *this;
	}

	FPath FPath::Rect(float X, float Y, float Width, float Height)
	{
		FPath Path;
		Path.MoveTo(X, Y).LineTo(X + Width, Y).LineTo(X + Width, Y + Height).LineTo(X, Y + Height);
		return Path;
	}

	FPath FPath::RoundedRect(float X, float Y, float Width, float Height, float Radius)
	{
		const float Clamped = FMath::Min(Radius, FMath::Min(Width, Height) * 0.5f);
		const int32 ArcSegments = 6;
		const FVector2f Centres[4] =
		{
			FVector2f(X + Width - Clamped, Y + Clamped),
			FVector2f(X + Width - Clamped, Y + Height - Clamped),
			FVector2f(X + Clamped, Y + Height - Clamped),
			FVector2f(X + Clamped, Y + Clamped)
		};

		FPath Path;
		for (int32 Corner = 0; Corner < 4; ++Corner)
		{
			// Corners run clockwise on screen, starting at top right; each arc sweeps a quarter turn
			const float StartAngle = -90.0f + 90.0f * Corner;
			for (int32 Step = 0; Step <= ArcSegments; ++Step)
			{
				const float Angle = FMath::DegreesToRadians(StartAngle + 90.0f * Step / ArcSegments);
				Path.Points.Add(Centres[Corner] + FVector2f(FMath::Cos(Angle), FMath::Sin(Angle)) * Clamped);
			}
		}
		return Path;
	}

	FPath FPath::Ellipse(float CenterX, float CenterY, float RadiusX, float RadiusY, int32 Segments)
	{
		FPath Path;
		for (int32 Index = 0; Index < Segments; ++Index)
		{
			const float Angle = UE_TWO_PI * Index / Segments;
			Path.Points.Emplace(CenterX + FMath::Cos(Angle) * RadiusX, CenterY + FMath::Sin(Angle) * RadiusY);
		}
		return Path;
	}

	FPath FPath::Placed(const FVector2f& Offset, float Scale) const
	{
		FPath Result;
		Result.Points.Reserve(Points.Num());
		for (const FVector2f& Point : Points)
		{
			Result.Points.Add(Point * Scale + Offset);
		}
		return Result;
	}

	FPath FPath::Rotated(float Degrees, const FVector2f& Pivot) const
	{
		const float Radians = FMath::DegreesToRadians(Degrees);
		const float Sine = FMath::Sin(Radians);
		const float Cosine = FMath::Cos(Radians);
		FPath Result;
		Result.Points.Reserve(Points.Num());
		for (const FVector2f& Point : Points)
		{
			const FVector2f Offset = Point - Pivot;
			Result.Points.Add(Pivot + FVector2f(Offset.X * Cosine - Offset.Y * Sine, Offset.X * Sine + Offset.Y * Cosine));
		}
		return Result;
	}

	void FillPolygon(FPaintTarget& Target, TConstArrayView<FVector2f> Points, const FLinearColor& Color)
	{
		if (Points.Num() < 3 || Color.A <= 0.0f)
		{
			return;
		}
		TArray<FSlateVertex> Vertices;
		Vertices.Reserve(Points.Num());
		for (const FVector2f& Point : Points)
		{
			Vertices.Add(MakeVertex(Target, Point, Color));
		}
		TArray<SlateIndex> Indices;
		Triangulate(Points, Indices);
		Submit(Target, Vertices, Indices);
	}

	void FillPolygonGradient(FPaintTarget& Target, TConstArrayView<FVector2f> Points, const FVector2f& BoxSize, const FGradient& Gradient)
	{
		if (Points.Num() < 3 || Gradient.Stops.IsEmpty())
		{
			return;
		}

		const float Radians = FMath::DegreesToRadians(Gradient.AngleDegrees);
		const FVector2f Direction(FMath::Sin(Radians), -FMath::Cos(Radians));
		const float Length = FMath::Max(FMath::Abs(BoxSize.X * Direction.X) + FMath::Abs(BoxSize.Y * Direction.Y), UE_SMALL_NUMBER);
		const FVector2f Centre = BoxSize * 0.5f;
		const auto PositionOf = [&](const FVector2f& Point)
		{
			return FVector2f::DotProduct(Point - Centre, Direction) / Length + 0.5f;
		};

		// A vertex-coloured triangle only blends linearly, so cut the shape at every stop and shade each slice
		TArray<float> Bounds;
		Bounds.Add(-TNumericLimits<float>::Max());
		for (const FGradientStop& Stop : Gradient.Stops)
		{
			Bounds.Add(Stop.Position);
		}
		Bounds.Add(TNumericLimits<float>::Max());

		for (int32 Slice = 0; Slice + 1 < Bounds.Num(); ++Slice)
		{
			const float Low = Bounds[Slice];
			const float High = Bounds[Slice + 1];
			if (High - Low <= UE_KINDA_SMALL_NUMBER)
			{
				continue;
			}

			TArray<FVector2f> Clipped = ClipByPlane(Points, [&](const FVector2f& Point) { return PositionOf(Point) - Low; });
			if (Clipped.Num() < 3)
			{
				continue;
			}
			Clipped = ClipByPlane(Clipped, [&](const FVector2f& Point) { return High - PositionOf(Point); });
			if (Clipped.Num() < 3)
			{
				continue;
			}

			// Sample just inside the slice so a hard stop (two stops at one position) gives a crisp edge, not a blend
			const float SliceInset = 1.0e-5f;
			TArray<FSlateVertex> Vertices;
			Vertices.Reserve(Clipped.Num());
			for (const FVector2f& Point : Clipped)
			{
				const float Sample = FMath::Clamp(PositionOf(Point), Low + SliceInset, High - SliceInset);
				Vertices.Add(MakeVertex(Target, Point, Gradient.Evaluate(Sample)));
			}
			TArray<SlateIndex> Indices;
			Triangulate(Clipped, Indices);
			Submit(Target, Vertices, Indices);
		}
	}

	void FillRect(FPaintTarget& Target, const FVector2f& TopLeft, const FVector2f& Size, const FLinearColor& Color)
	{
		const FVector2f Points[4] =
		{
			TopLeft,
			TopLeft + FVector2f(Size.X, 0.0f),
			TopLeft + Size,
			TopLeft + FVector2f(0.0f, Size.Y)
		};
		FillPolygon(Target, Points, Color);
	}

	void FillGlow(FPaintTarget& Target, const FVector2f& Center, const FVector2f& Radii, const FLinearColor& CenterColor, const FLinearColor& EdgeColor)
	{
		const int32 Segments = 48;
		TArray<FSlateVertex> Vertices;
		Vertices.Reserve(Segments + 1);
		Vertices.Add(MakeVertex(Target, Center, CenterColor));
		for (int32 Index = 0; Index < Segments; ++Index)
		{
			const float Angle = UE_TWO_PI * Index / Segments;
			Vertices.Add(MakeVertex(Target, Center + FVector2f(FMath::Cos(Angle) * Radii.X, FMath::Sin(Angle) * Radii.Y), EdgeColor));
		}

		TArray<SlateIndex> Indices;
		Indices.Reserve(Segments * 3);
		for (int32 Index = 0; Index < Segments; ++Index)
		{
			Indices.Add(0);
			Indices.Add(static_cast<SlateIndex>(1 + Index));
			Indices.Add(static_cast<SlateIndex>(1 + (Index + 1) % Segments));
		}
		Submit(Target, Vertices, Indices);
	}

	void StrokePolyline(FPaintTarget& Target, TConstArrayView<FVector2f> Points, const FLinearColor& Color, float Thickness, bool bClosed)
	{
		if (Points.Num() < 2 || Color.A <= 0.0f)
		{
			return;
		}
		TArray<FVector2f> Line(Points);
		if (bClosed)
		{
			Line.Add(Points[0]);
		}
		FSlateDrawElement::MakeLines(Target.Elements, Target.Layer++, Target.Geometry.ToPaintGeometry(), Line,
			ESlateDrawEffect::None, Color * Target.Tint, true, Thickness);
	}

	void DrawCenteredText(FPaintTarget& Target, const FString& Text, const FSlateFontInfo& Font, const FVector2f& Center, const FLinearColor& Color)
	{
		if (Text.IsEmpty() || !FSlateApplication::IsInitialized())
		{
			return;
		}
		const TSharedRef<FSlateFontMeasure> Measure = FSlateApplication::Get().GetRenderer()->GetFontMeasureService();
		const FVector2f TextSize(Measure->Measure(Text, Font));
		FSlateDrawElement::MakeText(Target.Elements, Target.Layer++,
			Target.Geometry.ToPaintGeometry(TextSize, FSlateLayoutTransform(Center - TextSize * 0.5f)),
			Text, Font, ESlateDrawEffect::None, Color * Target.Tint);
	}
}
