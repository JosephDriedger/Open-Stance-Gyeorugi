#include "Menu/OpenStanceMatchModel.h"

namespace
{
	int32 SideIndex(EOpenStanceSide Side)
	{
		return Side == EOpenStanceSide::Hong ? 1 : 0;
	}
}

UOpenStanceMatchModel::FSideState& UOpenStanceMatchModel::GetSide(EOpenStanceSide Side)
{
	return Sides[SideIndex(Side)];
}

const UOpenStanceMatchModel::FSideState& UOpenStanceMatchModel::GetSide(EOpenStanceSide Side) const
{
	return Sides[SideIndex(Side)];
}

void UOpenStanceMatchModel::Reset(const FString& ChungName, const FString& HongName)
{
	Sides[0] = FSideState();
	Sides[1] = FSideState();
	Sides[0].Name = ChungName;
	Sides[1].Name = HongName;
	Events.Reset();
	Round = 1;
	TimeRemaining = RoundSeconds;
	bPaused = false;
	bFinished = false;
	CallTerm = TEXT("SI-JAK");
	CallMeaning = TEXT("Begin");
}

void UOpenStanceMatchModel::PopulateSample()
{
	const FString Chung = Sides[0].Name.IsEmpty() ? TEXT("Min-jun Park") : Sides[0].Name;
	const FString Hong = Sides[1].Name.IsEmpty() ? TEXT("Dae-ho Kim") : Sides[1].Name;
	Reset(Chung, Hong);

	const auto Score = [this](EOpenStanceSide Side, int32 InRound, int32 Points, const TCHAR* Technique, bool bHead)
	{
		Round = InRound;
		AddPoints(Side, Points, Technique, bHead);
	};
	Score(EOpenStanceSide::Chung, 1, 2, TEXT("Roundhouse"), false);
	Score(EOpenStanceSide::Chung, 1, 4, TEXT("Spinning hook"), false);
	Score(EOpenStanceSide::Hong, 1, 2, TEXT("Back kick"), false);
	Score(EOpenStanceSide::Chung, 2, 3, TEXT("Axe kick"), true);
	Score(EOpenStanceSide::Hong, 2, 4, TEXT("Back kick"), false);
	Score(EOpenStanceSide::Chung, 3, 2, TEXT("Roundhouse"), false);
	Score(EOpenStanceSide::Chung, 3, 1, TEXT("Punch"), false);
	Score(EOpenStanceSide::Chung, 3, 2, TEXT("Roundhouse"), false);
	Score(EOpenStanceSide::Hong, 3, 1, TEXT("Punch"), false);
	AddGamJeom(EOpenStanceSide::Hong, TEXT("Grabbing"));
	Round = RoundCount;
	TimeRemaining = 0.0f;
	bFinished = true;
}

bool UOpenStanceMatchModel::Advance(float DeltaSeconds)
{
	ClockSeconds += DeltaSeconds;
	if (bPaused || bFinished)
	{
		return false;
	}

	TimeRemaining -= DeltaSeconds;
	if (TimeRemaining <= 0.0f)
	{
		if (Round < RoundCount)
		{
			++Round;
			TimeRemaining = RoundSeconds;
			SetCall(TEXT("SI-JAK"), TEXT("Begin"));
		}
		else
		{
			TimeRemaining = 0.0f;
		}
	}
	const bool bWasFinished = bFinished;
	CheckForEnd();
	return bFinished && !bWasFinished;
}

void UOpenStanceMatchModel::CheckForEnd()
{
	const bool bGapReached = FMath::Abs(Sides[0].Score - Sides[1].Score) >= PointGapToEnd;
	const bool bTimeUp = Round >= RoundCount && TimeRemaining <= 0.0f;
	if (!bFinished && (bGapReached || bTimeUp))
	{
		bFinished = true;
		SetCall(TEXT("KEU-MAN"), TEXT("Stop"));
		OnFinished.Broadcast();
	}
}

