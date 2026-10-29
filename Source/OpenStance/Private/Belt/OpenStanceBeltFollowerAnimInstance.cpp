#include "Belt/OpenStanceBeltFollowerAnimInstance.h"

#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"

void FOpenStanceBeltFollowerProxy::PreUpdate(UAnimInstance* InAnimInstance, float DeltaSeconds)
{
	FAnimInstanceProxy::PreUpdate(InAnimInstance, DeltaSeconds);

	const UOpenStanceBeltFollowerAnimInstance* Instance = Cast<UOpenStanceBeltFollowerAnimInstance>(InAnimInstance);
	const USkeletalMeshComponent* LeaderComponent = Instance ? Instance->Leader.Get() : nullptr;
	const USkeletalMeshComponent* FollowerComponent = InAnimInstance ? InAnimInstance->GetSkelMeshComponent() : nullptr;
	if (!LeaderComponent || !FollowerComponent || !LeaderComponent->GetSkeletalMeshAsset() || !FollowerComponent->GetSkeletalMeshAsset())
	{
		LeaderComponentSpace.Reset();
		FollowerToLeader.Reset();
		MappedLeaderMesh.Reset();
		MappedFollowerMesh.Reset();
		return;
	}

	const FReferenceSkeleton& LeaderRef = LeaderComponent->GetSkeletalMeshAsset()->GetRefSkeleton();
	const FReferenceSkeleton& FollowerRef = FollowerComponent->GetSkeletalMeshAsset()->GetRefSkeleton();
	if (FollowerToLeader.Num() != FollowerRef.GetNum()
		|| MappedLeaderMesh.Get() != LeaderComponent->GetSkeletalMeshAsset()
		|| MappedFollowerMesh.Get() != FollowerComponent->GetSkeletalMeshAsset())
	{
		MappedLeaderMesh = LeaderComponent->GetSkeletalMeshAsset();
		MappedFollowerMesh = FollowerComponent->GetSkeletalMeshAsset();
		FollowerToLeader.SetNumUninitialized(FollowerRef.GetNum());
		for (int32 i = 0; i < FollowerRef.GetNum(); ++i)
		{
			FollowerToLeader[i] = LeaderRef.FindBoneIndex(FollowerRef.GetBoneName(i));
		}
	}
	LeaderComponentSpace = LeaderComponent->GetComponentSpaceTransforms();
}

bool FOpenStanceBeltFollowerProxy::Evaluate(FPoseContext& Output)
{
	Output.ResetToRefPose();
	if (LeaderComponentSpace.IsEmpty())
	{
		return true;
	}

	const FBoneContainer& Bones = Output.Pose.GetBoneContainer();
	const FReferenceSkeleton& Ref = Bones.GetReferenceSkeleton();
	const TArray<FTransform>& RefPose = Ref.GetRefBonePose();

	// component-space pose of every follower bone: copied where the leader has the bone, otherwise reference pose on its parent
	TArray<FTransform> ComponentSpace;
	ComponentSpace.SetNumUninitialized(Ref.GetNum());
	for (int32 i = 0; i < Ref.GetNum(); ++i)
	{
		const int32 LeaderBone = FollowerToLeader.IsValidIndex(i) ? FollowerToLeader[i] : INDEX_NONE;
		if (LeaderBone != INDEX_NONE && LeaderComponentSpace.IsValidIndex(LeaderBone))
		{
			ComponentSpace[i] = LeaderComponentSpace[LeaderBone];
		}
		else
		{
			const int32 Parent = Ref.GetParentIndex(i);
			ComponentSpace[i] = Parent == INDEX_NONE ? RefPose[i] : RefPose[i] * ComponentSpace[Parent];
		}
	}

	for (FCompactPoseBoneIndex Compact : Output.Pose.ForEachBoneIndex())
	{
		const int32 Mesh = Bones.MakeMeshPoseIndex(Compact).GetInt();
		const int32 Parent = Ref.GetParentIndex(Mesh);
		Output.Pose[Compact] = Parent == INDEX_NONE ? ComponentSpace[Mesh] : ComponentSpace[Mesh].GetRelativeTransform(ComponentSpace[Parent]);
		Output.Pose[Compact].NormalizeRotation();
	}
	return true;
}

void UOpenStanceBeltFollowerAnimInstance::SetLeader(USkeletalMeshComponent* InLeader)
{
	if (USkeletalMeshComponent* Follower = GetSkelMeshComponent())
	{
		if (USkeletalMeshComponent* PreviousLeader = Leader.Get())
		{
			Follower->RemoveTickPrerequisiteComponent(PreviousLeader);
		}
		// A component cannot be its own animation source or tick prerequisite.
		if (InLeader == Follower)
		{
			InLeader = nullptr;
		}
		if (InLeader)
		{
			Follower->AddTickPrerequisiteComponent(InLeader); // leader poses first, so the copy is not a frame late
		}
	}
	Leader = InLeader;
}

FAnimInstanceProxy* UOpenStanceBeltFollowerAnimInstance::CreateAnimInstanceProxy()
{
	return new FOpenStanceBeltFollowerProxy(this);
}

void UOpenStanceBeltFollowerAnimInstance::DestroyAnimInstanceProxy(FAnimInstanceProxy* InProxy)
{
	delete static_cast<FOpenStanceBeltFollowerProxy*>(InProxy);
}
