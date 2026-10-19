#include "Menu/Screens/OpenStanceMatchScreen.h"

#include "InputCoreTypes.h"
#include "Menu/OpenStanceMatchModel.h"
#include "Menu/OpenStanceMenuContent.h"
#include "Menu/OpenStanceMenuSubsystem.h"
#include "Menu/OpenStanceMenuTheme.h"
#include "Menu/Slate/SOpenStanceArt.h"
#include "Menu/Slate/SOpenStanceFrame.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SConstraintCanvas.h"
#include "Widgets/SBoxPanel.h"

using namespace OpenStanceMenu;
using namespace OpenStanceMenuWidgets;

namespace
{
	/** The pop-up rises and fades over this long. */
	constexpr float PopSeconds = 1.0f;

	FString FormatClock(float SecondsRemaining)
	{
		const int32 Whole = FMath::CeilToInt(SecondsRemaining);
		return FString::Printf(TEXT("%d:%02d"), Whole / 60, Whole % 60);
	}
}

UOpenStanceMatchScreen::UOpenStanceMatchScreen(const FObjectInitializer& ObjectInitializer)
	: Super(ObjectInitializer)
{
	// The HUD takes the pause and demo keys itself, so it holds focus rather than a menu item
	SetIsFocusable(true);
	SetAnimateIn(false);
}

TArray<FOpenStanceHint> UOpenStanceMatchScreen::GetHints() const
{
	return
	{
		{ TEXT("A"), EOpenStanceGlyphLook::A, TEXT("Score a technique (demo)") },
		{ TEXT("MENU"), EOpenStanceGlyphLook::Neutral, TEXT("Pause") }
	};
}

FMargin UOpenStanceMatchScreen::GetContentPadding() const
{
	return FMargin(0.0f);
}

TSharedRef<SWidget> UOpenStanceMatchScreen::BuildBackground()
{
	return SNew(SOpenStanceArenaBackdrop);
}

EOpenStanceSex UOpenStanceMatchScreen::GetFighterSex(EOpenStanceSide Side) const
{
	const TArray<FOpenStanceFighterProfile>& Roster = OpenStanceMenuContent::GetRoster();
	const UOpenStanceMenuSubsystem* Menu = GetMenu();
	if (!Menu)
	{
		return EOpenStanceSex::Male;
	}
	const int32 Index = Side == EOpenStanceSide::Chung ? Menu->GetSession().ChungFighter : Menu->GetSession().HongFighter;
	return Roster.IsValidIndex(Index) ? Roster[Index].Sex : EOpenStanceSex::Male;
}

SConstraintCanvas::FSlot::FSlotArguments UOpenStanceMatchScreen::PlaceAt(float AnchorX, float OffsetX, float OffsetY, float AlignX, float AlignY, float AnchorY)
{
	SConstraintCanvas::FSlot::FSlotArguments Slot = SConstraintCanvas::Slot();
	Slot.Anchors(FAnchors(AnchorX, AnchorY))
		.Offset(FMargin(OffsetX, OffsetY, 0.0f, 0.0f))
		.Alignment(FVector2D(AlignX, AlignY))
		.AutoSize(true);
	return Slot;
}

TWeakObjectPtr<UOpenStanceMatchModel> UOpenStanceMatchScreen::GetModel() const
{
	UOpenStanceMenuSubsystem* Menu = GetMenu();
	return Menu ? Menu->GetMatchModel() : nullptr;
}

TSharedRef<SWidget> UOpenStanceMatchScreen::BuildFighter(EOpenStanceSide Side)
{
	TWeakObjectPtr<UOpenStanceMatchScreen> WeakThis(this);
	const bool bChung = Side == EOpenStanceSide::Chung;
	return SNew(SBox)
		.WidthOverride(U(20.0f))
		.HeightOverride(U(34.0f))
		[
			SNew(SOpenStanceFighterFigure)
			.BodyColor(bChung ? Palette::Chung : Palette::Hong)
			.TrimColor(bChung ? Palette::ChungDark : Palette::HongDark)
			.GearOn(true)
			.Kick(bChung)
			.Mirrored(!bChung)
			.Sex_Lambda([WeakThis, Side]()
			{
				const UOpenStanceMatchScreen* Screen = WeakThis.Get();
				return Screen ? Screen->GetFighterSex(Side) : EOpenStanceSex::Male;
			})
		];
}

