#include "Menu/Slate/SOpenStanceArt.h"

#include "Menu/Slate/OpenStanceMenuPaint.h"

using namespace OpenStanceMenu;
using namespace OpenStanceMenuPaint;

// SOpenStanceBackdrop

void SOpenStanceBackdrop::Construct(const FArguments& InArgs)
{
	SetClipping(EWidgetClipping::ClipToBounds);
}

FVector2D SOpenStanceBackdrop::ComputeDesiredSize(float LayoutScaleMultiplier) const
{
	return FVector2D(DesignWidth, DesignHeight);
}

int32 SOpenStanceBackdrop::OnPaint(const FPaintArgs& Args, const FGeometry& AllottedGeometry, const FSlateRect& MyCullingRect,
	FSlateWindowElementList& OutDrawElements, int32 LayerId, const FWidgetStyle& InWidgetStyle, bool bParentEnabled) const
{
	const FVector2f Size = AllottedGeometry.GetLocalSize();
	FPaintTarget Target(OutDrawElements, AllottedGeometry, InWidgetStyle, LayerId);

	const FPath Screen = FPath::Rect(0.0f, 0.0f, Size.X, Size.Y);

	FGradient Night;
	Night.AngleDegrees = 160.0f;
	Night.Stops = { { 0.0f, Hex(0x0a1530) }, { 0.55f, Hex(0x050912) }, { 1.0f, Hex(0x0b0710) } };
	FillPolygonGradient(Target, Screen.GetPoints(), Size, Night);

	// Radii are the prototype's ellipse extents, cut to where each gradient reaches transparent (70%)
	FillGlow(Target, FVector2f(Size.X * 0.0f, Size.Y), FVector2f(Size.X * 0.42f, Size.Y * 0.35f), Hex(0x2f6fe4, 0.22f), Hex(0x2f6fe4, 0.0f));
	FillGlow(Target, FVector2f(Size.X * 0.78f, 0.0f), FVector2f(Size.X * 0.49f, Size.Y * 0.42f), Hex(0x53c7ff, 0.28f), Hex(0x53c7ff, 0.0f));

	const FLinearColor Clear(1.0f, 1.0f, 1.0f, 0.0f);
	const FLinearColor Band(1.0f, 1.0f, 1.0f, 0.05f);
	const FLinearColor FaintBand(1.0f, 1.0f, 1.0f, 0.03f);
	FGradient Bands;
	Bands.AngleDegrees = 112.0f;
	Bands.Stops =
	{
		{ 0.0f, Clear }, { 0.55f, Clear },
		{ 0.55f, Band }, { 0.562f, Band },
		{ 0.562f, Clear }, { 0.60f, Clear },
		{ 0.60f, FaintBand }, { 0.63f, FaintBand },
		{ 0.63f, Clear }, { 1.0f, Clear }
	};
	FillPolygonGradient(Target, Screen.GetPoints(), Size, Bands);

	return Target.Layer;
}

// SOpenStanceArenaBackdrop

void SOpenStanceArenaBackdrop::Construct(const FArguments& InArgs)
{
	SetClipping(EWidgetClipping::ClipToBounds);
}

FVector2D SOpenStanceArenaBackdrop::ComputeDesiredSize(float LayoutScaleMultiplier) const
{
	return FVector2D(DesignWidth, DesignHeight);
}

