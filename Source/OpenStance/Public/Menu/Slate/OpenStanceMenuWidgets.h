#pragma once

#include "CoreMinimal.h"
#include "Menu/OpenStanceMenuTheme.h"
#include "Widgets/DeclarativeSyntaxSupport.h"

class STextBlock;

/** Button glyphs in the hint bar and the controls page. */
enum class EOpenStanceGlyphLook : uint8
{
	/** Face button A: green circle. */
	A,
	B,
	X,
	Y,
	/** Bone circle with dark text, for bumpers and the menu button in the hint bar. */
	Neutral,
	/** Small rounded square, for LB and RB beside tab strips. */
	Key
};

enum class EOpenStanceTagLook : uint8
{
	Standard,
	/** The amber Future tag. */
	Future,
	/** White on a dimmed backing, for use over artwork. */
	OnArtwork
};

/** One entry in a screen's hint bar, e.g. a green A and "Select". Key "MENU" draws the three-bar menu glyph. */
struct FOpenStanceHint
{
	FString Key;
	EOpenStanceGlyphLook Look = EOpenStanceGlyphLook::Neutral;
	FString Text;
};

/**
 * Builders for the small pieces every screen reuses, named after the prototype's CSS classes. They return plain
 * Slate widgets, so screens compose them with the usual SVerticalBox and SHorizontalBox slots.
 */
namespace OpenStanceMenuWidgets
{
	struct FTextSpec
	{
		OpenStanceMenu::EFont Font = OpenStanceMenu::EFont::Body;
		float SizeUnits = 1.2f;
		float LetterSpacing = 0.0f;
		bool bUpperCase = false;
	};

	OPENSTANCE_API TSharedRef<STextBlock> MakeText(const FString& Text, const FTextSpec& Spec, const TAttribute<FSlateColor>& Color);
	OPENSTANCE_API TSharedRef<STextBlock> MakeText(const FString& Text, const FTextSpec& Spec, const FLinearColor& Color);

	/** Same, with the text read from a function each frame, for scores, clocks and other live values. */
	OPENSTANCE_API TSharedRef<STextBlock> MakeLiveText(TFunction<FString()> GetText, const FTextSpec& Spec, const TAttribute<FSlateColor>& Color);

	/** Small spaced-out caps line above a title (.kick). */
	OPENSTANCE_API TSharedRef<SWidget> Kicker(const FString& Text);

	/** Screen title: large italic caps (h2.t). */
	OPENSTANCE_API TSharedRef<SWidget> Heading(const FString& Text, float SizeUnits = 4.2f);

	/** Wrapped body copy. */
	OPENSTANCE_API TSharedRef<SWidget> Paragraph(const FString& Text, float SizeUnits = 1.2f, const FLinearColor& Color = OpenStanceMenu::Palette::Bone);

	OPENSTANCE_API TSharedRef<SWidget> Tag(const FString& Text, EOpenStanceTagLook Look = EOpenStanceTagLook::Standard);

	/** A standard tag whose text is read each frame, e.g. the selected fighter's body type. */
	OPENSTANCE_API TSharedRef<SWidget> LiveTag(TFunction<FString()> GetText);

	/** Amber "Future" tag: features the design lists for after v1.0. */
	OPENSTANCE_API TSharedRef<SWidget> FutureTag();

	/** Kicker above a big title, stacked (.head). */
	OPENSTANCE_API TSharedRef<SWidget> Head(const FString& KickerText, const FString& Title, bool bFuture = false);

	/** Dark panel with a small heading and a body (.card). Pass an accent colour for a top rule. */
	OPENSTANCE_API TSharedRef<SWidget> Card(const FString& Title, const TSharedRef<SWidget>& Body, const FLinearColor& TopRule = FLinearColor::Transparent, bool bFutureTag = false);

	/** A card holding paragraphs of text. */
	OPENSTANCE_API TSharedRef<SWidget> TextCard(const FString& Title, const TArray<FString>& Paragraphs);

	/** Thin progress bar (.bar); the fill colour may change while it is showing, e.g. amber at low stamina. */
	OPENSTANCE_API TSharedRef<SWidget> Bar(const TAttribute<float>& Fraction, const TAttribute<FLinearColor>& FillColor, float HeightUnits = 0.6f);

	/** Label, bar and value on one line (.stat). */
	OPENSTANCE_API TSharedRef<SWidget> StatRow(const FString& Label, const TSharedRef<SWidget>& Middle, const FString& Value);

	/** Controller button glyph. */
	OPENSTANCE_API TSharedRef<SWidget> Glyph(const FString& Label, EOpenStanceGlyphLook Look, float SizeUnits = 2.1f);

	/** The row of glyphs and captions along the bottom of a screen (.hints). */
	OPENSTANCE_API TSharedRef<SWidget> HintBar(const TArray<FOpenStanceHint>& Hints);

	/** Fixed-size empty space, in prototype units. */
	OPENSTANCE_API TSharedRef<SWidget> Gap(float WidthUnits, float HeightUnits);

	/**
	 * Writes controller input as icons: button names (LS, RT, D-pad, A and so on) become chips, face buttons become
	 * coloured circles, and {q} {qf} {h} {hu} {f} become stick-turn icons; the rest stays text. Inverted draws it
	 * for a focused (light) row. With bAllowWrap off the pieces stay on one line, for use in a narrow slot.
	 */
	OPENSTANCE_API TSharedRef<SWidget> InputLine(const FString& Text, const TAttribute<bool>& Inverted, bool bAllowWrap = true);

	/** Name and rating of the Career fighter at the top right of the Career screens (.pbar). */
	OPENSTANCE_API TSharedRef<SWidget> PlayerBar(const FString& Name, const FString& Detail, const FString& Initials);

	/** The controller parts an input line uses (LS, RT, MENU, DPAD ...), for the controls page diagram. */
	OPENSTANCE_API TArray<FName> GetInputParts(const FString& Text);
}
