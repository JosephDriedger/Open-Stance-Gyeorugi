#pragma once

#include "CoreMinimal.h"

class UDataTable;
class UOpenStanceMatchModel;
class FOpenStanceMatchSim;

/**
 * Mirrors a running match simulation into the match HUD's model, so the scoreboard, stamina bars, round clock, penalties and
 * the referee's call show what is really happening (GDD 7.6, 8.5). The simulation owns every number; the model is only
 * told. It sends each change once, so call Update every tick after the simulation has stepped.
 *
 * Plain data in and out, no engine objects beyond the model, so the automation tests run it on scripted matches.
 */
struct OPENSTANCE_API FOpenStanceMatchModelSync
{
	/**
	 * Takes the model over from its demo: names the fighters, clears the match and starts counting from the simulation's
	 * current state. MoveTable gives each move's display name for the results page; it may be null.
	 */
	void Begin(const FOpenStanceMatchSim& Sim, UOpenStanceMatchModel& Model, const FString& ChungName, const FString& HongName, const UDataTable* MoveTable);

	/** Sends what changed since the last call: new scores and penalties, stamina, the clock and round, referee calls, the end. */
	void Update(const FOpenStanceMatchSim& Sim, UOpenStanceMatchModel& Model);

private:
	const UDataTable* Moves = nullptr;
	int32 SeenContacts = 0;
	int32 SeenLog = 0;
	int32 SeenPenalties[2] = { 0, 0 };
};
