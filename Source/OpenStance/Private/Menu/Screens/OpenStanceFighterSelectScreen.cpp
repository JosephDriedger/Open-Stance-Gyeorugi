#include "Menu/Screens/OpenStanceFighterSelectScreen.h"

#include "Menu/OpenStanceMenuContent.h"
#include "Menu/OpenStanceMenuSubsystem.h"
#include "Menu/OpenStanceMenuTheme.h"
#include "Menu/Slate/SOpenStanceArt.h"
#include "Menu/Slate/SOpenStanceFighterRender.h"
#include "Menu/Slate/SOpenStanceFrame.h"
#include "Menu/Slate/SOpenStanceItems.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SUniformGridPanel.h"
#include "Widgets/Layout/SWidgetSwitcher.h"
#include "Widgets/SBoxPanel.h"

using namespace OpenStanceMenu;
using namespace OpenStanceMenuWidgets;

TArray<FOpenStanceHint> UOpenStanceFighterSelectScreen::GetHints() const
{
	TArray<FOpenStanceHint> Hints = TabHints(TEXT("Men"), TEXT("Women"));
	Hints.Add({ TEXT("X"), EOpenStanceGlyphLook::X, TEXT("Random") });
	Hints.Add({ TEXT("Y"), EOpenStanceGlyphLook::Y, TEXT("You / Opponent") });
	return Hints;
}

EOpenStanceSide UOpenStanceFighterSelectScreen::GetPickSide() const
{
	const UOpenStanceMenuSubsystem* Menu = GetMenu();
	const EOpenStanceSide Yours = Menu ? Menu->GetSession().PlayerSide : EOpenStanceSide::Chung;
	const EOpenStanceSide Theirs = Yours == EOpenStanceSide::Chung ? EOpenStanceSide::Hong : EOpenStanceSide::Chung;
	return bChoosingOpponent ? Theirs : Yours;
}

FReply UOpenStanceFighterSelectScreen::NativeOnKeyDown(const FGeometry& InGeometry, const FKeyEvent& InKeyEvent)
{
	const FKey Key = InKeyEvent.GetKey();
	if (Key == EKeys::Gamepad_FaceButton_Top || Key == EKeys::Tab || Key == EKeys::Y)
	{
		bChoosingOpponent = !bChoosingOpponent;
		return FReply::Handled();
	}
	if (Key == EKeys::Gamepad_FaceButton_Left || Key == EKeys::R)
	{
		PickRandom();
		return FReply::Handled();
	}
	return Super::NativeOnKeyDown(InGeometry, InKeyEvent);
}

const FOpenStanceFighterProfile& UOpenStanceFighterSelectScreen::GetFighter(EOpenStanceSide Side) const
{
	static const FOpenStanceFighterProfile Fallback;
	const TArray<FOpenStanceFighterProfile>& Roster = OpenStanceMenuContent::GetRoster();
	const UOpenStanceMenuSubsystem* Menu = GetMenu();
	if (!Menu)
	{
		return Fallback;
	}

	const FOpenStanceMenuSession& Session = Menu->GetSession();
	const int32 Index = Side == EOpenStanceSide::Chung ? Session.ChungFighter : Session.HongFighter;
	return Roster.IsValidIndex(Index) ? Roster[Index] : Fallback;
}

