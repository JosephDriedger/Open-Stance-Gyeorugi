# Hit registration

Code: `Source/OpenStance/{Public,Private}/Combat/OpenStanceHit` (GDD 6.4, 8.3, 8.10, 11.3). Tests: `OpenStance.Hit.*`.
The tests throw real techniques through the combat state machine and trace a tip against a defender, with no actors.

## What is traced

Each frame the attacker's limb sweep (`FOpenStanceLimbTrace`, foot guard or glove) is tested against the defender's
zones, but only when `FOpenStanceCombatMachine::CanScore` is true: a real technique's Attack Active phase with play
live. Startup, recovery, fakes, stopped play and a finished match are never traced.

Zones are vertical cylinders sized from the defender's height (so every body type uses the same layout):

| Zone | Height | Radius |
| --- | --- | --- |
| Head | 82% to 100% | 7% |
| Trunk | belt line (55%) to 82% | 11% |
| Below belt | floor to the belt line | 10% |

A sweep is sampled 16 times, so a fast foot cannot skip a zone between frames. The height of a sample picks the zone; the
limb's own radius and the alignment tolerance widen it sideways.

## What registers

| Contact | Result |
| --- | --- |
| Kick on the trunk at or above the impact threshold (30) | Score: body kick 2, spinning 4 |
| Kick on the trunk below the threshold | `WeakImpact`: contact, no score |
| Kick on the head | Score: 3, spinning 6; valid contact is enough |
| Punch on the trunk | Score: 1 |
| Punch on the head | `PunchToHead`: illegal, 0 points, for the referee |
| Kick below the belt line | `KickBelowBelt`: foul, 0 points, for the referee |
| Punch below the belt line | nothing |

Impact is the row's `Impact` times the machine's stamina scale (0.8 below 25 stamina). The zone touched sets the points,
so a trunk kick that lands on the head is worth 3. Each technique registers one contact: later traces of the same
attack (matched by the machine's attack serial) are ignored; the next technique starts fresh.

## Range

The move's reach (`ReachCm` scaled by the attacker's height) bounds the contact: beyond reach plus the defender's trunk
radius plus the alignment tolerance (8 cm) nothing connects, whatever the trace does. The tolerance is the only
correction; it nudges a near miss into contact and never pulls an out-of-range attack in (GDD 1.7).

## Using it

```cpp
FOpenStanceHitContext Context;
Context.Attack = Machine.GetCurrentAttack();
Context.bCanScore = Machine.CanScore(State, Match);
Context.AttackSerial = Machine.GetAttackSerial();
Context.ImpactScale = Machine.GetImpactScale(State);
Context.Attacker = AttackerBody;  // root, height, side
Context.Defender = DefenderBody;
Context.Trace = ...;              // the foot or glove sweep this frame
Registry.Trace(Context, Contacts);
```

A `Score` contact goes to the match model (`AddPoints`) and to the defender's machine (`ApplyHit(Contact.Reaction)`); the
illegal contacts go to the penalty code. `GetLastTrace()` says whether the last trace was looked at and why not, for the
debug overlay. `SyntheticTip` places the foot or glove for greybox and placeholder animation; with a skeleton the
foot-guard and glove sockets supply the sweep instead.

The scores are independent of the menu's sample score events.
