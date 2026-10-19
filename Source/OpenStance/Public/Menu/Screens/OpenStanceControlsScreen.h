#pragma once

#include "CoreMinimal.h"
#include "Menu/OpenStanceScreen.h"
#include "OpenStanceControlsScreen.generated.h"

class SOpenStanceGamepadDiagram;
class SOpenStanceInteractive;

/**
 * Every input, by group (GDD 7.8): tabs for movement, modifiers, kicks, fakes, punches and defence, and the
 * Future referee mode. Each row writes its input as button chips and stick-turn icons, and the controller diagram
 * lights up the buttons of the row you are on. Opened from Options and from the pause menu (the move list opens
 * on the standing kicks tab).
 */
UCLASS()
class OPENSTANCE_API UOpenStanceControlsScreen : public UOpenStanceScreen
{
	GENERATED_BODY()

protected:
	virtual TSharedRef<SWidget> BuildContent() override;
	virtual TArray<FOpenStanceHint> GetHints() const override;
	virtual void HandleTabStep(int32 Direction) override;

private:
	void SelectTab(int32 TabIndex);
	void HighlightParts(const TArray<FName>& Parts);

	TWeakPtr<SOpenStanceGamepadDiagram> Diagram;
	TArray<TWeakPtr<SOpenStanceInteractive>> FirstRows;
};
