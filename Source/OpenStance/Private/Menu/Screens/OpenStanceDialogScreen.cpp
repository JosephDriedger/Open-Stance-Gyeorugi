#include "Menu/Screens/OpenStanceDialogScreen.h"

#include "Menu/OpenStanceMenuTheme.h"
#include "Menu/Slate/SOpenStanceFrame.h"
#include "Menu/Slate/SOpenStanceItems.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/SBoxPanel.h"

using namespace OpenStanceMenu;
using namespace OpenStanceMenuWidgets;

void UOpenStanceDialogScreen::SetRequest(FOpenStanceDialogRequest InRequest)
{
	Request = MoveTemp(InRequest);
	SetAnimateIn(false);
}

TSharedRef<SWidget> UOpenStanceDialogScreen::BuildBackground()
{
	// The veil that dims whatever is behind the dialog, including the letterbox bars
	return SNew(SOpenStanceFrame).Fill(Hex(0x05070b, 0.78f));
}

FMargin UOpenStanceDialogScreen::GetContentPadding() const
{
	return FMargin(0.0f);
}

TArray<FOpenStanceHint> UOpenStanceDialogScreen::GetHints() const
{
	return TArray<FOpenStanceHint>();
}

TSharedRef<SWidget> UOpenStanceDialogScreen::BuildContent()
{
	TSharedRef<SVerticalBox> Column = SNew(SVerticalBox)
		+ SVerticalBox::Slot().AutoHeight().Padding(0.0f, 0.0f, 0.0f, U(0.6f))
		[
			MakeText(Request.Title, { EFont::Display, 3.0f, 0.06f, true }, Palette::Bone)
		];

	if (!Request.Message.IsEmpty())
	{
		Column->AddSlot().AutoHeight().Padding(0.0f, 0.0f, 0.0f, U(0.8f))
		[
			Paragraph(Request.Message, 1.25f, Palette::Mute)
		];
	}

	TWeakObjectPtr<UOpenStanceDialogScreen> WeakThis(this);
	TSharedPtr<SOpenStanceInteractive> First;
	for (int32 Index = 0; Index < Request.Buttons.Num(); ++Index)
	{
		const FOpenStanceDialogButton& Button = Request.Buttons[Index];
		TSharedRef<SOpenStanceOption> Option = SNew(SOpenStanceOption)
			.Label(Button.Label)
			.Look(Button.bDanger ? EOpenStanceOptionLook::Danger : EOpenStanceOptionLook::Standard)
			.OnPressed(FSimpleDelegate::CreateWeakLambda(this, [WeakThis, Index]()
			{
				const UOpenStanceDialogScreen* Dialog = WeakThis.Get();
				if (!Dialog)
				{
					return;
				}
				// Copy first: closing the dialog destroys the request the callback lives in
				TFunction<void()> Callback = Dialog->Request.Buttons[Index].OnPressed;
				if (UOpenStanceMenuSubsystem* Menu = Dialog->GetMenu())
				{
					Menu->CloseDialog();
				}
				if (Callback)
				{
					Callback();
				}
			}));
		if (!First.IsValid())
		{
			First = Option;
		}
		Column->AddSlot().AutoHeight().Padding(0.0f, Index == 0 ? 0.0f : U(0.8f), 0.0f, 0.0f)
		[
			Option
		];
	}
	SetDefaultFocus(First);

	return SNew(SBox)
		.HAlign(HAlign_Center)
		.VAlign(VAlign_Center)
		[
			SNew(SBox)
			.WidthOverride(U(34.0f))
			[
				SNew(SOpenStanceFrame)
				.Fill(Palette::Panel)
				.AccentColor(Palette::Chung)
				.AccentEdge(EOpenStanceFrameEdge::Top)
				.AccentThickness(U(0.4f))
				.Padding(FMargin(U(2.2f)))
				[
					Column
				]
			]
		];
}

void UOpenStanceDialogScreen::HandleBack()
{
	TFunction<void()> OnBack = Request.OnBack;
	if (UOpenStanceMenuSubsystem* Menu = GetMenu())
	{
		Menu->CloseDialog();
	}
	if (OnBack)
	{
		OnBack();
	}
}
