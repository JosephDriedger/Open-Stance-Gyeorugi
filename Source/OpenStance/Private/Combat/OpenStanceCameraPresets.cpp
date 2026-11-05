#include "Combat/OpenStanceCameraPresets.h"

namespace
{
	using A = EOpenStanceCameraAnchor;

	TArray<FOpenStanceCameraPreset> MakePresets()
	{
		// Chosen from the gameplay captures (Saved/Screenshots/CameraAngles, 2026-11-04): Match is "Behind Offset
		// ThreeQuarter", behind the fighter and out to the side so the opponent is never hidden and kicks keep their depth.
		return {
			{ TEXT("Match"), A::BehindPlayer, 360.0f, 170.0f, 200.0f, 75.0f, 55.0f,
				TEXT("combat camera: behind and to the side of your fighter, stick up goes toward the opponent") },
			{ TEXT("SideBroadcast"), A::Midpoint, 0.0f, 520.0f, 135.0f, 100.0f, 40.0f,
				TEXT("replays: side-on at chest height, like World Taekwondo TV coverage") },
			{ TEXT("SideHigh"), A::Midpoint, 0.0f, 560.0f, 260.0f, 85.0f, 40.0f,
				TEXT("replays: side-on from above the coaches' chairs, shows the distance and footwork") },
			{ TEXT("ThreeQuarterCorner"), A::Midpoint, -330.0f, 420.0f, 240.0f, 95.0f, 42.0f,
				TEXT("replays and video packages: from the corner behind your fighter's shoulder") },
			{ TEXT("BehindShoulder"), A::BehindPlayer, 320.0f, 60.0f, 200.0f, 105.0f, 90.0f,
				TEXT("replays: straight behind your fighter, wide (the Milestone 1 combat camera)") },
			{ TEXT("BehindClose"), A::BehindPlayer, 230.0f, 70.0f, 175.0f, 115.0f, 55.0f,
				TEXT("video packages: tight over the shoulder, for entrances and the moment before a kick") },
			{ TEXT("BehindLow"), A::BehindPlayer, 300.0f, 60.0f, 140.0f, 110.0f, 50.0f,
				TEXT("video packages: low behind your fighter, makes head kicks look tall") },
			{ TEXT("BehindHighWide"), A::BehindPlayer, 380.0f, 40.0f, 320.0f, 80.0f, 50.0f,
				TEXT("replays: high behind, the whole exchange and the boundary in view") },
			{ TEXT("HighJudge"), A::Midpoint, 0.0f, 420.0f, 380.0f, 60.0f, 50.0f,
				TEXT("replays and the referee's review: high side view of both fighters' feet and the mat") },
		};
	}
}

const TArray<FOpenStanceCameraPreset>& OpenStanceCameraPresets::All()
{
	static const TArray<FOpenStanceCameraPreset> Presets = MakePresets();
	return Presets;
}

const FOpenStanceCameraPreset* OpenStanceCameraPresets::Find(FName Name)
{
	return All().FindByPredicate([Name](const FOpenStanceCameraPreset& Preset) { return Preset.Name.IsEqual(Name, ENameCase::IgnoreCase); });
}

const FOpenStanceCameraPreset& OpenStanceCameraPresets::Match()
{
	return All()[0];
}

void OpenStanceCameraPresets::Pose(const FOpenStanceCameraPreset& Preset, const FVector& Player, const FVector& Opponent,
	FVector& OutPosition, FRotator& OutRotation)
{
	FVector Line = Opponent - Player;
	Line.Z = 0.0;
	Line = Line.GetSafeNormal(UE_SMALL_NUMBER, FVector::ForwardVector);
	// Right of the line, as the fighter sees it: Unreal is left-handed, so with X forward Y is to the right.
	const FVector Right(-Line.Y, Line.X, 0.0);
	const FVector Mid = (Player + Opponent) * 0.5;
	const FVector Floor = Preset.Anchor == EOpenStanceCameraAnchor::BehindPlayer ? Player - Line * Preset.AlongCm : Mid + Line * Preset.AlongCm;
	OutPosition = Floor + Right * Preset.SideCm + FVector(0.0, 0.0, Preset.HeightCm);
	OutRotation = (Mid + FVector(0.0, 0.0, Preset.LookHeightCm) - OutPosition).Rotation();
}
