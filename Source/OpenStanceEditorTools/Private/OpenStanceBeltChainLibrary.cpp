#include "OpenStanceBeltChainLibrary.h"

#include "AssetRegistry/AssetRegistryModule.h"
#include "Engine/SkeletalMesh.h"
#include "UObject/Package.h"
#include "PhysicsEngine/BodySetup.h"
#include "PhysicsEngine/ConstraintInstance.h"
#include "PhysicsEngine/PhysicsAsset.h"
#include "PhysicsEngine/PhysicsConstraintTemplate.h"
#include "PhysicsEngine/SkeletalBodySetup.h"
#include "ReferenceSkeleton.h"

namespace OpenStanceBelt
{
	/** Transform of a bone relative to its parent, from the reference pose. */
	static FTransform LocalRef(const FReferenceSkeleton& Ref, int32 Bone)
	{
		return Ref.GetRefBonePose()[Bone];
	}

	/** Capsule from the bone's origin towards a point given in the bone's own space. */
	static FKSphylElem MakeCapsule(const FVector& ToLocal, float RadiusCm)
	{
		const float Span = ToLocal.Size();
		FKSphylElem Capsule;
		Capsule.Radius = RadiusCm;
		Capsule.Length = FMath::Max(0.0f, Span - 2.0f * RadiusCm);
		Capsule.Center = ToLocal * 0.5f;
		// Sphyls lie along Z; turn Z onto the bone-to-target direction
		Capsule.Rotation = FQuat::FindBetweenNormals(FVector::ZAxisVector, ToLocal.GetSafeNormal()).Rotator();
		return Capsule;
	}

	/** Position of descendant-or-child bone `Target` in the space of `Bone` using reference poses. */
	static FVector PointInBoneSpace(const FReferenceSkeleton& Ref, int32 Bone, int32 Target)
	{
		FTransform Accum = FTransform::Identity;
		for (int32 Current = Target; Current != INDEX_NONE && Current != Bone; Current = Ref.GetParentIndex(Current))
		{
			Accum = Accum * LocalRef(Ref, Current);
		}
		return Accum.GetTranslation();
	}
}

UPhysicsAsset* UOpenStanceBeltChainLibrary::CreateEmptyPhysicsAsset(const FString& PackagePath, const FString& AssetName)
{
	const FString PackageName = PackagePath / AssetName;
	if (FPackageName::DoesPackageExist(PackageName))
	{
		return nullptr;
	}
	UPackage* Package = CreatePackage(*PackageName);
	UPhysicsAsset* Asset = NewObject<UPhysicsAsset>(Package, *AssetName, RF_Public | RF_Standalone | RF_Transactional);
	if (Asset)
	{
		FAssetRegistryModule::AssetCreated(Asset);
		Package->MarkPackageDirty();
	}
	return Asset;
}

TArray<FString> UOpenStanceBeltChainLibrary::ListBones(USkeletalMesh* Mesh)
{
	TArray<FString> Result;
	if (!Mesh)
	{
		return Result;
	}
	const FReferenceSkeleton& Ref = Mesh->GetRefSkeleton();
	TArray<FTransform> ComponentSpace;
	ComponentSpace.SetNum(Ref.GetNum());
	for (int32 i = 0; i < Ref.GetNum(); ++i)
	{
		const int32 Parent = Ref.GetParentIndex(i);
		ComponentSpace[i] = Parent == INDEX_NONE ? Ref.GetRefBonePose()[i] : Ref.GetRefBonePose()[i] * ComponentSpace[Parent];
		const FVector P = ComponentSpace[i].GetTranslation();
		Result.Add(FString::Printf(TEXT("%s|%s|%.3f|%.3f|%.3f"), *Ref.GetBoneName(i).ToString(),
			Parent == INDEX_NONE ? TEXT("") : *Ref.GetBoneName(Parent).ToString(), P.X, P.Y, P.Z));
	}
	return Result;
}

