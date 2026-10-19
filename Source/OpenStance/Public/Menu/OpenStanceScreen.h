#pragma once

#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "Menu/OpenStanceMenuTypes.h"
#include "Menu/Slate/OpenStanceMenuWidgets.h"
#include "OpenStanceScreen.generated.h"

class SOpenStanceInteractive;
class SWidget;
class UOpenStanceMenuSubsystem;

/**
 * Base for every menu screen. A screen is a UMG widget whose layout is written in C++ (Slate, through
 * BuildContent), so the whole menu exists without Widget Blueprint assets. The base supplies what the prototype
 * gives every screen: the backdrop, the fixed 1920 x 1080 canvas scaled to the viewport, the padding, the hint
 * bar, the slide-in, and the shared keys (B or Escape goes back, LB and RB or Q and E change tabs).
 *
 * Derive, implement BuildContent and GetHints, and register the class in UOpenStanceMenuSubsystem.
 */
UCLASS(Abstract)
class OPENSTANCE_API UOpenStanceScreen : public UUserWidget
{
	GENERATED_BODY()

public:
	/** Gives the screen its owner and its id. Call before the screen is added to the viewport. */
	void InitScreen(UOpenStanceMenuSubsystem* InMenu, EOpenStanceMenuScreen InScreenId);

	EOpenStanceMenuScreen GetScreenId() const
	{
		return ScreenId;
	}

	/** Moves gamepad and keyboard focus to the screen's first item. Call once the screen is in the viewport. */
	void FocusDefault();

	/** Draws the default item as focused without Slate focus, for tools that render a screen offscreen. */
	void PreviewFocus();

	/** The slide-in plays by default; overlays and the HUD, and screenshots, turn it off. Set it before the screen is shown. */
	void SetAnimateIn(bool bInAnimateIn)
	{
		bAnimateIn = bInAnimateIn;
	}

protected:
	// UUserWidget
	virtual TSharedRef<SWidget> RebuildWidget() override;
	virtual void ReleaseSlateResources(bool bReleaseChildren) override;
	virtual void NativeConstruct() override;
	virtual void NativeTick(const FGeometry& MyGeometry, float InDeltaTime) override;
	virtual FReply NativeOnKeyDown(const FGeometry& InGeometry, const FKeyEvent& InKeyEvent) override;

	/** The screen's own layout, authored on the 1920 x 1080 canvas inside GetContentPadding. */
	virtual TSharedRef<SWidget> BuildContent() PURE_VIRTUAL(UOpenStanceScreen::BuildContent, return SNullWidget::NullWidget;);

	/** Fills the whole viewport behind the content, letterbox bars included. Defaults to the menu backdrop. */
	virtual TSharedRef<SWidget> BuildBackground();

	/** Glyphs and captions for the bottom bar. Return none for no bar. */
	virtual TArray<FOpenStanceHint> GetHints() const;

	/** The prototype's screen padding (3.2u top, 4u sides, 6.5u bottom, leaving room for the hint bar). */
	virtual FMargin GetContentPadding() const;

	/** B, Escape or Backspace. The default returns to the previous screen. */
	virtual void HandleBack();

	/** LB and RB (Q and E, Page Up and Down, [ and ]). Direction is -1 or +1. */
	virtual void HandleTabStep(int32 Direction)
	{
	}

	/** The item that gets focus first. Set it from BuildContent; the screen holds it weakly. */
	void SetDefaultFocus(const TSharedPtr<SOpenStanceInteractive>& Widget);

	/** Moves focus to a widget on this screen, e.g. to the first tile after a tab change. */
	void FocusWidget(const TSharedPtr<SWidget>& Widget) const;

	UOpenStanceMenuSubsystem* GetMenu() const
	{
		return OwningMenu.Get();
	}

	/** Standard hint sets from the prototype. */
	static TArray<FOpenStanceHint> StandardHints();
	static TArray<FOpenStanceHint> SelectHints();
	static TArray<FOpenStanceHint> TabHints(const FString& PreviousCaption, const FString& NextCaption);

private:
	TWeakObjectPtr<UOpenStanceMenuSubsystem> OwningMenu;
	TWeakPtr<SOpenStanceInteractive> DefaultFocus;
	EOpenStanceMenuScreen ScreenId = EOpenStanceMenuScreen::None;
	float TimeOnScreen = 0.0f;
	bool bAnimateIn = true;
};
