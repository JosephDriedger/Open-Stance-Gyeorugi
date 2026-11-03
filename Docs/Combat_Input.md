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

## Control decisions (GDD v0.12, 18.2)

Kicks without RT use the lead leg. The left stick moves the fighter, the Menu button pauses, and L3 and R3 are unused
in v1.0. The spin hook requires RT, because the back leg throws it; its gesture is a half circle down, from either
side, mirrored like any back-leg kick (GDD 7.2).

## Axe kick (GDD 7.2)

RS Left/Right, a forward quarter circle (3 o'clock to 12 o'clock), then Down: registered as `Toward, Up, Down` or `Away, Up,
Down`, always to the head, from either side and with either leg (RT for the back leg). Tap Y first for the jump axe.

## Landing and switching sides (not yet in the GDD)

Every back-leg kick (RT), and the spin side and spin hook kicks, land with the other leg in front: the sides switch as the
recovery begins, with the same animated switch as the A button, never an instant mirror. The GDD does not say this yet; it
needs a line in 7.4 or 8.7 if it stays.

## Real thumbs

- A direction only switches to a perpendicular one when the new axis is 1.35 times further along than the old one
  (`DirectionHysteresis`), so a circle near a diagonal does not flicker into extra steps and get rejected.
- The stick resting at neutral for 0.06 s ends a gesture (`NeutralGraceSeconds`); crossing the centre for a frame does not.
- The Y tap primes the next gesture for 0.5 s (`JumpPrimeSeconds`), because the same thumb has to move from the button to the stick.

## Clinch (GDD 6.4, 8.4, 11.3)

Chest-to-chest contact, centres within 76 cm, starts a clinch when play is live and neither fighter is throwing a technique,
whether both press in or one lands a Dash (B) on the other. Code: `FOpenStanceMatchSim::StepClinch`, tuning in
`FOpenStanceClinchTuning`; tests `OpenStance.Greybox.Clinch`. Starting values, tuned in playtests.

| Step | Behaviour |
| --- | --- |
| Held | Both fighters are locked: no stepping, dashing, switching sides or techniques (a punch or kick says `clinch: wait for the referee`). Guards still work. |
| Hold foul | Past 1.0 s, each fighter still pressing the left stick forward gets a gam-jeom and the opponent a point, once per clinch (GDD 8.4). |
| Kal-yeo | At 0.8 s the referee stops play (match state Stopped, the clock holds). Under the 2 s a Referee Mode player has before the call is late. |
| Separating | Over the first 0.5 s of the 0.8 s stoppage the fighters are drawn apart to 120 cm. |
| Kye-sok | Play resumes with the fighters apart. |

With the 0.8 s referee call the 1.0 s hold foul only happens if the call is slowed (`RefereeCallSeconds`) or a later
referee is late. Close-range kicks and clinch actions have no inputs yet (GDD 9.4), so nothing is thrown inside a clinch.

## Input window

All gestures share the Options window, 0.20 to 0.40 s with a default of 0.25 s (GDD 7.8). It is the time allowed between one
stick step and the next: every new step restarts it, so a three-step axe or a five-step tornado circle only has to keep moving,
and a pause longer than the window expires the gesture. The GDD does not say whether the window runs from the first step or
between steps; this is the reading that makes the longer gestures playable at the default setting. The greybox reads the setting.

## Spin hook and tornado kick (GDD 9.1, 9.2)

| Technique | Input | Registered as |
| --- | --- | --- |
| Spin hook | Hold RT, then a half circle down from either side | `Toward, Down, Away` or `Away, Down, Toward`, with `bRequiresBackLeg` |
| Tornado kick | Tap Y, then a half circle down and a half circle back up: one full circle that starts downward, from either side | `Toward, Down, Away, Up, Toward` or the mirror, with `bRequiresJump` |

A gesture that requires RT or the Y tap is ignored while that modifier is not latched, so it never delays the plain kick it
starts like: without RT, Right then Down is still a roundhouse and nothing else. With RT (or the Y tap) the roundhouse and hook
wait for the stick to return to neutral or for the window to close, as any prefix of a longer gesture does. The tornado is
always thrown airborne, so its move rows are the jump rows (`bJump` true); the five steps have to land inside the window, which
is why it is the hardest input in the game. The spin hook's jump version is allowed by the recognizer but has no move row yet.

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