int32 SOpenStanceArenaBackdrop::OnPaint(const FPaintArgs& Args, const FGeometry& AllottedGeometry, const FSlateRect& MyCullingRect,
	FSlateWindowElementList& OutDrawElements, int32 LayerId, const FWidgetStyle& InWidgetStyle, bool bParentEnabled) const
{
	const FVector2f Size = AllottedGeometry.GetLocalSize();
	FPaintTarget Target(OutDrawElements, AllottedGeometry, InWidgetStyle, LayerId);

	const FLinearColor Floor = Hex(0x10141d);
	FillRect(Target, FVector2f::ZeroVector, Size, Floor);
	FillGlow(Target, FVector2f(Size.X * 0.5f, Size.Y * 0.85f), FVector2f(Size.X * 0.7f, Size.Y * 0.85f), Hex(0x2b3547), Hex(0x2b3547, 0.0f));

	// The mat is the prototype's rotated rectangle, worked out as a trapezoid: wide near edge, narrower far edge
	const float NearY = Size.Y * 0.917f;
	const float FarY = Size.Y * 0.759f;
	const float NearLeft = Size.X * 0.12f;
	const float NearRight = Size.X * 0.88f;
	const float FarLeft = Size.X * 0.209f;
	const float FarRight = Size.X * 0.791f;

	FPath Mat;
	Mat.MoveTo(NearLeft, NearY).LineTo(NearRight, NearY).LineTo(FarRight, FarY).LineTo(FarLeft, FarY);
	FillPolygon(Target, Mat.GetPoints(), Hex(0x1b2433));

	// Alternate darker stripes, each 6u wide at the near edge and narrower with distance
	const int32 StripeCount = 12;
	for (int32 Stripe = 1; Stripe < StripeCount; Stripe += 2)
	{
		const float From = static_cast<float>(Stripe) / StripeCount;
		const float To = static_cast<float>(Stripe + 1) / StripeCount;
		FPath Band;
		Band.MoveTo(FMath::Lerp(NearLeft, NearRight, From), NearY).LineTo(FMath::Lerp(NearLeft, NearRight, To), NearY)
			.LineTo(FMath::Lerp(FarLeft, FarRight, To), FarY).LineTo(FMath::Lerp(FarLeft, FarRight, From), FarY);
		FillPolygon(Target, Band.GetPoints(), Hex(0x18202d));
	}
	StrokePolyline(Target, Mat.GetPoints(), Hex(0x2c3850), U(0.3f), true);

	return Target.Layer;
}

// SOpenStanceFighterFigure

void SOpenStanceFighterFigure::Construct(const FArguments& InArgs)
{
	BodyColor = InArgs._BodyColor;
	TrimColor = InArgs._TrimColor;
	SkinColor = InArgs._SkinColor;
	HairColor = InArgs._HairColor;
	GearOn = InArgs._GearOn;
	Kick = InArgs._Kick;
	Sex = InArgs._Sex;
	bMirrored = InArgs._Mirrored;
}

FVector2D SOpenStanceFighterFigure::ComputeDesiredSize(float LayoutScaleMultiplier) const
{
	return FVector2D(120.0f, 200.0f);
}

