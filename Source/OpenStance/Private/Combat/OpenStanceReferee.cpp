#include "Combat/OpenStanceReferee.h"

#include "Combat/OpenStanceMatchSim.h"

namespace
{
	using P = EOpenStanceRefereePose;

	const TCHAR* SideName(EOpenStanceSide Side)
	{
		return Side == EOpenStanceSide::Chung ? TEXT("Chung") : TEXT("Hong");
	}

	FVector2D Spot(const FOpenStanceFighterSim& F)
	{
		return F.Motion.Position;
	}

	FVector2D ClampToCircle(const FVector2D& Point, float Radius)
	{
		const double Length = Point.Size();
		return Length > Radius ? Point * (Radius / Length) : Point;
	}
}

const TCHAR* FOpenStanceReferee::GetRefereeName(int32 Index)
{
	static const TCHAR* Names[RefereeCount] = { TEXT("Bo"), TEXT("Jorge"), TEXT("Kelvin"), TEXT("Omari"), TEXT("Vivian"), TEXT("Walter") };
	return Names[FMath::Clamp(Index, 0, RefereeCount - 1)];
}

bool FOpenStanceReferee::CallFor(const FOpenStanceMatchLogEntry& Entry, FOpenStanceRefereeCall& OutCall)
{
	struct FPlain
	{
		const TCHAR* Log;
		const TCHAR* Term;
		const TCHAR* Meaning;
		const TCHAR* Cue;
		P Pose;
	};
	// GDD 8.5: the commands and their English meanings.
	static const FPlain Plain[] =
	{
		{ TEXT("charyeot"), TEXT("CHARYEOT"), TEXT("Attention"), TEXT("Charyeot"), P::Attention },
		{ TEXT("kyeongrye"), TEXT("KYEONGRYE"), TEXT("Bow"), TEXT("Kyeongrye"), P::Bow },
		{ TEXT("joon-bi"), TEXT("JOON-BI"), TEXT("Ready"), TEXT("JoonBi"), P::Ready },
		{ TEXT("shi-jak"), TEXT("SHI-JAK"), TEXT("Begin"), TEXT("ShiJak"), P::Start },
		{ TEXT("kal-yeo"), TEXT("KAL-YEO"), TEXT("Break"), TEXT("KalYeo"), P::Separate },
		{ TEXT("kye-sok"), TEXT("KYE-SOK"), TEXT("Continue"), TEXT("KyeSok"), P::Start },
		{ TEXT("keu-man"), TEXT("KEU-MAN"), TEXT("Stop"), TEXT("KeuMan"), P::Stop },
		{ TEXT("gong-gyeok"), TEXT("GONG-GYEOK"), TEXT("Attack"), TEXT("GongGyeok"), P::Start },
		{ TEXT("woo-se-girok"), TEXT("WOO-SE-GIROK"), TEXT("Record superiority"), TEXT("WooSeGirok"), P::Stop },
	};
	for (const FPlain& Row : Plain)
	{
		if (Entry.Text == Row.Log)
		{
			OutCall = FOpenStanceRefereeCall();
			OutCall.Term = Row.Term;
			OutCall.Meaning = Row.Meaning;
			OutCall.Cue = Row.Cue;
			OutCall.Pose = Row.Pose;
			return true;
		}
	}

	// Calls that name the side: the penalty, the count over a fighter, the winner.
	if (Entry.Text.StartsWith(TEXT("gam-jeom: ")))
	{
		OutCall = FOpenStanceRefereeCall();
		OutCall.Term = TEXT("GAM-JEOM");
		FString Reason = Entry.Text.RightChop(10);
		Reason = Reason.Left(1).ToUpper() + Reason.RightChop(1);
		OutCall.Meaning = FString::Printf(TEXT("%s, %s"), SideName(Entry.Side), *Reason);
		OutCall.Cue = Entry.Side == EOpenStanceSide::Chung ? TEXT("ChungGamJeom") : TEXT("HongGamJeom");
		OutCall.Pose = P::Point;
		OutCall.bNamesSide = true;
		OutCall.Side = Entry.Side;
		return true;
	}
	if (Entry.Text.StartsWith(TEXT("count ")))
	{
		static const TCHAR* Korean[] = { TEXT("HANA"), TEXT("DUL"), TEXT("SET"), TEXT("NET"), TEXT("DASEOT"), TEXT("YEOSEOT"), TEXT("ILGOP"), TEXT("YEODEOL") };
		static const TCHAR* English[] = { TEXT("One"), TEXT("Two"), TEXT("Three"), TEXT("Four"), TEXT("Five"), TEXT("Six"), TEXT("Seven"), TEXT("Eight") };
		const int32 N = FCString::Atoi(*Entry.Text.RightChop(6));
		if (N < 1 || N > 8)
		{
			return false;
		}
		OutCall = FOpenStanceRefereeCall();
		OutCall.Term = Korean[N - 1];
		OutCall.Meaning = English[N - 1];
		OutCall.Cue = FName(*FString::Printf(TEXT("Count%d"), N));
		OutCall.Pose = P::Count;
		OutCall.bNamesSide = true;
		OutCall.Side = Entry.Side;
		return true;
	}
	if (Entry.Text == TEXT("chung seung") || Entry.Text == TEXT("hong seung"))
	{
		const bool bChung = Entry.Text == TEXT("chung seung");
		OutCall = FOpenStanceRefereeCall();
		OutCall.Term = bChung ? TEXT("CHUNG SEUNG") : TEXT("HONG SEUNG");
		OutCall.Meaning = bChung ? TEXT("Chung wins") : TEXT("Hong wins");
		OutCall.Cue = bChung ? TEXT("ChungSeung") : TEXT("HongSeung");
		OutCall.Pose = P::RaiseWinner;
		OutCall.bNamesSide = true;
		OutCall.Side = bChung ? EOpenStanceSide::Chung : EOpenStanceSide::Hong;
		return true;
	}
	return false;
}

