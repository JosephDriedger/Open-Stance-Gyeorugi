#include "Menu/Screens/OpenStanceMainScreen.h"

#include "Menu/OpenStanceMenuContent.h"
#include "Menu/OpenStanceMenuSubsystem.h"
#include "Menu/OpenStanceMenuTheme.h"
#include "Menu/Slate/SOpenStanceFrame.h"
#include "Menu/Slate/SOpenStanceItems.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SWidgetSwitcher.h"
#include "Widgets/SBoxPanel.h"

using namespace OpenStanceMenu;
using namespace OpenStanceMenuWidgets;

namespace
{
	/** The strip of two cards under the tiles (.strip .card). */
	TSharedRef<SWidget> MakeInfoCard(const FString& Title, const FString& Message)
	{
		return SNew(SOpenStanceFrame)
			.Fill(Hex(0x0f192c, 0.85f))
			.AccentColor(Palette::Line)
			.AccentEdge(EOpenStanceFrameEdge::Top)
			.AccentThickness(1.5f)
			.Padding(FMargin(U(1.4f)))
			[
				SNew(SHorizontalBox)
				+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(0.0f, 0.0f, U(1.4f), 0.0f)
				[
					SNew(SBox).MaxDesiredWidth(U(9.0f))
					[
						SNew(STextBlock)
						.Text(FText::FromString(Title))
						.Font(MakeFont(EFont::DisplayItalic, 1.9f, 0.04f))
						.ColorAndOpacity(Palette::Ice)
						.TransformPolicy(ETextTransformPolicy::ToUpper)
						.AutoWrapText(true)
						.LineHeightPercentage(0.95f)
					]
				]
				+ SHorizontalBox::Slot().FillWidth(1.0f).VAlign(VAlign_Center)
				[
					Paragraph(Message, 1.2f, Palette::Mute)
				]
			];
	}
}

TArray<FOpenStanceHint> UOpenStanceMainScreen::GetHints() const
{
	return TabHints(TEXT("Previous tab"), TEXT("Next tab"));
}

TSharedRef<SWidget> UOpenStanceMainScreen::BuildContent()
{
	const TArray<OpenStanceMenuContent::FHub>& Hubs = OpenStanceMenuContent::GetHubs();
	TWeakObjectPtr<UOpenStanceMainScreen> WeakThis(this);
	const auto GetHubIndex = [WeakThis]()
	{
		const UOpenStanceMainScreen* Screen = WeakThis.Get();
		const UOpenStanceMenuSubsystem* Menu = Screen ? Screen->GetMenu() : nullptr;
		return Menu ? FMath::Clamp(Menu->GetSession().MainHubIndex, 0, OpenStanceMenuContent::GetHubs().Num() - 1) : 0;
	};

	// Tab strip: LB, the four hubs, RB
	TSharedRef<SHorizontalBox> Tabs = SNew(SHorizontalBox)
		+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(0.0f, 0.0f, U(0.6f), 0.0f)
		[
			Glyph(TEXT("LB"), EOpenStanceGlyphLook::Key)
		];
	for (int32 HubIndex = 0; HubIndex < Hubs.Num(); ++HubIndex)
	{
		Tabs->AddSlot().AutoWidth().VAlign(VAlign_Center).Padding(0.0f, 0.0f, U(0.6f), 0.0f)
		[
			SNew(SOpenStanceTabButton)
			.Label(Hubs[HubIndex].Name)
			.Selected_Lambda([GetHubIndex, HubIndex]() { return GetHubIndex() == HubIndex; })
			.OnPressed(FSimpleDelegate::CreateWeakLambda(this, [this, HubIndex]() { SelectHub(HubIndex); }))
		];
	}
	Tabs->AddSlot().AutoWidth().VAlign(VAlign_Center)
	[
		Glyph(TEXT("RB"), EOpenStanceGlyphLook::Key)
	];

	// One strip of tiles per hub; the switcher shows the selected one
	FirstTiles.Reset();
	TSharedRef<SWidgetSwitcher> Strips = SNew(SWidgetSwitcher).WidgetIndex_Lambda(GetHubIndex);
	for (int32 HubIndex = 0; HubIndex < Hubs.Num(); ++HubIndex)
	{
		TSharedRef<SHorizontalBox> Row = SNew(SHorizontalBox);
		for (int32 TileIndex = 0; TileIndex < Hubs[HubIndex].Tiles.Num(); ++TileIndex)
		{
			const OpenStanceMenuContent::FHubTile& Tile = Hubs[HubIndex].Tiles[TileIndex];
			TSharedRef<SOpenStanceHubTile> Widget = SNew(SOpenStanceHubTile)
				.Title(Tile.Title)
				.Subtitle(Tile.Subtitle)
				.GradientFrom(Tile.From)
				.GradientTo(Tile.To)
				.ShowKick(Tile.bKick)
				.Future(Tile.bFuture)
				.OnPressed(FSimpleDelegate::CreateWeakLambda(this, [this, HubIndex, TileIndex]() { OpenTile(HubIndex, TileIndex); }));
			if (TileIndex == 0)
			{
				FirstTiles.Add(Widget);
			}
			Row->AddSlot().FillWidth(1.0f).Padding(TileIndex == 0 ? 0.0f : U(1.2f), 0.0f, 0.0f, 0.0f)
			[
				Widget
			];
		}
		Strips->AddSlot()[Row];
	}

	const int32 StartHub = GetHubIndex();
	SetDefaultFocus(FirstTiles.IsValidIndex(StartHub) ? FirstTiles[StartHub].Pin() : nullptr);

	return SNew(SVerticalBox)
		+ SVerticalBox::Slot().AutoHeight()
		[
			SNew(SVerticalBox)
			+ SVerticalBox::Slot().AutoHeight()
			[
				Kicker(TEXT("Open Stance · Main menu"))
			]
			+ SVerticalBox::Slot().AutoHeight().Padding(0.0f, U(0.7f), 0.0f, 0.0f)
			[
				Tabs
			]
		]
		+ SVerticalBox::Slot().FillHeight(1.0f).Padding(0.0f, U(1.6f), 0.0f, U(1.6f))
		[
			Strips
		]
		+ SVerticalBox::Slot().AutoHeight()
		[
			SNew(SBox).HeightOverride(U(7.2f))
			[
				SNew(SHorizontalBox)
				+ SHorizontalBox::Slot().FillWidth(1.0f)
				[
					MakeInfoCard(TEXT("Up next"), TEXT("City Open · Career week 3. Enter your fighter before the calendar advances."))
				]
				+ SHorizontalBox::Slot().FillWidth(1.0f).Padding(U(1.2f), 0.0f, 0.0f, 0.0f)
				[
					MakeInfoCard(TEXT("Coach"), TEXT("Counters cost you the last three matches. Try the Counter timing drill."))
				]
			]
		];
}