TSharedRef<SWidget> UOpenStanceFighterSelectScreen::BuildSidePanel(EOpenStanceSide Side)
{
	const bool bChung = Side == EOpenStanceSide::Chung;
	const FLinearColor Colour = bChung ? Palette::Chung : Palette::Hong;
	const FLinearColor Dark = bChung ? Palette::ChungDark : Palette::HongDark;
	TWeakObjectPtr<UOpenStanceFighterSelectScreen> WeakThis(this);
	const auto Fighter = [WeakThis, Side]() -> const FOpenStanceFighterProfile&
	{
		static const FOpenStanceFighterProfile Fallback;
		const UOpenStanceFighterSelectScreen* Screen = WeakThis.Get();
		return Screen ? Screen->GetFighter(Side) : Fallback;
	};

	return SNew(SBox)
		.WidthOverride(U(25.0f))
		[
			SNew(SVerticalBox)
			+ SVerticalBox::Slot().AutoHeight()
			[
				SNew(SHorizontalBox)
				+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
				[
					MakeText(bChung ? TEXT("Chung") : TEXT("Hong"), { EFont::Display, 2.4f, 0.1f, false }, Colour)
				]
				+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(U(0.8f), 0.0f, 0.0f, 0.0f)
				[
					LiveTag([WeakThis, Side]()
					{
						// The side you chose on Side Select is yours; the other is the AI's or player 2's.
						const UOpenStanceFighterSelectScreen* Screen = WeakThis.Get();
						const UOpenStanceMenuSubsystem* MenuSubsystem = Screen ? Screen->GetMenu() : nullptr;
						return MenuSubsystem && MenuSubsystem->GetSession().PlayerSide == Side ? FString(TEXT("You")) : FString(TEXT("Opponent"));
					})
				]
			]
			// The portrait takes what is left, up to the prototype's 30u, so the name and tags always fit above the hint bar
			+ SVerticalBox::Slot().FillHeight(1.0f).MaxHeight(U(30.0f)).Padding(0.0f, U(0.8f), 0.0f, 0.0f)
			[
				SNew(SBox)
				[
					SNew(SOpenStanceFrame)
					.Fill(Palette::Panel)
					.Padding(FMargin(U(1.0f)))
					[
						// The fighter's body build in the sparring stance, without gear; the silhouette if it cannot render
						SNew(SOpenStanceFighterRender)
						.BodyType_Lambda([Fighter]() { return Fighter().BodyType; })
						.Sex_Lambda([Fighter]() { return Fighter().Sex; })
						.PortraitKey_Lambda([Fighter]() { return OpenStanceMenuContent::GetPortraitKey(Fighter()); })
						.FaceLeft(!bChung)
						.World(GetWorld())
						.Fallback()
						[
							SNew(SOpenStanceFighterFigure)
							.BodyColor(Colour)
							.TrimColor(Dark)
							.GearOn(true)
							.Kick(bChung)
							.Sex_Lambda([Fighter]() { return Fighter().Sex; })
						]
					]
				]
			]
			+ SVerticalBox::Slot().AutoHeight().Padding(0.0f, U(0.8f), 0.0f, 0.0f)
			[
				SNew(SHorizontalBox)
				+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(0.0f, 0.0f, U(0.8f), 0.0f)
				[
					LiveFlag([Fighter]() { return Fighter().CountryCode; }, 2.0f)
				]
				+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
				[
					MakeLiveText([Fighter]() { return Fighter().Name; }, { EFont::Display, 2.6f, 0.03f, false }, Palette::Bone)
				]
			]
			+ SVerticalBox::Slot().AutoHeight().Padding(0.0f, U(0.8f), 0.0f, 0.0f)
			[
				SNew(SHorizontalBox)
				+ SHorizontalBox::Slot().AutoWidth().Padding(0.0f, 0.0f, U(0.8f), 0.0f)
				[
					LiveTag([Fighter]() { return Fighter().CountryName; })
				]
				+ SHorizontalBox::Slot().AutoWidth().Padding(0.0f, 0.0f, U(0.8f), 0.0f)
				[
					LiveTag([Fighter]() { return OpenStanceMenuContent::GetBodyTypeName(Fighter().BodyType); })
				]
				+ SHorizontalBox::Slot().AutoWidth().Padding(0.0f, 0.0f, U(0.8f), 0.0f)
				[
					LiveTag([Fighter]() { return OpenStanceMenuContent::GetStyleName(Fighter().Style); })
				]
				+ SHorizontalBox::Slot().AutoWidth()
				[
					LiveTag([Fighter]() { return FString::Printf(TEXT("OVR %d"), Fighter().Overall); })
				]
			]
		];
}

TSharedRef<SWidget> UOpenStanceFighterSelectScreen::BuildRosterList(EOpenStanceSex Sex)
{
	const TArray<FOpenStanceFighterProfile>& Roster = OpenStanceMenuContent::GetRoster();
	TWeakObjectPtr<UOpenStanceFighterSelectScreen> WeakThis(this);

	// Two columns of compact tiles, filled row by row: twelve fighters a side fit where one column of four did
	TSharedRef<SUniformGridPanel> List = SNew(SUniformGridPanel).SlotPadding(FMargin(U(0.4f)));
	bool bFirst = true;
	int32 Cell = 0;
	for (const int32 RosterIndex : OpenStanceMenuContent::GetRosterIndices(Sex))
	{
		const FOpenStanceFighterProfile& Profile = Roster[RosterIndex];
		TSharedRef<SOpenStanceFighterTile> Tile = SNew(SOpenStanceFighterTile)
			.Name(Profile.Name)
			.CountryCode(Profile.CountryCode)
			.Compact(true)
			.Detail(FString::Printf(TEXT("%s · %s · %s · %d"), *Profile.CountryCode, *OpenStanceMenuContent::GetBodyTypeName(Profile.BodyType),
				*OpenStanceMenuContent::GetStyleName(Profile.Style), Profile.Overall))
			.Selected_Lambda([WeakThis, RosterIndex]()
			{
				const UOpenStanceFighterSelectScreen* Screen = WeakThis.Get();
				const UOpenStanceMenuSubsystem* Menu = Screen ? Screen->GetMenu() : nullptr;
				// Both picks are marked, each in its side's colour
				return Menu && (Menu->GetSession().ChungFighter == RosterIndex || Menu->GetSession().HongFighter == RosterIndex);
			})
			.Hong_Lambda([WeakThis, RosterIndex]()
			{
				const UOpenStanceFighterSelectScreen* Screen = WeakThis.Get();
				const UOpenStanceMenuSubsystem* Menu = Screen ? Screen->GetMenu() : nullptr;
				return Menu && Menu->GetSession().HongFighter == RosterIndex;
			})
			.OnPressed(FSimpleDelegate::CreateWeakLambda(this, [this, RosterIndex]() { PickFighter(RosterIndex); }));

		if (bFirst && GetMenu() && GetMenu()->GetSession().Category == Sex)
		{
			SetDefaultFocus(Tile);
		}
		List->AddSlot(Cell % 2, Cell / 2)
		[
			Tile
		];
		++Cell;
		bFirst = false;
	}
	return List;
}

