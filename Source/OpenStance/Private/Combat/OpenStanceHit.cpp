#include "Combat/OpenStanceHit.h"

#include "Combat/OpenStanceFootwork.h"

void FOpenStanceHitRegistry::Reset()
{
	Serial = -1;
	bConsumed = false;
	Debug = FOpenStanceTraceDebug();
}

void FOpenStanceHitRegistry::GetZoneBounds(const FOpenStanceFighterBody& Body, EOpenStanceBodyZone Zone, const FOpenStanceHitTuning& Tuning, float& OutBottom, float& OutTop, float& OutRadius)
{
	const float Height = Body.HeightCm;
	switch (Zone)
	{
	case EOpenStanceBodyZone::Head:
		OutBottom = Height * Tuning.HeadBottomFraction;
		OutTop = Height;
		OutRadius = Height * Tuning.HeadRadiusFraction;
		break;
	case EOpenStanceBodyZone::Trunk:
		OutBottom = Height * Tuning.BeltLineFraction;
		OutTop = Height * Tuning.HeadBottomFraction;
		OutRadius = Height * Tuning.TrunkRadiusFraction;
		break;
	default:
		OutBottom = 0.0f;
		OutTop = Height * Tuning.BeltLineFraction;
		OutRadius = Height * Tuning.BelowBeltRadiusFraction;
		break;
	}
}

EOpenStanceBodyZone FOpenStanceHitRegistry::FindContact(const FOpenStanceLimbTrace& Trace, const FOpenStanceFighterBody& Body, const FOpenStanceHitTuning& Tuning, FVector& OutPoint)
{
	const float LimbRadius = Trace.Limb == EOpenStanceStrikeLimb::Glove ? Tuning.GloveRadiusCm : Tuning.FootGuardRadiusCm;
	const int32 Samples = FMath::Max(Tuning.SamplesPerTrace, 2);
	const float BeltLine = Body.HeightCm * Tuning.BeltLineFraction;
	const float HeadBottom = Body.HeightCm * Tuning.HeadBottomFraction;

	// Walk the sweep from its start; the first sample inside a zone decides, so a trace meets the zone it enters first.
	for (int32 Index = 0; Index < Samples; ++Index)
	{
		const float Alpha = static_cast<float>(Index) / static_cast<float>(Samples - 1);
		const FVector Point = FMath::Lerp(Trace.Start, Trace.End, Alpha);
		const float Height = Point.Z - Body.Root.Z;
		if (Height < -Tuning.AlignmentToleranceCm || Height > Body.HeightCm + Tuning.AlignmentToleranceCm)
		{
			continue;
		}

		// The height picks the zone; the alignment tolerance only widens it sideways and at the very top and bottom.
		const EOpenStanceBodyZone Zone = Height >= HeadBottom ? EOpenStanceBodyZone::Head
			: Height >= BeltLine ? EOpenStanceBodyZone::Trunk
			: EOpenStanceBodyZone::BelowBelt;

		float Bottom, Top, Radius;
		GetZoneBounds(Body, Zone, Tuning, Bottom, Top, Radius);
		const float Horizontal = static_cast<float>(FVector2D::Distance(FVector2D(Point.X, Point.Y), FVector2D(Body.Root.X, Body.Root.Y)));
		if (Horizontal <= Radius + LimbRadius + Tuning.AlignmentToleranceCm)
		{
			OutPoint = Point;
			return Zone;
		}
	}
	return EOpenStanceBodyZone::None;
}

FVector FOpenStanceHitRegistry::SyntheticTip(const FOpenStanceFighterBody& Attacker, const FVector& FacingXY, const FOpenStanceMoveRow& Row, float Progress, const FOpenStanceHitTuning& Tuning)
{
	const float Alpha = FMath::Clamp(Progress, 0.0f, 1.0f);
	const float Smooth = Alpha * Alpha * (3.0f - 2.0f * Alpha);
	const FOpenStanceMovementTuning Movement;
	const float Reach = FOpenStanceFootwork::ScaleReachCm(Row.ReachCm, Attacker.HeightCm, Movement);
	const bool bHead = Row.Target == EOpenStanceTarget::Head;
	const float Height = Attacker.HeightCm * (bHead ? 0.90f : 0.70f);
	const FVector Direction = FVector(FacingXY.X, FacingXY.Y, 0.0).GetSafeNormal();
	return FVector(Attacker.Root.X, Attacker.Root.Y, Attacker.Root.Z + Height) + Direction * (Reach * Smooth);
}

