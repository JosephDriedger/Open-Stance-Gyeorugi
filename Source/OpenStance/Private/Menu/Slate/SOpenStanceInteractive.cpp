#include "Menu/Slate/SOpenStanceInteractive.h"

#include "Framework/Application/SlateApplication.h"
#include "InputCoreTypes.h"

void SOpenStanceInteractive::InitInteraction(bool bInLocked, const FSimpleDelegate& InOnPressed, const FOpenStanceStepDelegate& InOnStep, const FSimpleDelegate& InOnActivated)
{
	bLocked = bInLocked;
	OnPressed = InOnPressed;
	OnStep = InOnStep;
	OnActivated = InOnActivated;
}

bool SOpenStanceInteractive::IsActive() const
{
	return !bLocked && (bPreviewActive || HasAnyUserFocus().IsSet() || IsHovered());
}

void SOpenStanceInteractive::SetPreviewActive(bool bInPreviewActive)
{
	bPreviewActive = bInPreviewActive;
	RefreshActive();
}

void SOpenStanceInteractive::Press()
{
	if (!bLocked)
	{
		OnPressed.ExecuteIfBound();
	}
}

void SOpenStanceInteractive::RefreshActive()
{
	const bool bActive = IsActive();
	if (bActive == bWasActive)
	{
		return;
	}
	bWasActive = bActive;
	OnActiveChanged(bActive);
	if (bActive)
	{
		OnActivated.ExecuteIfBound();
	}
}

bool SOpenStanceInteractive::SupportsKeyboardFocus() const
{
	return !bLocked;
}

FReply SOpenStanceInteractive::OnFocusReceived(const FGeometry& MyGeometry, const FFocusEvent& InFocusEvent)
{
	RefreshActive();
	return FReply::Handled();
}

void SOpenStanceInteractive::OnFocusLost(const FFocusEvent& InFocusEvent)
{
	RefreshActive();
}

FReply SOpenStanceInteractive::OnKeyDown(const FGeometry& MyGeometry, const FKeyEvent& InKeyEvent)
{
	if (bLocked)
	{
		return FReply::Unhandled();
	}

	if (FSlateApplication::Get().GetNavigationActionFromKey(InKeyEvent) == EUINavigationAction::Accept)
	{
		Press();
		return FReply::Handled();
	}

	if (OnStep.IsBound())
	{
		const FKey Key = InKeyEvent.GetKey();
		if (Key == EKeys::Left || Key == EKeys::Gamepad_DPad_Left || Key == EKeys::Gamepad_LeftStick_Left)
		{
			OnStep.Execute(-1);
			return FReply::Handled();
		}
		if (Key == EKeys::Right || Key == EKeys::Gamepad_DPad_Right || Key == EKeys::Gamepad_LeftStick_Right)
		{
			OnStep.Execute(1);
			return FReply::Handled();
		}
	}
	return FReply::Unhandled();
}

FReply SOpenStanceInteractive::OnMouseButtonDown(const FGeometry& MyGeometry, const FPointerEvent& MouseEvent)
{
	if (bLocked || MouseEvent.GetEffectingButton() != EKeys::LeftMouseButton)
	{
		return FReply::Unhandled();
	}
	return FReply::Handled().CaptureMouse(AsShared()).SetUserFocus(AsShared(), EFocusCause::Mouse);
}

FReply SOpenStanceInteractive::OnMouseButtonUp(const FGeometry& MyGeometry, const FPointerEvent& MouseEvent)
{
	if (MouseEvent.GetEffectingButton() != EKeys::LeftMouseButton || !HasMouseCapture())
	{
		return FReply::Unhandled();
	}
	if (MyGeometry.IsUnderLocation(MouseEvent.GetScreenSpacePosition()))
	{
		Press();
	}
	return FReply::Handled().ReleaseMouseCapture();
}

void SOpenStanceInteractive::OnMouseEnter(const FGeometry& MyGeometry, const FPointerEvent& MouseEvent)
{
	SCompoundWidget::OnMouseEnter(MyGeometry, MouseEvent);
	if (!bLocked)
	{
		FSlateApplication::Get().SetUserFocus(MouseEvent.GetUserIndex(), AsShared(), EFocusCause::Mouse);
	}
	RefreshActive();
}

void SOpenStanceInteractive::OnMouseLeave(const FPointerEvent& MouseEvent)
{
	SCompoundWidget::OnMouseLeave(MouseEvent);
	RefreshActive();
}