TSharedRef<SWidget> UOpenStanceFighterSelectScreen::BuildContent()
{
	const UOpenStanceMenuSubsystem* Menu = GetMenu();
	TWeakObjectPtr<UOpenStanceFighterSelectScreen> WeakThis(this);
	const auto GetCategory = [WeakThis]()
	{
		const UOpenStanceFighterSelectScreen* Screen = WeakThis.Get();
		const UOpenStanceMenuSubsystem* MenuSubsystem = Screen ? Screen->GetMenu() : nullptr;
		return MenuSubsystem ? MenuSubsystem->GetSession().Category : EOpenStanceSex::Male;
	};

	const auto MakeCategoryTab = [this, GetCategory](const FString& Label, EOpenStanceSex Sex)
	{
		return SNew(SOpenStanceOption)
			.Label(Label)
			.Padding(FMargin(U(2.0f), U(0.7f)))
			.Current_Lambda([GetCategory, Sex]() { return GetCategory() == Sex; })
			.OnPressed(FSimpleDelegate::CreateWeakLambda(this, [this, Sex]() { SetCategory(Sex); }));
	};

	const auto MakePickTab = [this, WeakThis](const FString& Label, bool bOpponent)
	{
		return SNew(SOpenStanceOption)
			.Label(Label)
			.FontSize(1.3f)
			.Padding(FMargin(U(1.1f), U(0.35f)))
			.Current_Lambda([WeakThis, bOpponent]()
			{
				const UOpenStanceFighterSelectScreen* Screen = WeakThis.Get();
				return Screen && Screen->bChoosingOpponent == bOpponent;
			})
			.OnPressed(FSimpleDelegate::CreateWeakLambda(this, [this, bOpponent]() { bChoosingOpponent = bOpponent; }));
	};

	const FString ModeName = Menu && Menu->GetSession().Mode == EOpenStanceMatchMode::Tournament ? TEXT("Tournament") : TEXT("Sparring");

	TSharedRef<SWidgetSwitcher> Rosters = SNew(SWidgetSwitcher)
		.WidgetIndex_Lambda([GetCategory]() { return GetCategory() == EOpenStanceSex::Female ? 1 : 0; });
	Rosters->AddSlot()[BuildRosterList(EOpenStanceSex::Male)];
	Rosters->AddSlot()[BuildRosterList(EOpenStanceSex::Female)];

	const TSharedRef<SWidget> Centre = SNew(SVerticalBox)
		+ SVerticalBox::Slot().AutoHeight()
		[
			SNew(SHorizontalBox)
			+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(0.0f, 0.0f, U(0.4f), 0.0f)
			[
				Glyph(TEXT("LB"), EOpenStanceGlyphLook::Key)
			]
			+ SHorizontalBox::Slot().AutoWidth().Padding(0.0f, 0.0f, U(0.4f), 0.0f)
			[
				MakeCategoryTab(TEXT("Men"), EOpenStanceSex::Male)
			]
			+ SHorizontalBox::Slot().AutoWidth().Padding(0.0f, 0.0f, U(0.4f), 0.0f)
			[
				MakeCategoryTab(TEXT("Women"), EOpenStanceSex::Female)
			]
			+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
			[
				Glyph(TEXT("RB"), EOpenStanceGlyphLook::Key)
			]
		]
		+ SVerticalBox::Slot().AutoHeight().Padding(0.0f, U(0.8f), 0.0f, U(0.8f))
		[
			// Which fighter a pick sets: yours or your opponent's (Y switches)
			SNew(SHorizontalBox)
			+ SHorizontalBox::Slot().AutoWidth().Padding(0.0f, 0.0f, U(0.4f), 0.0f)
			[
				MakePickTab(TEXT("Your Fighter"), false)
			]
			+ SHorizontalBox::Slot().AutoWidth().Padding(0.0f, 0.0f, U(1.2f), 0.0f)
			[
				MakePickTab(TEXT("Opponent"), true)
			]
			+ SHorizontalBox::Slot().AutoWidth()
			[
				SNew(SOpenStanceOption)
				.Label(TEXT("Random"))
				.FontSize(1.3f)
				.Padding(FMargin(U(1.1f), U(0.35f)))
				.OnPressed(FSimpleDelegate::CreateWeakLambda(this, [this]() { PickRandom(); }))
			]
		]
		+ SVerticalBox::Slot().AutoHeight()
		[
			Rosters
		]
		+ SVerticalBox::Slot().AutoHeight().Padding(0.0f, U(1.0f), 0.0f, 0.0f)
		[
			SNew(SOpenStanceOption)
			.Label(TEXT("Start Match"))
			.Look(EOpenStanceOptionLook::Primary)
			.OnPressed(FSimpleDelegate::CreateWeakLambda(this, [this]()
			{
				if (UOpenStanceMenuSubsystem* MenuSubsystem = GetMenu())
				{
					MenuSubsystem->StartMatch();
				}
			}))
		];

	return SNew(SVerticalBox)
		+ SVerticalBox::Slot().AutoHeight()
		[
			Head(ModeName, TEXT("Fighter Select"))
		]
		+ SVerticalBox::Slot().FillHeight(1.0f).Padding(0.0f, U(1.6f), 0.0f, 0.0f)
		[
			SNew(SHorizontalBox)
			+ SHorizontalBox::Slot().AutoWidth()
			[
				BuildSidePanel(EOpenStanceSide::Chung)
			]
			+ SHorizontalBox::Slot().FillWidth(1.0f).Padding(U(2.4f), 0.0f)
			[
				SNew(SBox).VAlign(VAlign_Center)
				[
					Centre
				]
			]
			+ SHorizontalBox::Slot().AutoWidth()
			[
				BuildSidePanel(EOpenStanceSide::Hong)
			]
		];
}

