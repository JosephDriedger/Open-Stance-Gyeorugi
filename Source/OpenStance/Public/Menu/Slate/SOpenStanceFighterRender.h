#pragma once

#include "CoreMinimal.h"
#include "Menu/OpenStanceFighterStudio.h"
#include "Menu/OpenStanceMenuTypes.h"
#include "Styling/SlateBrush.h"
#include "UObject/StrongObjectPtr.h"
#include "Widgets/DeclarativeSyntaxSupport.h"
#include "Widgets/SCompoundWidget.h"

class UWorld;

/**
 * A fighter portrait rendered live from the 3D body build (UOpenStanceFighterStudio): the chosen body type, no gear, in
 * the sparring stance. Falls back to its Fallback content (the flat silhouette) when the studio cannot be built, such
 * as in a world with no rendering.
 */
class OPENSTANCE_API SOpenStanceFighterRender : public SCompoundWidget
{
public:
	SLATE_BEGIN_ARGS(SOpenStanceFighterRender)
		: _BodyType(EOpenStanceBodyType::Compact)
		, _Sex(EOpenStanceSex::Male)
		, _FaceLeft(false)
	{
	}
		SLATE_ATTRIBUTE(EOpenStanceBodyType, BodyType)
		SLATE_ATTRIBUTE(EOpenStanceSex, Sex)
		/** The premade fighter's portrait key (OpenStanceMenuContent::GetPortraitKey); empty shows the plain build. */
		SLATE_ATTRIBUTE(FString, PortraitKey)
		/** Turn toward the left of the screen (the right-hand, Hong, panel). */
		SLATE_ARGUMENT(bool, FaceLeft)
		/** The world the studio is built in (the screen's). */
		SLATE_ARGUMENT(TWeakObjectPtr<UWorld>, World)
		SLATE_NAMED_SLOT(FArguments, Fallback)
	SLATE_END_ARGS()

	void Construct(const FArguments& InArgs);
	virtual ~SOpenStanceFighterRender() override;

	virtual void Tick(const FGeometry& AllottedGeometry, const double InCurrentTime, const float InDeltaTime) override;

private:
	TAttribute<EOpenStanceBodyType> BodyType;
	TAttribute<EOpenStanceSex> Sex;
	TAttribute<FString> PortraitKey;
	TStrongObjectPtr<UOpenStanceFighterStudio> Studio;
	FSlateBrush Brush;
	float Seconds = 0.0f;
};
