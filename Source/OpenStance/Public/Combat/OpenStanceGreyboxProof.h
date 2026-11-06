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
 * The fighters play the placeholder technique clips; the retargeted capture (issue 8) replaces them at Milestone 2.
 */
struct OPENSTANCE_API FOpenStanceGreyboxProof
{
	struct FStage
	{
		FString Name;
		bool bPassed = false;
		FString Detail;
	};

	/**
	 * The script's controller input, one entry per 60 Hz step, and a caption for each stage (the step it starts on), so
	 * the live greybox can replay the same proof on screen (os.PlayProof). Replayed into a match started with
	 * StartDistanceCm, default Skill Stick settings and an idle Hong, it gives the same result as Run.
	 */
	struct FTrack
	{
		TArray<FOpenStanceFighterControls> Chung;
		TArray<TPair<int32, FString>> Captions;
	};

	static constexpr float StepSeconds = 1.0f / 60.0f;
	static constexpr float StartDistanceCm = 100.0f;
	static constexpr int32 ExpectedChungScore = 16;

	/** Starts a match on Sim (whose move table must be set) and plays the script; OutTrack, if given, records it. */
	static TArray<FStage> Run(FOpenStanceMatchSim& Sim, FTrack* OutTrack = nullptr);

	/** The stages and the match log as text. */
	static FString Format(const TArray<FStage>& Stages, const FOpenStanceMatchSim& Sim);

	static bool AllPassed(const TArray<FStage>& Stages);
};
