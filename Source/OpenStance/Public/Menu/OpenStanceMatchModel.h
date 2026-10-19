#pragma once

#include "CoreMinimal.h"
#include "Menu/OpenStanceMenuTypes.h"
#include "UObject/Object.h"
#include "OpenStanceMatchModel.generated.h"

/** One scored technique, kept for the results page. */
USTRUCT(BlueprintType)
struct OPENSTANCE_API FOpenStanceScoreEvent
{
	GENERATED_BODY()

	UPROPERTY(BlueprintReadOnly, Category = "Open Stance|Match")
	EOpenStanceSide Side = EOpenStanceSide::Chung;

	UPROPERTY(BlueprintReadOnly, Category = "Open Stance|Match")
	int32 Round = 1;

	UPROPERTY(BlueprintReadOnly, Category = "Open Stance|Match")
	int32 Points = 0;

	UPROPERTY(BlueprintReadOnly, Category = "Open Stance|Match")
	FString Technique;

	UPROPERTY(BlueprintReadOnly, Category = "Open Stance|Match")
	bool bHead = false;
};

DECLARE_MULTICAST_DELEGATE(FOpenStanceMatchFinished);

/**
 * What the match HUD and results page show: score, round clock, stamina, penalties and the referee's call.
 *
 * Gameplay owns the numbers and pushes them in (AddPoints, SetStamina, SetCall); the HUD only reads them. Until
 * gameplay drives a match, the HUD runs the clock itself through Advance so the screen can be played with in the
 * menu, as in the prototype.
 */
UCLASS(BlueprintType)
class OPENSTANCE_API UOpenStanceMatchModel : public UObject
{
	GENERATED_BODY()

public:
	/** The point gap that ends a match (WT rules, GDD 4.4). */
	static constexpr int32 PointGapToEnd = 12;
	static constexpr int32 RoundCount = 3;
	static constexpr float RoundSeconds = 120.0f;

	UFUNCTION(BlueprintCallable, Category = "Open Stance|Match")
	void Reset(const FString& ChungName, const FString& HongName);

	/** Fills in a finished example match (14 to 7) for the results page and screenshots. */
	UFUNCTION(BlueprintCallable, Category = "Open Stance|Match")
	void PopulateSample();

	/** Runs the round clock; returns true on the call that ends the match. */
	bool Advance(float DeltaSeconds);

	UFUNCTION(BlueprintCallable, Category = "Open Stance|Match")
	void AddPoints(EOpenStanceSide Side, int32 Points, const FString& Technique, bool bHead);

	UFUNCTION(BlueprintCallable, Category = "Open Stance|Match")
	void SetStamina(EOpenStanceSide Side, float Fraction);

	UFUNCTION(BlueprintCallable, Category = "Open Stance|Match")
	void AddGamJeom(EOpenStanceSide Side, const FString& Reason);

	/** The referee's current command: a Korean term and its English meaning, e.g. "KAL-YEO" and "Break". */
	UFUNCTION(BlueprintCallable, Category = "Open Stance|Match")
	void SetCall(const FString& Term, const FString& Meaning, const FString& Separator = TEXT(": "));

	UFUNCTION(BlueprintCallable, Category = "Open Stance|Match")
	void SetPaused(bool bInPaused);

	/** Sets the round (1-based) and the seconds left in it. */
	UFUNCTION(BlueprintCallable, Category = "Open Stance|Match")
	void SetClock(int32 InRound, float SecondsRemaining);

	UFUNCTION(BlueprintPure, Category = "Open Stance|Match")
	const FString& GetFighterName(EOpenStanceSide Side) const;

	UFUNCTION(BlueprintPure, Category = "Open Stance|Match")
	int32 GetScore(EOpenStanceSide Side) const;

	UFUNCTION(BlueprintPure, Category = "Open Stance|Match")
	float GetStamina(EOpenStanceSide Side) const;

	UFUNCTION(BlueprintPure, Category = "Open Stance|Match")
	int32 GetGamJeom(EOpenStanceSide Side) const;

	UFUNCTION(BlueprintPure, Category = "Open Stance|Match")
	int32 GetVideoReviewsLeft(EOpenStanceSide Side) const;

	/** Score of one side in one round (1-based). */
	int32 GetRoundScore(EOpenStanceSide Side, int32 Round) const;

	/** Technique names with their combined points for both fighters, highest first. */
	TArray<TPair<FString, int32>> GetPointsByTechnique() const;

	/** Reasons for each side's gam-jeom, e.g. grabbing. */
	const TArray<FString>& GetPenaltyReasons(EOpenStanceSide Side) const;

	UFUNCTION(BlueprintPure, Category = "Open Stance|Match")
	EOpenStanceSide GetWinner() const;

	UFUNCTION(BlueprintPure, Category = "Open Stance|Match")
	int32 GetRound() const
	{
		return Round;
	}

	UFUNCTION(BlueprintPure, Category = "Open Stance|Match")
	float GetTimeRemaining() const
	{
		return TimeRemaining;
	}

	UFUNCTION(BlueprintPure, Category = "Open Stance|Match")
	bool IsPaused() const
	{
		return bPaused;
	}

	UFUNCTION(BlueprintPure, Category = "Open Stance|Match")
	bool IsFinished() const
	{
		return bFinished;
	}

	const FString& GetCallTerm() const
	{
		return CallTerm;
	}

	const FString& GetCallMeaning() const
	{
		return CallMeaning;
	}

	const FString& GetCallSeparator() const
	{
		return CallSeparator;
	}

	const TArray<FOpenStanceScoreEvent>& GetEvents() const
	{
		return Events;
	}

	/** Seconds since the last score for a side, for the "+3" pop-up; large when it has not scored. */
	float GetSecondsSinceScore(EOpenStanceSide Side) const;
	int32 GetLastScorePoints(EOpenStanceSide Side) const;

	FOpenStanceMatchFinished OnFinished;

	/** While true the match HUD runs the clock and lets A score a random technique, for use before gameplay exists. Gameplay turns it off. */
	UPROPERTY(BlueprintReadWrite, Category = "Open Stance|Match")
	bool bDemoMode = true;

private:
	struct FSideState
	{
		FString Name;
		int32 Score = 0;
		float Stamina = 1.0f;
		int32 GamJeom = 0;
		int32 VideoReviewsLeft = 1;
		TArray<FString> PenaltyReasons;
		int32 LastScorePoints = 0;
		double LastScoreTime = -1000.0;
	};

	FSideState& GetSide(EOpenStanceSide Side);
	const FSideState& GetSide(EOpenStanceSide Side) const;

	/** Ends the match once the gap is reached or the last round runs out. */
	void CheckForEnd();

	FSideState Sides[2];
	TArray<FOpenStanceScoreEvent> Events;
	int32 Round = 1;
	float TimeRemaining = RoundSeconds;
	bool bPaused = false;
	bool bFinished = false;
	FString CallTerm;
	FString CallMeaning;
	FString CallSeparator = TEXT(": ");
	double ClockSeconds = 0.0;
};
