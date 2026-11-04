#include "Menu/Slate/SOpenStanceFighterRender.h"

#include "Engine/TextureRenderTarget2D.h"
#include "Engine/World.h"
#include "HAL/IConsoleManager.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Menu/OpenStanceFighterStudio.h"
#include "Widgets/Images/SImage.h"
#include "Widgets/Layout/SScaleBox.h"

void SOpenStanceFighterRender::Construct(const FArguments& InArgs)
{
	BodyType = InArgs._BodyType;
	Sex = InArgs._Sex;
	UWorld* World = InArgs._World.Get();
	if (World && !World->IsNetMode(NM_DedicatedServer) && FApp::CanEverRender())
	{
		Studio.Reset(NewObject<UOpenStanceFighterStudio>());
		if (!Studio->Init(World, InArgs._FaceLeft))
		{
			Studio->Shutdown();
			Studio.Reset();
		}
	}
	if (!Studio.IsValid())
	{
		ChildSlot[InArgs._Fallback.Widget];
		return;
	}

	Studio->SetFighter(BodyType.Get(), Sex.Get());
	Studio->Update(0.0f);
	static IConsoleVariable* Raw = IConsoleManager::Get().FindConsoleVariable(TEXT("os.FighterPortraitRaw"));
	Brush.SetResourceObject(Raw && Raw->GetInt() ? static_cast<UObject*>(Studio->GetColorTarget()) : static_cast<UObject*>(Studio->GetMaterial()));
	Brush.ImageSize = FVector2D(UOpenStanceFighterStudio::Width, UOpenStanceFighterStudio::Height);
	Brush.DrawAs = ESlateBrushDrawType::Image;
	ChildSlot
	[
		SNew(SScaleBox)
		.Stretch(EStretch::ScaleToFit)
		[
			SNew(SImage).Image(&Brush)
		]
	];
}

SOpenStanceFighterRender::~SOpenStanceFighterRender()
{
	if (Studio.IsValid())
	{
		Studio->Shutdown();
	}
}

void SOpenStanceFighterRender::Tick(const FGeometry& AllottedGeometry, const double InCurrentTime, const float InDeltaTime)
{
	SCompoundWidget::Tick(AllottedGeometry, InCurrentTime, InDeltaTime);
	if (Studio.IsValid())
	{
		Seconds += InDeltaTime;
		Studio->SetFighter(BodyType.Get(), Sex.Get());
		Studio->Update(Seconds);
	}
}

static TAutoConsoleVariable<int32> CVarFighterPortraitRaw(TEXT("os.FighterPortraitRaw"), 0,
	TEXT("Debug: 1 draws menu fighter portraits from the raw colour capture, without the cut-out material."));