void FOpenStanceReferee::Reset(const FOpenStanceMatchSim& Sim, int32 PlayerIndex, int32 Seed)
{
	FRandomStream Random(Seed);
	RefereeIndex = Random.RandRange(0, RefereeCount - 1);
	Pose = P::Idle;
	PoseElapsed = 0.0f;
	bGestureRight = true;
	bHasNamedSide = false;
	SeenLog = 0;
	NewCalls.Reset();
	Queued.Reset();
	Position = GetTarget(Sim, PlayerIndex);
	const FVector2D Mid = (Spot(Sim.Fighters[0]) + Spot(Sim.Fighters[1])) * 0.5;
	Facing = (Mid - Position).GetSafeNormal();
	if (Facing.IsNearlyZero())
	{
		Facing = FVector2D(1.0, 0.0);
	}
}

FVector2D FOpenStanceReferee::GetTarget(const FOpenStanceMatchSim& Sim, int32 PlayerIndex) const
{
	const FVector2D Player = Spot(Sim.Fighters[PlayerIndex]);
	const FVector2D Opponent = Spot(Sim.Fighters[1 - PlayerIndex]);
	const FVector2D Mid = (Player + Opponent) * 0.5;
	FVector2D Line = (Opponent - Player).GetSafeNormal();
	if (Line.IsNearlyZero())
	{
		Line = FVector2D(1.0, 0.0);
	}
	// The combat camera sits out to the player's right of the line (OpenStanceCameraPresets): the referee takes the
	// other side, so it never stands between the camera and the fighters.
	const FVector2D Right(-Line.Y, Line.X);
	const FVector2D Away = -Right;

	FVector2D Target;
	if (Sim.IsCounting())
	{
		// Over the fighter on the floor, on the far side.
		Target = Spot(Sim.Fighters[Sim.GetCountedFighter()]) + Away * Tuning.CountOffCm;
	}
	else if (Sim.IsInClinch() || Pose == P::Separate)
	{
		// Kal-yeo: step in between them.
		Target = Mid + Away * Tuning.SeparateOffCm;
	}
	else
	{
		Target = Mid + Away * Tuning.StandOffCm;
		// Clear of the exchange: never right on top of a fighter, even when they are far apart.
		for (const FOpenStanceFighterSim& F : Sim.Fighters)
		{
			const FVector2D Off = Target - Spot(F);
			if (Off.Size() < Tuning.ClearOfFighterCm)
			{
				Target = Spot(F) + Off.GetSafeNormal(UE_SMALL_NUMBER) * Tuning.ClearOfFighterCm;
			}
		}
	}
	return ClampToCircle(Target, Tuning.MatLimitCm);
}