TSharedRef<SWidget> UOpenStanceMatchScreen::BuildScoreboard(const TWeakObjectPtr<UOpenStanceMatchModel>& Model)
{
	const auto ScoreCell = [&Model](EOpenStanceSide Side, const FLinearColor& Colour)
	{
		return SNew(SOpenStanceFrame)
			.Fill(Colour)
			.Padding(FMargin(U(2.0f), U(0.6f)))
			[
				SNew(SBox)
				.HAlign(HAlign_Center)
				.VAlign(VAlign_Center)
				[
					MakeLiveText([Model, Side]() { return Model.IsValid() ? FString::FromInt(Model->GetScore(Side)) : FString(); },
						{ EFont::Display, 5.4f, 0.0f, false }, Palette::Bone)
				]
			];
	};

	return SNew(SBox)
		.WidthOverride(U(54.0f))
		[
			SNew(SOpenStanceFrame)
			.Fill(Palette::Shade)
			.OutlineColor(Palette::Line)
			.OutlineThickness(1.5f)
			[
				SNew(SHorizontalBox)
				+ SHorizontalBox::Slot().FillWidth(1.0f)
				[
					ScoreCell(EOpenStanceSide::Chung, Palette::Chung)
				]
				+ SHorizontalBox::Slot().AutoWidth()
				[
					SNew(SBox)
					.MinDesiredWidth(U(12.0f))
					.Padding(FMargin(U(2.4f), 0.0f))
					.VAlign(VAlign_Center)
					[
						SNew(SVerticalBox)
						+ SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Center)
						[
							MakeLiveText([Model]()
							{
								return Model.IsValid() ? FString::Printf(TEXT("Round %d / %d"), Model->GetRound(), UOpenStanceMatchModel::RoundCount) : FString();
							}, { EFont::BodyBold, 1.1f, 0.2f, true }, Palette::Mute)
						]
						+ SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Center)
						[
							MakeLiveText([Model]() { return Model.IsValid() ? FormatClock(Model->GetTimeRemaining()) : FString(); },
								{ EFont::Display, 3.4f, 0.0f, false }, Palette::Bone)
						]
					]
				]
				+ SHorizontalBox::Slot().FillWidth(1.0f)
				[
					ScoreCell(EOpenStanceSide::Hong, Palette::Hong)
				]
			]
		];
}

TSharedRef<SWidget> UOpenStanceMatchScreen::BuildReviewBox()
{
	return SNew(SBox)
		.WidthOverride(U(9.5f))
		[
			SNew(SOpenStanceFrame)
			.Fill(Hex(0x0f192c, 0.9f))
			.OutlineColor(Palette::Line)
			.OutlineThickness(1.5f)
			.Padding(FMargin(U(0.9f), U(0.7f)))
			[
				SNew(SVerticalBox)
				+ SVerticalBox::Slot().AutoHeight()
				[
					MakeText(TEXT("Video review"), { EFont::Display, 1.2f, 0.0f, true }, Palette::Bone)
				]
				+ SVerticalBox::Slot().AutoHeight().Padding(0.0f, U(0.4f), 0.0f, 0.0f)
				[
					MakeText(TEXT("1 left"), { EFont::BodyBold, 1.0f, 0.06f, true }, Palette::Mute)
				]
				+ SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Left).Padding(0.0f, U(0.4f), 0.0f, 0.0f)
				[
					FutureTag()
				]
			]
		];
}

TSharedRef<SWidget> UOpenStanceMatchScreen::BuildNameplate(const TWeakObjectPtr<UOpenStanceMatchModel>& Model, EOpenStanceSide Side)
{
	const bool bChung = Side == EOpenStanceSide::Chung;
	const EHorizontalAlignment Align = bChung ? HAlign_Left : HAlign_Right;

	return SNew(SBox)
		.WidthOverride(U(24.0f))
		[
			SNew(SVerticalBox)
			+ SVerticalBox::Slot().AutoHeight().HAlign(Align)
			[
				MakeLiveText([Model, Side]() { return Model.IsValid() ? Model->GetFighterName(Side) : FString(); },
					{ EFont::Display, 1.7f, 0.08f, true }, bChung ? Palette::Chung : Palette::Hong)
			]
			+ SVerticalBox::Slot().AutoHeight().Padding(0.0f, U(0.5f), 0.0f, 0.0f)
			[
				Bar(TAttribute<float>::CreateLambda([Model, Side]() { return Model.IsValid() ? Model->GetStamina(Side) : 0.0f; }),
					TAttribute<FLinearColor>::CreateLambda([Model, Side]()
					{
						return Model.IsValid() && Model->GetStamina(Side) < 0.25f ? Palette::Warn : Palette::Ok;
					}))
			]
			+ SVerticalBox::Slot().AutoHeight().HAlign(Align).Padding(0.0f, U(0.5f), 0.0f, 0.0f)
			[
				MakeText(TEXT("Stamina"), { EFont::Body, 1.0f }, Palette::Mute)
			]
		];
}

