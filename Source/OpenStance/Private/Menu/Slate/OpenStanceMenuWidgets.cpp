#include "Menu/Slate/OpenStanceMenuWidgets.h"

#include "Internationalization/Regex.h"
#include "Menu/Slate/SOpenStanceArt.h"
#include "Menu/Slate/SOpenStanceFrame.h"
#include "Styling/SlateTypes.h"
#include "Widgets/Images/SImage.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SWrapBox.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/SOverlay.h"
#include "Widgets/Text/STextBlock.h"

namespace OpenStanceMenuWidgets
{
	using namespace OpenStanceMenu;

	TSharedRef<STextBlock> MakeText(const FString& Text, const FTextSpec& Spec, const TAttribute<FSlateColor>& Color)
	{
		return SNew(STextBlock)
			.Text(FText::FromString(Text))
			.Font(MakeFont(Spec.Font, Spec.SizeUnits, Spec.LetterSpacing))
			.ColorAndOpacity(Color)
			.TransformPolicy(Spec.bUpperCase ? ETextTransformPolicy::ToUpper : ETextTransformPolicy::None);
	}

	TSharedRef<STextBlock> MakeText(const FString& Text, const FTextSpec& Spec, const FLinearColor& Color)
	{
		return MakeText(Text, Spec, TAttribute<FSlateColor>(FSlateColor(Color)));
	}

	TSharedRef<STextBlock> MakeLiveText(TFunction<FString()> GetText, const FTextSpec& Spec, const TAttribute<FSlateColor>& Color)
	{
		return SNew(STextBlock)
			.Text_Lambda([GetText = MoveTemp(GetText)]()
			{
				return FText::FromString(GetText());
			})
			.Font(MakeFont(Spec.Font, Spec.SizeUnits, Spec.LetterSpacing))
			.ColorAndOpacity(Color)
			.TransformPolicy(Spec.bUpperCase ? ETextTransformPolicy::ToUpper : ETextTransformPolicy::None);
	}

	TSharedRef<SWidget> Kicker(const FString& Text)
	{
		return MakeText(Text, { EFont::BodyBold, 1.05f, 0.2f, true }, Palette::Mute);
	}

	TSharedRef<SWidget> Heading(const FString& Text, float SizeUnits)
	{
		return MakeText(Text, { EFont::DisplayItalic, SizeUnits, 0.05f, true }, Palette::Bone);
	}

	TSharedRef<SWidget> Paragraph(const FString& Text, float SizeUnits, const FLinearColor& Color)
	{
		return SNew(STextBlock)
			.Text(FText::FromString(Text))
			.Font(MakeFont(EFont::Body, SizeUnits))
			.ColorAndOpacity(Color)
			.AutoWrapText(true)
			.LineHeightPercentage(1.45f);
	}

	TSharedRef<SWidget> Tag(const FString& Text, EOpenStanceTagLook Look)
	{
		FLinearColor TextColor = Palette::Mute;
		FLinearColor Outline = Palette::Mute;
		FLinearColor Fill = FLinearColor::Transparent;
		switch (Look)
		{
		case EOpenStanceTagLook::Future:
			TextColor = Palette::Warn;
			Outline = Palette::Warn;
			break;
		case EOpenStanceTagLook::OnArtwork:
			TextColor = FLinearColor::White;
			Outline = FLinearColor::White;
			Fill = FLinearColor(0.0f, 0.0f, 0.0f, 0.5f);
			break;
		default:
			break;
		}

		return SNew(SOpenStanceFrame)
			.Fill(Fill)
			.OutlineColor(Outline)
			.OutlineThickness(1.5f)
			.Padding(FMargin(U(0.6f), U(0.35f)))
			[
				MakeText(Text, { EFont::BodyBold, 0.85f, 0.14f, true }, TextColor)
			];
	}

	TSharedRef<SWidget> LiveTag(TFunction<FString()> GetText)
	{
		return SNew(SOpenStanceFrame)
			.OutlineColor(Palette::Mute)
			.OutlineThickness(1.5f)
			.Padding(FMargin(U(0.6f), U(0.35f)))
			[
				MakeLiveText(MoveTemp(GetText), { EFont::BodyBold, 0.85f, 0.14f, true }, Palette::Mute)
			];
	}

