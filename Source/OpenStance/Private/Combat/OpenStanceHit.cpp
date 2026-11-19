#include "Combat/OpenStanceHit.h"

#include "Combat/OpenStanceFootwork.h"

namespace
{
	/** Closest distance between two segments. */
	float SegmentDistance(const FVector& P1, const FVector& Q1, const FVector& P2, const FVector& Q2)
	{
		FVector A, B;
		FMath::SegmentDistToSegmentSafe(P1, Q1, P2, Q2, A, B);
		return static_cast<float>(FVector::Dist(A, B));
	}

	bool TouchesGuard(const FOpenStanceFighterBody& Body, const FVector& Start, const FVector& End, float LimbRadius)
	{
		for (const FOpenStanceLimbCapsule& Limb : Body.Guard)
		{
			if (SegmentDistance(Start, End, Limb.A, Limb.B) <= Limb.Radius + LimbRadius)
			{
				return true;
			}
		}
		return false;
	}
}

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

EOpenStanceBodyZone FOpenStanceHitRegistry::FindContact(const FOpenStanceLimbTrace& Trace, const FOpenStanceFighterBody& Body, const FOpenStanceHitTuning& Tuning, FVector& OutPoint, bool& bOutBlocked)
{
	bOutBlocked = false;
	const float LimbRadius = Trace.Limb == EOpenStanceStrikeLimb::Glove ? Tuning.GloveRadiusCm : Tuning.FootGuardRadiusCm;
	const int32 Samples = FMath::Max(Tuning.SamplesPerTrace, 2);
	const float BeltLine = Body.HeightCm * Tuning.BeltLineFraction;
	const float HeadBottom = Body.HeightCm * Tuning.HeadBottomFraction;
	const auto ZoneAt = [&](float Height)
	{
		return Height >= HeadBottom ? EOpenStanceBodyZone::Head : Height >= BeltLine ? EOpenStanceBodyZone::Trunk : EOpenStanceBodyZone::BelowBelt;
	};

	// Real contact first: walk the sweep and stop at the first thing the striking limb touches, a guard limb or the body.
	FVector Previous = Trace.Start;
	for (int32 Index = 0; Index < Samples; ++Index)
	{
		const float Alpha = static_cast<float>(Index) / static_cast<float>(Samples - 1);
		const FVector Point = FMath::Lerp(Trace.Start, Trace.End, Alpha);
		const float Height = Point.Z - Body.Root.Z;
		if (TouchesGuard(Body, Previous, Point, LimbRadius))
		{
			OutPoint = Point;
			bOutBlocked = true;
			return ZoneAt(Height);
		}
		Previous = Point;
		if (Height < 0.0f || Height > Body.HeightCm)
		{
			continue;
		}
		const EOpenStanceBodyZone Zone = ZoneAt(Height);
		float Bottom, Top, Radius;
		GetZoneBounds(Body, Zone, Tuning, Bottom, Top, Radius);
		const float Horizontal = static_cast<float>(FVector2D::Distance(FVector2D(Point.X, Point.Y), FVector2D(Body.Root.X, Body.Root.Y)));
		if (Horizontal <= Radius + LimbRadius)
		{
			OutPoint = Point;
			return Zone;
		}
	}

	// A near miss: the alignment tolerance may nudge it into the zone, but never through an arm or leg in the way.
	const EOpenStanceBodyZone Nudged = FindContact(Trace, Body, Tuning, OutPoint);
	if (Nudged != EOpenStanceBodyZone::None)
	{
		const FVector Target(Body.Root.X, Body.Root.Y, OutPoint.Z);
		bOutBlocked = TouchesGuard(Body, OutPoint, Target, LimbRadius);
	}
	return Nudged;
}

