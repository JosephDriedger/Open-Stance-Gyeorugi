#pragma once

#include "CoreMinimal.h"
#include "Combat/OpenStanceCombatTypes.h"
#include "Combat/OpenStanceFighterState.h"

/** One of the four directions the right stick can point; a gesture is a sequence of them (GDD 7.2). */
enum class EOpenStanceStickDir : uint8
{
	Neutral,
	Up,
	Down,
	Left,
	Right
};

/**
 * One step of a gesture. Up and Down are fixed; Toward and Away are relative to the leg throwing the kick, so the
 * same definition mirrors with the stance and with RT instead of tying a roundhouse to a screen side (GDD 7.4).
 */
enum class EOpenStanceGestureStep : uint8
{
	Up,
	Down,
	Toward,
	Away
};

/** A gesture the recognizer can match: a technique and the stick path that throws it. */
struct OPENSTANCE_API FOpenStanceGestureDef
{
	EOpenStanceTechnique Technique = EOpenStanceTechnique::None;
	TArray<EOpenStanceGestureStep> Steps;

	/** A leading tap of Y throws the technique airborne (GDD 7.4); false for techniques with no jump version. */
	bool bCanJump = false;
};

/** What Active Defense does with the Skill Stick while LT is held (GDD 8.8). */
enum class EOpenStanceDefenseKind : uint8
{
	HighBlock,
	LegCheck,
	Sway
};

/** The recognizer's tuning. The window and dead zone come from the Options screen (GDD 7.8). */
struct OPENSTANCE_API FOpenStanceSkillStickConfig
{
	static constexpr float MinWindowSeconds = 0.20f;
	static constexpr float MaxWindowSeconds = 0.40f;

	/** Seconds from the first stick step within which the rest of the gesture must follow. 0.20 to 0.40. */
	float WindowSeconds = 0.25f;

	/** Radial dead zone as a fraction of stick travel; movement inside it never counts. */
	float DeadZone = 0.15f;

	/** Travel, 0 to 1, a flick must reach to count as a step; raised to at least the dead zone. */
	float EngageThreshold = 0.6f;

	/** Travel below which the stick counts as back at neutral; raised to at least the dead zone. */
	float ReleaseThreshold = 0.35f;

	/** Seconds after a released tap of Y during which a gesture is thrown airborne. */
	float JumpPrimeSeconds = 0.25f;

	/** Builds a config from the Options values: dead zone in percent, window in seconds (clamped to 0.20 to 0.40). */
	static FOpenStanceSkillStickConfig FromSettings(float DeadZonePercent, float WindowSeconds);

	float GetEngage() const { return FMath::Max(EngageThreshold, DeadZone); }
	float GetRelease() const { return FMath::Min(FMath::Max(ReleaseThreshold, DeadZone), GetEngage()); }
};

/** The controller state the recognizer reads each frame. Xbox names; PlayStation maps one to one (GDD 7.1). */
struct OPENSTANCE_API FOpenStanceInputFrame
{
	/** Right stick, -1 to 1. X is positive toward the fighter's right side, Y is positive up. */
	FVector2D RightStick = FVector2D::ZeroVector;

	bool bRT = false; // back leg
	bool bRB = false; // head
	bool bLB = false; // fake
	bool bLT = false; // active defence
	bool bY = false;  // jump tap
};

/** What the recognizer reports; the combat state machine acts on Attack and Defense, the debug overlay on all of them. */
enum class EOpenStanceInputEventType : uint8
{
	/** A gesture matched: Technique, Target, Leg, bFake and bJump say what to throw. */
	Attack,

	/** LB held with no gesture: a generic fake attack. */
	GenericFake,

	/** LT held and the stick moved: DefenseKind says how to answer. */
	Defense,

	/** A tap of Y was released and a gesture may now follow. */
	JumpPrimed,

	/** The stick path matched nothing and ended. */
	GestureRejected,

	/** The window ran out on a path that was only the start of a gesture. */
	GestureExpired,

	/** The jump tap was never followed by a gesture. */
	JumpPrimeExpired,

	/** LT closed in on a gesture that was in progress, so it was dropped. */
	GestureCancelled
};

struct OPENSTANCE_API FOpenStanceInputEvent
{
	EOpenStanceInputEventType Type = EOpenStanceInputEventType::Attack;
	EOpenStanceTechnique Technique = EOpenStanceTechnique::None;
	EOpenStanceTarget Target = EOpenStanceTarget::Trunk;
	EOpenStanceLegSide Leg = EOpenStanceLegSide::Right;
	EOpenStanceLegRole LegRole = EOpenStanceLegRole::Lead;
	EOpenStanceDefenseKind DefenseKind = EOpenStanceDefenseKind::HighBlock;
	bool bFake = false;
	bool bJump = false;

	/** The stick path that produced the event, as text for the debug overlay, for example "Down, Up". */
	FString Path;

	/** Seconds since the recognizer was created, for ordering events in the overlay. */
	double Time = 0.0;
};

