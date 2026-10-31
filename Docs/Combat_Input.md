# Skill Stick recognition

How controller input becomes a technique (GDD 7.1-7.4, 8.6). Code: `Source/OpenStance/{Public,Private}/Combat/OpenStanceSkillStick`.
Tests: `OpenStance.SkillStick.*` (run commands in [Combat_Data.md](Combat_Data.md)).

## Pipeline

`FOpenStanceSkillStickRecognizer::Update` takes one `FOpenStanceInputFrame` per tick (right stick, RT, RB, LB, LT, Y)
and the fighter's `FOpenStanceFighterState`. It copies the held buttons into the state, keeps the jump-primed flag
there, and appends `FOpenStanceInputEvent`s: an `Attack` (technique, target, leg, fake, jump) is what the combat
state machine acts on; every other event type exists so the debug overlay can show a failed input.

The recognizer touches no engine objects, so scripted frames test it and the AI can feed it synthesized frames
(GDD 16.7).

## Steps and the window

- The stick is split into four directions by dominant axis. A step counts when travel reaches the engage threshold
  (0.6, raised to at least the dead zone); the stick is back at neutral below 0.35 (also at least the dead zone).
  Between the two it keeps its direction, so a wobble on the way back to centre is not a step.
- Dead zone and window come from the Options screen: `FOpenStanceSkillStickConfig::FromSettings(DeadZonePercent,
  WindowSeconds)`; the window is clamped to 0.20-0.40 s (default 0.25 s).
- A gesture is the sequence of steps starting at the first step. A step that arrives after the window starts a new gesture.

## No prefix misfires

The whole path is matched, not its tail. Down then Up is a spin side kick; it never fires a side kick on its last Up.

| Path state | Result |
| --- | --- |
| Exactly one gesture and nothing longer starts the same way | fires at once |
| Exactly one gesture, and a longer one starts the same way | waits for neutral or the end of the window, then fires |
| Start of a longer gesture only | `GestureExpired` at neutral or the end of the window |
| No gesture starts this way | `GestureRejected` at once |

After a kick fires, expires or is rejected, the stick is ignored until it returns to neutral, so a held stick throws
one kick.

## Legs and mirroring

Gestures are defined with `Up`, `Down`, `Toward` and `Away`. Toward is the side of the leg throwing the kick: the lead
leg without RT, the back leg with it. In Right Lead RS Right is the lead-leg roundhouse and RS Left the hook; Left Lead
swaps them; RT mirrors them again. RS Up is the same on either stance. Stick X is positive toward the fighter's own
right side.

## Modifiers

RT, RB and LB latch for the length of a gesture: held at any moment from the first step to the commit counts. RB sets the
head target. LB makes the technique a fake; LB alone is a `GenericFake`, once per press, after the window or on release.

## Jump

A released tap of Y primes the next gesture and sets `bJumpPrimed` in the fighter state. The prime runs out after
`JumpPrimeSeconds` (the window) unless a gesture is in progress. A Y pressed after the stick has started moving
does not prime. The prime is spent by the gesture; only gestures with `bCanJump` (side, roundhouse, hook, axe, spin
hook) are thrown airborne.

## Active Defense

While LT is held the stick answers defence only: Up high block, Down leg check, Left or Right sway. Offensive
recognition stops, a gesture in progress is cancelled, and the stick must return to neutral after LT is released before
offence resumes.

## Adding a gesture

```cpp
FOpenStanceGestureDef Axe;
Axe.Technique = EOpenStanceTechnique::Axe;
Axe.Steps = { EOpenStanceGestureStep::Toward, EOpenStanceGestureStep::Down };
Recognizer.AddGesture(Axe);
```

Circle motions are written as steps (a quarter circle from the side down is Toward, Down). Techniques without an
approved input (GDD 9.4) are not registered.

## Provisional decisions (issue 2)

These stand until the GDD records the decision: kicks without RT use the lead leg; left stick movement; the spin hook's
RT requirement is not decided, so the spin hook is not registered.

# Footwork and stance

Code: `OpenStanceFootwork`, tuning in `UOpenStanceCombatSettings` (Project Settings > Game > Open Stance Combat, saved
to `Config/DefaultGame.ini`). Tests: `OpenStance.Footwork.*`. All numbers are GDD 6.4's starting values, editable, and
are replaced by the Milestone 1 capture's measurements.

| Rule | Behaviour |
| --- | --- |
| Tap | A press owes a whole step: 40 cm forward or back, 35 cm sideways. Releasing early finishes the step. |
| Hold | 1.2 m/s while the stick is held. |
| Circling | Sideways motion swings round the opponent at the same distance; the fighter keeps facing them. |
| Dash (B) | 1.0 m in 0.3 s along the stick or toward the opponent, 12 stamina; held B dashes once. |
| Switch Sides (A) | Takes 0.35 s; lead and back swap halfway, `SwitchBlend` rises smoothly 0 to 1 for the mirrored pose, no technique can start meanwhile, and none can be switched into mid-technique. |
| Technique | A neutral stick roots the fighter. A held stick slides it at the step speed (120 cm/s); it never steers toward the opponent, so an out-of-range attack stays out of range. |
| Guard | D-pad Up high, Left cross, Right mixed, Down low. The runtime state holds it at once; `GuardTransitionLeft` and `PreviousGuard` are there for the transition the M2 defence adds. |
| Collision | Capsule radius 35 cm. `SeparateFighters` pushes overlapping fighters apart; they never overlap. |
| Reach | `ScaleReachCm` scales the table's reach (written for 175 cm) by the fighter's height. |

The same RT kick after switching sides is checked by `OpenStance.Footwork.SameKickAfterSwitch`: in Right Lead the RT
roundhouse is RS Left with the left leg; after the switch it is RS Right with the right leg, and RS Left is the hook.
