#pragma once

#include "CoreMinimal.h"

/**
 * The gam-jeom the game detects on its own (GDD 8.4), with editable starting values. A time or limit of 0 turns that
 * check off. Contact fouls (punch to the head, kick below the belt), Falling and holding are decided where they happen.
 */
struct OPENSTANCE_API FOpenStancePenaltyTuning
{
	/** The octagon is 8 m across its flats, so each edge is this far from the centre (GDD 6.3). */
	float MatApothemCm = 400.0f;

	/** Each foot sits this far ahead of and behind the fighter's centre, along its facing. */
	float FootReachCm = 30.0f;

	/** A foot is over the edge once its centre is this far past the line: the whole foot, not one touching the line. */
	float FootClearCm = 12.0f;

	/** Pushing or holding by the opponent forces a fighter out without a penalty for this long after (WT Article 14). */
	float ForcedOutGraceSeconds = 0.5f;

	/** Turning the back: facing more than this far from the opponent for longer than TurnAwaySeconds. */
	float TurnAwayDegrees = 90.0f;
	float TurnAwaySeconds = 1.0f;

	/** Crouching below Low Guard's posture for longer than this without attacking. */
	float CrouchSeconds = 1.0f;

	/** A leg held above hip height outside its own technique for longer than this (WT Article 14, 4.1.5). */
	float LegLiftSeconds = 3.0f;

	/** No technique of either fighter reaching its active phase: GONG-GYEOK at the call, a gam-jeom at the limit. */
	float PassivityCallSeconds = 3.0f;
	float PassivitySeconds = 6.0f;

	/** Over the passivity window, net movement away from the opponent beyond this is "the one who moved back". */
	float RetreatMarginCm = 50.0f;

	/** The referee stops play to declare a gam-jeom: kal-yeo, gam-jeom, kye-sok. The clock holds meanwhile. */
	float StopSeconds = 1.0f;

	/** How far past the edge a point is (negative inside), using the octagon's eight edges. */
	float GetOverhangCm(const FVector2D& Point) const
	{
		float Most = -MAX_flt;
		for (int32 Edge = 0; Edge < 8; ++Edge)
		{
			const float Angle = Edge * UE_PI / 4.0f;
			Most = FMath::Max(Most, static_cast<float>(Point.X * FMath::Cos(Angle) + Point.Y * FMath::Sin(Angle)));
		}
		return Most - MatApothemCm;
	}

	/** True if a foot of a fighter at Position facing Facing is wholly over the edge. */
	bool IsFootOut(const FVector2D& Position, const FVector2D& Facing) const
	{
		return GetOverhangCm(Position + Facing * FootReachCm) > FootClearCm || GetOverhangCm(Position - Facing * FootReachCm) > FootClearCm;
	}

	/** Moves a point back inside the octagon so that both feet are at least MarginCm inside the edge. */
	FVector2D KeepInside(FVector2D Point, float MarginCm) const
	{
		const float Limit = MatApothemCm - FootReachCm - MarginCm;
		for (int32 Pass = 0; Pass < 3; ++Pass)
		{
			for (int32 Edge = 0; Edge < 8; ++Edge)
			{
				const float Angle = Edge * UE_PI / 4.0f;
				const FVector2D Normal(FMath::Cos(Angle), FMath::Sin(Angle));
				const float Over = static_cast<float>(FVector2D::DotProduct(Point, Normal)) - Limit;
				if (Over > 0.0f)
				{
					Point -= Normal * Over;
				}
			}
		}
		return Point;
	}
};

/** One fighter's running penalty timers. A counted incident stays counted until its condition clears, so it scores once. */
struct OPENSTANCE_API FOpenStancePenaltyWatch
{
	float TurnedAwaySeconds = 0.0f;
	bool bTurnCounted = false;

	float CrouchedSeconds = 0.0f;
	bool bCrouchCounted = false;

	float LegRaisedSeconds = 0.0f;
	bool bLegCounted = false;

	/** Seconds since the opponent last pushed or held this fighter; large when it never has. */
	float SinceForcedSeconds = 1000.0f;

	/** Net movement toward the opponent since the passivity timer last restarted. */
	float PassivityPressureCm = 0.0f;
};