TSharedRef<SWidget> UOpenStanceMatchScreen::BuildScorePop(const TWeakObjectPtr<UOpenStanceMatchModel>& Model, EOpenStanceSide Side)
{
	const FLinearColor Colour = Side == EOpenStanceSide::Chung ? Palette::Chung : Palette::Hong;
	const auto Progress = [Model, Side]()
	{
		return Model.IsValid() ? Model->GetSecondsSinceScore(Side) / PopSeconds : 1.0f;
	};

	// Fades in over the first 15% then out, rising from 2u below to 4u above (the prototype's pop keyframes)
	return SNew(STextBlock)
		.Text_Lambda([Model, Side]()
		{
			return Model.IsValid() ? FText::FromString(FString::Printf(TEXT("+%d"), Model->GetLastScorePoints(Side))) : FText::GetEmpty();
		})
		.Font(MakeFont(EFont::Display, 5.0f))
		.ColorAndOpacity_Lambda([Colour, Progress]()
		{
			const float T = Progress();
			const float Opacity = T >= 1.0f ? 0.0f : (T < 0.15f ? T / 0.15f : 1.0f - (T - 0.15f) / 0.85f);
			return FSlateColor(FLinearColor(Colour.R, Colour.G, Colour.B, Opacity));
		})
		.RenderTransform_Lambda([Progress]()
		{
			return TOptional<FSlateRenderTransform>(FSlateRenderTransform(FVector2f(0.0f, FMath::Lerp(U(2.0f), -U(4.0f), FMath::Clamp(Progress(), 0.0f, 1.0f)))));
		});
}

TSharedRef<SWidget> UOpenStanceMatchScreen::BuildCallBanner(const TWeakObjectPtr<UOpenStanceMatchModel>& Model)
{
	const FTextSpec Spec{ EFont::Display, 1.6f, 0.1f, true };
	return SNew(SOpenStanceFrame)
		.Fill(Hex(0x05070b, 0.85f))
		.Padding(FMargin(U(2.0f), U(0.7f)))
		[
			SNew(SHorizontalBox)
			+ SHorizontalBox::Slot().AutoWidth()
			[
				MakeLiveText([Model]() { return Model.IsValid() ? Model->GetCallTerm() : FString(); }, Spec, Palette::Warn)
			]
			+ SHorizontalBox::Slot().AutoWidth()
			[
				MakeLiveText([Model]() { return Model.IsValid() ? Model->GetCallSeparator() : FString(); }, Spec, Palette::Bone)
			]
			+ SHorizontalBox::Slot().AutoWidth()
			[
				MakeLiveText([Model]() { return Model.IsValid() ? Model->GetCallMeaning() : FString(); }, Spec, Palette::Bone)
			]
		];
}