int32 SOpenStanceFighterFigure::OnPaint(const FPaintArgs& Args, const FGeometry& AllottedGeometry, const FSlateRect& MyCullingRect,
	FSlateWindowElementList& OutDrawElements, int32 LayerId, const FWidgetStyle& InWidgetStyle, bool bParentEnabled) const
{
	// Coordinates below are the prototype's SVG, drawn in its 120 x 200 view box and fitted to the widget
	const FVector2f Size = AllottedGeometry.GetLocalSize();
	const float Scale = FMath::Min(Size.X / 120.0f, Size.Y / 200.0f);
	const FVector2f Offset((Size.X - 120.0f * Scale) * 0.5f, (Size.Y - 200.0f * Scale) * 0.5f);

	FPaintTarget Target(OutDrawElements, AllottedGeometry, InWidgetStyle, LayerId);
	const auto Draw = [&](const FPath& Path, const FLinearColor& Color)
	{
		TArray<FVector2f> Mapped;
		Mapped.Reserve(Path.GetPoints().Num());
		for (const FVector2f& Point : Path.GetPoints())
		{
			Mapped.Add(FVector2f(bMirrored ? 120.0f - Point.X : Point.X, Point.Y) * Scale + Offset);
		}
		FillPolygon(Target, Mapped, Color);
	};

	const bool bGear = GearOn.Get(false);
	const bool bKick = Kick.Get(false);
	const bool bFemale = Sex.Get(EOpenStanceSex::Male) == EOpenStanceSex::Female;
	const FLinearColor Skin = SkinColor.Get(Hex(0xc99a76));
	const FLinearColor Hair = HairColor.Get(Hex(0x1b1410));
	const FLinearColor Body = bGear ? BodyColor.Get(Palette::Chung) : Hex(0xe7e5de);
	const FLinearColor Trim = bGear ? TrimColor.Get(Palette::ChungDark) : Hex(0xbdb9ad);

	Draw(FPath::Ellipse(60.0f, 193.0f, 38.0f, 5.0f), FLinearColor(0.0f, 0.0f, 0.0f, 0.4f));

	FPath BackLeg;
	BackLeg.MoveTo(46.0f, 120.0f).LineTo(40.0f, 188.0f).LineTo(54.0f, 188.0f).LineTo(60.0f, 130.0f);
	Draw(BackLeg, Body);

	if (bKick)
	{
		FPath Leg;
		Leg.MoveTo(64.0f, 128.0f).LineTo(108.0f, 100.0f).LineTo(114.0f, 112.0f).LineTo(72.0f, 148.0f);
		Draw(Leg, Body);
		Draw(FPath::Rect(104.0f, 96.0f, 16.0f, 22.0f).Rotated(-25.0f, FVector2f(112.0f, 107.0f)), bGear ? Body : Skin);
	}
	else
	{
		FPath Leg;
		Leg.MoveTo(62.0f, 128.0f).LineTo(84.0f, 188.0f).LineTo(98.0f, 188.0f).LineTo(74.0f, 124.0f);
		Draw(Leg, Body);
	}
	if (bGear)
	{
		Draw(FPath::Rect(38.0f, 172.0f, 18.0f, 16.0f), Trim);
	}

	FPath Torso;
	if (bFemale)
	{
		Torso.MoveTo(42.0f, 62.0f).LineTo(78.0f, 62.0f).LineTo(85.0f, 126.0f).LineTo(35.0f, 126.0f);
	}
	else
	{
		Torso.MoveTo(38.0f, 62.0f).LineTo(82.0f, 62.0f).LineTo(88.0f, 126.0f).LineTo(34.0f, 126.0f);
	}
	Draw(Torso, Body);
	Draw(FPath::Rect(34.0f, 94.0f, 54.0f, 8.0f), bGear ? Hex(0x161a22) : Hex(0x232a38));
	if (bGear)
	{
		Draw(FPath::Rect(42.0f, 68.0f, 36.0f, 24.0f), Trim * FLinearColor(1.0f, 1.0f, 1.0f, 0.9f));
	}

	FPath LeftArm;
	LeftArm.MoveTo(38.0f, 66.0f).LineTo(18.0f, 100.0f).LineTo(28.0f, 108.0f).LineTo(46.0f, 82.0f);
	Draw(LeftArm, Body);
	FPath RightArm;
	RightArm.MoveTo(82.0f, 66.0f).LineTo(100.0f, 92.0f).LineTo(90.0f, 100.0f).LineTo(76.0f, 82.0f);
	Draw(RightArm, Body);
	Draw(FPath::Ellipse(22.0f, 106.0f, 9.0f, 9.0f), bGear ? Trim : Skin);
	Draw(FPath::Ellipse(94.0f, 98.0f, 9.0f, 9.0f), bGear ? Trim : Skin);

	Draw(FPath::Rect(54.0f, 50.0f, 12.0f, 14.0f), Skin);
	if (bFemale)
	{
		FPath Ponytail;
		Ponytail.MoveTo(72.0f, 28.0f).QuadTo(106.0f, 30.0f, 98.0f, 74.0f).QuadTo(93.0f, 54.0f, 72.0f, 46.0f);
		Draw(Ponytail, Hair);
	}
	Draw(FPath::Ellipse(60.0f, 38.0f, 17.0f, 20.0f), Skin);

	FPath HeadGear;
	if (bGear)
	{
		HeadGear.MoveTo(42.0f, 36.0f).QuadTo(60.0f, 4.0f, 78.0f, 36.0f).LineTo(78.0f, 44.0f).QuadTo(60.0f, 36.0f, 42.0f, 44.0f);
		Draw(HeadGear, Body);
	}
	else
	{
		HeadGear.MoveTo(43.0f, 34.0f).QuadTo(60.0f, 8.0f, 77.0f, 34.0f).QuadTo(60.0f, 24.0f, 43.0f, 34.0f);
		Draw(HeadGear, Hair);
	}

	return Target.Layer;
}

