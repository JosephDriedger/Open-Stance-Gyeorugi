#pragma once

#include "CoreMinimal.h"
#include "Combat/OpenStanceCameraPresets.h"

class FOpenStanceMatchSim;

/** What the match camera is showing (GDD 13). */
enum class EOpenStanceShot : uint8
{
	/** The combat camera the player plays with (the Match preset, framed to the exchange). */
	Combat,
	/** The opening ceremony before the first shi-jak: a wide side view of both fighters and the referee's line. */
	Ceremony,
	/** The break between rounds: high side view. */
	Break,
	/** A spinning kick scored: a 1.5 s cut to the side view, then straight back (GDD 13). */
	SpinCut,
	/** The match is over: side view while the winner is named and the fighters bow. */
	Results
};

/** Combat camera framing and shot timing. Starting values, tuned in playtests. */
struct OPENSTANCE_API FOpenStanceCameraTuning
{
	/** How long the cut on a spinning-kick score holds (GDD 13). */
	float SpinCutSeconds = 1.5f;

	/** The Match preset is written for fighters this far apart; past it the camera pulls back and rises. */
	float FramedGapCm = 200.0f;
	float PullBackPerCm = 0.8f;
	float RisePerCm = 0.3f;
	float MaxPullBackCm = 260.0f;

	/** The camera stays within this many cm of the mat's centre on each axis: inside the arena, never in a wall. */
	float ArenaHalfCm = 580.0f;

	/** With a fighter down, the camera looks this low so the fighter on the floor stays in frame. */
	float DownLookHeightCm = 45.0f;

	/** The Match preset's look height is for a 175 cm fighter; taller or shorter fighters raise or lower it. */
	float ReferenceHeightCm = 175.0f;

	/**
	 * When a fighter's head or feet would leave the frame (the arena kept the camera close, or the fighters are far
	 * apart), the camera cranes up by this much and widens by this much per step until both fit, up to MaxFieldOfViewDeg.
	 */
	float FitRaiseCm = 35.0f;
	float FitWidenDeg = 2.5f;
	float MaxFieldOfViewDeg = 80.0f;
	int32 FitSteps = 14;

	/** The share of the frame's half-width and half-height a fighter must stay inside (16:9). */
	float FrameMargin = 0.9f;
};

/** Where the camera is this frame, in the simulation's space (cm, the mat centre at the origin). */
struct OPENSTANCE_API FOpenStanceCameraFrame
{
	EOpenStanceShot Shot = EOpenStanceShot::Combat;
	FVector Position = FVector::ZeroVector;
	FRotator Rotation = FRotator::ZeroRotator;
	float FieldOfViewDeg = 55.0f;

	/** A cut: jump straight to this pose instead of easing into it. */
	bool bCut = false;
};

/**
 * Picks the match camera's shot from the simulation and frames it (GDD 13, issue 16): the behind-offset combat camera,
 * pulled back as the fighters separate and kept inside the arena; the ceremony, break and results views; and a 1.5 s cut
 * on every spinning-kick score. It only reads the match, so cuts never touch the clock or the score, and a pause holds
 * the shot where it is. Plain C++ so the tests run it on scripted matches.
 */
class OPENSTANCE_API FOpenStanceCameraDirector
{
public:
	FOpenStanceCameraTuning Tuning;

	/** Starts from the combat shot, ignoring any contacts the simulation already has. */
	void Reset(const FOpenStanceMatchSim& Sim);

	/** The frame for this tick. DeltaSeconds is presentation time; while bPaused nothing advances. */
	FOpenStanceCameraFrame Update(float DeltaSeconds, const FOpenStanceMatchSim& Sim, int32 PlayerIndex, bool bPaused);

	EOpenStanceShot GetShot() const { return Shot; }

	/** The combat framing on its own, for the tests: the Match preset adjusted to the fighters' spacing, heights and state. */
	FOpenStanceCameraFrame FrameCombat(const FOpenStanceMatchSim& Sim, int32 PlayerIndex) const;

	/** True if a point is inside the frame's 16:9 picture, within Margin of its half-width and half-height. */
	static bool IsOnScreen(const FOpenStanceCameraFrame& Frame, const FVector& Point, float Margin);

	/** True if both fighters' feet and heads are on screen (a fighter on the floor counts at 30 cm). */
	bool FramesBoth(const FOpenStanceCameraFrame& Frame, const FOpenStanceMatchSim& Sim) const;

	/** A preset placed on the fighters, kept inside the arena. */
	FOpenStanceCameraFrame FramePreset(const FOpenStanceCameraPreset& Preset, const FOpenStanceMatchSim& Sim, int32 PlayerIndex) const;

private:
	EOpenStanceShot Shot = EOpenStanceShot::Combat;
	float ShotElapsed = 0.0f;
	int32 SeenContacts = 0;
	FOpenStanceCameraFrame Last;
};
