#include "Combat/OpenStanceCombatOverlay.h"

namespace
{
	const TCHAR* DirText(EOpenStanceStickDir Dir)
	{
		switch (Dir)
		{
		case EOpenStanceStickDir::Up: return TEXT("Up");
		case EOpenStanceStickDir::Down: return TEXT("Down");
		case EOpenStanceStickDir::Left: return TEXT("Left");
		case EOpenStanceStickDir::Right: return TEXT("Right");
		default: return TEXT("Neutral");
		}
	}

	const TCHAR* GuardText(EOpenStanceGuard Guard)
	{
		switch (Guard)
		{
		case EOpenStanceGuard::High: return TEXT("High");
		case EOpenStanceGuard::Cross: return TEXT("Cross");
		case EOpenStanceGuard::Mixed: return TEXT("Mixed");
		default: return TEXT("Low");
		}
	}

	const TCHAR* TechniqueText(EOpenStanceTechnique Technique)
	{
		switch (Technique)
		{
		case EOpenStanceTechnique::SideKick: return TEXT("Side Kick");
		case EOpenStanceTechnique::Roundhouse: return TEXT("Roundhouse");
		case EOpenStanceTechnique::Hook: return TEXT("Hook Kick");
		case EOpenStanceTechnique::Axe: return TEXT("Axe Kick");
		case EOpenStanceTechnique::SpinSide: return TEXT("Spin Side Kick");
		case EOpenStanceTechnique::SpinHook: return TEXT("Spin Hook Kick");
		case EOpenStanceTechnique::Tornado: return TEXT("Tornado Kick");
		case EOpenStanceTechnique::Punch: return TEXT("Punch");
		default: return TEXT("None");
		}
	}

	FString LegWords(const FOpenStanceInputEvent& Event)
	{
		return FString::Printf(TEXT("%s (%s)"), Event.Leg == EOpenStanceLegSide::Left ? TEXT("Left") : TEXT("Right"), Event.LegRole == EOpenStanceLegRole::Back ? TEXT("back") : TEXT("lead"));
	}
}

FString FOpenStanceCombatOverlay::StateName(EOpenStanceCombatState State)
{
	switch (State)
	{
	case EOpenStanceCombatState::IdleMovement: return TEXT("Idle");
	case EOpenStanceCombatState::AttackStartup: return TEXT("Attack Startup");
	case EOpenStanceCombatState::AttackActive: return TEXT("Attack Active");
	case EOpenStanceCombatState::AttackRecovery: return TEXT("Attack Recovery");
	case EOpenStanceCombatState::ActiveDefense: return TEXT("Active Defense");
	case EOpenStanceCombatState::HitReaction: return TEXT("Hit Reaction");
	case EOpenStanceCombatState::Staggered: return TEXT("Staggered");
	case EOpenStanceCombatState::KnockedDown: return TEXT("Knocked Down");
	case EOpenStanceCombatState::Recovering: return TEXT("Recovering");
	default: return TEXT("Match Finished");
	}
}

FString FOpenStanceCombatOverlay::HeldButtons(const FOpenStanceFighterState& State)
{
	TArray<FString> Held;
	if (State.bBackLegHeld) { Held.Add(TEXT("RT")); }
	if (State.bHeadHeld) { Held.Add(TEXT("RB")); }
	if (State.bFakeHeld) { Held.Add(TEXT("LB")); }
	if (State.bDefenseHeld) { Held.Add(TEXT("LT")); }
	if (State.bJumpPrimed) { Held.Add(TEXT("Y(primed)")); }
	return Held.Num() ? FString::Join(Held, TEXT(" ")) : FString(TEXT("-"));
}

FString FOpenStanceCombatOverlay::StickHistory(const FOpenStanceSkillStickRecognizer& Recognizer)
{
	TArray<FString> Steps;
	for (const FOpenStanceStickStep& Step : Recognizer.GetStepHistory())
	{
		Steps.Add(DirText(Step.Dir));
	}
	return Steps.Num() ? FString::Join(Steps, TEXT(" > ")) : FString(TEXT("-"));
}

