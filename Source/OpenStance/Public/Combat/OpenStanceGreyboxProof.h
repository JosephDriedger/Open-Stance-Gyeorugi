#pragma once

#include "CoreMinimal.h"
#include "Combat/OpenStanceMatchSim.h"

/**
 * The repeatable Milestone 1 greybox proof (GDD 19, 20.1): two greybox fighters, scripted controller input only. Chung
 * throws the side kick, the roundhouse and the spin side kick, switches legs and throws the same RT kick from the other
 * side, misses from too far, closes in and scores a spinning head kick. Hong stands still. Each stage is checked against
 * what the rules should say, so the same script is the automation test (OpenStance.Greybox.Proof), the os.RunProof
 * console command and the record written to Saved/Logs/OpenStanceGreyboxProof.txt.
 *
 * The retargeted capture playing on the fighter (issue 8) is not part of this script: it needs the capture itself.
 */
struct OPENSTANCE_API FOpenStanceGreyboxProof
{
	struct FStage
	{
		FString Name;
		bool bPassed = false;
		FString Detail;
	};

	/** Starts a match on Sim (whose move table must be set) and plays the script. */
	static TArray<FStage> Run(FOpenStanceMatchSim& Sim);

	/** The stages and the match log as text. */
	static FString Format(const TArray<FStage>& Stages, const FOpenStanceMatchSim& Sim);

	static bool AllPassed(const TArray<FStage>& Stages);
};
