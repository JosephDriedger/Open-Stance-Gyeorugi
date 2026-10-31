#pragma once

#include "CoreMinimal.h"
#include "Combat/OpenStanceCombatMachine.h"
#include "Combat/OpenStanceCombatTypes.h"
#include "Menu/OpenStanceMenuTypes.h"

/** Where on a fighter a trace landed (GDD 8.3, 8.4). */
enum class EOpenStanceBodyZone : uint8
{
	None,
	Head,
	Trunk,
	BelowBelt
};

/**
 * Hit registration numbers. Zones are vertical cylinders sized as fractions of the fighter's height so every body type
 * gets the same layout; starting values, checked against the MetaHuman bodies when the colliders are built.
 */
struct OPENSTANCE_API FOpenStanceHitTuning
{
	/** The trunk protector needs a kick at least this strong to register (GDD 8.3). Punches need none. */
	float TrunkImpactThreshold = 30.0f;

	/** The most a trace may be nudged into contact. It never makes an out-of-range attack reach (GDD 1.7). */
	float AlignmentToleranceCm = 8.0f;

	float FootGuardRadiusCm = 9.0f;
	float GloveRadiusCm = 7.0f;

	/** Heights, as a share of the fighter's height: the belt line splits trunk from below-belt, the trunk ends where the head begins. */
	float BeltLineFraction = 0.55f;
	float HeadBottomFraction = 0.82f;

	float HeadRadiusFraction = 0.07f;
	float TrunkRadiusFraction = 0.11f;
	float BelowBeltRadiusFraction = 0.10f;

	/** Points tested along each frame's sweep, so a fast foot cannot skip a zone between frames. */
	int32 SamplesPerTrace = 16;
};

/** A fighter's body for hit tests: the floor point under the centre, and the height. Centimetres, Z up. */
struct OPENSTANCE_API FOpenStanceFighterBody
{
	FVector Root = FVector::ZeroVector;
	float HeightCm = 175.0f;
	EOpenStanceSide Side = EOpenStanceSide::Chung;
};

/** The path a striking limb swept this frame, in world space. */
struct OPENSTANCE_API FOpenStanceLimbTrace
{
	FVector Start = FVector::ZeroVector;
	FVector End = FVector::ZeroVector;
	EOpenStanceStrikeLimb Limb = EOpenStanceStrikeLimb::FootGuard;
};

enum class EOpenStanceContactType : uint8
{
	/** A valid hit: Points says how many. */
	Score,

	/** A punch reached the head: illegal, scores nothing, a foul (GDD 8.3, 8.4). */
	PunchToHead,

	/** A kick's trace registered below the belt line: a foul (GDD 8.4). */
	KickBelowBelt,

	/** A kick touched the trunk protector below the impact threshold: contact, but no score. */
	WeakImpact
};

/** One registered contact, once per technique; the match, the referee and the debug overlay all read it. */
struct OPENSTANCE_API FOpenStanceContact
{
	EOpenStanceContactType Type = EOpenStanceContactType::Score;
	FName Move;
	EOpenStanceTechnique Technique = EOpenStanceTechnique::None;
	EOpenStanceSide Attacker = EOpenStanceSide::Chung;
	EOpenStanceSide Defender = EOpenStanceSide::Hong;
	EOpenStanceBodyZone Zone = EOpenStanceBodyZone::None;
	bool bSpinning = false;

	/** 1, 2, 3, 4 or 6 for a Score, otherwise 0. */
	int32 Points = 0;

	/** Impact after the stamina penalty. */
	float Impact = 0.0f;

	EOpenStanceReactionSeverity Reaction = EOpenStanceReactionSeverity::Normal;
	FVector Point = FVector::ZeroVector;
};

/** What the overlay shows about the last trace: whether it was looked at, and why it was not counted. */
struct OPENSTANCE_API FOpenStanceTraceDebug
{
	bool bEvaluated = false;
	FString Ignored;
	bool bOutOfRange = false;
	EOpenStanceBodyZone ZoneHit = EOpenStanceBodyZone::None;
	FVector Start = FVector::ZeroVector;
	FVector End = FVector::ZeroVector;
};

struct OPENSTANCE_API FOpenStanceHitContext
{
	/** The technique in flight, or null when there is none. */
	const FOpenStanceAttackRequest* Attack = nullptr;

	/** FOpenStanceCombatMachine::CanScore for the attacker: a real technique's active phase with play live. */
	bool bCanScore = false;

	/** FOpenStanceCombatMachine::GetAttackSerial. */
	int32 AttackSerial = 0;

	/** FOpenStanceCombatMachine::GetImpactScale. */
	float ImpactScale = 1.0f;

	FOpenStanceFighterBody Attacker;
	FOpenStanceFighterBody Defender;
	FOpenStanceLimbTrace Trace;
};

/**
 * PSS-style hit registration for one attacker (GDD 8.3). Each frame the attacker's limb trace is tested against the
 * defender's head, trunk and below-belt zones, but only in a real technique's active phase and only within the move's
 * reach. A technique registers one contact: further traces of the same attack are ignored.
 */
class OPENSTANCE_API FOpenStanceHitRegistry
{
public:
	FOpenStanceHitTuning Tuning;

	/** Tests one frame's trace and appends at most one contact. Returns true if a contact was appended. */
	bool Trace(const FOpenStanceHitContext& Context, TArray<FOpenStanceContact>& OutContacts);

	const FOpenStanceTraceDebug& GetLastTrace() const { return Debug; }

	/** Forgets the attack in progress; call when the round restarts. */
	void Reset();

	/** The cylinder of a zone on a body: bottom and top Z (world) and horizontal radius. */
	static void GetZoneBounds(const FOpenStanceFighterBody& Body, EOpenStanceBodyZone Zone, const FOpenStanceHitTuning& Tuning, float& OutBottom, float& OutTop, float& OutRadius);

	/** Where the trace first meets a zone, with Tuning's alignment tolerance and the limb's radius. */
	static EOpenStanceBodyZone FindContact(const FOpenStanceLimbTrace& Trace, const FOpenStanceFighterBody& Body, const FOpenStanceHitTuning& Tuning, FVector& OutPoint);

	/**
	 * The foot or glove position of a technique that is not driven by a skeleton yet (greybox, placeholder
	 * animation): it travels along the attacker's facing out to the move's scaled reach, at the height of its target.
	 * Progress is 0 to 1 through the active phase.
	 */
	static FVector SyntheticTip(const FOpenStanceFighterBody& Attacker, const FVector& FacingXY, const FOpenStanceMoveRow& Row, float Progress, const FOpenStanceHitTuning& Tuning);

private:
	int32 Serial = -1;
	bool bConsumed = false;
	FOpenStanceTraceDebug Debug;
};
