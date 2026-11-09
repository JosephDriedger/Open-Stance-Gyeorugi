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
	RoundOutcomes.Reset();
	RoundCount = DefaultRoundCount;
	RoundSeconds = DefaultRoundSeconds;
	PointGap = DefaultPointGap;
	bHasMatchResult = false;
	MatchWinner = EOpenStanceSide::Chung;
	MatchReason.Reset();
	BreakSecondsLeft = 0.0f;
	bCeremony = false;
	Round = 1;
	TimeRemaining = RoundSeconds;
	bPaused = false;
	bFinished = false;
	CallTerm = TEXT("SHI-JAK");
	CallMeaning = TEXT("Begin");
}

void UOpenStanceMatchModel::SetRules(int32 InRoundCount, float InRoundSeconds, int32 InPointGap)
{
	RoundCount = FMath::Max(1, InRoundCount);
	RoundSeconds = FMath::Max(1.0f, InRoundSeconds);
	PointGap = FMath::Max(0, InPointGap);
	TimeRemaining = FMath::Min(TimeRemaining, RoundSeconds);
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
	Score(EOpenStanceSide::Chung, 1, 4, TEXT("Spinning Hook"), false);
	Score(EOpenStanceSide::Hong, 1, 2, TEXT("Back Kick"), false);
	Score(EOpenStanceSide::Chung, 2, 3, TEXT("Axe Kick"), true);
	Score(EOpenStanceSide::Hong, 2, 4, TEXT("Back Kick"), false);
	Score(EOpenStanceSide::Chung, 3, 2, TEXT("Roundhouse"), false);
	Score(EOpenStanceSide::Chung, 3, 1, TEXT("Punch"), false);
	Score(EOpenStanceSide::Chung, 3, 2, TEXT("Roundhouse"), false);
	Score(EOpenStanceSide::Hong, 3, 1, TEXT("Punch"), false);
	AddGamJeom(EOpenStanceSide::Hong, TEXT("Grabbing"));
	SetRoundResult(1, EOpenStanceSide::Chung, TEXT("Points"));
	SetRoundResult(2, EOpenStanceSide::Hong, TEXT("Points"));
	SetRoundResult(3, EOpenStanceSide::Chung, TEXT("Points"));
	Round = RoundCount;
	TimeRemaining = 0.0f;
	bHasMatchResult = true;
	MatchWinner = EOpenStanceSide::Chung;
	MatchReason = TEXT("Points");
	bFinished = true;
}

bool UOpenStanceMatchModel::Advance(float DeltaSeconds)
{
	ClockSeconds += DeltaSeconds;
	if (bPaused || bFinished)
	{
		return false;
	}

	const bool bWasFinished = bFinished;
	TimeRemaining -= DeltaSeconds;
	if (TimeRemaining <= 0.0f)
	{
		// The demo's round goes to the higher score; a level one to Chung, standing in for the referee's decision.
		TimeRemaining = 0.0f;
		const int32 Chung = GetScore(EOpenStanceSide::Chung);
		const int32 Hong = GetScore(EOpenStanceSide::Hong);
		EndDemoRound(Hong > Chung ? EOpenStanceSide::Hong : EOpenStanceSide::Chung, Chung == Hong ? TEXT("Referee's decision") : TEXT("Points"));
	}
	return bFinished && !bWasFinished;
}

void UOpenStanceMatchModel::CheckForEnd()
{
	// Gameplay decides rounds and the match itself and tells the model; only the demo decides here.
	if (!bDemoMode || bFinished)
	{
		return;
	}
	const int32 Chung = GetScore(EOpenStanceSide::Chung);
	const int32 Hong = GetScore(EOpenStanceSide::Hong);
	if (PointGap > 0 && FMath::Abs(Chung - Hong) >= PointGap)
	{
		EndDemoRound(Chung > Hong ? EOpenStanceSide::Chung : EOpenStanceSide::Hong, TEXT("Point gap"));
	}
}