void UOpenStanceMatchModel::AddPoints(EOpenStanceSide Side, int32 Points, const FString& Technique, bool bHead)
{
	FSideState& State = GetSide(Side);
	State.Score += Points;
	State.LastScorePoints = Points;
	State.LastScoreTime = ClockSeconds;

	FOpenStanceScoreEvent Event;
	Event.Side = Side;
	Event.Round = Round;
	Event.Points = Points;
	Event.Technique = Technique;
	Event.bHead = bHead;
	Events.Add(Event);

	SetCall(bHead ? TEXT("Head kick") : TEXT("Body kick"), FString::Printf(TEXT("%d points"), Points), TEXT(" · "));
	CheckForEnd();
}

void UOpenStanceMatchModel::SetStamina(EOpenStanceSide Side, float Fraction)
{
	GetSide(Side).Stamina = FMath::Clamp(Fraction, 0.0f, 1.0f);
}

void UOpenStanceMatchModel::AddGamJeom(EOpenStanceSide Side, const FString& Reason)
{
	FSideState& State = GetSide(Side);
	++State.GamJeom;
	State.PenaltyReasons.Add(Reason);
}

void UOpenStanceMatchModel::SetCall(const FString& Term, const FString& Meaning, const FString& Separator)
{
	CallTerm = Term;
	CallMeaning = Meaning;
	CallSeparator = Separator;
}

void UOpenStanceMatchModel::SetPaused(bool bInPaused)
{
	bPaused = bInPaused;
}

void UOpenStanceMatchModel::SetClock(int32 InRound, float SecondsRemaining)
{
	Round = FMath::Clamp(InRound, 1, RoundCount);
	TimeRemaining = FMath::Clamp(SecondsRemaining, 0.0f, RoundSeconds);
}

const FString& UOpenStanceMatchModel::GetFighterName(EOpenStanceSide Side) const
{
	return GetSide(Side).Name;
}

int32 UOpenStanceMatchModel::GetScore(EOpenStanceSide Side) const
{
	return GetSide(Side).Score;
}

float UOpenStanceMatchModel::GetStamina(EOpenStanceSide Side) const
{
	return GetSide(Side).Stamina;
}

int32 UOpenStanceMatchModel::GetGamJeom(EOpenStanceSide Side) const
{
	return GetSide(Side).GamJeom;
}

int32 UOpenStanceMatchModel::GetVideoReviewsLeft(EOpenStanceSide Side) const
{
	return GetSide(Side).VideoReviewsLeft;
}

int32 UOpenStanceMatchModel::GetRoundScore(EOpenStanceSide Side, int32 InRound) const
{
	int32 Total = 0;
	for (const FOpenStanceScoreEvent& Event : Events)
	{
		if (Event.Side == Side && Event.Round == InRound)
		{
			Total += Event.Points;
		}
	}
	return Total;
}

TArray<TPair<FString, int32>> UOpenStanceMatchModel::GetPointsByTechnique() const
{
	TMap<FString, int32> Totals;
	for (const FOpenStanceScoreEvent& Event : Events)
	{
		Totals.FindOrAdd(Event.Technique) += Event.Points;
	}

	TArray<TPair<FString, int32>> Sorted;
	for (const TPair<FString, int32>& Pair : Totals)
	{
		Sorted.Add(Pair);
	}
	Sorted.Sort([](const TPair<FString, int32>& A, const TPair<FString, int32>& B)
	{
		return A.Value != B.Value ? A.Value > B.Value : A.Key < B.Key;
	});
	return Sorted;
}

const TArray<FString>& UOpenStanceMatchModel::GetPenaltyReasons(EOpenStanceSide Side) const
{
	return GetSide(Side).PenaltyReasons;
}

EOpenStanceSide UOpenStanceMatchModel::GetWinner() const
{
	return Sides[0].Score >= Sides[1].Score ? EOpenStanceSide::Chung : EOpenStanceSide::Hong;
}

float UOpenStanceMatchModel::GetSecondsSinceScore(EOpenStanceSide Side) const
{
	return static_cast<float>(ClockSeconds - GetSide(Side).LastScoreTime);
}

int32 UOpenStanceMatchModel::GetLastScorePoints(EOpenStanceSide Side) const
{
	return GetSide(Side).LastScorePoints;
}
