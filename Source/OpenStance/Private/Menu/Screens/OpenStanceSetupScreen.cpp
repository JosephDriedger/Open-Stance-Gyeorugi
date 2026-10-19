#include "Menu/Screens/OpenStanceSetupScreen.h"

#include "Menu/OpenStanceMenuContent.h"
#include "Menu/OpenStanceMenuSubsystem.h"
#include "Menu/OpenStanceMenuTheme.h"
#include "Menu/Slate/SOpenStanceItems.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/SBoxPanel.h"

using namespace OpenStanceMenu;
using namespace OpenStanceMenuWidgets;

TArray<FOpenStanceHint> UOpenStanceSetupScreen::GetHints() const
{
	return SelectHints();
}

TSharedRef<SWidget> UOpenStanceSetupScreen::BuildContent()
{
	const OpenStanceMenuContent::FSetupDefinition* Definition = OpenStanceMenuContent::FindSetup(GetScreenId());
	if (!Definition)
	{
		return SNullWidget::NullWidget;
	}

	TSharedRef<SVerticalBox> Rows = SNew(SVerticalBox);
	TSharedPtr<SOpenStanceInteractive> FirstRow;
	for (int32 RowIndex = 0; RowIndex < Definition->Rows.Num(); ++RowIndex)
	{
		TSharedRef<SOpenStanceOption> Row = SNew(SOpenStanceOption)
			.Label(Definition->Rows[RowIndex].Label)
			.Value_UObject(this, &UOpenStanceSetupScreen::GetRowValue, RowIndex)
			.OnPressed(FSimpleDelegate::CreateWeakLambda(this, [this, RowIndex]() { CycleRow(RowIndex, 1); }))
			.OnStep(FOpenStanceStepDelegate::CreateWeakLambda(this, [this, RowIndex](int32 Direction) { CycleRow(RowIndex, Direction); }));
		if (!FirstRow.IsValid())
		{
			FirstRow = Row;
		}
		Rows->AddSlot().AutoHeight().Padding(0.0f, RowIndex == 0 ? 0.0f : U(0.8f), 0.0f, 0.0f)
		[
			Row
		];
	}

	TSharedRef<SOpenStanceOption> ContinueButton = SNew(SOpenStanceOption)
		.Label(Definition->ContinueLabel)
		.Look(EOpenStanceOptionLook::Primary)
		.OnPressed(FSimpleDelegate::CreateWeakLambda(this, [this]() { Continue(); }));
	Rows->AddSlot().AutoHeight().Padding(0.0f, U(1.8f), 0.0f, 0.0f)
	[
		ContinueButton
	];
	SetDefaultFocus(FirstRow);

	TSharedRef<SVerticalBox> Cards = SNew(SVerticalBox);
	for (int32 CardIndex = 0; CardIndex < Definition->Cards.Num(); ++CardIndex)
	{
		Cards->AddSlot().AutoHeight().Padding(0.0f, CardIndex == 0 ? 0.0f : U(0.8f), 0.0f, 0.0f)
		[
			TextCard(Definition->Cards[CardIndex].Title, Definition->Cards[CardIndex].Paragraphs)
		];
	}

	return SNew(SVerticalBox)
		+ SVerticalBox::Slot().AutoHeight()
		[
			Head(Definition->Kicker, Definition->Title, Definition->bFuture)
		]
		+ SVerticalBox::Slot().FillHeight(1.0f).Padding(0.0f, U(1.6f), 0.0f, 0.0f)
		[
			SNew(SHorizontalBox)
			+ SHorizontalBox::Slot().AutoWidth()
			[
				SNew(SBox).WidthOverride(U(46.0f))
				[
					Rows
				]
			]
			+ SHorizontalBox::Slot().FillWidth(1.0f).Padding(U(2.4f), 0.0f, 0.0f, 0.0f)
			[
				Cards
			]
		];
}

FString UOpenStanceSetupScreen::GetRowValue(int32 RowIndex) const
{
	const OpenStanceMenuContent::FSetupDefinition* Definition = OpenStanceMenuContent::FindSetup(GetScreenId());
	const UOpenStanceMenuSubsystem* Menu = GetMenu();
	if (!Definition || !Menu || !Definition->Rows.IsValidIndex(RowIndex))
	{
		return FString();
	}

	const OpenStanceMenuContent::FChoiceRow& Row = Definition->Rows[RowIndex];
	const int32 Index = Menu->GetChoiceIndex(GetScreenId(), Row.Id, Row.DefaultIndex);
	return Row.Values.IsValidIndex(Index) ? Row.Values[Index] : FString();
}

void UOpenStanceSetupScreen::CycleRow(int32 RowIndex, int32 Direction)
{
	const OpenStanceMenuContent::FSetupDefinition* Definition = OpenStanceMenuContent::FindSetup(GetScreenId());
	UOpenStanceMenuSubsystem* Menu = GetMenu();
	if (!Definition || !Menu || !Definition->Rows.IsValidIndex(RowIndex))
	{
		return;
	}

	const OpenStanceMenuContent::FChoiceRow& Row = Definition->Rows[RowIndex];
	const int32 Count = Row.Values.Num();
	const int32 Index = Menu->GetChoiceIndex(GetScreenId(), Row.Id, Row.DefaultIndex);
	Menu->SetChoiceIndex(GetScreenId(), Row.Id, (Index + Direction + Count) % Count);
}

void UOpenStanceSetupScreen::Continue()
{
	const OpenStanceMenuContent::FSetupDefinition* Definition = OpenStanceMenuContent::FindSetup(GetScreenId());
	if (UOpenStanceMenuSubsystem* Menu = GetMenu())
	{
		if (Definition)
		{
			Menu->ShowScreen(Definition->Next);
		}
	}
}