// SOpenStanceGamepadDiagram

namespace
{
	const FVector2f GamepadViewBox(400.0f, 250.0f);

	struct FGamepadPart
	{
		FName Id;
		FString Label;
		FVector2f Position;
		FVector2f Size;
		/** Round buttons use Size.X as the radius; boxes use the full size with rounded corners. */
		bool bRound;
	};

	const TArray<FGamepadPart>& GetGamepadParts()
	{
		static const TArray<FGamepadPart> Parts =
		{
			{ TEXT("LT"), TEXT("LT"), FVector2f(52.0f, 6.0f), FVector2f(62.0f, 22.0f), false },
			{ TEXT("RT"), TEXT("RT"), FVector2f(286.0f, 6.0f), FVector2f(62.0f, 22.0f), false },
			{ TEXT("LB"), TEXT("LB"), FVector2f(48.0f, 34.0f), FVector2f(76.0f, 20.0f), false },
			{ TEXT("RB"), TEXT("RB"), FVector2f(276.0f, 34.0f), FVector2f(76.0f, 20.0f), false },
			{ TEXT("LS"), TEXT("LS"), FVector2f(118.0f, 100.0f), FVector2f(22.0f, 22.0f), true },
			{ TEXT("RS"), TEXT("RS"), FVector2f(250.0f, 156.0f), FVector2f(22.0f, 22.0f), true },
			{ TEXT("MENU"), TEXT(""), FVector2f(200.0f, 96.0f), FVector2f(10.0f, 10.0f), true },
			{ TEXT("Y"), TEXT("Y"), FVector2f(282.0f, 80.0f), FVector2f(12.0f, 12.0f), true },
			{ TEXT("X"), TEXT("X"), FVector2f(258.0f, 102.0f), FVector2f(12.0f, 12.0f), true },
			{ TEXT("B"), TEXT("B"), FVector2f(306.0f, 102.0f), FVector2f(12.0f, 12.0f), true },
			{ TEXT("A"), TEXT("A"), FVector2f(282.0f, 124.0f), FVector2f(12.0f, 12.0f), true }
		};
		return Parts;
	}
}

void SOpenStanceGamepadDiagram::Construct(const FArguments& InArgs)
{
}

void SOpenStanceGamepadDiagram::SetHighlighted(const TArray<FName>& Keys)
{
	Highlighted = TSet<FName>(Keys);
	Invalidate(EInvalidateWidgetReason::Paint);
}

FVector2D SOpenStanceGamepadDiagram::ComputeDesiredSize(float LayoutScaleMultiplier) const
{
	return FVector2D(GamepadViewBox.X, GamepadViewBox.Y);
}

