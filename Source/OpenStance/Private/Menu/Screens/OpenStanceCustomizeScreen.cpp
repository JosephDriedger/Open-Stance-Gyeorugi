#include "Menu/Screens/OpenStanceCustomizeScreen.h"

#include "Menu/OpenStanceMenuContent.h"
#include "Menu/OpenStanceMenuSubsystem.h"
#include "Menu/OpenStanceMenuTheme.h"
#include "Menu/Slate/SOpenStanceArt.h"
#include "Menu/Slate/SOpenStanceFrame.h"
#include "Menu/Slate/SOpenStanceItems.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SWrapBox.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/SOverlay.h"

using namespace OpenStanceMenu;
using namespace OpenStanceMenuWidgets;

TArray<FOpenStanceHint> UOpenStanceCustomizeScreen::GetHints() const
{
	return SelectHints();
}

FOpenStanceFighterAppearance& UOpenStanceCustomizeScreen::GetAppearance() const
{
	static FOpenStanceFighterAppearance Fallback;
	UOpenStanceMenuSubsystem* Menu = GetMenu();
	return Menu ? Menu->GetSession().CareerAppearance : Fallback;
}

TSharedRef<SOpenStanceOption> UOpenStanceCustomizeScreen::BuildChoiceRow(const FString& Label, const TArray<FString>& Values, TFunction<int32()> Get, TFunction<void(int32)> Set)
{
	const auto Cycle = [Values, Get, Set](int32 Direction)
	{
		Set((Get() + Direction + Values.Num()) % Values.Num());
	};
	return SNew(SOpenStanceOption)
		.Label(Label)
		.Value_Lambda([Values, Get]() { return Values.IsValidIndex(Get()) ? Values[Get()] : FString(); })
		.OnPressed(FSimpleDelegate::CreateWeakLambda(this, [Cycle]() { Cycle(1); }))
		.OnStep(FOpenStanceStepDelegate::CreateWeakLambda(this, [Cycle](int32 Direction) { Cycle(Direction); }));
}

TSharedRef<SWidget> UOpenStanceCustomizeScreen::BuildSwatchGroup(const FString& Title, const TArray<FLinearColor>& Colours, TFunction<int32()> Get, TFunction<void(int32)> Set)
{
	TSharedRef<SWrapBox> Swatches = SNew(SWrapBox).UseAllottedSize(true).InnerSlotPadding(FVector2D(U(0.6f), U(0.6f)));
	for (int32 Index = 0; Index < Colours.Num(); ++Index)
	{
		Swatches->AddSlot()
		[
			SNew(SOpenStanceSwatch)
			.Color(Colours[Index])
			.Selected_Lambda([Get, Index]() { return Get() == Index; })
			.OnPressed(FSimpleDelegate::CreateWeakLambda(this, [Set, Index]() { Set(Index); }))
		];
	}

	return SNew(SVerticalBox)
		+ SVerticalBox::Slot().AutoHeight().Padding(0.0f, 0.0f, 0.0f, U(0.7f))
		[
			MakeText(Title, { EFont::Display, 1.6f, 0.08f, true }, Palette::Mute)
		]
		+ SVerticalBox::Slot().AutoHeight()
		[
			Swatches
		];
}

