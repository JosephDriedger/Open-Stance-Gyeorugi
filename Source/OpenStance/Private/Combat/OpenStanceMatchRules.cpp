#include "Combat/OpenStanceMatchRules.h"

namespace
{
	EOpenStanceSide SideOf(int32 Index)
	{
		return Index == 0 ? EOpenStanceSide::Chung : EOpenStanceSide::Hong;
	}
}

void FOpenStanceRoundTally::AddScore(int32 InPoints, bool bHead, bool bPunch, bool bTurning)
{
	Points += InPoints;
	++ProtectorHits;
	if (bPunch)
	{
		PunchPoints += InPoints;
		return;
	}
	if (bHead)
	{
		HeadPoints += InPoints;
	}
	else
	{
		TrunkPoints += InPoints;
	}
	if (bTurning)
	{
		TurningPoints += InPoints;
	}
}

bool FOpenStanceMatchRules::CheckRoundStop(const FOpenStanceRoundTuning& Rules, const FOpenStanceRoundTally Tally[2], EOpenStanceSide& OutWinner, EOpenStanceRoundEnd& OutReason)
{
	// The penalty limit first: the fighter who reaches it loses the round, whatever the score.
	if (Rules.RoundGamJeomLimit > 0)
	{
		for (int32 Index = 0; Index < 2; ++Index)
		{
			if (Tally[Index].GamJeom >= Rules.RoundGamJeomLimit)
			{
				OutWinner = SideOf(1 - Index);
				OutReason = EOpenStanceRoundEnd::PenaltyLimit;
				return true;
			}
		}
	}
	if (Rules.GapToEnd > 0 && FMath::Abs(Tally[0].Points - Tally[1].Points) >= Rules.GapToEnd)
	{
		OutWinner = Tally[0].Points > Tally[1].Points ? EOpenStanceSide::Chung : EOpenStanceSide::Hong;
		OutReason = EOpenStanceRoundEnd::PointGap;
		return true;
	}
	return false;
}

void FOpenStanceMatchRules::DecideAtTime(const FOpenStanceRoundTally Tally[2], EOpenStanceSide RefereeCoin, EOpenStanceSide& OutWinner, EOpenStanceRoundEnd& OutReason)
{
	struct FStep
	{
		int32 FOpenStanceRoundTally::* Field;
		EOpenStanceRoundEnd Reason;
	};
	static const FStep Order[] =
	{
		{ &FOpenStanceRoundTally::Points, EOpenStanceRoundEnd::Points },
		{ &FOpenStanceRoundTally::TurningPoints, EOpenStanceRoundEnd::TieBreakTurning },
		{ &FOpenStanceRoundTally::HeadPoints, EOpenStanceRoundEnd::TieBreakHead },
		{ &FOpenStanceRoundTally::TrunkPoints, EOpenStanceRoundEnd::TieBreakTrunk },
		{ &FOpenStanceRoundTally::PunchPoints, EOpenStanceRoundEnd::TieBreakPunch },
		{ &FOpenStanceRoundTally::GamJeomPoints, EOpenStanceRoundEnd::TieBreakGamJeom },
		{ &FOpenStanceRoundTally::ProtectorHits, EOpenStanceRoundEnd::TieBreakProtectorHits },
		{ &FOpenStanceRoundTally::ActiveAttacks, EOpenStanceRoundEnd::RefereeDecision },
	};
	for (const FStep& Step : Order)
	{
		const int32 A = Tally[0].*Step.Field;
		const int32 B = Tally[1].*Step.Field;
		if (A != B)
		{
			OutWinner = A > B ? EOpenStanceSide::Chung : EOpenStanceSide::Hong;
			OutReason = Step.Reason;
			return;
		}
	}
	OutWinner = RefereeCoin;
	OutReason = EOpenStanceRoundEnd::RefereeDecision;
}

FString FOpenStanceMatchRules::Describe(EOpenStanceRoundEnd Reason)
{
	switch (Reason)
	{
	case EOpenStanceRoundEnd::Points: return TEXT("Points");
	case EOpenStanceRoundEnd::PointGap: return TEXT("Point gap");
	case EOpenStanceRoundEnd::PenaltyLimit: return TEXT("Gam-jeom limit");
	case EOpenStanceRoundEnd::TieBreakTurning: return TEXT("Tie-break: turning kicks");
	case EOpenStanceRoundEnd::TieBreakHead: return TEXT("Tie-break: head points");
	case EOpenStanceRoundEnd::TieBreakTrunk: return TEXT("Tie-break: trunk points");
	case EOpenStanceRoundEnd::TieBreakPunch: return TEXT("Tie-break: punch points");
	case EOpenStanceRoundEnd::TieBreakGamJeom: return TEXT("Tie-break: gam-jeom points");
	case EOpenStanceRoundEnd::TieBreakProtectorHits: return TEXT("Tie-break: protector hits");
	case EOpenStanceRoundEnd::RefereeDecision: return TEXT("Referee's decision");
	case EOpenStanceRoundEnd::MatchPenaltyLimit: return TEXT("Match gam-jeom limit");
	default: return TEXT("-");
	}
}
