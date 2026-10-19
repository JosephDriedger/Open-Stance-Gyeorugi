#pragma once

#include "CoreMinimal.h"
#include "Menu/OpenStanceMenuTypes.h"
#include "Menu/OpenStanceScreen.h"
#include "Widgets/Layout/SConstraintCanvas.h"
#include "OpenStanceMatchScreen.generated.h"

class UOpenStanceMatchModel;

/**
 * Match HUD: scoreboard, round clock, names, stamina, gam-jeom counts, the referee's call and score pop-ups.
 * It only reads UOpenStanceMatchModel, which gameplay fills in. While the model is in demo mode the HUD also runs
 * the clock, and A scores a random technique, so the screen can be tried before gameplay exists. B, Escape or the
 * menu button pauses.
 */
UCLASS()
class OPENSTANCE_API UOpenStanceMatchScreen : public UOpenStanceScreen
{
	GENERATED_BODY()

public:
	UOpenStanceMatchScreen(const FObjectInitializer& ObjectInitializer);

protected:
	virtual TSharedRef<SWidget> BuildContent() override;
	virtual TSharedRef<SWidget> BuildBackground() override;
	virtual TArray<FOpenStanceHint> GetHints() const override;
	virtual FMargin GetContentPadding() const override;
	virtual void NativeTick(const FGeometry& MyGeometry, float InDeltaTime) override;
	virtual FReply NativeOnKeyDown(const FGeometry& InGeometry, const FKeyEvent& InKeyEvent) override;

	// The pieces are shared with the referee view, which reads the same model
	TSharedRef<SWidget> BuildScoreboard(const TWeakObjectPtr<UOpenStanceMatchModel>& Model);
	TSharedRef<SWidget> BuildNameplate(const TWeakObjectPtr<UOpenStanceMatchModel>& Model, EOpenStanceSide Side);
	TSharedRef<SWidget> BuildReviewBox();
	TSharedRef<SWidget> BuildScorePop(const TWeakObjectPtr<UOpenStanceMatchModel>& Model, EOpenStanceSide Side);
	TSharedRef<SWidget> BuildCallBanner(const TWeakObjectPtr<UOpenStanceMatchModel>& Model);
	TSharedRef<SWidget> BuildFighter(EOpenStanceSide Side);

	/** The match model the menu owns, or null when the screen has no menu. */
	TWeakObjectPtr<UOpenStanceMatchModel> GetModel() const;

	/** Absolute placement on the 1920 x 1080 canvas: anchor on an edge, offset in canvas pixels. */
	static SConstraintCanvas::FSlot::FSlotArguments PlaceAt(float AnchorX, float OffsetX, float OffsetY, float AlignX, float AlignY = 0.0f, float AnchorY = 0.0f);

private:
	/** Demo only: awards a random technique to a random side. */
	void ScoreRandomTechnique();

	EOpenStanceSex GetFighterSex(EOpenStanceSide Side) const;

	bool bCheckedPause = false;
	bool bLeaving = false;
};