int32 SOpenStanceGamepadDiagram::OnPaint(const FPaintArgs& Args, const FGeometry& AllottedGeometry, const FSlateRect& MyCullingRect,
	FSlateWindowElementList& OutDrawElements, int32 LayerId, const FWidgetStyle& InWidgetStyle, bool bParentEnabled) const
{
	const FVector2f Size = AllottedGeometry.GetLocalSize();
	const float Scale = FMath::Min(Size.X / GamepadViewBox.X, Size.Y / GamepadViewBox.Y);
	const FVector2f Offset((Size.X - GamepadViewBox.X * Scale) * 0.5f, (Size.Y - GamepadViewBox.Y * Scale) * 0.5f);
	FPaintTarget Target(OutDrawElements, AllottedGeometry, InWidgetStyle, LayerId);

	const FLinearColor PartFill = Palette::Panel2;
	const FLinearColor PartStroke = Hex(0x2e4468);
	const float StrokeWidth = 1.5f * Scale;

	const auto Place = [&](const FPath& Path) { return Path.Placed(Offset, Scale); };

	// Controller body
	FPath Body;
	Body.MoveTo(70.0f, 62.0f).LineTo(330.0f, 62.0f).QuadTo(372.0f, 66.0f, 378.0f, 150.0f).QuadTo(382.0f, 222.0f, 336.0f, 226.0f)
		.QuadTo(300.0f, 228.0f, 278.0f, 190.0f).LineTo(122.0f, 190.0f).QuadTo(100.0f, 228.0f, 64.0f, 226.0f)
		.QuadTo(18.0f, 222.0f, 22.0f, 150.0f).QuadTo(28.0f, 66.0f, 70.0f, 62.0f);
	const FPath PlacedBody = Place(Body);
	FillPolygon(Target, PlacedBody.GetPoints(), Palette::Panel);
	StrokePolyline(Target, PlacedBody.GetPoints(), PartStroke, StrokeWidth, true);

	const auto DrawPart = [&](const FPath& Path, const FVector2f& LabelCenter, const FString& Label, bool bLit)
	{
		const FPath Placed = Place(Path);
		FillPolygon(Target, Placed.GetPoints(), bLit ? Palette::Ice : PartFill);
		StrokePolyline(Target, Placed.GetPoints(), bLit ? FLinearColor::White : PartStroke, StrokeWidth, true);
		DrawCenteredText(Target, Label, MakeFont(EFont::Display, 11.0f * Scale / UnitSize, 0.06f),
			LabelCenter * Scale + Offset, bLit ? Hex(0x04101f) : Palette::Mute);
	};

	for (const FGamepadPart& Part : GetGamepadParts())
	{
		const bool bLit = Highlighted.Contains(Part.Id);
		if (Part.bRound)
		{
			const float Radius = Part.Size.X;
			if (Part.Id == TEXT("MENU"))
			{
				DrawPart(FPath::Ellipse(Part.Position.X, Part.Position.Y, Radius, Radius), Part.Position, FString(), bLit);
				// Three short bars for the menu button
				for (int32 Bar = -1; Bar <= 1; ++Bar)
				{
					const FVector2f BarCentre = Part.Position + FVector2f(0.0f, Bar * 3.0f);
					const FPath Line = Place(FPath::Rect(BarCentre.X - 4.0f, BarCentre.Y - 0.6f, 8.0f, 1.2f));
					FillPolygon(Target, Line.GetPoints(), bLit ? Hex(0x04101f) : Palette::Mute);
				}
			}
			else
			{
				DrawPart(FPath::Ellipse(Part.Position.X, Part.Position.Y, Radius, Radius), Part.Position, Part.Label, bLit);
			}
		}
		else
		{
			DrawPart(FPath::RoundedRect(Part.Position.X, Part.Position.Y, Part.Size.X, Part.Size.Y, 8.0f),
				Part.Position + Part.Size * 0.5f, Part.Label, bLit);
		}
	}

	// D-pad: a plus shape, drawn as one concave polygon
	FPath DPad;
	DPad.MoveTo(141.0f, 130.0f).LineTo(159.0f, 130.0f).LineTo(159.0f, 147.0f).LineTo(176.0f, 147.0f).LineTo(176.0f, 165.0f)
		.LineTo(159.0f, 165.0f).LineTo(159.0f, 182.0f).LineTo(141.0f, 182.0f).LineTo(141.0f, 165.0f).LineTo(124.0f, 165.0f)
		.LineTo(124.0f, 147.0f).LineTo(141.0f, 147.0f);
	DrawPart(DPad, FVector2f(150.0f, 160.0f), TEXT("D-pad"), Highlighted.Contains(TEXT("DPAD")));

	return Target.Layer;
}

// SOpenStanceGestureIcon

void SOpenStanceGestureIcon::Construct(const FArguments& InArgs)
{
	Gesture = InArgs._Gesture;
	Inverted = InArgs._Inverted;
}

FString SOpenStanceGestureIcon::GetCaption(EOpenStanceGesture Gesture)
{
	switch (Gesture)
	{
	case EOpenStanceGesture::Half:
	case EOpenStanceGesture::HalfContinued:
		return TEXT("½ turn");
	case EOpenStanceGesture::Full:
		return TEXT("full turn");
	default:
		return TEXT("¼ turn");
	}
}

FVector2D SOpenStanceGestureIcon::ComputeDesiredSize(float LayoutScaleMultiplier) const
{
	return FVector2D(U(3.0f), U(3.0f));
}