/** One entry of the stick history the overlay draws. */
struct OPENSTANCE_API FOpenStanceStickStep
{
	EOpenStanceStickDir Dir = EOpenStanceStickDir::Neutral;
	double Time = 0.0;
};

/**
 * Turns right-stick motions and held buttons into techniques (GDD 7.1-7.4, 8.6).
 *
 * The recognizer is plain data in, events out, with no engine objects, so it can be tested with scripted frames and
 * runs the same for the player and for the AI's synthesized inputs (GDD 16.7). Each frame it:
 *  - copies the held buttons into the fighter state (RT back leg, RB head, LB fake, LT defence) and keeps the jump flag;
 *  - splits the stick into steps (Up, Down, Left, Right) once it passes the dead zone and engage threshold;
 *  - matches the whole step path against the gesture definitions, so "Down, Up" is a spin side kick and never a
 *    side kick that fired on its final Up. A path that is also the start of a longer gesture waits for the stick to
 *    return to neutral or the window to close; any other exact match fires at once.
 *
 * Modifiers latch for the length of a gesture: one that is held at any moment between the first step and the commit
 * counts, so pressing RT a moment before or with the flick behaves the same.
 */
class OPENSTANCE_API FOpenStanceSkillStickRecognizer
{
public:
	FOpenStanceSkillStickRecognizer();

	FOpenStanceSkillStickConfig Config;

	/** The Milestone 1 set: side/cut (Up), roundhouse (toward the throwing leg), hook (away) and spin side (Down, Up). */
	static TArray<FOpenStanceGestureDef> MakeDefaultGestures();

	/** Replaces the definitions; later mapped moves are added here without touching the matching. */
	void SetGestures(const TArray<FOpenStanceGestureDef>& InGestures);
	void AddGesture(const FOpenStanceGestureDef& Gesture);
	const TArray<FOpenStanceGestureDef>& GetGestures() const { return Gestures; }

	/**
	 * Advances the recognizer by one frame. Reads the stance from State and writes back the held modifiers and the
	 * jump-primed flag. Events are appended to OutEvents in the order they happened.
	 */
	void Update(float DeltaSeconds, const FOpenStanceInputFrame& Input, FOpenStanceFighterState& State, TArray<FOpenStanceInputEvent>& OutEvents);

	/** Forgets any gesture in progress and the jump tap; used when play stops or the fighter is hit. */
	void Reset(FOpenStanceFighterState& State);

	/** The stick steps of the gesture in progress or the last one, newest last. */
	const TArray<FOpenStanceStickStep>& GetStepHistory() const { return History; }

	bool IsGestureInProgress() const { return bInGesture; }

	/** The direction a stick position points at, or Neutral inside the dead zone. */
	static EOpenStanceStickDir ToDirection(const FVector2D& Stick, float Engage);

	static FString PathToString(const TArray<EOpenStanceStickDir>& Path);

private:
	enum class EMatch : uint8
	{
		None,
		Partial,
		Exact,
		ExactWithLonger
	};

	struct FMatch
	{
		EMatch Kind = EMatch::None;
		const FOpenStanceGestureDef* Def = nullptr;
	};

	FMatch MatchPath(const FOpenStanceFighterState& State) const;
	EOpenStanceStickDir ResolveStep(EOpenStanceGestureStep Step, const FOpenStanceFighterState& State) const;
	void Commit(const FMatch& Match, FOpenStanceFighterState& State, TArray<FOpenStanceInputEvent>& OutEvents);
	void Finish(FOpenStanceFighterState& State, TArray<FOpenStanceInputEvent>& OutEvents);
	void Emit(TArray<FOpenStanceInputEvent>& OutEvents, EOpenStanceInputEventType Type, const FOpenStanceFighterState& State) const;
	void BeginGesture(const FOpenStanceInputFrame& Input, FOpenStanceFighterState& State);
	void EndGesture();

	TArray<FOpenStanceGestureDef> Gestures;

	double Clock = 0.0;
	EOpenStanceStickDir CurrentDir = EOpenStanceStickDir::Neutral;

	/** Steps of the gesture in progress, as stick directions. */
	TArray<EOpenStanceStickDir> Path;
	TArray<FOpenStanceStickStep> History;
	double GestureStart = 0.0;
	bool bInGesture = false;

	/** The gesture already fired or was dropped; ignore the stick until it is back at neutral. */
	bool bSpent = false;

	/** Modifiers held at any point during the gesture. */
	bool bLatchedRT = false;
	bool bLatchedRB = false;
	bool bLatchedLB = false;
	bool bLatchedJump = false;

	bool bPrevY = false;
	bool bPrevLB = false;
	bool bPrevLT = false;
	bool bYHeldDuringGesture = false;
	double JumpPrimeUntil = -1.0;

	/** LB went down with no gesture yet: a generic fake if none follows within the window. */
	bool bFakeCandidate = false;
	double FakeCandidateStart = 0.0;
};