	TSharedRef<SWidget> FutureTag()
	{
		return Tag(TEXT("Future"), EOpenStanceTagLook::Future);
	}

	TSharedRef<SWidget> Head(const FString& KickerText, const FString& Title, bool bFuture)
	{
		TSharedRef<SHorizontalBox> TitleRow = SNew(SHorizontalBox)
			+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
			[
				Heading(Title)
			];
		if (bFuture)
		{
			TitleRow->AddSlot().AutoWidth().VAlign(VAlign_Center).Padding(U(0.8f), 0.0f, 0.0f, 0.0f)
			[
				FutureTag()
			];
		}

		return SNew(SVerticalBox)
			+ SVerticalBox::Slot().AutoHeight()
			[
				Kicker(KickerText)
			]
			+ SVerticalBox::Slot().AutoHeight().Padding(0.0f, U(0.7f), 0.0f, 0.0f)
			[
				TitleRow
			];
	}

	TSharedRef<SWidget> Card(const FString& Title, const TSharedRef<SWidget>& Body, const FLinearColor& TopRule, bool bFutureTag)
	{
		TSharedRef<SHorizontalBox> TitleRow = SNew(SHorizontalBox)
			+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
			[
				MakeText(Title, { EFont::Display, 1.6f, 0.08f, true }, Palette::Mute)
			];
		if (bFutureTag)
		{
			TitleRow->AddSlot().AutoWidth().VAlign(VAlign_Center).Padding(U(0.6f), 0.0f, 0.0f, 0.0f)
			[
				FutureTag()
			];
		}

		return SNew(SOpenStanceFrame)
			.Fill(Palette::Panel)
			.AccentColor(TopRule)
			.AccentEdge(TopRule.A > 0.0f ? EOpenStanceFrameEdge::Top : EOpenStanceFrameEdge::None)
			.AccentThickness(U(0.4f))
			.Padding(FMargin(U(1.4f)))
			[
				SNew(SVerticalBox)
				+ SVerticalBox::Slot().AutoHeight()
				[
					TitleRow
				]
				+ SVerticalBox::Slot().AutoHeight().Padding(0.0f, U(0.7f), 0.0f, 0.0f)
				[
					Body
				]
			];
	}

	TSharedRef<SWidget> TextCard(const FString& Title, const TArray<FString>& Paragraphs)
	{
		TSharedRef<SVerticalBox> Body = SNew(SVerticalBox);
		for (const FString& Text : Paragraphs)
		{
			Body->AddSlot().AutoHeight().Padding(0.0f, 0.0f, 0.0f, U(0.7f))
			[
				Paragraph(Text)
			];
		}
		return Card(Title, Body);
	}

	TSharedRef<SWidget> Bar(const TAttribute<float>& Fraction, const TAttribute<FLinearColor>& FillColor, float HeightUnits)
	{
		const TAttribute<float> Remainder = TAttribute<float>::CreateLambda([Fraction]()
		{
			return FMath::Max(1.0f - Fraction.Get(0.0f), UE_KINDA_SMALL_NUMBER);
		});

		return SNew(SBox)
			.HeightOverride(U(HeightUnits))
			[
				SNew(SOverlay)
				+ SOverlay::Slot()
				[
					SNew(SOpenStanceFrame).Fill(Palette::Line)
				]
				+ SOverlay::Slot()
				[
					SNew(SHorizontalBox)
					+ SHorizontalBox::Slot().FillWidth(Fraction)
					[
						SNew(SOpenStanceFrame).Fill(FillColor)
					]
					+ SHorizontalBox::Slot().FillWidth(Remainder)
					[
						SNullWidget::NullWidget
					]
				]
			];
	}