void UOpenStanceMatchModel::EndDemoRound(EOpenStanceSide Winner, const FString& Reason)
{
	SetRoundResult(Round, Winner, Reason);
	const int32 ToWin = RoundCount / 2 + 1;
	if (GetRoundWins(Winner) >= ToWin || Round >= RoundCount)
	{
		SetMatchResult(GetRoundWins(EOpenStanceSide::Hong) > GetRoundWins(EOpenStanceSide::Chung) ? EOpenStanceSide::Hong : EOpenStanceSide::Chung, Reason);
		return;
	}
	++Round;
	TimeRemaining = RoundSeconds;
	SetCall(TEXT("SHI-JAK"), TEXT("Begin"));
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

	// The call names the scoring category, which the points decide: 6 spinning head, 4 spinning body, 3 head, 2 body, 1 punch (GDD 8.3).
	const TCHAR* Category = TEXT("Point");
	switch (Points)
	{
	case 6: Category = TEXT("Spin Head Kick"); break;
	case 4: Category = TEXT("Spin Body Kick"); break;
	case 3: Category = TEXT("Head Kick"); break;
	case 2: Category = TEXT("Body Kick"); break;
	case 1: Category = Technique == TEXT("Punch") ? TEXT("Punch") : TEXT("Point"); break;
	default: break;
	}
	SetCall(Category, FString::Printf(TEXT("%d %s"), Points, Points == 1 ? TEXT("Point") : TEXT("Points")), TEXT(" · "));
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
	State.PenaltyRounds.Add(Round);
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

void UOpenStanceMatchModel::ForceFinish()
{
	if (bFinished)
	{
		return;
	}
	bFinished = true;
	BreakSecondsLeft = 0.0f;
	SetCall(TEXT("KEU-MAN"), TEXT("Stop"));
	OnFinished.Broadcast();
}

void UOpenStanceMatchModel::SetRoundResult(int32 InRound, EOpenStanceSide Winner, const FString& Reason)
{
	for (FOpenStanceRoundOutcome& Outcome : RoundOutcomes)
	{
		if (Outcome.Round == InRound)
		{
			Outcome.Winner = Winner;
			Outcome.Reason = Reason;
			return;
		}
	}
	FOpenStanceRoundOutcome& Outcome = RoundOutcomes.AddDefaulted_GetRef();
	Outcome.Round = InRound;
	Outcome.Winner = Winner;
	Outcome.Reason = Reason;
}

void UOpenStanceMatchModel::SetMatchResult(EOpenStanceSide Winner, const FString& Reason)
{
	bHasMatchResult = true;
	MatchWinner = Winner;
	MatchReason = Reason;
	ForceFinish();
}

void UOpenStanceMatchModel::SetBreak(float SecondsLeft, bool bInCeremony)
{
	BreakSecondsLeft = FMath::Max(0.0f, SecondsLeft);
	bCeremony = bInCeremony && BreakSecondsLeft > 0.0f;
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
	return GetRoundScore(Side, Round);
}

int32 UOpenStanceMatchModel::GetTotalScore(EOpenStanceSide Side) const
{
	return GetSide(Side).Score;
}

int32 UOpenStanceMatchModel::GetRoundWins(EOpenStanceSide Side) const
{
	int32 Wins = 0;
	for (const FOpenStanceRoundOutcome& Outcome : RoundOutcomes)
	{
		Wins += Outcome.Winner == Side ? 1 : 0;
	}
	return Wins;
}

const FOpenStanceRoundOutcome* UOpenStanceMatchModel::GetRoundOutcome(int32 InRound) const
{
	return RoundOutcomes.FindByPredicate([InRound](const FOpenStanceRoundOutcome& Outcome) { return Outcome.Round == InRound; });
}

float UOpenStanceMatchModel::GetStamina(EOpenStanceSide Side) const
{
	return GetSide(Side).Stamina;
}

int32 UOpenStanceMatchModel::GetGamJeom(EOpenStanceSide Side) const
{
	int32 Count = 0;
	for (const int32 PenaltyRound : GetSide(Side).PenaltyRounds)
	{
		Count += PenaltyRound == Round ? 1 : 0;
	}
	return Count;
}

int32 UOpenStanceMatchModel::GetMatchGamJeom(EOpenStanceSide Side) const
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
	// Round wins decide a match, never total points (GDD 8.2); totals only stand in before any round has a result.
	if (bHasMatchResult)
	{
		return MatchWinner;
	}
	const int32 ChungWins = GetRoundWins(EOpenStanceSide::Chung);
	const int32 HongWins = GetRoundWins(EOpenStanceSide::Hong);
	if (ChungWins != HongWins)
	{
		return ChungWins > HongWins ? EOpenStanceSide::Chung : EOpenStanceSide::Hong;
	}
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