void UOpenStanceMainScreen::SelectHub(int32 HubIndex)
{
	UOpenStanceMenuSubsystem* Menu = GetMenu();
	if (!Menu || !FirstTiles.IsValidIndex(HubIndex))
	{
		return;
	}
	Menu->GetSession().MainHubIndex = HubIndex;
	FocusWidget(FirstTiles[HubIndex].Pin());
}

void UOpenStanceMainScreen::HandleTabStep(int32 Direction)
{
	const UOpenStanceMenuSubsystem* Menu = GetMenu();
	const int32 HubCount = OpenStanceMenuContent::GetHubs().Num();
	if (Menu && HubCount > 0)
	{
		SelectHub((Menu->GetSession().MainHubIndex + Direction + HubCount) % HubCount);
	}
}

void UOpenStanceMainScreen::OpenTile(int32 HubIndex, int32 TileIndex)
{
	UOpenStanceMenuSubsystem* Menu = GetMenu();
	const TArray<OpenStanceMenuContent::FHub>& Hubs = OpenStanceMenuContent::GetHubs();
	if (!Menu || !Hubs.IsValidIndex(HubIndex) || !Hubs[HubIndex].Tiles.IsValidIndex(TileIndex))
	{
		return;
	}

	const OpenStanceMenuContent::FHubTile& Tile = Hubs[HubIndex].Tiles[TileIndex];
	if (Tile.bQuit)
	{
		Menu->ShowQuitGameDialog();
		return;
	}

	// The Play hub entries decide which kind of match the setup and select screens build
	switch (Tile.Target)
	{
	case EOpenStanceMenuScreen::Sparring:
		Menu->GetSession().Mode = EOpenStanceMatchMode::Sparring;
		break;
	case EOpenStanceMenuScreen::Tournament:
		Menu->GetSession().Mode = EOpenStanceMatchMode::Tournament;
		break;
	case EOpenStanceMenuScreen::RefereeSetup:
		Menu->GetSession().Mode = EOpenStanceMatchMode::Referee;
		break;
	default:
		break;
	}
	Menu->ShowScreen(Tile.Target);
}
