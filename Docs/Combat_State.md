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
  scores. Its stamina cost is the technique's times `FakeCostScale` (1.0: the GDD gives no discount).
- Stamina is spent when a technique starts and never blocks it. Below 25, recovery is 30% longer and `GetImpactScale`
  is 0.8.
- Hits: Minor is additive and changes no state; Normal is Hit Reaction (0.4 s), Heavy is Staggered (1.0 s),
  Knockdown is Knocked Down (3.0 s) then Recovering (0.6 s). A hit cuts the technique in progress. Nothing hits a
  fighter who is down or getting up.
- `CanScore` is true only in a real technique's active phase with play live: startup, recovery, fakes, stopped and
  finished matches never score.

## Stamina

Tuning: `FOpenStanceStaminaTuning` (Project Settings > Game > Open Stance Combat > Stamina; `Sim.StaminaRules`). Per-technique
costs are MoveData's, the dash cost the footwork tuning's. Tests: `OpenStance.Stamina.*` (GDD 8.9, issue 12).

| Rule | Starting value |
| --- | --- |
| Pool | 100 at attribute 70; the Stamina attribute scales it by a third of a percent per point (GDD 5.4) |
| Regeneration | 15 per second after 1.0 s without spending; the Recovery attribute scales the rate |
| Costs | punch 3, kick 8, dash 12, axe 12, jump kick 14, jump axe 18, spin 20, jump spin hook 26, tornado 30; footwork free |
| Low stamina | below an absolute 25 (not a share of the pool): recovery 30% longer, impact 20% lower; the HUD bar turns amber |
| Fake | `FakeCostScale` of the technique's cost, 1.0 (no discount in the GDD) |
| Active Defense | **Provisional:** 3 to raise the guard (a punch's cost), then 0.2 s before a technique can start once LT is released |
| Round break | refill to the fighter's own pool |

Stamina never locks a control: techniques, defense and the dash all go on an empty pool, which stays at zero. Equal
Terms (`Sim.bEqualTerms`, on by default) holds the attributes at 70. Career sets `StaminaAttribute` and
`RecoveryAttribute` on each fighter before `StartMatch`. The values are starting values, to publish once the M2 playtests
have tuned them.

## Knockdown cause

The machine records why a fighter went down and reports it in a `KnockedDown` event:

| Cause | Path | Penalty |
| --- | --- | --- |
| `Hit` | `ApplyHit` with Knockdown severity | none; the referee counts |
| `FailedLanding` | Attack Recovery ends and the move's `SelfFallChance` roll fails | Falling (GDD 8.4); `bFoulFall` is true |

The roll uses the machine's seedable `FRandomStream`. The chance is the row's alone; it does not yet depend on distance.

## Rounds and the match

Code: `Source/OpenStance/{Public,Private}/Combat/OpenStanceMatchRules` (the pure rules) and `FOpenStanceMatchSim::StepRules`
(the flow). Tests: `OpenStance.Match.*` (GDD 8.2-8.4, issue 10).

| Match state | What happens |
| --- | --- |
| Ready | Opening ceremony, `CeremonySeconds` (4 s): charyeot, kyeongrye, joon-bi, shi-jak. No attacks, the clock holds. |
| Running | The clock runs. The round stops early on the gap or the round's gam-jeom limit. |
| Stopped | A referee stop (a clinch). The clock holds; a round can still be lost on penalties. |
| RoundBreak | `BreakSeconds` (1:00). `SkipBreak` (A in the break, or `os.SkipBreak`) ends it. |
| Finished | A fighter has won enough rounds or reached the match gam-jeom limit: winner's call, then the final bow. |

- `FOpenStanceRoundTuning` holds match setup's options: 1 or 3 rounds, 60/90/120 s rounds, point gap 0 (off), 12 or 20.
- Each round is scored on its own: `State.Score` and `State.GamJeom` are the round's and reset when the next round
  starts. Stamina refills and the fighters go back to their marks then too. Round wins, match gam-jeom, penalty reasons
  and `RoundHistory` carry over.
- A lead of the gap wins the round on the spot. Five gam-jeom in a round lose the round. Ten in the match lose the match.
- At time the higher score wins the round, then WT Article 15: turning-kick points, head, trunk, punch, gam-jeom points,
  then protector hits (scoring or under the impact threshold).
- **Provisional:** the referee's decision, the last step, goes to the fighter who brought more real techniques to their
  active phase in the round, then to a seeded coin. The GDD does not say how the game's referee decides.
- Two round wins take a best of three; total points never decide a match. The HUD model gets each round's result
  and the winner from the simulation (`FOpenStanceMatchModelSync`), and Results shows rounds won, each round and
  the total points.
- The greybox proof (`os.RunProof`, `os.PlayProof`) uses `FOpenStanceGreyboxProof::UseProofRules`: one round with no
  ceremony, so it still ends 16 to 0 on the gap as recorded.