void FOpenStanceReferee::Show(const FOpenStanceRefereeCall& Call)
{
	Pose = Call.Pose;
	PoseElapsed = 0.0f;
	bHasNamedSide = Call.bNamesSide;
	NamedSide = Call.Side;
}

float FOpenStanceReferee::MinShowSeconds() const
{
	return Pose == P::RaiseWinner ? Tuning.RaiseWinnerSeconds : Tuning.MinGestureSeconds;
}

void FOpenStanceReferee::Update(float DeltaSeconds, const FOpenStanceMatchSim& Sim, int32 PlayerIndex)
{
	NewCalls.Reset();

	// New commands in the log, in order (the log keeps the last 200: count from the running total).
	if (SeenLog > Sim.LogEventCount)
	{
		SeenLog = 0; // a new match
	}
	const int32 Fresh = FMath::Min(Sim.LogEventCount - SeenLog, Sim.Log.Num());
	for (int32 Index = Sim.Log.Num() - Fresh; Index < Sim.Log.Num(); ++Index)
	{
		FOpenStanceRefereeCall Call;
		if (CallFor(Sim.Log[Index], Call))
		{
			NewCalls.Add(Call);
			// The same gesture again (the next count) carries on; a new one replaces the current once it has been seen,
			// and calls made together play in turn.
			if (Queued.IsEmpty() && Call.Pose == Pose && Call.bNamesSide == bHasNamedSide && Call.Side == NamedSide)
			{
				PoseElapsed = 0.0f;
			}
			else if (Queued.IsEmpty() && (Pose == P::Idle || PoseElapsed >= MinShowSeconds()))
			{
				Show(Call);
			}
			else
			{
				Queued.Add(Call);
			}
		}
	}
	SeenLog = Sim.LogEventCount;

	PoseElapsed += DeltaSeconds;
	if (!Queued.IsEmpty() && PoseElapsed >= MinShowSeconds())
	{
		Show(Queued[0]);
		Queued.RemoveAt(0);
	}

	// A gesture holds, then the referee is back at ease. A count holds through the count, a separation through the stop,
	// the winner's hand stays up while the match is over.
	const bool bHeld = !Queued.IsEmpty() || (Pose == P::Count && Sim.IsCounting())
		|| (Pose == P::Separate && Sim.Match.State == EOpenStanceMatchState::Stopped)
		|| (Pose == P::RaiseWinner && Sim.Match.State == EOpenStanceMatchState::Finished)
		|| (Pose == P::Attention && Sim.Match.State == EOpenStanceMatchState::Ready);
	if (!bHeld && Pose != P::Idle && PoseElapsed >= Tuning.GestureSeconds)
	{
		Pose = P::Idle;
		bHasNamedSide = false;
	}

	// Walk toward the spot for this moment, at walking pace.
	const FVector2D Target = GetTarget(Sim, PlayerIndex);
	const FVector2D Step = Target - Position;
	const double MaxStep = Tuning.WalkCmPerSecond * DeltaSeconds;
	Position = Step.Size() <= MaxStep ? Target : Position + Step.GetSafeNormal() * MaxStep;

	// Face the fighters, or the one being counted; gesture with the arm on the named fighter's side.
	const FVector2D Mid = (Spot(Sim.Fighters[0]) + Spot(Sim.Fighters[1])) * 0.5;
	const FVector2D Look = Sim.IsCounting() ? Spot(Sim.Fighters[Sim.GetCountedFighter()]) : Mid;
	const FVector2D ToLook = (Look - Position).GetSafeNormal();
	if (!ToLook.IsNearlyZero())
	{
		Facing = ToLook;
	}
	if (bHasNamedSide)
	{
		const FVector2D Named = Spot(Sim.Fighters[NamedSide == EOpenStanceSide::Chung ? 0 : 1]);
		const FVector2D RefRight(-Facing.Y, Facing.X);
		bGestureRight = FVector2D::DotProduct(Named - Position, RefRight) >= 0.0;
	}
	else
	{
		bGestureRight = true;
	}
}
