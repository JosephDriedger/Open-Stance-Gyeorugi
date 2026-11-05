#pragma once

#include "CoreMinimal.h"

/** What a camera preset is placed from. */
enum class EOpenStanceCameraAnchor : uint8
{
	/** Behind the controlling fighter, on the line to the opponent: the stick directions match the screen (up = toward the opponent). */
	BehindPlayer,
	/** From the point between the fighters, out to the side of their line (broadcast-style views). */
	Midpoint
};

/**
 * One camera angle on a match. Every preset is placed from the two fighters' floor positions each frame, so it frames the
 * exchange wherever it moves on the mat. "Match" is the combat camera the player plays with; the others are kept for
 * instant replays and match video packages (GDD 3.4, 13) and can be previewed live with os.CameraPreset <Name>.
 * Tools/Unreal/capture_camera_angles.py photographs the same presets for comparison.
 */
struct FOpenStanceCameraPreset
{
	FName Name;
	EOpenStanceCameraAnchor Anchor = EOpenStanceCameraAnchor::BehindPlayer;
	/** BehindPlayer: how far back from the fighter. Midpoint: how far along the line toward the controlling fighter's opponent. */
	float AlongCm = 0.0f;
	/** Out to the controlling fighter's right of the line (negative: left). */
	float SideCm = 0.0f;
	float HeightCm = 0.0f;
	/** Where it looks: the point between the fighters at this height. */
	float LookHeightCm = 100.0f;
	float FieldOfViewDeg = 50.0f;
	/** What the angle is for, shown by os.CameraPreset. */
	const TCHAR* Use = TEXT("");
};

namespace OpenStanceCameraPresets
{
	/** Every preset, the match camera first. */
	OPENSTANCE_API const TArray<FOpenStanceCameraPreset>& All();

	/** The preset with this name (case-insensitive), or null. */
	OPENSTANCE_API const FOpenStanceCameraPreset* Find(FName Name);

	/** The combat camera the player plays with. */
	OPENSTANCE_API const FOpenStanceCameraPreset& Match();

	/**
	 * Places a preset. Player and Opponent are the fighters' floor positions in world space; the controlling fighter is
	 * Player. Returns the camera position and the rotation that looks at the point between the fighters.
	 */
	OPENSTANCE_API void Pose(const FOpenStanceCameraPreset& Preset, const FVector& Player, const FVector& Opponent,
		FVector& OutPosition, FRotator& OutRotation);
}