void FOpenStanceHitRegistry::BuildGuard(FOpenStanceFighterBody& Body, EOpenStanceGuard Guard, EOpenStanceGuardCover Cover, bool bRightLead)
{
	Body.Guard.Reset();
	const float H = Body.HeightCm;
	const float Scale = H / 175.0f;
	const FVector Forward = FVector(Body.Facing.X, Body.Facing.Y, 0.0).GetSafeNormal();
	const FVector Right(-Forward.Y, Forward.X, 0.0);
	// Lead and rear sides of the body, as signs along Right.
	const float Lead = bRightLead ? 1.0f : -1.0f;
	const float Rear = -Lead;

	// A point in the fighter's frame: forward and sideways in cm at the reference height, up as a share of the height.
	const auto At = [&](float ForwardCm, float SideCm, float UpFraction)
	{
		return Body.Root + Forward * (ForwardCm * Scale) + Right * (SideCm * Scale) + FVector(0.0, 0.0, H * UpFraction);
	};
	const auto Add = [&](const FVector& A, const FVector& B, float Radius = 6.0f)
	{
		FOpenStanceLimbCapsule& Limb = Body.Guard.AddDefaulted_GetRef();
		Limb.A = A;
		Limb.B = B;
		Limb.Radius = Radius * Scale;
	};

	// Forearms stand outside the body's own zones (trunk radius 19 cm, head 12 cm at 175 cm), and in every posture they
	// leave the centre line open: a straight kick passes between them, a kick swinging in from a side meets that arm.
	const auto HeadSide = [&](float Side) { Add(At(10.0f, Side * 18.0f, 0.82f), At(12.0f, Side * 18.0f, 0.95f)); };
	const auto TrunkFlank = [&](float Side) { Add(At(14.0f, Side * 22.0f, 0.58f), At(14.0f, Side * 22.0f, 0.72f)); };

	switch (Cover)
	{
	case EOpenStanceGuardCover::Closed:
		// The guard closed over the protector: forearms together in front, elbows tight at the flanks. The head is open.
		Add(At(26.0f, -8.0f, 0.58f), At(26.0f, -8.0f, 0.80f));
		Add(At(26.0f, 8.0f, 0.58f), At(26.0f, 8.0f, 0.80f));
		Add(At(14.0f, -22.0f, 0.60f), At(14.0f, -22.0f, 0.78f));
		Add(At(14.0f, 22.0f, 0.60f), At(14.0f, 22.0f, 0.78f));
		return;
	case EOpenStanceGuardCover::High:
		// Forearms up in front of the face and the upper arms beside the head. The trunk is open.
		Add(At(20.0f, -8.0f, 0.82f), At(20.0f, -8.0f, 0.98f));
		Add(At(20.0f, 8.0f, 0.82f), At(20.0f, 8.0f, 0.98f));
		HeadSide(-1.0f);
		HeadSide(1.0f);
		return;
	default:
		break;
	}

	switch (Guard)
	{
	case EOpenStanceGuard::High:
		HeadSide(Lead);
		HeadSide(Rear);
		break;
	case EOpenStanceGuard::Low:
		TrunkFlank(Lead);
		TrunkFlank(Rear);
		break;
	case EOpenStanceGuard::Mixed:
		TrunkFlank(Lead);
		HeadSide(Rear);
		break;
	case EOpenStanceGuard::Cross:
		// The rear forearm across the front of the trunk covers body kicks on the open side; the lead hand guards the head.
		Add(At(24.0f, Rear * 12.0f, 0.64f), At(26.0f, Lead * 14.0f, 0.72f));
		HeadSide(Lead);
		break;
	}

	if (Cover == EOpenStanceGuardCover::LegCheck)
	{
		// The lead knee lifted in front of the protector: thigh up to the knee, shin hanging from it.
		const FVector Knee = At(32.0f, Lead * 6.0f, 0.64f);
		Add(At(10.0f, Lead * 10.0f, 0.50f), Knee, 7.0f);
		Add(Knee, At(30.0f, Lead * 6.0f, 0.38f), 7.0f);
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

FVector FOpenStanceHitRegistry::SyntheticTip(const FOpenStanceFighterBody& Attacker, const FVector& FacingXY, const FOpenStanceMoveRow& Row, float Progress, const FOpenStanceHitTuning& Tuning,
	EOpenStanceLegSide Leg)
{
	const float Alpha = FMath::Clamp(Progress, 0.0f, 1.0f);
	const float Smooth = Alpha * Alpha * (3.0f - 2.0f * Alpha);
	const FOpenStanceMovementTuning Movement;
	const float Reach = FOpenStanceFootwork::ScaleReachCm(Row.ReachCm, Attacker.HeightCm, Movement);
	const bool bHead = Row.Target == EOpenStanceTarget::Head;
	const bool bPunch = Row.Technique == EOpenStanceTechnique::Punch;
	// Head kicks at the face, body kicks at the protector's middle, a punch at the chest.
	const float Height = Attacker.HeightCm * (bHead ? 0.90f : bPunch ? 0.76f : 0.70f);
	const FVector Forward = FVector(FacingXY.X, FacingXY.Y, 0.0).GetSafeNormal();
	const FVector Right(-Forward.Y, Forward.X, 0.0);

	// Turning kicks swing in from a side and straighten onto the target: the roundhouse and tornado from the kicking leg's
	// side, the hook and spin hook from the other. Side, axe and spin side kicks and the punch travel straight.
	float Side = 0.0f;
	switch (Row.Technique)
	{
	case EOpenStanceTechnique::Roundhouse:
	case EOpenStanceTechnique::Tornado:
		Side = Leg == EOpenStanceLegSide::Right ? 1.0f : -1.0f;
		break;
	case EOpenStanceTechnique::Hook:
	case EOpenStanceTechnique::SpinHook:
		Side = Leg == EOpenStanceLegSide::Right ? -1.0f : 1.0f;
		break;
	default:
		break;
	}
	const float Angle = FMath::DegreesToRadians(70.0f) * (1.0f - Smooth) * Side;
	const FVector Direction = Forward * FMath::Cos(Angle) + Right * FMath::Sin(Angle);
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
	bool bBlocked = false;
	const EOpenStanceBodyZone Zone = FindContact(Context.Trace, Context.Defender, Tuning, Point, bBlocked);
	Debug.ZoneHit = Zone;
	if (Zone == EOpenStanceBodyZone::None && !bBlocked)
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

	// An arm or leg of the guard took it: the technique is spent and nothing registers on the protector.
	if (bBlocked)
	{
		Contact.Type = EOpenStanceContactType::Blocked;
		bConsumed = true;
		OutContacts.Add(Contact);
		return true;
	}

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
