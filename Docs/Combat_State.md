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
- Still level: superiority (woo-se-girok, WT Article 15 Explanation 1). One vote per criterion the fighters differ on:
  aggressive match management (net distance moved toward the opponent in live play, `PressureCm`, with a 50 cm margin),
  the greater number of techniques executed (real techniques reaching their active phase), more advanced techniques
  (spinning, jumping and tornado kicks among them) and better competition manner (fewer gam-jeom). More votes win; a
  level vote goes to a seeded coin, the referee's call. The log records the call and the votes. **Provisional:** how
  each criterion is measured is the game's reading of the WT text; tune after playtests.
- Two round wins take a best of three; total points never decide a match. The HUD model gets each round's result
  and the winner from the simulation (`FOpenStanceMatchModelSync`), and Results shows rounds won, each round and
  the total points.
- The greybox proof (`os.RunProof`, `os.PlayProof`) uses `FOpenStanceGreyboxProof::UseProofRules`: one round with no
  ceremony, so it still ends 16 to 0 on the gap as recorded.

## Penalties the referee watches for

Code: `Combat/OpenStancePenalties.h` (`FOpenStancePenaltyTuning`, `Sim.PenaltyRules`) and `FOpenStanceMatchSim::StepPenalties`.
Tests: `OpenStance.Penalty.*` (GDD 8.4, issue 11). A time of 0 turns a check off.

| Gam-jeom | Rule | Starting value |
| --- | --- | --- |
| Boundary | a whole foot past the 8 m octagon's edge; a foot on the line is safe | foot 30 cm from centre, 12 cm past the line |
| Forced out | no penalty while clinched or just after the opponent's holding/pushing gam-jeom | 0.5 s grace |
| Turning the back | body turned more than 90 degrees from the opponent, outside a technique | over 1.0 s |
| Crouching | below Low Guard's posture without attacking; Low Guard never counts | over 1.0 s |
| Leg lifting | a leg above the hip outside its own technique (a held leg check) | over 3.0 s |
| Passivity | no technique of either fighter reaches its active phase: GONG-GYEOK, then a gam-jeom to the one who moved back (net 50 cm away), otherwise to both | call at 3 s, gam-jeom at 6 s |

Already decided where they happen: punch to the head and kick below the belt (hit registration), Falling (a Knocked Down
that no landed hit caused; a hit knockdown is never a penalty) and holding or pushing (the clinch).

Each incident counts once: a counted turn, crouch or lift stays counted until the condition clears, and a fighter over the
edge is brought back inside. Every gam-jeom outside a clinch is a referee's stop: kal-yeo, the gam-jeom, then kye-sok
after 1 s, with the clock held.

**Hooks:** footwork always faces the opponent and has no crouch, so turning the back and crouching watch
`Motion.TurnedAwayDeg` and `Motion.CrouchCm`, which stay 0 until animation or the AI sets them. `Motion.bLegRaised` is
set by the leg check below.

**GDD note:** 6.3 still says "both feet" over the edge; 8.4 and the WT rules check say one foot. The code follows 8.4.

## Blocking and scoring by collision

Code: `FOpenStanceHitRegistry::BuildGuard` and `FindContact` (`Combat/OpenStanceHit`), `FOpenStanceMatchSim::StepGuard`.
Tests: `OpenStance.Defense.*` (GDD 8.3, 8.7, 8.8).

Each fighter in guard (idle, moving or in Active Defense) has arm capsules, and a leg capsule in a leg check, placed by
its guard posture. Each frame the striking foot or glove sweeps its path, and the first thing it touches decides:
an arm or leg is a block (no points, no protector hit, no hit reaction, the HUD calls "Blocked"); the head, the trunk
protector or below the belt is a contact for that zone, scored by GDD 8.3 as before. The 8 cm alignment tolerance
only nudges a near miss into a zone when no guard limb lies between the strike and the target. A fighter throwing a
technique, reeling or down has no guard up.

| Guard (D-pad) | Arms | Covers |
| --- | --- | --- |
| High (Up) | both hands beside the head | head kicks swinging in from either side |
| Low (Down) | both forearms at the trunk's flanks | body kicks swinging in from either side |
| Mixed (Right) | lead hand low at the flank, rear hand high beside the head | lead-side body, rear-side head |
| Cross (Left) | rear forearm across the front of the trunk, lead hand beside the head | straight body kicks and punches, lead-side head |
| LT alone | forearms closed in front of the trunk, elbows at the flanks | punches and body kicks from any side; the head is open |
| LT + RS Up | forearms in front of the face, upper arms beside the head | head kicks; the trunk is open |
| LT + RS Down | the lead knee lifted in front of the trunk, posture arms kept | straight body kicks; punches pass above the knee; over 3 s is leg lifting |
| LT + RS Left/Right | sway: a 40 cm step off the line | anything in the first 0.35 s (a timing rule, not a collision) |

The middle is open in every posture, so a straight side kick or spinning side kick gets between the hands. Until the
captured animation drives the foot, the strike path is synthetic: roundhouse and tornado kicks swing in 70 degrees from
the kicking leg's side, hook and spin hook kicks from the other side, and side, axe and spin side kicks and punches
travel straight. Kicks aim at 0.70 of the height for the body and 0.90 for the head, punches at 0.76. **Provisional:**
limb positions are starting values at a 175 cm fighter, scaled with height; check them against the MetaHuman bodies
and the captured guards. `os.ShowHitboxes 1` draws the guard capsules in cyan.

### Guard readiness (GDD 8.7)

Guards change timing, never stats (`Sim.GuardRules`, footwork tuning). Tests: `OpenStance.Guards.Readiness`.

| Guard | Startup to the head | Startup to the body | Changing from it | High block (LT + RS Up) comes up in |
| --- | --- | --- | --- | --- |
| High | x0.9 | x1.15 | 0.25 s | 0.05 s |
| Low | x1.1 | x0.9 | 0.25 s | 0.2 s |
| Mixed | x1.0 | x1.0 | 0.15 s | 0.05 s |
| Cross | x1.0 | x0.95 | 0.2 s | 0.05 s |

While the hands move between two guards they cover nothing, so changing guard is an opening.

### Hit severity (GDD 8.10)

`FOpenStanceMatchSim::ResolveSeverity`; tests `OpenStance.Reactions.*`. A landed hit starts from the technique's
authored reaction. The impact (already cut 20% for a tired attacker) is divided by the defender's Composure effect
(a third of a percent per point from 70; Equal Terms holds it at 70) and raised 20% for a defender on low stamina.
Under 0.9 of the technique's own impact the reaction is a step lighter; at 1.15 or more, a step heavier. So a fresh
fighter takes a head roundhouse as a stagger, a tired one goes down (cause Hit: the referee counts, no penalty). A
failed landing is still the Falling gam-jeom. **Provisional:** all three numbers. Reaction times stay 0.4 s Normal,
1.0 s Heavy, 3.0 s down plus 0.6 s getting up.

Still for later: defense and reaction animation (placeholder clips first, then capture).
