#include "OpenStanceClothLibrary.h"

#include "ClothingAsset.h"
#include "ClothingAssetFactoryInterface.h"
#include "ClothingSystemEditorInterfaceModule.h"
#include "Engine/SkeletalMesh.h"
#include "Modules/ModuleManager.h"
#include "PhysicsEngine/PhysicsAsset.h"
#include "PointWeightMap.h"
#include "Rendering/SkeletalMeshLODModel.h"
#include "Rendering/SkeletalMeshModel.h"
#include "SkeletalMeshClothingSystemUtilities.h"

namespace OpenStanceCloth
{
	static float SmoothStep(float Edge0, float Edge1, float X)
	{
		if (FMath::IsNearlyEqual(Edge0, Edge1))
		{
			return X <= Edge1 ? 1.0f : 0.0f;
		}
		const float T = FMath::Clamp((X - Edge0) / (Edge1 - Edge0), 0.0f, 1.0f);
		return T * T * (3.0f - 2.0f * T);
	}
}

void UOpenStanceClothLibrary::RemoveUnusedClothingAssets(USkeletalMesh* Mesh)
{
	// Unbinding a section keeps its clothing asset in the mesh; drop assets no section refers to
	if (!Mesh || !Mesh->GetImportedModel())
	{
		return;
	}
	TSet<FGuid> UsedGuids;
	for (const FSkeletalMeshLODModel& Lod : Mesh->GetImportedModel()->LODModels)
	{
		for (const FSkelMeshSection& Section : Lod.Sections)
		{
			if (Section.HasClothingData())
			{
				UsedGuids.Add(Section.ClothingData.AssetGuid);
			}
		}
	}
	Mesh->GetMeshClothingAssets().RemoveAll([&UsedGuids](const TObjectPtr<UClothingAssetBase>& Asset)
	{
		return !Asset || !UsedGuids.Contains(Asset->GetAssetGuid());
	});
}

FString UOpenStanceClothLibrary::SetupSectionCloth(USkeletalMesh* Mesh, int32 SectionIndex, UPhysicsAsset* PhysicsAsset,
	float PinZ, float FreeZ, float MaxDistance, FVector BoxMin, FVector BoxMax)
{
	if (!Mesh || !Mesh->GetImportedModel() || !Mesh->GetImportedModel()->LODModels.IsValidIndex(0))
	{
		return TEXT("ERROR: invalid mesh");
	}
	const FSkeletalMeshLODModel& LodModel = Mesh->GetImportedModel()->LODModels[0];
	if (!LodModel.Sections.IsValidIndex(SectionIndex))
	{
		return FString::Printf(TEXT("ERROR: section %d out of range (%d sections)"), SectionIndex, LodModel.Sections.Num());
	}

	Mesh->Modify();
	if (LodModel.Sections[SectionIndex].HasClothingData())
	{
		FScopedSkeletalMeshPostEditChange RemoveScope(Mesh);
		Mesh->RemoveClothingAsset(0, SectionIndex);
	}

	FScopedSkeletalMeshPostEditChange EditScope(Mesh);

	FSkeletalMeshClothBuildParams Params;
	Params.AssetName = FString::Printf(TEXT("%s_Cloth_%d"), *Mesh->GetName(), SectionIndex);
	Params.LodIndex = 0;
	Params.SourceSection = SectionIndex;
	Params.bRemoveFromMesh = false;
	Params.PhysicsAsset = PhysicsAsset;

	FClothingSystemEditorInterfaceModule& ClothingEditorModule =
		FModuleManager::LoadModuleChecked<FClothingSystemEditorInterfaceModule>("ClothingSystemEditorInterface");
	UClothingAssetFactoryBase* Factory = ClothingEditorModule.GetClothingAssetFactory();
	UClothingAssetCommon* Asset = Factory ? Cast<UClothingAssetCommon>(Factory->CreateFromSkeletalMesh(Mesh, Params)) : nullptr;
	if (!Asset || Asset->LodData.Num() == 0)
	{
		return TEXT("ERROR: clothing asset creation failed");
	}
	Mesh->AddClothingAsset(Asset);

	// Max Distance from the height rule, pinned outside the box
	FClothPhysicalMeshData& PhysMesh = Asset->LodData[0].PhysicalMeshData;
	FPointWeightMap& MaxDistances = PhysMesh.FindOrAddWeightMap(EWeightMapTargetCommon::MaxDistance);
	const int32 NumVerts = PhysMesh.Vertices.Num();
	MaxDistances.Values.SetNum(NumVerts);
	const FBox Box(BoxMin, BoxMax);
	int32 NumDynamic = 0;
	for (int32 Index = 0; Index < NumVerts; ++Index)
	{
		const FVector Position(PhysMesh.Vertices[Index]);
		float Value = 0.0f;
		if (Box.IsInsideOrOn(Position))
		{
			// PinZ is above FreeZ: weight rises from 0 at PinZ to 1 at FreeZ as the vertex gets lower
			Value = MaxDistance * OpenStanceCloth::SmoothStep(PinZ, FreeZ, Position.Z);
		}
		MaxDistances.Values[Index] = Value;
		NumDynamic += Value > 0.1f ? 1 : 0;
	}
	Asset->PhysicsAsset = PhysicsAsset;
	Asset->ApplyParameterMasks(true, true);

	FString Error;
	if (!FSkeletalMeshClothingSystemUtilities::AssignClothingToSection(Mesh, Asset, 0, SectionIndex, 0, &Error))
	{
		return FString::Printf(TEXT("ERROR: could not assign cloth to section: %s"), *Error);
	}
	RemoveUnusedClothingAssets(Mesh);
	Mesh->MarkPackageDirty();
	return FString::Printf(TEXT("%d sim verts, %d dynamic"), NumVerts, NumDynamic);
}

void UOpenStanceClothLibrary::RemoveAllCloth(USkeletalMesh* Mesh)
{
	if (!Mesh || !Mesh->GetImportedModel() || !Mesh->GetImportedModel()->LODModels.IsValidIndex(0))
	{
		return;
	}
	Mesh->Modify();
	FScopedSkeletalMeshPostEditChange EditScope(Mesh);
	const int32 NumSections = Mesh->GetImportedModel()->LODModels[0].Sections.Num();
	for (int32 Section = 0; Section < NumSections; ++Section)
	{
		if (Mesh->GetImportedModel()->LODModels[0].Sections[Section].HasClothingData())
		{
			Mesh->RemoveClothingAsset(0, Section);
		}
	}
	RemoveUnusedClothingAssets(Mesh);
	Mesh->MarkPackageDirty();
}

FString UOpenStanceClothLibrary::DescribeCloth(USkeletalMesh* Mesh)
{
	if (!Mesh || !Mesh->GetImportedModel() || !Mesh->GetImportedModel()->LODModels.IsValidIndex(0))
	{
		return TEXT("no mesh");
	}
	const FSkeletalMeshLODModel& LodModel = Mesh->GetImportedModel()->LODModels[0];
	TArray<FString> Flags;
	for (const FSkelMeshSection& Section : LodModel.Sections)
	{
		Flags.Add(Section.HasClothingData() ? TEXT("cloth") : TEXT("-"));
	}
	return FString::Printf(TEXT("%d sections: [%s], %d clothing assets"), LodModel.Sections.Num(),
		*FString::Join(Flags, TEXT(", ")), Mesh->GetMeshClothingAssets().Num());
}
