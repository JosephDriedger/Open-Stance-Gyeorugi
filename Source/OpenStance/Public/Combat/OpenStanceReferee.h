#pragma once

#include "CoreMinimal.h"
#include "Menu/OpenStanceMenuTypes.h"

class FOpenStanceMatchSim;
struct FOpenStanceMatchLogEntry;

/** The referee's gesture (GDD 8.5, 11.2). Each has a placeholder pose clip, AS_Placeholder_Referee_<Name>. */
enum class EOpenStanceRefereePose : uint8
{
	/** Standing ready off the line, hands relaxed in front. */
	Idle,
	/** CHARYEOT: feet together, arms at the sides. */
	Attention,
	/** KYEONGRYE: the bow. */
	Bow,
	/** JOON-BI: the open hand held out between the fighters. */
	Ready,
	/** SHI-JAK, KYE-SOK, GONG-GYEOK: the hand drawn down to start play. */
	Start,
	/** KAL-YEO: the arm out flat between the fighters. */
	Separate,
	/** KEU-MAN: the arm raised to stop the round. */
	Stop,
	/** GAM-JEOM: pointing at the penalized fighter. */
	Point,
	/** HANA to YEODEOL: counting over a knocked-down fighter, hand raised. */
	Count,
	/** CHUNG SEUNG, HONG SEUNG: the winner's side arm raised. */
	RaiseWinner
};

/** One referee command: the Korean term, its English meaning for the subtitle, and the voice line to play. */
struct OPENSTANCE_API FOpenStanceRefereeCall
{
	FString Term;
	FString Meaning;

	/** The voice line in the referee's set: /Game/Audio/Referee/<Referee>/<Cue>. */
	FName Cue;

	EOpenStanceRefereePose Pose = EOpenStanceRefereePose::Idle;

	/** Calls that name a fighter (a penalty, a count, the winner) say which. */
	bool bNamesSide = false;
	EOpenStanceSide Side = EOpenStanceSide::Chung;
};

/** Where the referee stands and how long a gesture holds. Starting values. */
struct OPENSTANCE_API FOpenStanceRefereeTuning
{
	/** In play the referee stands this far off the fighters' line, on the side away from the camera. */
	float StandOffCm = 170.0f;

	/** For KAL-YEO and the clinch, this far off the line: stepping in between. */
	float SeparateOffCm = 45.0f;

	/** Never closer than this to a fighter outside a separation. */
	float ClearOfFighterCm = 120.0f;

	/** Counting, beside the fighter on the floor, this far out. */
	float CountOffCm = 95.0f;

	float WalkCmPerSecond = 220.0f;

	/** A gesture holds this long before the referee goes back to Idle (a count holds until the next). */
	float GestureSeconds = 1.2f;

	/** Each gesture shows at least this long before the next call's replaces it; calls made together play in turn. */
	float MinGestureSeconds = 0.5f;

	/** The winner's hand stays up at least this long before the bow. */
	float RaiseWinnerSeconds = 2.0f;

	/** The referee stays within this distance of the mat's centre. */
	float MatLimitCm = 360.0f;
};

/**
 * The NPC referee (GDD 8.5, 11.2, issue 15). One of the six referees, picked at random, follows the match: every command
 * in the simulation's log becomes a call (term, English meaning, voice cue) and a gesture, and the referee walks to stay
 * clear of the exchange on the side away from the combat camera, steps in to separate a clinch and stands over a count.
 * The simulation decides every stop and resume; the referee only shows them. Plain C++ so the tests run it.
 */
class OPENSTANCE_API FOpenStanceReferee
{
public:
	static constexpr int32 RefereeCount = 6;

	/** The six referees' names, as their assets are named (MH_Referee_<Name>). */
	static const TCHAR* GetRefereeName(int32 Index);

	/** The call a log entry makes, or false for entries the referee does not call (scores, misses, the clinch itself). */
	static bool CallFor(const FOpenStanceMatchLogEntry& Entry, FOpenStanceRefereeCall& OutCall);

	FOpenStanceRefereeTuning Tuning;

	/** Picks a referee from Seed and places them at their spot for the start of the match. */
	void Reset(const FOpenStanceMatchSim& Sim, int32 PlayerIndex, int32 Seed);

	/** Follows the match: new calls, the gesture and the walk. The calls made this tick are in GetNewCalls. */
	void Update(float DeltaSeconds, const FOpenStanceMatchSim& Sim, int32 PlayerIndex);

	int32 GetRefereeIndex() const { return RefereeIndex; }
	const FVector2D& GetPosition() const { return Position; }
	const FVector2D& GetFacing() const { return Facing; }
	EOpenStanceRefereePose GetPose() const { return Pose; }

	/** The gesture is made with the right arm toward the named fighter; false means the mirrored, left-arm version. */
	bool IsGestureRight() const { return bGestureRight; }

	const TArray<FOpenStanceRefereeCall>& GetNewCalls() const { return NewCalls; }

	/** Where the referee is heading: the spot for the current moment of the match. */
	FVector2D GetTarget(const FOpenStanceMatchSim& Sim, int32 PlayerIndex) const;

private:
	int32 RefereeIndex = 0;
	FVector2D Position = FVector2D::ZeroVector;
	FVector2D Facing = FVector2D(1.0, 0.0);
	EOpenStanceRefereePose Pose = EOpenStanceRefereePose::Idle;
	float PoseElapsed = 0.0f;
	bool bGestureRight = true;
	bool bHasNamedSide = false;
	EOpenStanceSide NamedSide = EOpenStanceSide::Chung;
	int32 SeenLog = 0;

	/** Gestures waiting their turn, oldest first. */
	TArray<FOpenStanceRefereeCall> Queued;

	void Show(const FOpenStanceRefereeCall& Call);
	float MinShowSeconds() const;
	TArray<FOpenStanceRefereeCall> NewCalls;
};