	TSharedRef<SWidget> StatRow(const FString& Label, const TSharedRef<SWidget>& Middle, const FString& Value)
	{
		return SNew(SHorizontalBox)
			+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
			[
				SNew(SBox).WidthOverride(U(9.0f))
				[
					MakeText(Label, { EFont::Body, 1.05f }, Palette::Mute)
				]
			]
			+ SHorizontalBox::Slot().FillWidth(1.0f).VAlign(VAlign_Center).Padding(U(0.8f), 0.0f)
			[
				Middle
			]
			+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
			[
				SNew(SBox).WidthOverride(U(2.4f)).HAlign(HAlign_Right)
				[
					MakeText(Value, { EFont::Body, 1.05f }, Palette::Bone)
				]
			];
	}

	TSharedRef<SWidget> Glyph(const FString& Label, EOpenStanceGlyphLook Look, float SizeUnits)
	{
		const float Scale = SizeUnits / 2.1f;
		const FTextSpec Spec{ EFont::Display, 1.2f * Scale, 0.0f, false };

		if (Look == EOpenStanceGlyphLook::Key)
		{
			return SNew(SBox)
				.WidthOverride(U(2.6f * Scale))
				.HeightOverride(U(2.1f * Scale))
				[
					SNew(SOverlay)
					+ SOverlay::Slot()
					[
						SNew(SImage).Image(Brushes::SmallRound()).ColorAndOpacity(Palette::Chip)
					]
					+ SOverlay::Slot().HAlign(HAlign_Center).VAlign(VAlign_Center)
					[
						MakeText(Label, { EFont::Display, 1.0f * Scale, 0.0f, false }, Palette::Bone)
					]
				];
		}

		FLinearColor Fill = Palette::Bone;
		FLinearColor TextColor = Palette::Ink;
		switch (Look)
		{
		case EOpenStanceGlyphLook::A:
			Fill = Palette::Ok;
			break;
		case EOpenStanceGlyphLook::B:
			Fill = Palette::Hong;
			TextColor = FLinearColor::White;
			break;
		case EOpenStanceGlyphLook::X:
			Fill = Palette::Chung;
			TextColor = FLinearColor::White;
			break;
		case EOpenStanceGlyphLook::Y:
			Fill = Palette::Warn;
			break;
		default:
			break;
		}

		TSharedRef<SWidget> Face = SNullWidget::NullWidget;
		if (Label == TEXT("MENU"))
		{
			// Three bars, drawn rather than typed so the glyph never depends on font coverage
			TSharedRef<SVerticalBox> Bars = SNew(SVerticalBox);
			for (int32 Bar = 0; Bar < 3; ++Bar)
			{
				Bars->AddSlot().AutoHeight().Padding(0.0f, U(0.11f * Scale))
				[
					SNew(SBox).WidthOverride(U(1.0f * Scale)).HeightOverride(U(0.17f * Scale))
					[
						SNew(SImage).Image(Brushes::White()).ColorAndOpacity(TextColor)
					]
				];
			}
			Face = Bars;
		}
		else
		{
			Face = MakeText(Label, Spec, TextColor);
		}

		return SNew(SBox)
			.WidthOverride(U(SizeUnits))
			.HeightOverride(U(SizeUnits))
			[
				SNew(SOverlay)
				+ SOverlay::Slot()
				[
					SNew(SImage).Image(Brushes::Circle()).ColorAndOpacity(Fill)
				]
				+ SOverlay::Slot().HAlign(HAlign_Center).VAlign(VAlign_Center)
				[
					Face
				]
			];
	}

	TSharedRef<SWidget> HintBar(const TArray<FOpenStanceHint>& Hints)
	{
		TSharedRef<SHorizontalBox> Row = SNew(SHorizontalBox);
		for (const FOpenStanceHint& Hint : Hints)
		{
			Row->AddSlot().AutoWidth().VAlign(VAlign_Center).Padding(0.0f, 0.0f, U(2.4f), 0.0f)
			[
				SNew(SHorizontalBox)
				+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
				[
					Glyph(Hint.Key, Hint.Look)
				]
				+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(U(0.6f), 0.0f, 0.0f, 0.0f)
				[
					MakeText(Hint.Text, { EFont::BodyMedium, 1.15f }, Palette::Mute)
				]
			];
		}
		return Row;
	}