void UOpenStanceFighterSelectScreen::HandleTabStep(int32 Direction)
{
	SetCategory(Direction < 0 ? EOpenStanceSex::Male : EOpenStanceSex::Female);
}

void UOpenStanceFighterSelectScreen::SetCategory(EOpenStanceSex Sex)
{
	UOpenStanceMenuSubsystem* Menu = GetMenu();
	if (!Menu)
	{
		return;
	}

	// Choosing a roster picks its first two fighters so Chung and Hong always come from the same list
	FOpenStanceMenuSession& Session = Menu->GetSession();
	const TArray<int32> Indices = OpenStanceMenuContent::GetRosterIndices(Sex);
	Session.Category = Sex;
	if (Indices.Num() >= 2)
	{
		Session.ChungFighter = Indices[0];
		Session.HongFighter = Indices[1];
	}
}

void UOpenStanceFighterSelectScreen::PickRandom()
{
	UOpenStanceMenuSubsystem* Menu = GetMenu();
	if (!Menu)
	{
		return;
	}
	FOpenStanceMenuSession& Session = Menu->GetSession();
	TArray<int32> Indices = OpenStanceMenuContent::GetRosterIndices(Session.Category);
	if (Indices.Num() < 2)
	{
		return;
	}
	// Two different fighters: the first draw, then one from the rest
	const int32 First = FMath::RandRange(0, Indices.Num() - 1);
	Session.ChungFighter = Indices[First];
	Indices.RemoveAt(First);
	Session.HongFighter = Indices[FMath::RandRange(0, Indices.Num() - 1)];
}

void UOpenStanceFighterSelectScreen::PickFighter(int32 RosterIndex)
{
	UOpenStanceMenuSubsystem* Menu = GetMenu();
	if (!Menu)
	{
		return;
	}

	// The pick sets yours, or the opponent's while choosing the opponent; picking the fighter the other side has swaps them.
	FOpenStanceMenuSession& Session = Menu->GetSession();
	const bool bChungPick = GetPickSide() == EOpenStanceSide::Chung;
	int32& Picked = bChungPick ? Session.ChungFighter : Session.HongFighter;
	int32& Other = bChungPick ? Session.HongFighter : Session.ChungFighter;
	if (Other == RosterIndex)
	{
		Other = Picked;
	}
	Picked = RosterIndex;
}
