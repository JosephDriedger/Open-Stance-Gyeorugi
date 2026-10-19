#pragma once

#include "CoreMinimal.h"
#include "Menu/OpenStanceScreen.h"
#include "OpenStanceOptionsScreen.generated.h"

class SOpenStanceInteractive;
class UOpenStanceUserSettings;

/**
 * Audio, Video, Controls and Accessibility settings (GDD 7.8). Every change is applied and saved straight away
 * through UOpenStanceUserSettings, so there is no Apply button. Entries the design tags Future are shown with the
 * Future tag and store their value but do nothing yet.
 */
UCLASS()
class OPENSTANCE_API UOpenStanceOptionsScreen : public UOpenStanceScreen
{
	GENERATED_BODY()

protected:
	virtual TSharedRef<SWidget> BuildContent() override;
	virtual TArray<FOpenStanceHint> GetHints() const override;
	virtual void HandleTabStep(int32 Direction) override;

private:
	TSharedRef<SWidget> BuildAudioTab();
	TSharedRef<SWidget> BuildVideoTab();
	TSharedRef<SWidget> BuildControlsTab();
	TSharedRef<SWidget> BuildAccessibilityTab();

	/** A value row that cycles through named values. Get returns the current index; Set receives the new one. */
	TSharedRef<SOpenStanceInteractive> MakeChoiceRow(const FString& Label, const TArray<FString>& Values, TFunction<int32()> Get, TFunction<void(int32)> Set, bool bFuture = false, bool bVideo = false);

	/** On and off, in the order the prototype lists them for each setting. */
	TSharedRef<SOpenStanceInteractive> MakeToggleRow(const FString& Label, bool UOpenStanceUserSettings::* Setting, bool bOnFirst, bool bFuture = false);

	TSharedRef<SOpenStanceInteractive> MakeSliderRow(const FString& Label, float UOpenStanceUserSettings::* Setting, float Min, float Max, float Step,
		TFunction<FString(float)> Format, bool bFuture = false);

	/** Remembers the first row of a tab so a tab change can focus it. */
	void RegisterFirstRow(const TSharedRef<SOpenStanceInteractive>& Row);

	void SelectTab(int32 TabIndex);
	UOpenStanceUserSettings* GetSettings() const;
	void Commit(bool bVideoChanged) const;

	TArray<TWeakPtr<SOpenStanceInteractive>> FirstRows;
};
