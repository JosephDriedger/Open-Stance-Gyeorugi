#pragma once

#include "CoreMinimal.h"
#include "Menu/OpenStanceMenuTypes.h"

/**
 * Round and match rules (WT rules, GDD 8.2-8.4). Match setup picks the options; the defaults are the WT default.
 * Rounds: 1 (single round) or 3 (best of three). Round length: 60, 90 or 120 s. Point gap: 0 (off), 12 or 20.
 */
struct OPENSTANCE_API FOpenStanceRoundTuning
{
	int32 RoundCount = 3;
	float RoundSeconds = 120.0f;

	/** A lead of this many points wins the round on the spot; 0 turns the gap off. Per round, as the score is (GDD 8.2). */
	int32 GapToEnd = 12;

	/** The break between rounds (GDD 8.2: 1:00, skippable in local play). */
	float BreakSeconds = 60.0f;

	/** The opening ceremony before the first shi-jak: charyeot, kyeongrye, joon-bi. 0 starts play at once. */
	float CeremonySeconds = 4.0f;

	/** A fighter with this many gam-jeom in one round loses the round (WT Article 14, best of three). */
	int32 RoundGamJeomLimit = 5;

	/** A fighter with this many gam-jeom across the match loses the match (WT Article 14). */
	int32 MatchGamJeomLimit = 10;

	/** Round wins that take the match: 2 of 3, or 1 of 1. */
	int32 GetRoundsToWin() const { return FMath::Max(1, RoundCount / 2 + 1); }
};

/** Why a round or a match ended the way it did, for the referee, the HUD and the results page. */
enum class EOpenStanceRoundEnd : uint8
{
	None,
	Points,
	PointGap,
	PenaltyLimit,
	TieBreakTurning,
	TieBreakHead,
	TieBreakTrunk,
	TieBreakPunch,
	TieBreakGamJeom,
	TieBreakProtectorHits,
	RefereeDecision,
	MatchPenaltyLimit
};

/** One fighter's round, everything the tie-break needs (WT Article 15, GDD 8.3). */
struct OPENSTANCE_API FOpenStanceRoundTally
{
	int32 Points = 0;

	/** Points from turning and spinning kicks (4 and 6). */
	int32 TurningPoints = 0;
	int32 HeadPoints = 0;
	int32 TrunkPoints = 0;
	int32 PunchPoints = 0;

	/** Points given to this fighter for the opponent's gam-jeom. */
	int32 GamJeomPoints = 0;

	/** Hits the protector registered, scoring or under the impact threshold. */
	int32 ProtectorHits = 0;

	/** Real techniques that reached their active phase: the judges' "greater number of techniques executed". */
	int32 ActiveAttacks = 0;

	/** Of those, spinning, jumping and tornado kicks: the judges' "more advanced techniques". */
	int32 AdvancedAttacks = 0;

	/** Net distance moved toward the opponent in live play, in cm; backing off takes it down. The judges' "aggressive match management". */
	float PressureCm = 0.0f;

	/** Gam-jeom against this fighter in the round. */
	int32 GamJeom = 0;

	/** A scoring technique (GDD 8.3). bTurning: a turning or spinning kick, whose points also count first in a tie-break. */
	void AddScore(int32 InPoints, bool bHead, bool bPunch, bool bTurning);
};

/** How one round ended. */
struct OPENSTANCE_API FOpenStanceRoundResult
{
	int32 Round = 1;
	EOpenStanceSide Winner = EOpenStanceSide::Chung;
	EOpenStanceRoundEnd Reason = EOpenStanceRoundEnd::None;
	FOpenStanceRoundTally Tally[2];

	/** Seconds of play the round ran. */
	float PlayedSeconds = 0.0f;
};

/** The pure rules: no simulation, no clock. The match simulation, the HUD's demo and the tests all decide rounds here. */
struct OPENSTANCE_API FOpenStanceMatchRules
{
	/**
	 * Whether the round ends now, before the clock runs out: a fighter at the round's gam-jeom limit loses it, and a lead of
	 * the gap wins it. Returns false while the round goes on.
	 */
	static bool CheckRoundStop(const FOpenStanceRoundTuning& Rules, const FOpenStanceRoundTally Tally[2], EOpenStanceSide& OutWinner, EOpenStanceRoundEnd& OutReason);

	/**
	 * The winner of a round the clock ended: more points, then WT Article 15 in order (turning kicks, head, trunk, punch,
	 * gam-jeom, protector hits), then the referee and judges' superiority decision (see JudgeSuperiority). Only a
	 * superiority vote that is level goes to RefereeCoin.
	 */
	static void DecideAtTime(const FOpenStanceRoundTally Tally[2], EOpenStanceSide RefereeCoin, EOpenStanceSide& OutWinner, EOpenStanceRoundEnd& OutReason);

	/**
	 * Superiority (WT Article 15, Explanation 1): one vote per criterion the fighters differ on, for aggressive match
	 * management (more PressureCm), the greater number of techniques executed (ActiveAttacks), more advanced techniques
	 * (AdvancedAttacks) and better competition manner (fewer GamJeom). OutVotes gets each side's votes. Returns the side
	 * with more votes, or false when they are level.
	 */
	static bool JudgeSuperiority(const FOpenStanceRoundTally Tally[2], int32 OutVotes[2], EOpenStanceSide& OutWinner);

	/** Net forward movement under this much is a draw on aggression, so standing still does not win a vote. */
	static constexpr float PressureMarginCm = 50.0f;

	/** "Point gap", "Superiority: head" and so on, for the log and the results page. */
	static FString Describe(EOpenStanceRoundEnd Reason);
};
