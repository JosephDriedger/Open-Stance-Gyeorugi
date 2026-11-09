#include "Combat/OpenStanceCameraDirector.h"

#include "Combat/OpenStanceMatchSim.h"

namespace
{
	FVector Floor(const FOpenStanceFighterSim& F)
	{
		return FVector(F.Motion.Position.X, F.Motion.Position.Y, 0.0);
	}

	bool IsDown(const FOpenStanceFighterSim& F)
	{
		return F.State.CombatState == EOpenStanceCombatState::KnockedDown || F.State.CombatState == EOpenStanceCombatState::Recovering;
	}

	const FOpenStanceCameraPreset& PresetOr(const TCHAR* Name)
	{
		const FOpenStanceCameraPreset* Found = OpenStanceCameraPresets::Find(Name);
		return Found ? *Found : OpenStanceCameraPresets::Match();
	}
}

bool FOpenStanceCameraDirector::IsOnScreen(const FOpenStanceCameraFrame& Frame, const FVector& Point, float Margin, float AspectRatio)
{
	const FRotationMatrix Axes(Frame.Rotation);
	const FVector D = Point - Frame.Position;
	const double Forward = FVector::DotProduct(D, Axes.GetScaledAxis(EAxis::X));
	if (Forward <= 1.0)
	{
		return false;
	}
	const double Right = FVector::DotProduct(D, Axes.GetScaledAxis(EAxis::Y));
	const double Up = FVector::DotProduct(D, Axes.GetScaledAxis(EAxis::Z));
	const double TanH = FMath::Tan(FMath::DegreesToRadians(Frame.FieldOfViewDeg * 0.5));
	// Unreal keeps the horizontal field of view; the vertical one follows the view's shape.
	const double TanV = TanH / FMath::Max(AspectRatio, 0.1f);
	return FMath::Abs(Right / Forward) <= TanH * Margin && FMath::Abs(Up / Forward) <= TanV * Margin;
}

bool FOpenStanceCameraDirector::FramesBoth(const FOpenStanceCameraFrame& Frame, const FOpenStanceMatchSim& Sim) const
{
	for (const FOpenStanceFighterSim& F : Sim.Fighters)
	{
		const FVector Feet = Floor(F);
		const FVector Head = Feet + FVector(0.0, 0.0, F.State.CombatState == EOpenStanceCombatState::KnockedDown ? 30.0f : F.Motion.HeightCm);
		if (!IsOnScreen(Frame, Feet, Tuning.FrameMargin, Tuning.AspectRatio) || !IsOnScreen(Frame, Head, Tuning.FrameMargin, Tuning.AspectRatio))
		{
			return false;
		}
	}
	return true;
}

void FOpenStanceCameraDirector::Reset(const FOpenStanceMatchSim& Sim)
{
	Shot = EOpenStanceShot::Combat;
	ShotElapsed = 0.0f;
	SeenContacts = Sim.Contacts.Num();
	Last = FOpenStanceCameraFrame();
}

FOpenStanceCameraFrame FOpenStanceCameraDirector::FramePreset(const FOpenStanceCameraPreset& Preset, const FOpenStanceMatchSim& Sim, int32 PlayerIndex) const
{
	FOpenStanceCameraFrame Frame;
	const FOpenStanceFighterSim& Player = Sim.Fighters[PlayerIndex];
	const FOpenStanceFighterSim& Opponent = Sim.Fighters[1 - PlayerIndex];
	OpenStanceCameraPresets::Pose(Preset, Floor(Player), Floor(Opponent), Frame.Position, Frame.Rotation);
	Frame.FieldOfViewDeg = Preset.FieldOfViewDeg;

	// Inside the arena: near the edge the behind camera would back into a wall, so it slides in and re-aims.
	const FVector Clamped(FMath::Clamp(Frame.Position.X, -Tuning.ArenaHalfCm, Tuning.ArenaHalfCm),
		FMath::Clamp(Frame.Position.Y, -Tuning.ArenaHalfCm, Tuning.ArenaHalfCm), Frame.Position.Z);
	if (!Clamped.Equals(Frame.Position))
	{
		const FVector Mid = (Floor(Player) + Floor(Opponent)) * 0.5 + FVector(0.0, 0.0, Preset.LookHeightCm);
		Frame.Position = Clamped;
		Frame.Rotation = (Mid - Frame.Position).Rotation();
	}
	return Frame;
}

