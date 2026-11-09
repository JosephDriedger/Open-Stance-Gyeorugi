#include "Combat/OpenStanceMatchModelSync.h"

#include "Combat/OpenStanceMatchRules.h"

#include "Combat/OpenStanceMatchSim.h"
#include "Combat/OpenStanceMoveData.h"
#include "Engine/DataTable.h"
#include "Menu/OpenStanceMatchModel.h"

namespace
{
	EOpenStanceSide SideOf(int32 Index)
	{
		return Index == 0 ? EOpenStanceSide::Chung : EOpenStanceSide::Hong;
	}

	/** The move's name for the results page, without the "(Head)" the row name carries for the head version. */
	FString MoveName(const UDataTable* Table, FName Row)
	{
		if (Table)
		{
			if (const FOpenStanceMoveRow* Found = Table->FindRow<FOpenStanceMoveRow>(Row, TEXT("MatchModelSync"), false))
			{
				FString Name = Found->DisplayName;
				Name.ReplaceInline(TEXT(" (Head)"), TEXT(""));
				return Name;
			}
		}
		return Row.ToString();
	}
}

void FOpenStanceMatchModelSync::Begin(const FOpenStanceMatchSim& Sim, UOpenStanceMatchModel& Model, const FString& ChungName, const FString& HongName, const UDataTable* MoveTable)
{
	Moves = MoveTable;
	Model.bDemoMode = false;
	Model.Reset(ChungName, HongName);
	Model.SetRules(Sim.RoundRules.RoundCount, Sim.RoundRules.RoundSeconds, Sim.RoundRules.GapToEnd);
	Model.SetClock(Sim.Match.Round, Sim.Match.ClockSeconds);
	Model.SetBreak(Sim.GetPauseSecondsLeft(), Sim.Match.State == EOpenStanceMatchState::Ready);
	if (Sim.Match.State == EOpenStanceMatchState::Ready)
	{
		Model.SetCall(TEXT("CHARYEOT"), TEXT("Attention"));
	}
	SeenRounds = Sim.RoundHistory.Num();
	SeenContacts = Sim.Contacts.Num();
	SeenLog = Sim.LogEventCount;
	SeenPenalties[0] = Sim.Fighters[0].PenaltyReasons.Num();
	SeenPenalties[1] = Sim.Fighters[1].PenaltyReasons.Num();
}

void FOpenStanceMatchModelSync::Update(const FOpenStanceMatchSim& Sim, UOpenStanceMatchModel& Model)
{
	// The clock and round first, so a score or penalty is filed under the round it happened in.
	Model.SetClock(Sim.Match.Round, Sim.Match.ClockSeconds);
	Model.SetBreak(Sim.GetPauseSecondsLeft(), Sim.Match.State == EOpenStanceMatchState::Ready);

	// Referee calls, in the order they happened. The log keeps the last 200 entries, so count from the running total.
	const int32 NewLog = FMath::Min(Sim.LogEventCount - SeenLog, Sim.Log.Num());
	for (int32 Index = Sim.Log.Num() - NewLog; Index < Sim.Log.Num(); ++Index)
	{
		const FString& Text = Sim.Log[Index].Text;
		if (Text == TEXT("charyeot"))
		{
			Model.SetCall(TEXT("CHARYEOT"), TEXT("Attention"));
		}
		else if (Text == TEXT("kyeongrye"))
		{
			Model.SetCall(TEXT("KYEONGRYE"), TEXT("Bow"));
		}
		else if (Text == TEXT("joon-bi"))
		{
			Model.SetCall(TEXT("JOON-BI"), TEXT("Ready"));
		}
		else if (Text == TEXT("woo-se-girok"))
		{
			Model.SetCall(TEXT("WOO-SE-GIROK"), TEXT("Record superiority"));
		}
		else if (Text == TEXT("chung seung"))
		{
			Model.SetCall(TEXT("CHUNG SEUNG"), TEXT("Chung wins"));
		}
		else if (Text == TEXT("hong seung"))
		{
			Model.SetCall(TEXT("HONG SEUNG"), TEXT("Hong wins"));
		}
		else if (Text == TEXT("kal-yeo"))
		{
			Model.SetCall(TEXT("KAL-YEO"), TEXT("Break"));
		}
		else if (Text == TEXT("kye-sok"))
		{
			Model.SetCall(TEXT("KYE-SOK"), TEXT("Continue"));
		}
		else if (Text == TEXT("keu-man"))
		{
			Model.SetCall(TEXT("KEU-MAN"), TEXT("Stop"));
		}
		else if (Text == TEXT("shi-jak"))
		{
			Model.SetCall(TEXT("SHI-JAK"), TEXT("Begin"));
		}
	}
	SeenLog = Sim.LogEventCount;

	// Scores: every contact the hit registry counted, with the technique's name and whether it was to the head.
	for (; SeenContacts < Sim.Contacts.Num(); ++SeenContacts)
	{
		const FOpenStanceContact& Contact = Sim.Contacts[SeenContacts];
		if (Contact.Type == EOpenStanceContactType::Score)
		{
			Model.AddPoints(Contact.Attacker, Contact.Points, MoveName(Moves, Contact.Move), Contact.Zone == EOpenStanceBodyZone::Head);
		}
	}

	// Penalties: a gam-jeom for the fighter, a point for the other (GDD 8.3, 8.4), and the referee's call.
	for (int32 Index = 0; Index < 2; ++Index)
	{
		const TArray<FString>& Reasons = Sim.Fighters[Index].PenaltyReasons;
		for (; SeenPenalties[Index] < Reasons.Num(); ++SeenPenalties[Index])
		{
			Model.AddGamJeom(SideOf(Index), Reasons[SeenPenalties[Index]]);
			Model.AddPoints(SideOf(1 - Index), 1, TEXT("Gam-jeom"), false);
			Model.SetCall(TEXT("GAM-JEOM"), Reasons[SeenPenalties[Index]]);
		}
	}

	for (int32 Index = 0; Index < 2; ++Index)
	{
		const FOpenStanceFighterState& State = Sim.Fighters[Index].State;
		Model.SetStamina(SideOf(Index), State.Stamina / FMath::Max(1.0f, State.MaxStamina));
		// Low stamina is an absolute amount (below 25), not a share of the bar, so the simulation says when it is.
		Model.SetLowStamina(SideOf(Index), State.IsLowStamina());
	}

	// Each round's result, as the simulation decided it (WT rules, GDD 8.2-8.4).
	for (; SeenRounds < Sim.RoundHistory.Num(); ++SeenRounds)
	{
		const FOpenStanceRoundResult& Result = Sim.RoundHistory[SeenRounds];
		Model.SetRoundResult(Result.Round, Result.Winner, FOpenStanceMatchRules::Describe(Result.Reason));
	}

	// The simulation decides when the match is over and who won it; the HUD follows. ForceFinish calls keu-man, so the
	// winner's call goes on after it.
	if (Sim.Match.State == EOpenStanceMatchState::Finished && !Model.IsFinished())
	{
		Model.SetMatchResult(Sim.MatchWinner, FOpenStanceMatchRules::Describe(Sim.MatchEnd));
		Model.SetCall(Sim.MatchWinner == EOpenStanceSide::Chung ? TEXT("CHUNG SEUNG") : TEXT("HONG SEUNG"),
			Sim.MatchWinner == EOpenStanceSide::Chung ? TEXT("Chung wins") : TEXT("Hong wins"));
	}
}
