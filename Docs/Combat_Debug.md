# Combat display, test commands and the M1 greybox proof

Code: `OpenStanceMatchSim` (the rules for two fighters), `OpenStanceCombatOverlay` (the text), `OpenStanceCombatDebugSubsystem`
(controller, drawing and commands), `OpenStanceGreyboxProof` (the script). Tests: `OpenStance.Greybox.*` (GDD 7.6, 7.7, 16.8, 19).

## Running the greybox

In a game world (PIE or `-game`, any level, for example `L_TrainingDojang`), with a gamepad connected, open the console:

```
os.Greybox 1       start the match: you are Chung, Hong stands still, side-on camera
os.CombatDebug 1   the debug overlay on both edges of the screen
os.ShowHitboxes 1  capsules, target zones and the limb trace
os.Greybox 0       stop
```

The fighters are capsules with target zones; there is no animation yet, so a technique is the fighter's state plus a synthetic
foot or glove travelling to the move's reach. The overlay and gamepad path are written but have not been looked at on a
screen; the rules under them are covered by the automation tests and the headless run of `os.RunProof`.

## What is shown

| Display | Contents |
| --- | --- |
| Debug overlay (`os.CombatDebug`) | Stance, guard, combat state, held buttons, stick history, last input and the three before it (rejected and expired gestures stay visible), resolved leg, move, target, stamina, score and gam-jeom, hit result, the last trace and why it was ignored |
| Training display (`SetTrainingDisplay`, `os.TrainingDisplay`) | The player-facing subset (GDD 7.6): last input, leg, move, target, stamina, hit result |

Chung's bar is on the left edge and Hong's on the right. The Training screen only has to call
`UOpenStanceCombatDebugSubsystem::SetTrainingDisplay(true)` when its level loads.

## Commands

Development builds only; the commands are compiled out of shipping. `slomo <scale>` is Unreal's own time dilation, for example
`slomo 0.25`; the simulation steps at a fixed 60 Hz so slow motion changes how long it takes, not what happens.

| Command | Effect |
| --- | --- |
| `os.InfiniteStamina 0\|1` | Stamina never drains |
| `os.SetScore <Chung> <Hong>` | Sets the score |
| `os.SetClock <seconds>` | Sets the round clock |
| `os.AIMode idle\|block` | Hong stands still or holds LT. `mirror` and `normal` are refused until the AI exists |
| `os.ShowHitboxes 0\|1` | Draws limb traces and target zones |
| `os.CombatDebug 0\|1` | The debug overlay |
| `os.TrainingDisplay 0\|1` | The Training display |
| `os.Greybox 0\|1`, `os.RunProof` | Start or stop the greybox, play the scripted proof |
| `os.SetRank` | Not added: there is no Career rank to set until Career lands |

`UOpenStanceCombatDebugSubsystem::AreCheatsActive()` becomes true as soon as `os.InfiniteStamina 1`, `os.SetScore`, `os.SetClock`
or `os.AIMode` changes the match, so achievement reporting can be suppressed.

## The M1 greybox proof

`os.RunProof` (or the automation test `OpenStance.Greybox.Proof`) plays the script in `OpenStanceGreyboxProof` on two fighters
with controller input only and writes `Saved/Logs/OpenStanceGreyboxProof.txt`. The last recorded run:

1. Side kick (RS Up) with the lead leg: +2.
2. Roundhouse (RS toward the lead leg): +2.
3. Spin side kick (RS Down, Up): +4.
4. Switch sides (A): visibly switching, then Left Lead.
5. The same RT roundhouse after the switch, now RS toward the other side with the right leg as the back leg: +2.
6. A side kick from too far: a clean miss, score unchanged.
7. Close in and a spin side kick to the head (RB): +6.
8. Final score Chung 16, Hong 0.

Not in the proof: the retargeted capture playing on the geared fighter. That needs the capture and retarget (issue 8), and the
greybox keeps placeholder timing until then.
