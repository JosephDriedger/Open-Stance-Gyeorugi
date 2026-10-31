#pragma once

#include "CoreMinimal.h"
#include "Combat/OpenStanceMatchSim.h"

/**
 * The text of the live combat display (GDD 7.6, 7.7, 16.8). Two forms of one source:
 *  - the debug overlay (os.CombatDebug): everything, including the combat state, the stick history, rejected and expired
 *    gestures and the last hit trace;
 *  - the player-facing Training display: the last input, leg, move, target, stamina and hit result.
 *
 * Building the lines is separate from drawing them so the content can be tested and the drawing swapped.
 */
struct OPENSTANCE_API FOpenStanceCombatOverlay
{
	/** Lines for one fighter. */
	static TArray<FString> BuildLines(const FOpenStanceMatchSim& Sim, int32 FighterIndex, bool bPlayerFacing);

	/** One input event as a short line: "Attack: Spin Side Kick, Left (back), Head" or "Rejected: Down, Left". */
	static FString DescribeInput(const FOpenStanceInputEvent& Event);

	/** The combat state in words. */
	static FString StateName(EOpenStanceCombatState State);

	/** Stick history, e.g. "Down > Up", from the recognizer's last gesture. */
	static FString StickHistory(const FOpenStanceSkillStickRecognizer& Recognizer);

	/** The held buttons, e.g. "RT RB". */
	static FString HeldButtons(const FOpenStanceFighterState& State);
};
