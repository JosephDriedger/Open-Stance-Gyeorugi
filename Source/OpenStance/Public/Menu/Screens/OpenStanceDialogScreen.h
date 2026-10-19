#pragma once

#include "CoreMinimal.h"
#include "Menu/OpenStanceMenuSubsystem.h"
#include "Menu/OpenStanceScreen.h"
#include "OpenStanceDialogScreen.generated.h"

/** Modal dialog over the current screen: a title, a message and a stack of buttons. Also the pause menu. */
UCLASS()
class OPENSTANCE_API UOpenStanceDialogScreen : public UOpenStanceScreen
{
	GENERATED_BODY()

public:
	/** Set before the dialog is shown. */
	void SetRequest(FOpenStanceDialogRequest InRequest);

protected:
	virtual TSharedRef<SWidget> BuildContent() override;
	virtual TSharedRef<SWidget> BuildBackground() override;
	virtual TArray<FOpenStanceHint> GetHints() const override;
	virtual FMargin GetContentPadding() const override;
	virtual void HandleBack() override;

private:
	FOpenStanceDialogRequest Request;
};
