#pragma once

#include "CoreMinimal.h"
#include "Fonts/SlateFontInfo.h"

struct FSlateBrush;

/**
 * Look of the menu system, ported from the HTML prototype (Docs/Prototype/menu_prototype.html).
 *
 * The prototype sizes everything in container-query width units, where 1u is 1% of a 16:9 stage. Screens here
 * are authored on a fixed 1920 x 1080 canvas and scaled to the viewport, so U(1.0f) is 19.2 canvas pixels and
 * the numbers in the prototype's CSS can be used as they are.
 */
namespace OpenStanceMenu
{
	constexpr float DesignWidth = 1920.0f;
	constexpr float DesignHeight = 1080.0f;
	constexpr float UnitSize = DesignWidth / 100.0f;

	/** Prototype width units to canvas pixels. */
	constexpr float U(float Units)
	{
		return Units * UnitSize;
	}

	/** An sRGB hex colour (0xRRGGBB) as the linear colour Slate expects. */
	OPENSTANCE_API FLinearColor Hex(uint32 Rgb, float Alpha = 1.0f);

	/** The prototype's colour variables, plus the few literals it uses for focused and inverted states. */
	namespace Palette
	{
		OPENSTANCE_API extern const FLinearColor Ink;
		OPENSTANCE_API extern const FLinearColor Panel;
		OPENSTANCE_API extern const FLinearColor Panel2;
		OPENSTANCE_API extern const FLinearColor Line;
		OPENSTANCE_API extern const FLinearColor Ice;
		OPENSTANCE_API extern const FLinearColor Bone;
		OPENSTANCE_API extern const FLinearColor Mute;
		OPENSTANCE_API extern const FLinearColor Chung;
		OPENSTANCE_API extern const FLinearColor ChungDark;
		OPENSTANCE_API extern const FLinearColor Hong;
		OPENSTANCE_API extern const FLinearColor HongDark;
		OPENSTANCE_API extern const FLinearColor Ok;
		OPENSTANCE_API extern const FLinearColor Warn;

		/** End of the white-to-pale-blue gradient a focused item gets. */
		OPENSTANCE_API extern const FLinearColor FocusEnd;
		/** Muted text on a focused (light) item. */
		OPENSTANCE_API extern const FLinearColor MuteOnFocus;
		/** Controller chip fill, and its fill on a focused row. */
		OPENSTANCE_API extern const FLinearColor Chip;
		OPENSTANCE_API extern const FLinearColor ChipOnFocus;
		/** Near-black behind the HUD hint bar and dialogs. */
		OPENSTANCE_API extern const FLinearColor Shade;
	}

	enum class EFont : uint8
	{
		/** Condensed bold italic: titles, buttons, tabs. */
		DisplayItalic,
		/** Condensed bold: scores, big numbers, dialog titles. */
		Display,
		Body,
		BodyMedium,
		BodyBold
	};

	/**
	 * A font from the engine's bundled Roboto family, sized in prototype width units. The condensed bold faces
	 * stand in for the prototype's Barlow Condensed; swap them in OpenStanceMenuTheme.cpp to change the look.
	 * LetterSpacingEm is in ems, so 0.07 matches the prototype's letter-spacing:.07em.
	 */
	OPENSTANCE_API FSlateFontInfo MakeFont(EFont Font, float SizeUnits, float LetterSpacingEm = 0.0f);

	namespace Brushes
	{
		/** Flat white tile; tint it with a colour. */
		OPENSTANCE_API const FSlateBrush* White();

		/** White pill, a circle on a square widget. */
		OPENSTANCE_API const FSlateBrush* Circle();

		/** White box with the small corner radius used by controller chips and badges. */
		OPENSTANCE_API const FSlateBrush* SmallRound();
	}
}
