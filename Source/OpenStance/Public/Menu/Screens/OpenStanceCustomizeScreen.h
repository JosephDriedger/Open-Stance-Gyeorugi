#pragma once

#include "CoreMinimal.h"
#include "Menu/OpenStanceMenuTypes.h"
#include "Menu/OpenStanceScreen.h"
#include "OpenStanceCustomizeScreen.generated.h"

class SOpenStanceOption;

/**
 * Fighter creator for the Career fighter: sex, body type, fighting style, and natural skin, hair and eye presets.
 * The protector and helmet are only Chung blue or Hong red (Docs/Character_Customization.md), and appearance never
 * changes attributes. Edits go straight to the menu session's FOpenStanceFighterAppearance.
 */
UCLASS()
class OPENSTANCE_API UOpenStanceCustomizeScreen : public UOpenStanceScreen
{
	GENERATED_BODY()

protected:
	virtual TSharedRef<SWidget> BuildContent() override;
	virtual TArray<FOpenStanceHint> GetHints() const override;

private:
	FOpenStanceFighterAppearance& GetAppearance() const;

	TSharedRef<SOpenStanceOption> BuildChoiceRow(const FString& Label, const TArray<FString>& Values, TFunction<int32()> Get, TFunction<void(int32)> Set);
	TSharedRef<SWidget> BuildSwatchGroup(const FString& Title, const TArray<FLinearColor>& Colours, TFunction<int32()> Get, TFunction<void(int32)> Set);
};