int32 SOpenStanceGestureIcon::OnPaint(const FPaintArgs& Args, const FGeometry& AllottedGeometry, const FSlateRect& MyCullingRect,
	FSlateWindowElementList& OutDrawElements, int32 LayerId, const FWidgetStyle& InWidgetStyle, bool bParentEnabled) const
{
	// The prototype draws this as a 36 unit SVG: a well, an arc from the start angle, an arrowhead and a start dot
	float StartAngle = 0.0f;
	float EndAngle = 90.0f;
	switch (Gesture)
	{
	case EOpenStanceGesture::QuarterReverse:
		EndAngle = -90.0f;
		break;
	case EOpenStanceGesture::Half:
		EndAngle = 180.0f;
		break;
	case EOpenStanceGesture::HalfContinued:
		StartAngle = 180.0f;
		EndAngle = 360.0f;
		break;
	case EOpenStanceGesture::Full:
		EndAngle = 359.9f;
		break;
	default:
		break;
	}

	const bool bInverted = Inverted.Get(false);
	const FLinearColor WellFill = bInverted ? Hex(0xe3edfb) : Hex(0x0b1424);
	const FLinearColor WellStroke = bInverted ? Hex(0x7c8aa8) : Hex(0x5b6f94);
	const FLinearColor ArrowColor = bInverted ? Palette::ChungDark : Palette::Ice;
	const FLinearColor DotColor = bInverted ? Hex(0x0b1220) : FLinearColor::White;

	const FVector2f Size = AllottedGeometry.GetLocalSize();
	const float Scale = FMath::Min(Size.X, Size.Y) / 36.0f;
	const FVector2f Offset((Size.X - 36.0f * Scale) * 0.5f, (Size.Y - 36.0f * Scale) * 0.5f);
	const FVector2f Centre(18.0f, 18.0f);
	const float Radius = 9.0f;
	const auto AtAngle = [&](float Degrees, float Distance)
	{
		const float Radians = FMath::DegreesToRadians(Degrees);
		return Centre + FVector2f(FMath::Cos(Radians), FMath::Sin(Radians)) * Distance;
	};
	const auto ToWidget = [&](const FVector2f& Point) { return Point * Scale + Offset; };

	FPaintTarget Target(OutDrawElements, AllottedGeometry, InWidgetStyle, LayerId);

	const FPath Well = FPath::Ellipse(18.0f, 18.0f, 16.0f, 16.0f, 40).Placed(Offset, Scale);
	FillPolygon(Target, Well.GetPoints(), WellFill);
	StrokePolyline(Target, Well.GetPoints(), WellStroke, 1.5f * Scale, true);

	TArray<FVector2f> Arc;
	const float Sweep = EndAngle - StartAngle;
	const int32 ArcSteps = FMath::Max(2, FMath::CeilToInt(FMath::Abs(Sweep) / 6.0f));
	for (int32 Step = 0; Step <= ArcSteps; ++Step)
	{
		Arc.Add(ToWidget(AtAngle(StartAngle + Sweep * Step / ArcSteps, Radius)));
	}
	StrokePolyline(Target, Arc, ArrowColor, 3.8f * Scale, false);

	// Arrowhead at the end of the arc, pointing along the direction of travel
	const float Direction = EndAngle >= StartAngle ? 1.0f : -1.0f;
	const float EndRadians = FMath::DegreesToRadians(EndAngle);
	const FVector2f Tangent(-Direction * FMath::Sin(EndRadians), Direction * FMath::Cos(EndRadians));
	const FVector2f Normal(FMath::Cos(EndRadians), FMath::Sin(EndRadians));
	const FVector2f EndPoint = AtAngle(EndAngle, Radius);
	const FVector2f Head[3] =
	{
		ToWidget(EndPoint + Tangent * 6.5f),
		ToWidget(EndPoint + Normal * 4.4f),
		ToWidget(EndPoint - Normal * 4.4f)
	};
	FillPolygon(Target, Head, ArrowColor);

	const FPath Dot = FPath::Ellipse(AtAngle(StartAngle, Radius).X, AtAngle(StartAngle, Radius).Y, 2.4f, 2.4f, 16).Placed(Offset, Scale);
	FillPolygon(Target, Dot.GetPoints(), DotColor);

	return Target.Layer;
}