FString FOpenStanceCombatOverlay::DescribeInput(const FOpenStanceInputEvent& Event)
{
	switch (Event.Type)
	{
	case EOpenStanceInputEventType::Attack:
		return FString::Printf(TEXT("%s%s, %s, %s%s"), Event.bFake ? TEXT("Fake: ") : TEXT("Attack: "), TechniqueText(Event.Technique), *LegWords(Event),
			Event.Target == EOpenStanceTarget::Head ? TEXT("Head") : TEXT("Trunk"), Event.bJump ? TEXT(", jump") : TEXT(""));
	case EOpenStanceInputEventType::GenericFake:
		return TEXT("Fake attack");
	case EOpenStanceInputEventType::Defense:
		return FString::Printf(TEXT("Defense: %s"), Event.DefenseKind == EOpenStanceDefenseKind::HighBlock ? TEXT("high block") : Event.DefenseKind == EOpenStanceDefenseKind::LegCheck ? TEXT("leg check") : TEXT("sway"));
	case EOpenStanceInputEventType::JumpPrimed:
		return TEXT("Jump primed");
	case EOpenStanceInputEventType::JumpPrimeExpired:
		return TEXT("Jump prime expired");
	case EOpenStanceInputEventType::GestureRejected:
		return FString::Printf(TEXT("Rejected: %s"), *Event.Path);
	case EOpenStanceInputEventType::GestureExpired:
		return FString::Printf(TEXT("Expired: %s"), *Event.Path);
	default:
		return TEXT("Cancelled by LT");
	}
}

TArray<FString> FOpenStanceCombatOverlay::BuildLines(const FOpenStanceMatchSim& Sim, int32 FighterIndex, bool bPlayerFacing)
{
	const FOpenStanceFighterSim& F = Sim.Fighters[FighterIndex];
	TArray<FString> Lines;
	const TCHAR* Name = F.Side == EOpenStanceSide::Chung ? TEXT("CHUNG") : TEXT("HONG");

	const FString Last = F.RecentInput.Num() ? DescribeInput(F.RecentInput.Last()) : FString(TEXT("-"));
	if (bPlayerFacing)
	{
		// Training only: controller input, leg, move, target, stamina and hit result (GDD 7.6).
		Lines.Add(FString::Printf(TEXT("%s"), Name));
		Lines.Add(FString::Printf(TEXT("Input: %s"), *Last));
		Lines.Add(FString::Printf(TEXT("Leg: %s"), *F.LastLeg));
		Lines.Add(FString::Printf(TEXT("Move: %s"), *F.LastMove));
		Lines.Add(FString::Printf(TEXT("Target: %s"), *F.LastTarget));
		Lines.Add(FString::Printf(TEXT("Stamina: %.0f"), F.State.Stamina));
		Lines.Add(FString::Printf(TEXT("Result: %s"), *F.LastResult));
		return Lines;
	}

	Lines.Add(FString::Printf(TEXT("%s  score %d  gam-jeom %d"), Name, F.State.Score, F.State.GamJeom));
	Lines.Add(FString::Printf(TEXT("%s | %s guard | %s%s"), F.State.Stance == EOpenStanceStance::LeftLead ? TEXT("Left Lead") : TEXT("Right Lead"),
		GuardText(F.State.Guard), *StateName(F.State.CombatState), F.Motion.bSwitching ? TEXT(" | switching sides") : TEXT("")));
	Lines.Add(FString::Printf(TEXT("Held: %s"), *HeldButtons(F.State)));
	Lines.Add(FString::Printf(TEXT("Stick: %s"), *StickHistory(F.Recognizer)));
	Lines.Add(FString::Printf(TEXT("Input: %s"), *Last));

	// The last few gestures, so a rejected or expired one stays visible after the stick moves on.
	const int32 First = FMath::Max(0, F.RecentInput.Num() - 4);
	for (int32 Index = F.RecentInput.Num() - 2; Index >= First; --Index)
	{
		Lines.Add(FString::Printf(TEXT("  before: %s"), *DescribeInput(F.RecentInput[Index])));
	}

	Lines.Add(FString::Printf(TEXT("Leg: %s | Move: %s | Target: %s"), *F.LastLeg, *F.LastMove, *F.LastTarget));
	Lines.Add(FString::Printf(TEXT("Stamina: %.0f%s"), F.State.Stamina, F.State.IsLowStamina() ? TEXT(" (low)") : TEXT("")));
	Lines.Add(FString::Printf(TEXT("Result: %s"), *F.LastResult));

	const FOpenStanceTraceDebug& Trace = F.Registry.GetLastTrace();
	if (Trace.bEvaluated)
	{
		const TCHAR* Zone = Trace.ZoneHit == EOpenStanceBodyZone::Head ? TEXT("head") : Trace.ZoneHit == EOpenStanceBodyZone::Trunk ? TEXT("trunk")
			: Trace.ZoneHit == EOpenStanceBodyZone::BelowBelt ? TEXT("below belt") : TEXT("none");
		Lines.Add(FString::Printf(TEXT("Trace: %s%s"), Zone, Trace.Ignored.IsEmpty() ? TEXT("") : *FString::Printf(TEXT(" (%s)"), *Trace.Ignored)));
	}
	else if (!Trace.Ignored.IsEmpty())
	{
		Lines.Add(FString::Printf(TEXT("Trace: off (%s)"), *Trace.Ignored));
	}
	return Lines;
}
