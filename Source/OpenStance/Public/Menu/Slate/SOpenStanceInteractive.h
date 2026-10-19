#pragma once

#include "CoreMinimal.h"
#include "Widgets/SCompoundWidget.h"

/** Called with -1 for left and +1 for right (arrow keys, D-pad or the left stick). */
DECLARE_DELEGATE_OneParam(FOpenStanceStepDelegate, int32);

/**
 * Behaviour shared by everything the player can focus and press: gamepad and keyboard focus, accept, left and
 * right stepping for value rows, pointer click, and hover that moves focus (so the prototype's single "selected"
 * look holds for mouse and pad alike). Derived widgets draw themselves and read IsActive().
 *
 * Locked items (greyed Future entries, locked lessons) stay visible but take no focus or input.
 */
class OPENSTANCE_API SOpenStanceInteractive : public SCompoundWidget
{
public:
	/** True while the item has focus or the pointer is over it. */
	bool IsActive() const;

	bool IsLocked() const
	{
		return bLocked;
	}

	/** Run the press action as if accepted; the screens use it for shortcuts. */
	void Press();

	/** Draws the item as focused without Slate focus, for tools that render a screen offscreen. */
	void SetPreviewActive(bool bInPreviewActive);

	virtual bool SupportsKeyboardFocus() const override;
	virtual FReply OnFocusReceived(const FGeometry& MyGeometry, const FFocusEvent& InFocusEvent) override;
	virtual void OnFocusLost(const FFocusEvent& InFocusEvent) override;
	virtual FReply OnKeyDown(const FGeometry& MyGeometry, const FKeyEvent& InKeyEvent) override;
	virtual FReply OnMouseButtonDown(const FGeometry& MyGeometry, const FPointerEvent& MouseEvent) override;
	virtual FReply OnMouseButtonUp(const FGeometry& MyGeometry, const FPointerEvent& MouseEvent) override;
	virtual void OnMouseEnter(const FGeometry& MyGeometry, const FPointerEvent& MouseEvent) override;
	virtual void OnMouseLeave(const FPointerEvent& MouseEvent) override;

protected:
	void InitInteraction(bool bInLocked, const FSimpleDelegate& InOnPressed, const FOpenStanceStepDelegate& InOnStep, const FSimpleDelegate& InOnActivated);

	/** Focus or hover changed; derived widgets use it for effects that are not part of painting (the hub tile lift). */
	virtual void OnActiveChanged(bool bActive)
	{
	}

private:
	void RefreshActive();

	bool bLocked = false;
	bool bWasActive = false;
	bool bPreviewActive = false;
	FSimpleDelegate OnPressed;
	FOpenStanceStepDelegate OnStep;
	FSimpleDelegate OnActivated;
};

/** Arguments every interactive widget accepts, so each derived widget does not repeat them. */
#define OPENSTANCE_INTERACTIVE_ARGUMENTS \
	SLATE_ARGUMENT(bool, Locked) \
	SLATE_EVENT(FSimpleDelegate, OnPressed) \
	SLATE_EVENT(FOpenStanceStepDelegate, OnStep) \
	SLATE_EVENT(FSimpleDelegate, OnActivated)
