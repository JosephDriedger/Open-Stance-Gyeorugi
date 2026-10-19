#include "Menu/Screens/OpenStanceInfoScreen.h"

#include "Menu/OpenStanceMenuContent.h"
#include "Menu/OpenStanceMenuTheme.h"
#include "Menu/Slate/SOpenStanceItems.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/SBoxPanel.h"

using namespace OpenStanceMenu;
using namespace OpenStanceMenuWidgets;

TSharedRef<SWidget> UOpenStanceInfoScreen::BuildContent()
{
	const OpenStanceMenuContent::FListDefinition* Definition = OpenStanceMenuContent::FindList(GetScreenId());
	if (!Definition)
	{
		return SNullWidget::NullWidget;
	}

	TSharedRef<SVerticalBox> Items = SNew(SVerticalBox);
	TSharedPtr<SOpenStanceInteractive> FirstItem;
	for (int32 Index = 0; Index < Definition->Items.Num(); ++Index)
	{
		TSharedRef<SOpenStanceOption> Item = SNew(SOpenStanceOption)
			.Label(Definition->Items[Index].Label)
			.Small(Definition->Items[Index].Detail);
		if (!FirstItem.IsValid())
		{
			FirstItem = Item;
		}
		Items->AddSlot().AutoHeight().Padding(0.0f, Index == 0 ? 0.0f : U(0.8f), 0.0f, 0.0f)
		[
			Item
		];
	}
	SetDefaultFocus(FirstItem);

	TSharedRef<SVerticalBox> Cards = SNew(SVerticalBox);
	for (int32 Index = 0; Index < Definition->Cards.Num(); ++Index)
	{
		const OpenStanceMenuContent::FInfoCard& Card = Definition->Cards[Index];
		TSharedRef<SVerticalBox> Body = SNew(SVerticalBox);
		for (const FString& Text : Card.Paragraphs)
		{
			Body->AddSlot().AutoHeight().Padding(0.0f, 0.0f, 0.0f, U(0.7f))
			[
				Paragraph(Text)
			];
		}
		Cards->AddSlot().AutoHeight().Padding(0.0f, Index == 0 ? 0.0f : U(0.8f), 0.0f, 0.0f)
		[
			OpenStanceMenuWidgets::Card(Card.Title, Body, FLinearColor::Transparent, Card.bFutureTag)
		];
	}

	return SNew(SVerticalBox)
		+ SVerticalBox::Slot().AutoHeight()
		[
			Head(Definition->Kicker, Definition->Title, true)
		]
		+ SVerticalBox::Slot().FillHeight(1.0f).Padding(0.0f, U(1.6f), 0.0f, 0.0f)
		[
			SNew(SHorizontalBox)
			+ SHorizontalBox::Slot().AutoWidth()
			[
				SNew(SBox).WidthOverride(U(Definition->WidthUnits))
				[
					Items
				]
			]
			+ SHorizontalBox::Slot().FillWidth(1.0f).Padding(U(2.4f), 0.0f, 0.0f, 0.0f)
			[
				Cards
			]
		];
}