	TSharedRef<SWidget> Gap(float WidthUnits, float HeightUnits)
	{
		return SNew(SBox).WidthOverride(U(WidthUnits)).HeightOverride(U(HeightUnits));
	}

	namespace
	{
		enum class EInputTokenKind : uint8
		{
			Text,
			Button,
			Gesture
		};

		struct FInputToken
		{
			EInputTokenKind Kind = EInputTokenKind::Text;
			FString Value;
			/** A gesture written as "{h}," carries its comma into the caption. */
			bool bComma = false;
		};

		TArray<FInputToken> TokenizeInput(const FString& Text)
		{
			// Button names, then stick gestures; the alternation order matters (RT before RS before LS ...)
			static const FRegexPattern Pattern(TEXT("(\\{(?:qf|hu|q|h|f)\\},?|Menu button|D-pad|RT|RB|LB|LT|RS|LS|\\b[ABXY]\\b)"));

			TArray<FInputToken> Tokens;
			const auto AddText = [&Tokens](const FString& Segment)
			{
				const FString Trimmed = Segment.TrimStartAndEnd();
				if (!Trimmed.IsEmpty())
				{
					Tokens.Add({ EInputTokenKind::Text, Trimmed, false });
				}
			};

			FRegexMatcher Matcher(Pattern, Text);
			int32 Cursor = 0;
			while (Matcher.FindNext())
			{
				AddText(Text.Mid(Cursor, Matcher.GetMatchBeginning() - Cursor));
				const FString Match = Matcher.GetCaptureGroup(1);
				if (Match.StartsWith(TEXT("{")))
				{
					Tokens.Add({ EInputTokenKind::Gesture, Match.Mid(1, Match.Find(TEXT("}")) - 1), Match.EndsWith(TEXT(",")) });
				}
				else
				{
					Tokens.Add({ EInputTokenKind::Button, Match, false });
				}
				Cursor = Matcher.GetMatchEnding();
			}
			AddText(Text.Mid(Cursor));
			return Tokens;
		}

		EOpenStanceGesture GestureFromCode(const FString& Code)
		{
			if (Code == TEXT("qf"))
			{
				return EOpenStanceGesture::QuarterReverse;
			}
			if (Code == TEXT("h"))
			{
				return EOpenStanceGesture::Half;
			}
			if (Code == TEXT("hu"))
			{
				return EOpenStanceGesture::HalfContinued;
			}
			if (Code == TEXT("f"))
			{
				return EOpenStanceGesture::Full;
			}
			return EOpenStanceGesture::Quarter;
		}

		TSharedRef<SWidget> MakeChip(const FString& Label, const TAttribute<bool>& Inverted)
		{
			const bool bFace = Label.Len() == 1 && FString(TEXT("ABXY")).Contains(Label);
			if (bFace)
			{
				// Face buttons are the same coloured circles as the hint bar
				return Glyph(Label, Label == TEXT("A") ? EOpenStanceGlyphLook::A : Label == TEXT("B") ? EOpenStanceGlyphLook::B
					: Label == TEXT("X") ? EOpenStanceGlyphLook::X : EOpenStanceGlyphLook::Y, 2.0f);
			}

			return SNew(SBox)
				.MinDesiredWidth(U(2.2f))
				.HeightOverride(U(2.0f))
				[
					SNew(SOverlay)
					+ SOverlay::Slot()
					[
						SNew(SImage)
						.Image(Brushes::SmallRound())
						.ColorAndOpacity_Lambda([Inverted]() { return Inverted.Get(false) ? FSlateColor(Palette::ChipOnFocus) : FSlateColor(Palette::Chip); })
					]
					+ SOverlay::Slot().HAlign(HAlign_Center).VAlign(VAlign_Center).Padding(U(0.55f), 0.0f)
					[
						MakeText(Label, { EFont::Display, 1.05f, 0.04f, false }, FLinearColor::White)
					]
				];
		}
	}