FOpenStanceCameraFrame FOpenStanceCameraDirector::FrameCombat(const FOpenStanceMatchSim& Sim, int32 PlayerIndex) const
{
	FOpenStanceCameraPreset Preset = OpenStanceCameraPresets::Match();
	const FOpenStanceFighterSim& Player = Sim.Fighters[PlayerIndex];
	const FOpenStanceFighterSim& Opponent = Sim.Fighters[1 - PlayerIndex];

	// Wider spacing: back off and rise so the opponent and the mat between stay in frame.
	const float Gap = static_cast<float>(FVector::Dist(Floor(Player), Floor(Opponent)));
	const float Extra = FMath::Clamp((Gap - Tuning.FramedGapCm) * Tuning.PullBackPerCm, 0.0f, Tuning.MaxPullBackCm);
	Preset.AlongCm += Extra;
	Preset.HeightCm += Extra * (Tuning.RisePerCm / FMath::Max(Tuning.PullBackPerCm, 0.01f));

	// Look at the fighters' own height, and down at the floor when one of them is down.
	const float Heights = (Player.Motion.HeightCm + Opponent.Motion.HeightCm) * 0.5f;
	Preset.LookHeightCm *= Heights / FMath::Max(Tuning.ReferenceHeightCm, 1.0f);
	if (IsDown(Player) || IsDown(Opponent))
	{
		Preset.LookHeightCm = FMath::Min(Preset.LookHeightCm, Tuning.DownLookHeightCm);
	}
	FOpenStanceCameraFrame Frame = FramePreset(Preset, Sim, PlayerIndex);

	// Fit: if a fighter would leave the picture, crane up and widen a little at a time, aimed between them (GDD 13: both
	// fighters always in frame), so the camera never needs to leave the arena to keep them.
	const FVector Look = (Floor(Player) + Floor(Opponent)) * 0.5 + FVector(0.0, 0.0, Preset.LookHeightCm);
	for (int32 Step = 0; Step < Tuning.FitSteps && !FramesBoth(Frame, Sim); ++Step)
	{
		Frame.Position.Z += Tuning.FitRaiseCm;
		Frame.FieldOfViewDeg = FMath::Min(Frame.FieldOfViewDeg + Tuning.FitWidenDeg, Tuning.MaxFieldOfViewDeg);
		Frame.Rotation = (Look - Frame.Position).Rotation();
	}
	Frame.Shot = EOpenStanceShot::Combat;
	return Frame;
}

FOpenStanceCameraFrame FOpenStanceCameraDirector::Update(float DeltaSeconds, const FOpenStanceMatchSim& Sim, int32 PlayerIndex, bool bPaused)
{
	if (bPaused)
	{
		// The pause menu holds the shot exactly where it is; nothing counts down.
		FOpenStanceCameraFrame Held = Last;
		Held.bCut = false;
		return Held;
	}

	// A spinning kick that scored since the last frame cuts to the side view (GDD 13).
	bool bSpinScored = false;
	for (; SeenContacts < Sim.Contacts.Num(); ++SeenContacts)
	{
		const FOpenStanceContact& Contact = Sim.Contacts[SeenContacts];
		bSpinScored |= Contact.Type == EOpenStanceContactType::Score && Contact.bSpinning;
	}
	if (SeenContacts > Sim.Contacts.Num())
	{
		SeenContacts = Sim.Contacts.Num(); // a new match
	}

	// The match state picks the shot; a spin cut plays out its 1.5 s whatever the state does meanwhile, except the end.
	EOpenStanceShot Wanted = EOpenStanceShot::Combat;
	switch (Sim.Match.State)
	{
	case EOpenStanceMatchState::Ready: Wanted = EOpenStanceShot::Ceremony; break;
	case EOpenStanceMatchState::RoundBreak: Wanted = EOpenStanceShot::Break; break;
	case EOpenStanceMatchState::Finished: Wanted = EOpenStanceShot::Results; break;
	default: break;
	}
	if (bSpinScored)
	{
		Wanted = EOpenStanceShot::SpinCut;
	}
	else if (Shot == EOpenStanceShot::SpinCut && ShotElapsed + DeltaSeconds < Tuning.SpinCutSeconds - KINDA_SMALL_NUMBER)
	{
		Wanted = EOpenStanceShot::SpinCut;
	}

	const EOpenStanceShot Previous = Shot;
	if (Wanted != Shot || bSpinScored)
	{
		Shot = Wanted;
		ShotElapsed = 0.0f;
	}
	ShotElapsed += DeltaSeconds;

	FOpenStanceCameraFrame Frame;
	switch (Shot)
	{
	case EOpenStanceShot::Ceremony:
	case EOpenStanceShot::SpinCut:
	case EOpenStanceShot::Results:
		Frame = FramePreset(PresetOr(TEXT("SideBroadcast")), Sim, PlayerIndex);
		break;
	case EOpenStanceShot::Break:
		Frame = FramePreset(PresetOr(TEXT("SideHigh")), Sim, PlayerIndex);
		break;
	default:
		Frame = FrameCombat(Sim, PlayerIndex);
		break;
	}
	Frame.Shot = Shot;
	// Into and out of a spin cut is a cut, as on a broadcast; the other changes ease across.
	Frame.bCut = Shot != Previous && (Shot == EOpenStanceShot::SpinCut || Previous == EOpenStanceShot::SpinCut);
	Last = Frame;
	return Frame;
}
