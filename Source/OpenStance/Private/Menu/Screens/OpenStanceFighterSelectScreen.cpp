#include "Menu/Screens/OpenStanceFighterSelectScreen.h"

#include "Menu/OpenStanceMenuContent.h"
#include "Menu/OpenStanceMenuSubsystem.h"
#include "Menu/OpenStanceMenuTheme.h"
#include "Menu/Slate/SOpenStanceArt.h"
#include "Menu/Slate/SOpenStanceFrame.h"
#include "Menu/Slate/SOpenStanceItems.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SWidgetSwitcher.h"
#include "Widgets/SBoxPanel.h"

using namespace OpenStanceMenu;
using namespace OpenStanceMenuWidgets;

TArray<FOpenStanceHint> UOpenStanceFighterSelectScreen::GetHints() const
{
	return TabHints(TEXT("Men"), TEXT("Women"));
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
					Tag(TEXT("Assigned"))
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
						SNew(SOpenStanceFighterFigure)
						.BodyColor(Colour)
						.TrimColor(Dark)
						.GearOn(true)
						.Kick(bChung)
						.Sex_Lambda([Fighter]() { return Fighter().Sex; })
					]
				]
			]
			+ SVerticalBox::Slot().AutoHeight().Padding(0.0f, U(0.8f), 0.0f, 0.0f)
			[
				MakeLiveText([Fighter]() { return Fighter().Name; }, { EFont::Display, 2.6f, 0.03f, false }, Palette::Bone)
			]
			+ SVerticalBox::Slot().AutoHeight().Padding(0.0f, U(0.8f), 0.0f, 0.0f)
			[
				SNew(SHorizontalBox)
				+ SHorizontalBox::Slot().AutoWidth().Padding(0.0f, 0.0f, U(0.8f), 0.0f)
				[
					LiveTag([Fighter]() { return Fighter().Sex == EOpenStanceSex::Female ? FString(TEXT("Women")) : FString(TEXT("Men")); })
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

	TSharedRef<SVerticalBox> List = SNew(SVerticalBox);
	bool bFirst = true;
	for (const int32 RosterIndex : OpenStanceMenuContent::GetRosterIndices(Sex))
	{
		const FOpenStanceFighterProfile& Profile = Roster[RosterIndex];
		TSharedRef<SOpenStanceFighterTile> Tile = SNew(SOpenStanceFighterTile)
			.Name(Profile.Name)
			.Detail(FString::Printf(TEXT("%s · %s · OVR %d"), *OpenStanceMenuContent::GetBodyTypeName(Profile.BodyType),
				*OpenStanceMenuContent::GetStyleName(Profile.Style), Profile.Overall))
			.Selected_Lambda([WeakThis, RosterIndex]()
			{
				const UOpenStanceFighterSelectScreen* Screen = WeakThis.Get();
				const UOpenStanceMenuSubsystem* Menu = Screen ? Screen->GetMenu() : nullptr;
				return Menu && Menu->GetSession().ChungFighter == RosterIndex;
			})
			.OnPressed(FSimpleDelegate::CreateWeakLambda(this, [this, RosterIndex]() { PickFighter(RosterIndex); }));

		if (bFirst && GetMenu() && GetMenu()->GetSession().Category == Sex)
		{
			SetDefaultFocus(Tile);
		}
		List->AddSlot().AutoHeight().Padding(0.0f, bFirst ? 0.0f : U(0.8f), 0.0f, 0.0f)
		[
			Tile
		];
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
			MakeLiveText([GetCategory]()
			{
				return GetCategory() == EOpenStanceSex::Female ? FString(TEXT("Premade women’s fighters · choose one"))
					: FString(TEXT("Premade men’s fighters · choose one"));
			}, { EFont::BodyBold, 1.05f, 0.2f, true }, Palette::Mute)
		]
		+ SVerticalBox::Slot().AutoHeight()
		[
			Rosters
		]
		+ SVerticalBox::Slot().AutoHeight().Padding(0.0f, U(1.4f), 0.0f, 0.0f)
		[
			SNew(SOpenStanceOption)
			.Label(TEXT("Start match"))
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
			Head(ModeName, TEXT("Fighter select"))
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

void UOpenStanceFighterSelectScreen::PickFighter(int32 RosterIndex)
{
	UOpenStanceMenuSubsystem* Menu = GetMenu();
	if (!Menu)
	{
		return;
	}

	FOpenStanceMenuSession& Session = Menu->GetSession();
	Session.ChungFighter = RosterIndex;
	if (Session.HongFighter == RosterIndex)
	{
		// The opponent may not be the same fighter: take the first other one in this roster
		const TArray<int32> Indices = OpenStanceMenuContent::GetRosterIndices(Session.Category);
		for (const int32 Candidate : Indices)
		{
			if (Candidate != RosterIndex)
			{
				Session.HongFighter = Candidate;
				break;
			}
		}
	}
}