TSharedRef<SWidget> UOpenStanceCustomizeScreen::BuildContent()
{
	TWeakObjectPtr<UOpenStanceCustomizeScreen> WeakThis(this);
	const auto Appearance = [WeakThis]() -> FOpenStanceFighterAppearance&
	{
		static FOpenStanceFighterAppearance Fallback;
		const UOpenStanceCustomizeScreen* Screen = WeakThis.Get();
		return Screen ? Screen->GetAppearance() : Fallback;
	};

	// Preview: the same silhouette the menu uses, recoloured live from the chosen presets
	const TSharedRef<SWidget> Preview = SNew(SOpenStanceFighterFigure)
		.BodyColor_Lambda([Appearance]() { return Appearance().ProtectorSide == EOpenStanceSide::Hong ? Palette::Hong : Palette::Chung; })
		.TrimColor_Lambda([Appearance]() { return Appearance().ProtectorSide == EOpenStanceSide::Hong ? Palette::HongDark : Palette::ChungDark; })
		.SkinColor_Lambda([Appearance]()
		{
			const TArray<FLinearColor>& Presets = OpenStanceMenuContent::GetSkinPresets();
			return Presets[FMath::Clamp(Appearance().SkinIndex, 0, Presets.Num() - 1)];
		})
		.HairColor_Lambda([Appearance]()
		{
			const TArray<FLinearColor>& Presets = OpenStanceMenuContent::GetHairPresets();
			return Presets[FMath::Clamp(Appearance().HairIndex, 0, Presets.Num() - 1)];
		})
		.GearOn_Lambda([Appearance]() { return Appearance().bGearOn; })
		.Sex_Lambda([Appearance]() { return Appearance().Sex; });

	const auto MakeGearButton = [this, Appearance](const FString& Label, bool bGear)
	{
		return SNew(SOpenStanceOption)
			.Label(Label)
			.CenterLabel(true)
			.Current_Lambda([Appearance, bGear]() { return Appearance().bGearOn == bGear; })
			.OnPressed(FSimpleDelegate::CreateWeakLambda(this, [Appearance, bGear]() { Appearance().bGearOn = bGear; }));
	};

	TSharedRef<SOpenStanceOption> SexRow = BuildChoiceRow(TEXT("Sex"), { TEXT("Male"), TEXT("Female") },
		[Appearance]() { return static_cast<int32>(Appearance().Sex); },
		[Appearance](int32 Index) { Appearance().Sex = static_cast<EOpenStanceSex>(Index); });
	TSharedRef<SWidget> BodyRow = BuildChoiceRow(TEXT("Body type"), { TEXT("Compact"), TEXT("Lean tall"), TEXT("Stocky"), TEXT("Tall") },
		[Appearance]() { return static_cast<int32>(Appearance().BodyType); },
		[Appearance](int32 Index) { Appearance().BodyType = static_cast<EOpenStanceBodyType>(Index); });
	TSharedRef<SWidget> StyleRow = BuildChoiceRow(TEXT("Fighting style"), { TEXT("Counter"), TEXT("Kicker"), TEXT("Pressure") },
		[Appearance]() { return static_cast<int32>(Appearance().Style); },
		[Appearance](int32 Index) { Appearance().Style = static_cast<EOpenStanceFightingStyle>(Index); });
	SetDefaultFocus(SexRow);

	const TArray<FLinearColor> ProtectorColours = { Palette::Chung, Palette::Hong };
	const TSharedRef<SWidget> Palettes = SNew(SVerticalBox)
		+ SVerticalBox::Slot().AutoHeight()
		[
			SNew(SHorizontalBox)
			+ SHorizontalBox::Slot().FillWidth(1.0f).Padding(0.0f, 0.0f, U(1.5f), 0.0f)
			[
				BuildSwatchGroup(TEXT("Skin"), OpenStanceMenuContent::GetSkinPresets(),
					[Appearance]() { return Appearance().SkinIndex; }, [Appearance](int32 Index) { Appearance().SkinIndex = Index; })
			]
			+ SHorizontalBox::Slot().FillWidth(1.0f).Padding(U(1.5f), 0.0f, 0.0f, 0.0f)
			[
				BuildSwatchGroup(TEXT("Hair"), OpenStanceMenuContent::GetHairPresets(),
					[Appearance]() { return Appearance().HairIndex; }, [Appearance](int32 Index) { Appearance().HairIndex = Index; })
			]
		]
		+ SVerticalBox::Slot().AutoHeight().Padding(0.0f, U(1.0f), 0.0f, 0.0f)
		[
			SNew(SHorizontalBox)
			+ SHorizontalBox::Slot().FillWidth(1.0f).Padding(0.0f, 0.0f, U(1.5f), 0.0f)
			[
				BuildSwatchGroup(TEXT("Eyes"), OpenStanceMenuContent::GetEyePresets(),
					[Appearance]() { return Appearance().EyeIndex; }, [Appearance](int32 Index) { Appearance().EyeIndex = Index; })
			]
			+ SHorizontalBox::Slot().FillWidth(1.0f).Padding(U(1.5f), 0.0f, 0.0f, 0.0f)
			[
				BuildSwatchGroup(TEXT("Protector and helmet"), ProtectorColours,
					[Appearance]() { return static_cast<int32>(Appearance().ProtectorSide); },
					[Appearance](int32 Index) { Appearance().ProtectorSide = static_cast<EOpenStanceSide>(Index); })
			]
		];

	const UOpenStanceMenuSubsystem* Menu = GetMenu();
	const FString Name = Menu ? Menu->GetSession().CareerName : FString(TEXT("Jae-won Choi"));

	TSharedRef<SWidget> Body = SNew(SVerticalBox)
		+ SVerticalBox::Slot().AutoHeight()
		[
			Head(TEXT("Career · created fighter"), TEXT("Fighter creator"))
		]
		+ SVerticalBox::Slot().FillHeight(1.0f).Padding(0.0f, U(1.6f), 0.0f, 0.0f)
		[
			SNew(SHorizontalBox)
			+ SHorizontalBox::Slot().AutoWidth()
			[
				SNew(SBox).WidthOverride(U(26.0f))
				[
					SNew(SVerticalBox)
					+ SVerticalBox::Slot().FillHeight(1.0f)
					[
						SNew(SOpenStanceFrame)
						.Fill(Palette::Panel)
						.Padding(FMargin(U(1.0f)))
						[
							Preview
						]
					]
					+ SVerticalBox::Slot().AutoHeight().Padding(0.0f, U(0.8f), 0.0f, 0.0f)
					[
						SNew(SHorizontalBox)
						+ SHorizontalBox::Slot().FillWidth(1.0f)
						[
							MakeGearButton(TEXT("Gear on"), true)
						]
						+ SHorizontalBox::Slot().FillWidth(1.0f).Padding(U(0.4f), 0.0f, 0.0f, 0.0f)
						[
							MakeGearButton(TEXT("Gear off"), false)
						]
					]
				]
			]
			+ SHorizontalBox::Slot().FillWidth(1.0f).Padding(U(2.4f), 0.0f, 0.0f, 0.0f)
			[
				SNew(SVerticalBox)
				+ SVerticalBox::Slot().AutoHeight()
				[
					SexRow
				]
				+ SVerticalBox::Slot().AutoHeight().Padding(0.0f, U(0.8f), 0.0f, 0.0f)
				[
					BodyRow
				]
				+ SVerticalBox::Slot().AutoHeight().Padding(0.0f, U(0.8f), 0.0f, 0.0f)
				[
					StyleRow
				]
				+ SVerticalBox::Slot().AutoHeight().Padding(0.0f, U(0.8f), 0.0f, 0.0f)
				[
					SNew(SOpenStanceFrame)
					.Fill(Palette::Panel)
					.Padding(FMargin(U(1.4f)))
					[
						Palettes
					]
				]
				+ SVerticalBox::Slot().AutoHeight().Padding(0.0f, U(0.8f), 0.0f, 0.0f)
				[
					MakeText(TEXT("Appearance never changes attributes. Body type and style shift Career base ratings only."), { EFont::Body, 1.0f }, Palette::Mute)
				]
				+ SVerticalBox::Slot().AutoHeight().Padding(0.0f, U(0.8f), 0.0f, 0.0f)
				[
					SNew(SHorizontalBox)
					+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(0.0f, 0.0f, U(0.8f), 0.0f)
					[
						Kicker(TEXT("Later"))
					]
					+ SHorizontalBox::Slot().AutoWidth().Padding(0.0f, 0.0f, U(0.8f), 0.0f)
					[
						Tag(TEXT("Gear styles · Future"), EOpenStanceTagLook::Future)
					]
					+ SHorizontalBox::Slot().AutoWidth().Padding(0.0f, 0.0f, U(0.8f), 0.0f)
					[
						Tag(TEXT("Dojang · Future"), EOpenStanceTagLook::Future)
					]
					+ SHorizontalBox::Slot().AutoWidth()
					[
						Tag(TEXT("Ceremony · Future"), EOpenStanceTagLook::Future)
					]
				]
			]
		];

	return SNew(SOverlay)
		+ SOverlay::Slot()
		[
			Body
		]
		+ SOverlay::Slot().HAlign(HAlign_Right).VAlign(VAlign_Top)
		[
			PlayerBar(Name, TEXT("Your fighter · Green belt · OVR 74"), TEXT("JC"))
		];
}