	TSharedRef<SWidget> PlayerBar(const FString& Name, const FString& Detail, const FString& Initials)
	{
		return SNew(SHorizontalBox)
			+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
			[
				SNew(SVerticalBox)
				+ SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Right)
				[
					MakeText(Name, { EFont::DisplayItalic, 1.5f, 0.06f, true }, Palette::Bone)
				]
				+ SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Right)
				[
					MakeText(Detail, { EFont::Body, 0.95f }, Palette::Mute)
				]
			]
			+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(U(1.0f), 0.0f, 0.0f, 0.0f)
			[
				SNew(SBox)
				.WidthOverride(U(3.4f))
				.HeightOverride(U(3.4f))
				[
					SNew(SOverlay)
					+ SOverlay::Slot()
					[
						SNew(SImage).Image(Brushes::Circle()).ColorAndOpacity(Palette::Chung)
					]
					+ SOverlay::Slot().HAlign(HAlign_Center).VAlign(VAlign_Center)
					[
						MakeText(Initials, { EFont::DisplayItalic, 1.5f }, Palette::Bone)
					]
				]
			];
	}

	TSharedRef<SWidget> InputLine(const FString& Text, const TAttribute<bool>& Inverted, bool bAllowWrap)
	{
		TArray<TSharedRef<SWidget>> Pieces;
		for (const FInputToken& Token : TokenizeInput(Text))
		{
			TSharedRef<SWidget> Piece = SNullWidget::NullWidget;
			switch (Token.Kind)
			{
			case EInputTokenKind::Button:
				Piece = MakeChip(Token.Value, Inverted);
				break;
			case EInputTokenKind::Gesture:
			{
				const TAttribute<FSlateColor> CaptionColor = TAttribute<FSlateColor>::CreateLambda([Inverted]()
				{
					return Inverted.Get(false) ? FSlateColor(Hex(0x3b465a)) : FSlateColor(Palette::Mute);
				});
				const EOpenStanceGesture Gesture = GestureFromCode(Token.Value);
				Piece = SNew(SHorizontalBox)
					+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
					[
						SNew(SOpenStanceGestureIcon).Gesture(Gesture).Inverted(Inverted)
					]
					+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
					[
						MakeText(SOpenStanceGestureIcon::GetCaption(Gesture) + (Token.bComma ? TEXT(",") : TEXT("")), { EFont::BodyBold, 0.95f, 0.04f, false }, CaptionColor)
					];
				break;
			}
			default:
				Piece = SNew(STextBlock)
					.Text(FText::FromString(Token.Value))
					.Font(MakeFont(EFont::Body, 1.1f))
					.ColorAndOpacity(FSlateColor::UseForeground());
				break;
			}
			Pieces.Add(Piece);
		}

		const float Gap = U(0.35f);
		if (!bAllowWrap)
		{
			TSharedRef<SHorizontalBox> Row = SNew(SHorizontalBox);
			for (int32 Index = 0; Index < Pieces.Num(); ++Index)
			{
				Row->AddSlot().AutoWidth().VAlign(VAlign_Center).Padding(Index == 0 ? 0.0f : Gap, 0.0f, 0.0f, 0.0f)[Pieces[Index]];
			}
			return Row;
		}

		TSharedRef<SWrapBox> Line = SNew(SWrapBox).UseAllottedSize(true).InnerSlotPadding(FVector2D(Gap, U(0.2f)));
		for (const TSharedRef<SWidget>& Piece : Pieces)
		{
			Line->AddSlot().VAlign(VAlign_Center)[Piece];
		}
		return Line;
	}

	TArray<FName> GetInputParts(const FString& Text)
	{
		TArray<FName> Parts;
		for (const FInputToken& Token : TokenizeInput(Text))
		{
			if (Token.Kind != EInputTokenKind::Button)
			{
				continue;
			}
			const FName Part = Token.Value == TEXT("Menu button") ? FName(TEXT("MENU")) : Token.Value == TEXT("D-pad") ? FName(TEXT("DPAD")) : FName(*Token.Value);
			Parts.AddUnique(Part);
		}
		return Parts;
	}
}
