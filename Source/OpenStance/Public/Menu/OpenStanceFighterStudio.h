#pragma once

#include "CoreMinimal.h"
#include "Menu/OpenStanceMenuTypes.h"
#include "UObject/Object.h"
#include "OpenStanceFighterStudio.generated.h"

class AActor;
class UAnimSequenceBase;
class UMaterialInstanceDynamic;
class USceneCaptureComponent2D;
class USkeletalMeshComponent;
class UTextureRenderTarget2D;

/**
 * A small photo studio for the menu's fighter portraits: one fighter (the body type as a man or a woman in the
 * traditional dobok, no sparring gear) looping the sparring stance, lit by its own lights and filmed by two scene
 * captures out of sight of the level. The colour capture and the depth capture feed M_FighterPreview, which keeps only
 * the fighter, so the portrait draws straight onto the menu panel. The camera never changes between body types, so a Tall fighter reads
 * taller than a Compact one.
 */
UCLASS(Transient)
class OPENSTANCE_API UOpenStanceFighterStudio : public UObject
{
	GENERATED_BODY()

public:
	/** Builds the studio in World. bFaceLeft turns and mirrors the fighter for the right-hand (Hong) panel. */
	bool Init(UWorld* World, bool bFaceLeft);

	/**
	 * Shows a premade fighter's portrait (PortraitKey, OpenStanceMenuContent::GetPortraitKey), or with no key or no such
	 * asset the plain build of this body type and sex; does nothing if it is already showing.
	 */
	void SetFighter(EOpenStanceBodyType BodyType, EOpenStanceSex Sex, const FString& PortraitKey = FString());

	/** Poses the stance at Seconds into its loop and renders both captures. */
	void Update(float Seconds);

	/** The material the portrait draws with; null if the studio could not be built. */
	UMaterialInstanceDynamic* GetMaterial() const { return Material; }

	/** The colour and depth captures (for review tools). */
	UTextureRenderTarget2D* GetColorTarget() const { return ColorTarget; }
	UTextureRenderTarget2D* GetDepthTarget() const { return DepthTarget; }

	/** Removes the studio from the world. */
	void Shutdown();

	virtual void BeginDestroy() override;

	/** Portrait render size in pixels (3:4). */
	static constexpr int32 Width = 600;
	static constexpr int32 Height = 800;

private:
	UPROPERTY()
	TObjectPtr<AActor> Actor;

	UPROPERTY()
	TObjectPtr<USkeletalMeshComponent> Body;

	UPROPERTY()
	TObjectPtr<USceneCaptureComponent2D> ColorCapture;

	UPROPERTY()
	TObjectPtr<USceneCaptureComponent2D> DepthCapture;

	UPROPERTY()
	TObjectPtr<UTextureRenderTarget2D> ColorTarget;

	UPROPERTY()
	TObjectPtr<UTextureRenderTarget2D> DepthTarget;

	UPROPERTY()
	TObjectPtr<UMaterialInstanceDynamic> Material;

	UPROPERTY()
	TObjectPtr<UAnimSequenceBase> Stance;

	EOpenStanceBodyType ShownBodyType = EOpenStanceBodyType::Compact;
	EOpenStanceSex ShownSex = EOpenStanceSex::Male;
	FString ShownKey;
	bool bHasBody = false;
};