TSharedRef<SWidget> UOpenStanceMatchScreen::BuildContent()
{
	UOpenStanceMenuSubsystem* Menu = GetMenu();
	const TWeakObjectPtr<UOpenStanceMatchModel> Model = Menu ? Menu->GetMatchModel() : nullptr;
	return SNew(SConstraintCanvas)
		+ PlaceAt(0.5f, 0.0f, U(2.0f), 0.5f)[BuildScoreboard(Model)]
		+ PlaceAt(0.0f, U(12.5f), U(2.0f), 0.0f)[BuildReviewBox()]
		+ PlaceAt(1.0f, -U(12.5f), U(2.0f), 1.0f)[BuildReviewBox()]
		+ PlaceAt(0.0f, U(23.0f), U(11.6f), 0.0f)
		[
			MakeLiveText([Model]() { return Model.IsValid() ? FString::Printf(TEXT("Gam-jeom %d"), Model->GetGamJeom(EOpenStanceSide::Chung)) : FString(); },
				{ EFont::BodyBold, 1.05f, 0.1f, true }, Palette::Mute)
		]
		+ PlaceAt(0.0f, U(77.0f), U(11.6f), 1.0f)
		[
			MakeLiveText([Model]() { return Model.IsValid() ? FString::Printf(TEXT("Gam-jeom %d"), Model->GetGamJeom(EOpenStanceSide::Hong)) : FString(); },
				{ EFont::BodyBold, 1.05f, 0.1f, true }, Palette::Mute)
		]
		+ PlaceAt(0.0f, U(4.0f), U(14.0f), 0.0f)[BuildNameplate(Model, EOpenStanceSide::Chung)]
		+ PlaceAt(1.0f, -U(4.0f), U(14.0f), 1.0f)[BuildNameplate(Model, EOpenStanceSide::Hong)]
		+ PlaceAt(0.0f, U(26.0f), U(17.75f), 0.0f)[BuildFighter(EOpenStanceSide::Chung)]
		+ PlaceAt(0.0f, U(54.0f), U(17.75f), 0.0f)[BuildFighter(EOpenStanceSide::Hong)]
		+ PlaceAt(0.0f, U(30.0f), DesignHeight * 0.3f, 0.0f)[BuildScorePop(Model, EOpenStanceSide::Chung)]
		+ PlaceAt(1.0f, -U(30.0f), DesignHeight * 0.3f, 1.0f)[BuildScorePop(Model, EOpenStanceSide::Hong)]
		+ PlaceAt(0.5f, 0.0f, -U(7.5f), 0.5f, 1.0f, 1.0f)[BuildCallBanner(Model)];
}

void UOpenStanceMatchScreen::NativeTick(const FGeometry& MyGeometry, float InDeltaTime)
{
	Super::NativeTick(MyGeometry, InDeltaTime);

	UOpenStanceMenuSubsystem* Menu = GetMenu();
	if (!Menu || bLeaving)
	{
		return;
	}
	UOpenStanceMatchModel* Model = Menu->GetMatchModel();

	// Coming back from Controls or Options with the match on hold: put the pause menu up again
	if (!bCheckedPause)
	{
		bCheckedPause = true;
		if (Model->IsPaused() && !Model->IsFinished())
		{
			Menu->ShowPauseMenu();
		}
	}

	if (Model->bDemoMode)
	{
		Model->Advance(InDeltaTime);
	}
	if (Model->IsFinished())
	{
		bLeaving = true;
		Menu->ReplaceScreen(EOpenStanceMenuScreen::Results);
	}
}

FReply UOpenStanceMatchScreen::NativeOnKeyDown(const FGeometry& InGeometry, const FKeyEvent& InKeyEvent)
{
	const FKey Key = InKeyEvent.GetKey();
	UOpenStanceMenuSubsystem* Menu = GetMenu();
	if (Menu && Key == EKeys::Gamepad_Special_Right)
	{
		Menu->ShowPauseMenu();
		return FReply::Handled();
	}
	if (Menu && !Menu->IsDialogOpen() && (Key == EKeys::Enter || Key == EKeys::SpaceBar || Key == EKeys::Gamepad_FaceButton_Bottom))
	{
		ScoreRandomTechnique();
		return FReply::Handled();
	}
	return Super::NativeOnKeyDown(InGeometry, InKeyEvent);
}

void UOpenStanceMatchScreen::ScoreRandomTechnique()
{
	UOpenStanceMenuSubsystem* Menu = GetMenu();
	UOpenStanceMatchModel* Model = Menu ? Menu->GetMatchModel() : nullptr;
	if (!Model || !Model->bDemoMode || Model->IsPaused() || Model->IsFinished())
	{
		return;
	}

	static const TCHAR* const Techniques[] = { TEXT("Roundhouse"), TEXT("Back kick"), TEXT("Spinning hook"), TEXT("Axe kick"), TEXT("Side kick"), TEXT("Punch") };
	const EOpenStanceSide Side = FMath::FRand() < 0.5f ? EOpenStanceSide::Chung : EOpenStanceSide::Hong;
	const int32 Points = FMath::RandRange(1, 6);
	Model->AddPoints(Side, Points, Techniques[FMath::RandRange(0, UE_ARRAY_COUNT(Techniques) - 1)], Points >= 4);
	Model->SetStamina(Side, FMath::Max(0.12f, Model->GetStamina(Side) - 0.08f));
}
