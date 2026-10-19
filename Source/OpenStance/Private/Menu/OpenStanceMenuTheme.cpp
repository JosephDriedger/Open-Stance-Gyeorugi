#include "Menu/OpenStanceMenuTheme.h"

#include "Brushes/SlateRoundedBoxBrush.h"
#include "Fonts/CompositeFont.h"
#include "Misc/Paths.h"
#include "Styling/CoreStyle.h"
#include "Styling/SlateBrush.h"

namespace OpenStanceMenu
{
	FLinearColor Hex(uint32 Rgb, float Alpha)
	{
		const FColor Colour(static_cast<uint8>((Rgb >> 16) & 0xFF), static_cast<uint8>((Rgb >> 8) & 0xFF), static_cast<uint8>(Rgb & 0xFF));
		FLinearColor Result = FLinearColor::FromSRGBColor(Colour);
		Result.A = Alpha;
		return Result;
	}

	namespace Palette
	{
		const FLinearColor Ink = Hex(0x050912);
		const FLinearColor Panel = Hex(0x0f192c);
		const FLinearColor Panel2 = Hex(0x17243d);
		const FLinearColor Line = Hex(0x243453);
		const FLinearColor Ice = Hex(0x53c7ff);
		const FLinearColor Bone = Hex(0xeceae3);
		const FLinearColor Mute = Hex(0x8c95a6);
		const FLinearColor Chung = Hex(0x2f6fe4);
		const FLinearColor ChungDark = Hex(0x1b3f8a);
		const FLinearColor Hong = Hex(0xe03a40);
		const FLinearColor HongDark = Hex(0x8c1f25);
		const FLinearColor Ok = Hex(0x47c27a);
		const FLinearColor Warn = Hex(0xe8a93a);
		const FLinearColor FocusEnd = Hex(0xcfe6ff);
		const FLinearColor MuteOnFocus = Hex(0x4a5365);
		const FLinearColor Chip = Hex(0x26354f);
		const FLinearColor ChipOnFocus = Hex(0x1a2c4d);
		const FLinearColor Shade = Hex(0x05070b);
	}

	namespace
	{
		const FName DisplayItalicFace(TEXT("DisplayItalic"));
		const FName DisplayFace(TEXT("Display"));
		const FName BodyFace(TEXT("Body"));
		const FName BodyMediumFace(TEXT("BodyMedium"));
		const FName BodyBoldFace(TEXT("BodyBold"));

		TSharedRef<const FCompositeFont> GetCompositeFont()
		{
			static const TSharedRef<const FCompositeFont> Font = []()
			{
				const FString FontDir = FPaths::EngineContentDir() / TEXT("Slate/Fonts/");
				TSharedRef<FCompositeFont> Composite = MakeShared<FCompositeFont>();
				const auto AddFace = [&Composite, &FontDir](const FName& Face, const TCHAR* FileName)
				{
					Composite->DefaultTypeface.AppendFont(Face, FontDir + FileName, EFontHinting::Default, EFontLoadingPolicy::LazyLoad);
				};
				AddFace(DisplayItalicFace, TEXT("Roboto-BoldCondensedItalic.ttf"));
				AddFace(DisplayFace, TEXT("Roboto-BoldCondensed.ttf"));
				AddFace(BodyFace, TEXT("Roboto-Regular.ttf"));
				AddFace(BodyMediumFace, TEXT("Roboto-Medium.ttf"));
				AddFace(BodyBoldFace, TEXT("Roboto-Bold.ttf"));

				// Roboto has no arrows (the controls page writes stick directions with them), so glyphs it lacks fall
				// back to the engine's broad-coverage face
				Composite->FallbackTypeface.Typeface.AppendFont(TEXT("Fallback"), FontDir + TEXT("DroidSansFallback.ttf"),
					EFontHinting::Default, EFontLoadingPolicy::LazyLoad);
				return Composite;
			}();
			return Font;
		}

		constexpr float DisplayWidthFactor = 0.90f;

		FName FaceName(EFont Font)
		{
			switch (Font)
			{
			case EFont::DisplayItalic:
				return DisplayItalicFace;
			case EFont::Display:
				return DisplayFace;
			case EFont::BodyMedium:
				return BodyMediumFace;
			case EFont::BodyBold:
				return BodyBoldFace;
			default:
				return BodyFace;
			}
		}
	}

	FSlateFontInfo MakeFont(EFont Font, float SizeUnits, float LetterSpacingEm)
	{
		// Roboto Condensed is wider than the prototype's Barlow Condensed, so the display faces are drawn a little smaller
		// to keep each title in the space the layout gives it
		const bool bDisplay = Font == EFont::Display || Font == EFont::DisplayItalic;
		const float Pixels = U(SizeUnits) * (bDisplay ? DisplayWidthFactor : 1.0f);

		// Slate font sizes are points, rendered at 96 DPI; convert so the size is the pixel size the CSS asks for
		FSlateFontInfo Info(GetCompositeFont(), Pixels * 72.0f / static_cast<float>(FontConstants::RenderDPI), FaceName(Font));
		Info.LetterSpacing = FMath::RoundToInt(LetterSpacingEm * 1000.0f);
		return Info;
	}

	namespace Brushes
	{
		const FSlateBrush* White()
		{
			return FCoreStyle::Get().GetBrush("GenericWhiteBox");
		}

		const FSlateBrush* Circle()
		{
			static const FSlateBrush Brush = []()
			{
				FSlateRoundedBoxBrush Rounded(FLinearColor::White, 0.0f);
				Rounded.OutlineSettings.RoundingType = ESlateBrushRoundingType::HalfHeightRadius;
				return static_cast<FSlateBrush>(Rounded);
			}();
			return &Brush;
		}

		const FSlateBrush* SmallRound()
		{
			static const FSlateRoundedBoxBrush Brush(FLinearColor::White, U(0.45f));
			return &Brush;
		}
	}
}
