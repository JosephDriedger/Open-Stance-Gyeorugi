#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "OpenStanceClothLibrary.generated.h"

class USkeletalMesh;
class UPhysicsAsset;

/**
 * Editor scripting for cloth physics (Python: unreal.OpenStanceClothLibrary).
 *
 * Creates Chaos cloth on a skeletal mesh section and fills its Max Distance map from a height rule,
 * so garments can be set up from Tools/Unreal scripts instead of hand-painting in the mesh editor.
 * Coordinates are mesh space in centimetres (Z up, character standing at the origin).
 */
UCLASS()
class UOpenStanceClothLibrary : public UBlueprintFunctionLibrary
{
	GENERATED_BODY()

public:
	/**
	 * Replace any cloth on SectionIndex (LOD 0) with a new clothing asset.
	 *
	 * Max Distance per simulation vertex = MaxDistance * smoothstep(PinZ -> FreeZ) on height, so
	 * vertices at or above PinZ stay skinned and vertices at or below FreeZ may move MaxDistance cm.
	 * Vertices outside the [BoxMin, BoxMax] box are pinned (use it to limit cloth to e.g. belt tails).
	 * PhysicsAsset provides the collision capsules (use the character's body physics asset).
	 * Returns a summary ("<verts> sim verts, <n> dynamic") or an error message starting with "ERROR".
	 */
	UFUNCTION(BlueprintCallable, Category = "Open Stance|Cloth")
	static FString SetupSectionCloth(USkeletalMesh* Mesh, int32 SectionIndex, UPhysicsAsset* PhysicsAsset,
		float PinZ, float FreeZ, float MaxDistance, FVector BoxMin, FVector BoxMax);

	/** Remove cloth from every section of LOD 0. */
	UFUNCTION(BlueprintCallable, Category = "Open Stance|Cloth")
	static void RemoveAllCloth(USkeletalMesh* Mesh);

	/** Number of sections on LOD 0 and whether each uses cloth, e.g. "2 sections: [cloth, -]". */
	UFUNCTION(BlueprintCallable, Category = "Open Stance|Cloth")
	static FString DescribeCloth(USkeletalMesh* Mesh);

private:
	static void RemoveUnusedClothingAssets(USkeletalMesh* Mesh);
};
