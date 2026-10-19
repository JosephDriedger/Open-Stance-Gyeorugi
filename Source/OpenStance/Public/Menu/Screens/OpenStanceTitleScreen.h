#pragma once

#include "CoreMinimal.h"
#include "Menu/OpenStanceScreen.h"
#include "OpenStanceTitleScreen.generated.h"

/** Logo and "press any button". Any key, button or click continues to the main menu. */
UCLASS()
class OPENSTANCE_API UOpenStanceTitleScreen : public UOpenStanceScreen
{
	GENERATED_BODY()

public:
	UOpenStanceTitleScreen(const FObjectInitializer& ObjectInitializer);

protected:
	virtual TSharedRef<SWidget> BuildContent() override;
	virtual TArray<FOpenStanceHint> GetHints() const override;
	virtual FReply NativeOnKeyDown(const FGeometry& InGeometry, const FKeyEvent& InKeyEvent) override;
	virtual FReply NativeOnMouseButtonDown(const FGeometry& InGeometry, const FPointerEvent& InMouseEvent) override;

private:
	void Proceed();
};
