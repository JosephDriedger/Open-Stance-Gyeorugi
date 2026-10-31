# Combat state machine

Code: `Source/OpenStance/{Public,Private}/Combat/OpenStanceCombatMachine` (GDD 16.3, 8.6, 8.10). Tests:
`OpenStance.Combat.*`, a scripted one-fighter scenario with no actors, animation or screen.

## States and transitions

Idle/Movement, Attack Startup, Attack Active, Attack Recovery, Active Defense, Hit Reaction, Staggered, Knocked Down,
Recovering and Match Finished. `IsLegalTransition` is the whole table and a test checks every pair:

| From | May go to |
| --- | --- |
| Idle/Movement | Startup, Active Defense, Hit Reaction, Staggered, Knocked Down |
| Startup | Active (Recovery directly for a fake), Hit Reaction, Staggered, Knocked Down |
| Active | Recovery, Hit Reaction, Staggered, Knocked Down |
| Recovery | Idle, Hit Reaction, Staggered, Knocked Down; Startup only inside the move's cancel window |
| Active Defense | Idle, Hit Reaction, Staggered, Knocked Down |
| Hit Reaction, Staggered | Idle, Hit Reaction, Staggered, Knocked Down |
| Knocked Down | Recovering |
| Recovering | Idle |
| any but Match Finished | Match Finished |

Play stopping cuts a technique or guard back to Idle (the one forced transition); a fighter being hit or getting up
finishes that first.

## Timing

A technique's startup, active and recovery are the `MoveData` row's. With `Tuning.bNotifyDriven` the montage's
notifies decide instead: `NotifyActiveBegin` opens the trace window and `NotifyActiveEnd` closes it, out-of-order
notifies are ignored, and the row's times still bound each phase at twice their length so a missing notify cannot
freeze a fighter. A technique's `CancelWindowSeconds` is the only way to start another inside its recovery.

- A fake plays its startup and goes straight to a shorter recovery (40% of the technique's), never active, never
  scores. It costs the same stamina as the real thing (the GDD gives no discount).
- Stamina is spent when a technique starts and never blocks it. Below 25, recovery is 30% longer and `GetImpactScale`
  is 0.8.
- Hits: Minor is additive and changes no state; Normal is Hit Reaction (0.4 s), Heavy is Staggered (1.0 s),
  Knockdown is Knocked Down (3.0 s) then Recovering (0.6 s). A hit cuts the technique in progress. Nothing hits a
  fighter who is down or getting up.
- `CanScore` is true only in a real technique's active phase with play live: startup, recovery, fakes, stopped and
  finished matches never score.

## Knockdown cause

The machine records why a fighter went down and reports it in a `KnockedDown` event:

| Cause | Path | Penalty |
| --- | --- | --- |
| `Hit` | `ApplyHit` with Knockdown severity | none; the referee counts |
| `FailedLanding` | Attack Recovery ends and the move's `SelfFallChance` roll fails | Falling (GDD 8.4); `bFoulFall` is true |

The roll uses the machine's seedable `FRandomStream`. The chance is the row's alone; it does not yet depend on distance.