TArray<FName> UOpenStanceBeltChainLibrary::FindChainBones(USkeletalMesh* Mesh, const FString& ChainPrefix)
{
	TArray<FName> Result;
	if (!Mesh)
	{
		return Result;
	}
	const FReferenceSkeleton& Ref = Mesh->GetRefSkeleton();
	for (int32 i = 0; i < Ref.GetNum(); ++i)
	{
		if (Ref.GetBoneName(i).ToString().StartsWith(ChainPrefix))
		{
			Result.Add(Ref.GetBoneName(i));
		}
	}
	return Result;
}

FString UOpenStanceBeltChainLibrary::BuildBeltChainPhysicsAsset(USkeletalMesh* Mesh, UPhysicsAsset* PhysicsAsset,
	const TArray<FName>& BodyBones, const TArray<FName>& AimBones, const TArray<float>& BodyRadii,
	const FString& ChainPrefix, float ChainRadius, float ChainMassKg, float SwingLimitDeg,
	float LinearDamping, float AngularDamping)
{
	if (!Mesh || !PhysicsAsset)
	{
		return TEXT("ERROR: mesh or physics asset missing");
	}
	if (BodyBones.Num() != AimBones.Num() || BodyBones.Num() != BodyRadii.Num())
	{
		return TEXT("ERROR: BodyBones, AimBones and BodyRadii must be the same length");
	}
	const FReferenceSkeleton& Ref = Mesh->GetRefSkeleton();
	const TArray<FName> Chain = FindChainBones(Mesh, ChainPrefix);
	if (Chain.IsEmpty())
	{
		return FString::Printf(TEXT("ERROR: no bones start with %s"), *ChainPrefix);
	}

	PhysicsAsset->Modify();
	PhysicsAsset->SkeletalBodySetups.Empty();
	PhysicsAsset->ConstraintSetup.Empty();
	PhysicsAsset->CollisionDisableTable.Empty();

	auto AddBody = [&](FName Bone, const FKSphylElem& Capsule, bool bSimulated, float MassKg) -> int32
	{
		USkeletalBodySetup* Body = NewObject<USkeletalBodySetup>(PhysicsAsset, NAME_None, RF_Transactional);
		Body->BoneName = Bone;
		Body->CollisionTraceFlag = CTF_UseSimpleAsComplex;
		Body->AggGeom.SphylElems.Add(Capsule);
		Body->DefaultInstance.SetObjectType(ECC_PhysicsBody);
		Body->DefaultInstance.SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
		Body->PhysicsType = bSimulated ? EPhysicsType::PhysType_Default : EPhysicsType::PhysType_Kinematic;
		Body->DefaultInstance.LinearDamping = LinearDamping;
		Body->DefaultInstance.AngularDamping = AngularDamping;
		if (bSimulated)
		{
			Body->DefaultInstance.bOverrideMass = true;
			Body->DefaultInstance.SetMassOverride(MassKg, true);
		}
		return PhysicsAsset->SkeletalBodySetups.Add(Body);
	};

	// kinematic body capsules the tails collide with
	int32 BodyCount = 0;
	for (int32 i = 0; i < BodyBones.Num(); ++i)
	{
		const int32 Bone = Ref.FindBoneIndex(BodyBones[i]);
		const int32 Aim = Ref.FindBoneIndex(AimBones[i]);
		if (Bone == INDEX_NONE || Aim == INDEX_NONE)
		{
			return FString::Printf(TEXT("ERROR: bone %s or %s not in the mesh"), *BodyBones[i].ToString(), *AimBones[i].ToString());
		}
		AddBody(BodyBones[i], OpenStanceBelt::MakeCapsule(OpenStanceBelt::PointInBoneSpace(Ref, Bone, Aim), BodyRadii[i]), false, 0.0f);
		++BodyCount;
	}

	// simulated chain capsules, each running towards its child (the last one reuses the previous direction)
	TArray<int32> ChainBodyIndex;
	TMap<FName, FVector> ChainDirection; // bone-space direction towards the next link
	FVector LastDirection = FVector(0, 1, 0) * 3.0f;
	for (const FName& Name : Chain)
	{
		const int32 Bone = Ref.FindBoneIndex(Name);
		int32 Child = INDEX_NONE;
		for (int32 j = 0; j < Ref.GetNum(); ++j)
		{
			if (Ref.GetParentIndex(j) == Bone && Chain.Contains(Ref.GetBoneName(j)))
			{
				Child = j;
				break;
			}
		}
		const FVector To = Child != INDEX_NONE ? OpenStanceBelt::PointInBoneSpace(Ref, Bone, Child) : LastDirection;
		LastDirection = To;
		ChainDirection.Add(Name, To);
		ChainBodyIndex.Add(AddBody(Name, OpenStanceBelt::MakeCapsule(To, ChainRadius), true, ChainMassKg));
	}

	PhysicsAsset->UpdateBodySetupIndexMap();
	// ball joints: each chain bone to its parent bone (pelvis for the first link)
	int32 Joints = 0;
	for (const FName& Name : Chain)
	{
		const int32 Bone = Ref.FindBoneIndex(Name);
		const FName ParentName = Ref.GetBoneName(Ref.GetParentIndex(Bone));
		if (PhysicsAsset->FindBodyIndex(ParentName) == INDEX_NONE)
		{
			// first link's parent (pelvis) must exist as a body; a missing one is a setup error
			return FString::Printf(TEXT("ERROR: parent %s of %s has no body; add it to BodyBones"), *ParentName.ToString(), *Name.ToString());
		}
		UPhysicsConstraintTemplate* Joint = NewObject<UPhysicsConstraintTemplate>(PhysicsAsset, NAME_None, RF_Transactional);
		FConstraintInstance& Instance = Joint->DefaultInstance;
		Instance.ConstraintBone1 = Name;       // child
		Instance.ConstraintBone2 = ParentName; // parent
		Instance.SetDisableCollision(true);
		Instance.SetLinearXLimit(LCM_Locked, 0);
		Instance.SetLinearYLimit(LCM_Locked, 0);
		Instance.SetLinearZLimit(LCM_Locked, 0);
		Instance.SetAngularSwing1Limit(ACM_Limited, SwingLimitDeg);
		Instance.SetAngularSwing2Limit(ACM_Limited, SwingLimitDeg);
		Instance.SetAngularTwistLimit(ACM_Locked, 0.0f);
		// frames: the constraint's X axis is its twist axis, so turn X onto the link's own direction in the child
		// frame; the parent frame is the same frame placed through the child's reference transform
		const FQuat AlignX = FQuat::FindBetweenNormals(FVector::XAxisVector, ChainDirection[Name].GetSafeNormal());
		const FTransform ChildFrame(AlignX);
		Instance.SetRefFrame(EConstraintFrame::Frame1, ChildFrame);
		Instance.SetRefFrame(EConstraintFrame::Frame2, ChildFrame * OpenStanceBelt::LocalRef(Ref, Bone));
		// the runtime takes its limits from the template's default profile (and saving overwrites the instance's
		// profile with it), so copy the settings there or they are silently lost
		Joint->SetDefaultProfile(Instance);
		PhysicsAsset->ConstraintSetup.Add(Joint);
		++Joints;
	}

	PhysicsAsset->UpdateBodySetupIndexMap();
	PhysicsAsset->UpdateBoundsBodiesArray();
	// tails touch only the body: no collision between any two chain bodies
	for (int32 a = 0; a < ChainBodyIndex.Num(); ++a)
	{
		for (int32 b = a + 1; b < ChainBodyIndex.Num(); ++b)
		{
			PhysicsAsset->DisableCollision(ChainBodyIndex[a], ChainBodyIndex[b]);
		}
	}
	PhysicsAsset->SetPreviewMesh(Mesh);
	Mesh->SetPhysicsAsset(PhysicsAsset);
	PhysicsAsset->MarkPackageDirty();
	Mesh->MarkPackageDirty();
	return FString::Printf(TEXT("%d collision bodies, %d chain bodies, %d joints"), BodyCount, Chain.Num(), Joints);
}