bool FOpenStanceHitRegistry::Trace(const FOpenStanceHitContext& Context, TArray<FOpenStanceContact>& OutContacts)
{
	Debug = FOpenStanceTraceDebug();
	Debug.Start = Context.Trace.Start;
	Debug.End = Context.Trace.End;

	// Startup, recovery, fakes, stopped play and finished matches never register: the machine says so.
	if (!Context.bCanScore || !Context.Attack)
	{
		Debug.Ignored = TEXT("not a real technique's active phase");
		return false;
	}
	Debug.bEvaluated = true;

	if (Context.AttackSerial != Serial)
	{
		Serial = Context.AttackSerial;
		bConsumed = false;
	}
	if (bConsumed)
	{
		Debug.Ignored = TEXT("this technique already registered a contact");
		return false;
	}

	const FOpenStanceMoveRow& Row = Context.Attack->Row;

	// Range: the technique reaches as far as its row says for this fighter's height, and no further. The alignment
	// tolerance and the defender's own width are the only slack, so an attack thrown from too far never connects.
	const FOpenStanceMovementTuning Movement;
	const float Reach = FOpenStanceFootwork::ScaleReachCm(Row.ReachCm, Context.Attacker.HeightCm, Movement);
	const float Gap = static_cast<float>(FVector2D::Distance(FVector2D(Context.Attacker.Root.X, Context.Attacker.Root.Y), FVector2D(Context.Defender.Root.X, Context.Defender.Root.Y)));
	float Bottom, Top, TrunkRadius;
	GetZoneBounds(Context.Defender, EOpenStanceBodyZone::Trunk, Tuning, Bottom, Top, TrunkRadius);
	if (Gap > Reach + TrunkRadius + Tuning.AlignmentToleranceCm)
	{
		Debug.bOutOfRange = true;
		Debug.Ignored = TEXT("out of range");
		return false;
	}

	FVector Point = FVector::ZeroVector;
	const EOpenStanceBodyZone Zone = FindContact(Context.Trace, Context.Defender, Tuning, Point);
	Debug.ZoneHit = Zone;
	if (Zone == EOpenStanceBodyZone::None)
	{
		return false;
	}

	const bool bPunch = Row.Technique == EOpenStanceTechnique::Punch;
	FOpenStanceContact Contact;
	Contact.Move = Context.Attack->MoveName;
	Contact.Technique = Row.Technique;
	Contact.Attacker = Context.Attacker.Side;
	Contact.Defender = Context.Defender.Side;
	Contact.Zone = Zone;
	Contact.bSpinning = Row.bSpinning;
	Contact.Impact = Row.Impact * Context.ImpactScale;
	Contact.Reaction = Row.Reaction;
	Contact.Point = Point;

	if (Zone == EOpenStanceBodyZone::BelowBelt)
	{
		// A kick below the waist is a foul; a punch down there simply misses the protector.
		if (!bPunch)
		{
			Contact.Type = EOpenStanceContactType::KickBelowBelt;
			bConsumed = true;
			OutContacts.Add(Contact);
			return true;
		}
		return false;
	}
	if (Zone == EOpenStanceBodyZone::Head && bPunch)
	{
		Contact.Type = EOpenStanceContactType::PunchToHead;
		bConsumed = true;
		OutContacts.Add(Contact);
		return true;
	}
	if (Zone == EOpenStanceBodyZone::Trunk && !bPunch && Contact.Impact < Tuning.TrunkImpactThreshold)
	{
		Contact.Type = EOpenStanceContactType::WeakImpact;
		bConsumed = true;
		OutContacts.Add(Contact);
		return true;
	}

	// The zone that was touched sets the value: a trunk kick that lands on the head is worth the head's points.
	Contact.Type = EOpenStanceContactType::Score;
	Contact.Points = FOpenStanceMoveData::PointsFor(Row.Technique, Zone == EOpenStanceBodyZone::Head ? EOpenStanceTarget::Head : EOpenStanceTarget::Trunk, Row.bSpinning);
	bConsumed = true;
	OutContacts.Add(Contact);
	return true;
}
