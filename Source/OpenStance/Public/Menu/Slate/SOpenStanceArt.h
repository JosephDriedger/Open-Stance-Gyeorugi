#pragma once

#include "CoreMinimal.h"
#include "Menu/OpenStanceMenuTheme.h"
#include "Menu/OpenStanceMenuTypes.h"
#include "Widgets/DeclarativeSyntaxSupport.h"
#include "Widgets/SLeafWidget.h"

/** Full-screen menu background: the prototype's blue night gradient, two soft glows and two faint diagonal bands. */
class OPENSTANCE_API SOpenStanceBackdrop : public SLeafWidget
{
public:
	SLATE_BEGIN_ARGS(SOpenStanceBackdrop)
	{
	}
	SLATE_END_ARGS()

	void Construct(const FArguments& InArgs);

	virtual int32 OnPaint(const FPaintArgs& Args, const FGeometry& AllottedGeometry, const FSlateRect& MyCullingRect,
		FSlateWindowElementList& OutDrawElements, int32 LayerId, const FWidgetStyle& InWidgetStyle, bool bParentEnabled) const override;
	virtual FVector2D ComputeDesiredSize(float LayoutScaleMultiplier) const override;
};

/** Stand-in arena for the match HUD in the menu prototype: a lit floor and a striped mat in perspective. */
class OPENSTANCE_API SOpenStanceArenaBackdrop : public SLeafWidget
{
public:
	SLATE_BEGIN_ARGS(SOpenStanceArenaBackdrop)
	{
	}
	SLATE_END_ARGS()

	void Construct(const FArguments& InArgs);

	virtual int32 OnPaint(const FPaintArgs& Args, const FGeometry& AllottedGeometry, const FSlateRect& MyCullingRect,
		FSlateWindowElementList& OutDrawElements, int32 LayerId, const FWidgetStyle& InWidgetStyle, bool bParentEnabled) const override;
	virtual FVector2D ComputeDesiredSize(float LayoutScaleMultiplier) const override;
};

/**
 * Flat-colour fighter silhouette, drawn from the prototype's SVG so screens look like the design before the 3D
 * fighters are placed on them. Body, trim, skin and hair colours are attributes, so the creator can recolour it live.
 */
class OPENSTANCE_API SOpenStanceFighterFigure : public SLeafWidget
{
public:
	SLATE_BEGIN_ARGS(SOpenStanceFighterFigure)
		: _BodyColor(OpenStanceMenu::Hex(0xe7e5de))
		, _TrimColor(OpenStanceMenu::Hex(0xbdb9ad))
		, _SkinColor(OpenStanceMenu::Hex(0xc99a76))
		, _HairColor(OpenStanceMenu::Hex(0x1b1410))
		, _GearOn(false)
		, _Kick(false)
		, _Sex(EOpenStanceSex::Male)
		, _Mirrored(false)
	{
	}
		/** Dobok colour: white without gear, Chung or Hong with it. */
		SLATE_ATTRIBUTE(FLinearColor, BodyColor)
		/** Protector, belt-side trim and gloves with gear on. */
		SLATE_ATTRIBUTE(FLinearColor, TrimColor)
		SLATE_ATTRIBUTE(FLinearColor, SkinColor)
		SLATE_ATTRIBUTE(FLinearColor, HairColor)
		SLATE_ATTRIBUTE(bool, GearOn)
		SLATE_ATTRIBUTE(bool, Kick)
		SLATE_ATTRIBUTE(EOpenStanceSex, Sex)
		/** Face left instead of right (the Hong fighter in the match view). */
		SLATE_ARGUMENT(bool, Mirrored)
	SLATE_END_ARGS()

	void Construct(const FArguments& InArgs);

	virtual int32 OnPaint(const FPaintArgs& Args, const FGeometry& AllottedGeometry, const FSlateRect& MyCullingRect,
		FSlateWindowElementList& OutDrawElements, int32 LayerId, const FWidgetStyle& InWidgetStyle, bool bParentEnabled) const override;
	virtual FVector2D ComputeDesiredSize(float LayoutScaleMultiplier) const override;

private:
	TAttribute<FLinearColor> BodyColor;
	TAttribute<FLinearColor> TrimColor;
	TAttribute<FLinearColor> SkinColor;
	TAttribute<FLinearColor> HairColor;
	TAttribute<bool> GearOn;
	TAttribute<bool> Kick;
	TAttribute<EOpenStanceSex> Sex;
	bool bMirrored = false;
};

/** Controller diagram for the controls page. Buttons light up for the row being pointed at. */
class OPENSTANCE_API SOpenStanceGamepadDiagram : public SLeafWidget
{
public:
	SLATE_BEGIN_ARGS(SOpenStanceGamepadDiagram)
	{
	}
	SLATE_END_ARGS()

	void Construct(const FArguments& InArgs);

	/** Lights the named parts: LT, RT, LB, RB, LS, RS, MENU, DPAD, A, B, X, Y. */
	void SetHighlighted(const TArray<FName>& Keys);

	virtual int32 OnPaint(const FPaintArgs& Args, const FGeometry& AllottedGeometry, const FSlateRect& MyCullingRect,
		FSlateWindowElementList& OutDrawElements, int32 LayerId, const FWidgetStyle& InWidgetStyle, bool bParentEnabled) const override;
	virtual FVector2D ComputeDesiredSize(float LayoutScaleMultiplier) const override;

private:
	TSet<FName> Highlighted;
};

/** Skill Stick motions the controls page writes as icons instead of words. */
enum class EOpenStanceGesture : uint8
{
	/** Quarter turn, clockwise from the right. */
	Quarter,
	/** Quarter turn the other way, for the axe kick's start. */
	QuarterReverse,
	Half,
	/** Half turn continuing from the bottom, for the tornado kick. */
	HalfContinued,
	Full
};

/** A circle with an arrow showing which way the stick turns. */
class OPENSTANCE_API SOpenStanceGestureIcon : public SLeafWidget
{
public:
	SLATE_BEGIN_ARGS(SOpenStanceGestureIcon)
		: _Gesture(EOpenStanceGesture::Quarter)
		, _Inverted(false)
	{
	}
		SLATE_ARGUMENT(EOpenStanceGesture, Gesture)
		/** Dark-on-light colours, for a focused row. */
		SLATE_ATTRIBUTE(bool, Inverted)
	SLATE_END_ARGS()

	void Construct(const FArguments& InArgs);

	/** Caption shown beside the icon, e.g. "1/4 turn". */
	static FString GetCaption(EOpenStanceGesture Gesture);

	virtual int32 OnPaint(const FPaintArgs& Args, const FGeometry& AllottedGeometry, const FSlateRect& MyCullingRect,
		FSlateWindowElementList& OutDrawElements, int32 LayerId, const FWidgetStyle& InWidgetStyle, bool bParentEnabled) const override;
	virtual FVector2D ComputeDesiredSize(float LayoutScaleMultiplier) const override;

private:
	EOpenStanceGesture Gesture = EOpenStanceGesture::Quarter;
	TAttribute<bool> Inverted;
};
