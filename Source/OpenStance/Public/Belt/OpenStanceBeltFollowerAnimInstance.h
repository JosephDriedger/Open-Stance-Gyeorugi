#pragma once

#include "CoreMinimal.h"
#include "Animation/AnimInstance.h"
#include "Animation/AnimInstanceProxy.h"
#include "OpenStanceBeltFollowerAnimInstance.generated.h"

class USkeletalMeshComponent;
class USkeletalMesh;

/** Worker-thread side: copies the leader's pose by bone name, leaves unmatched bones (the belt chain) at rest. */
struct FOpenStanceBeltFollowerProxy : public FAnimInstanceProxy
{
	FOpenStanceBeltFollowerProxy() = default;
	explicit FOpenStanceBeltFollowerProxy(UAnimInstance* InInstance) : FAnimInstanceProxy(InInstance) {}

	virtual void PreUpdate(UAnimInstance* InAnimInstance, float DeltaSeconds) override;
	virtual bool Evaluate(FPoseContext& Output) override;

	TArray<FTransform> LeaderComponentSpace;
	/** Follower mesh bone index -> leader mesh bone index (INDEX_NONE where the leader has no such bone). */
	TArray<int32> FollowerToLeader;
	TWeakObjectPtr<USkeletalMesh> MappedLeaderMesh;
	TWeakObjectPtr<USkeletalMesh> MappedFollowerMesh;
};

/**
 * Anim instance for a body-following mesh that carries simulated bones, such as the belt-tail chain.
 *
 * Leader Pose overwrites a follower's bones every frame, so physics bodies on a follower never simulate.
 * This instance does the same copy by bone name, but as ordinary animation output, so the physics asset's
 * simulated bodies blend on top of it. Bones the leader does not have (belt_l_01..) stay at their reference
 * pose relative to their parent until simulation moves them.
 *
 * Set it as the follower component's AnimClass (single-node and Leader Pose off), then call SetLeader after the
 * component is registered. Both components must share the same world transform, as with Leader Pose.
 */
UCLASS(Transient)
class OPENSTANCE_API UOpenStanceBeltFollowerAnimInstance : public UAnimInstance
{
	GENERATED_BODY()

public:
	UFUNCTION(BlueprintCallable, Category = "Open Stance|Belt")
	void SetLeader(USkeletalMeshComponent* InLeader);

	UFUNCTION(BlueprintPure, Category = "Open Stance|Belt")
	USkeletalMeshComponent* GetLeader() const { return Leader.Get(); }

protected:
	virtual FAnimInstanceProxy* CreateAnimInstanceProxy() override;
	virtual void DestroyAnimInstanceProxy(FAnimInstanceProxy* InProxy) override;

private:
	friend struct FOpenStanceBeltFollowerProxy;
	TWeakObjectPtr<USkeletalMeshComponent> Leader;
};
