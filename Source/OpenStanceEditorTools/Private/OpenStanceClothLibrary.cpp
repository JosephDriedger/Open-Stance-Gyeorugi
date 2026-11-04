#include "OpenStanceClothLibrary.h"

#include "ClothingAsset.h"
#include "ClothingAssetFactoryInterface.h"
#include "ClothingSystemEditorInterfaceModule.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Modules/ModuleManager.h"
#include "PhysicsEngine/PhysicsAsset.h"
#include "PhysicsEngine/SkeletalBodySetup.h"
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

	// Max Distance from the height rule, pinned outside the box. It is written as an enabled painted mask: ApplyParameterMasks
	// clears the physical mesh's weight maps and rebuilds them from the masks, so a value written straight into
	// PhysicalMeshData is wiped and every particle stays kinematic (the cloth then just follows the skinning).
	FClothLODDataCommon& Lod = Asset->LodData[0];
	FClothPhysicalMeshData& PhysMesh = Lod.PhysicalMeshData;
	Lod.PointWeightMaps.RemoveAll([](const FPointWeightMap& Mask)
	{
		return Mask.CurrentTarget == (uint8)EWeightMapTargetCommon::MaxDistance;
	});
	FPointWeightMap& MaxDistances = Lod.PointWeightMaps.AddDefaulted_GetRef();
	MaxDistances.Name = TEXT("MaxDistance");
	MaxDistances.CurrentTarget = (uint8)EWeightMapTargetCommon::MaxDistance;
	MaxDistances.bEnabled = true;
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
	// Read back what the simulation will use.
	int32 Applied = 0;
	if (const FPointWeightMap* Final = Asset->LodData[0].PhysicalMeshData.FindWeightMap(EWeightMapTargetCommon::MaxDistance))
	{
		for (const float Value : Final->Values)
		{
			Applied += Value > 0.1f ? 1 : 0;
		}
	}
	return FString::Printf(TEXT("%d sim verts, %d dynamic (%d after masks applied)"), NumVerts, NumDynamic, Applied);
}

FString UOpenStanceClothLibrary::InflateCapsules(UPhysicsAsset* PhysicsAsset, const TArray<FString>& BonePrefixes, float Delta)
{
	if (!PhysicsAsset)
	{
		return TEXT("ERROR: no physics asset");
	}
	PhysicsAsset->Modify();
	TArray<FString> Grown;
	for (USkeletalBodySetup* Setup : PhysicsAsset->SkeletalBodySetups)
	{
		if (!Setup)
		{
			continue;
		}
		const FString Bone = Setup->BoneName.ToString();
		if (!BonePrefixes.ContainsByPredicate([&Bone](const FString& Prefix) { return Bone.StartsWith(Prefix); }))
		{
			continue;
		}
		Setup->Modify();
		for (FKSphylElem& Capsule : Setup->AggGeom.SphylElems)
		{
			Grown.Add(FString::Printf(TEXT("%s %.1f->%.1f"), *Bone, Capsule.Radius, Capsule.Radius + Delta));
			Capsule.Radius += Delta;
		}
		for (FKSphereElem& Sphere : Setup->AggGeom.SphereElems)
		{
			Grown.Add(FString::Printf(TEXT("%s sphere %.1f->%.1f"), *Bone, Sphere.Radius, Sphere.Radius + Delta));
			Sphere.Radius += Delta;
		}
		Setup->InvalidatePhysicsData();
		Setup->CreatePhysicsMeshes();
	}
	PhysicsAsset->MarkPackageDirty();
	return FString::Join(Grown, TEXT(", "));
}

FString UOpenStanceClothLibrary::DescribeClothSimulation(USkeletalMeshComponent* Component)
{
	if (!Component)
	{
		return TEXT("no component");
	}
	static TMap<TWeakObjectPtr<USkeletalMeshComponent>, TArray<FVector3f>> Previous;
	// Stalls until this frame's cloth task finishes, so the data is complete.
	const TMap<int32, FClothSimulData>& Data = Component->GetCurrentClothingData_AnyThread();
	TArray<FVector3f> Now;
	for (const TPair<int32, FClothSimulData>& Pair : Data)
	{
		// Simulation positions are in the sim space given by the data's transform; bring them to component space.
		const FTransform ToComponent = Pair.Value.Transform * Pair.Value.ComponentRelativeTransform;
		for (const FVector3f& Position : Pair.Value.Positions)
		{
			Now.Add(FVector3f(ToComponent.TransformPosition(FVector(Position))));
		}
	}
	float MinZ = Now.Num() ? TNumericLimits<float>::Max() : 0.0f;
	float MaxMove = 0.0f;
	const TArray<FVector3f>* Last = Previous.Find(Component);
	for (int32 Index = 0; Index < Now.Num(); ++Index)
	{
		MinZ = FMath::Min(MinZ, Now[Index].Z);
		if (Last && Last->Num() == Now.Num())
		{
			MaxMove = FMath::Max(MaxMove, FVector3f::Distance(Now[Index], (*Last)[Index]));
		}
	}
	Previous.Add(Component, Now);
	return FString::Printf(TEXT("%d assets, %d particles, min z %.1f, max move %.2f cm, sim suspended %s, cloth disabled %s, blend weight %.2f, render LOD %d"),
		Data.Num(), Now.Num(), MinZ, MaxMove, Component->IsClothingSimulationSuspended() ? TEXT("yes") : TEXT("no"),
		Component->bDisableClothSimulation ? TEXT("yes") : TEXT("no"), Component->ClothBlendWeight, Component->GetPredictedLODLevel());
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
		// The renderer can only show the simulation where the section has mesh-to-mesh mapping data.
		Flags.Add(Section.HasClothingData()
			? FString::Printf(TEXT("cloth (%d mapped verts)"), Section.ClothMappingDataLODs.Num() ? Section.ClothMappingDataLODs[0].Num() : 0)
			: TEXT("-"));
	}
	return FString::Printf(TEXT("%d sections: [%s], %d clothing assets"), LodModel.Sections.Num(),
		*FString::Join(Flags, TEXT(", ")), Mesh->GetMeshClothingAssets().Num());
}
