#pragma once

#include "CoreMinimal.h"
#include "OpenStanceCombatTypes.generated.h"

/** Which foot is forward. Switch Sides changes it with a visible animation (GDD 8.7). */
UENUM(BlueprintType)
enum class EOpenStanceStance : uint8
{
	LeftLead,
	RightLead
};

/** The body's own sides, as opposed to lead and back, which follow the stance. */
UENUM(BlueprintType)
enum class EOpenStanceLegSide : uint8
{
	Left,
	Right
};

/** Which leg of the stance throws a kick: RT held selects the back leg (GDD 7.4). */
UENUM(BlueprintType)
enum class EOpenStanceLegRole : uint8
{
	Lead,
	Back
};

/** The four guard postures: they differ in posture, readiness and transition timing, never in stats (GDD 8.7). */
UENUM(BlueprintType)
enum class EOpenStanceGuard : uint8
{
	High,
	Cross,
	Mixed,
	Low
};

/** The kick or strike a Skill Stick gesture asks for (GDD 7.2, 9). Leg and target are chosen by modifiers. */
UENUM(BlueprintType)
enum class EOpenStanceTechnique : uint8
{
	None,
	SideKick,
	Roundhouse,
	Hook,
	Axe,
	SpinSide,
	SpinHook,
	Tornado,
	Punch
};

/** Where a technique is aimed; a score needs a matching zone (GDD 8.3). */
UENUM(BlueprintType)
enum class EOpenStanceTarget : uint8
{
	Trunk,
	Head
};

/** The part of the fighter that carries the hit trace during Attack Active. */
UENUM(BlueprintType)
enum class EOpenStanceStrikeLimb : uint8
{
	FootGuard,
	Glove
};

/** How hard a landed technique hits the defender (GDD 8.10). */
UENUM(BlueprintType)
enum class EOpenStanceReactionSeverity : uint8
{
	Minor,
	Normal,
	Heavy,
	Knockdown
};

/** The fighter's combat state (GDD 16.3). */
UENUM(BlueprintType)
enum class EOpenStanceCombatState : uint8
{
	IdleMovement,
	AttackStartup,
	AttackActive,
	AttackRecovery,
	ActiveDefense,
	HitReaction,
	Staggered,
	KnockedDown,
	Recovering,
	MatchFinished
};

/** The match's own state, separate from either fighter's combat state. */
UENUM(BlueprintType)
enum class EOpenStanceMatchState : uint8
{
	NotStarted,
	Ready,
	Running,
	Stopped,
	RoundBreak,
	Finished
};
