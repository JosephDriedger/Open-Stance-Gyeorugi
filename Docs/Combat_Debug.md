# Combat display, test commands and the M1 greybox proof

Code: `OpenStanceMatchSim` (the rules for two fighters), `OpenStanceCombatOverlay` (the text), `OpenStanceCombatDebugSubsystem`
(controller, drawing and commands), `OpenStanceGreyboxProof` (the script). Tests: `OpenStance.Greybox.*` (GDD 7.6, 7.7, 16.8, 19).

## Running the greybox

In development builds the greybox starts by itself when Play begins on any map except `L_MainMenu`: press Play on
`L_TrainingDojang`, click the viewport and use the controller. `os.GreyboxAutoStart 0` (or `os.GreyboxAutoStart=0` under
`[SystemSettings]` in `DefaultEngine.ini`) turns that off. To start it by hand instead:

In a game world (PIE or `-game`, any level, for example `L_TrainingDojang`), with a gamepad connected, open the console:

```
os.Greybox 1       start the match: you are Chung, Hong stands still, the camera follows you from behind
os.CombatDebug 1   the debug overlay on both edges of the screen (os.Greybox 1 already turns it on)
os.ShowHitboxes 1  capsules, target zones and the limb trace
os.Greybox 0       stop
```

The fighters are capsules with target zones; there is no animation yet, so a technique is the fighter's state plus a synthetic
foot or glove travelling to the move's reach. The overlay and gamepad path are written but have not been looked at on a
screen; the rules under them are covered by the automation tests and the headless run of `os.RunProof`.

## What is shown

While the greybox runs, every input Chung's Skill Stick produces is also printed as a line of on-screen text (Unreal's
`AddOnScreenDebugMessage`, three seconds each): green for a technique, yellow for a fake, block, sway or jump prime, red for a
rejected, expired or cancelled gesture. It needs neither `os.CombatDebug` nor `os.TrainingDisplay`.

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
| `os.ShowInput 0\|1` | Live controller input at the top of the screen: both sticks, both triggers, held buttons and the last eight presses and releases. Works without the greybox, so it also checks that the pad reaches the game |
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
4. The spin side kick lands in front, so the sides have switched: Left Lead. (Spin side and spin hook kicks switch sides on landing,
   with the same animated switch as the A button.)
5. The same RT roundhouse after the switch, now RS toward the other side with the right leg as the back leg: +2.
6. A side kick from too far: a clean miss, score unchanged.
7. Close in and a spin side kick to the head (RB): +6.
8. Final score Chung 16, Hong 0.

Not in the proof: the retargeted capture playing on the geared fighter. That needs the capture and retarget (issue 8), and the
greybox keeps placeholder timing until then.

## Connection to the menu's match HUD

While the greybox runs, the menu's Match screen is the display and its model is fed from the simulation
(`FOpenStanceMatchModelSync`, tests `OpenStance.Greybox.MatchModelSync`):

| Menu | Simulation |
| --- | --- |
| Score, results page, points by technique | Every contact the hit registry counted, with the move's name; a gam-jeom also gives the other fighter a point |
| Gam-jeom count and reasons | `PenaltyReasons` (punch to the head, kick below the belt, falling, holding or pushing) |
| Stamina bars | Each fighter's stamina |
| Round and clock | Three 2-minute rounds with a 2 s break; the clock holds while play is stopped |
| Referee call | Shi-jak, kal-yeo and kye-sok around a clinch, keu-man between rounds, gam-jeom on a penalty |
| Pause menu (Menu button, Esc) | Holds the simulation; Resume continues, Restart starts a fresh match |
| End of match | The 12-point gap or the last round's clock ends the simulation, and the HUD moves to the Results page |

Flow: Sparring, Fighter Select and Start raise `OnMatchRequested`; from the menu level the arena chosen on the setup screen
loads (Training dojang, Club dojang, National arena, Olympic arena are `L_TrainingDojang`, `L_ClubDojang`, `L_NationalArena`,
`L_CompetitionArena`) and the match starts itself, ready for the HUD. Quit to main menu returns to `L_MainMenu` at the main menu.
While gameplay drives the HUD every button belongs to the fighter; only Menu (or Esc) is taken, to pause.

## Choosing a side

Sparring now goes Setup, Side Select, Fighter Select, Match. Side Select shows Chung (blue, left) and Hong (red, right) with a
controller marker (P1, and P2 in a two-player match): left or right on the D-pad or left stick moves it, A continues, B goes
back. The side is kept in the menu session and handed to gameplay as `FOpenStanceMatchSetup::PlayerSide`. In the greybox the
controller drives that fighter, the camera follows it from behind, and the other side stands idle (or blocks, `os.AIMode`).
Fighter Select then picks the fighter on your side, and tags the sides "You" and "Opponent". The scoreboard, names and colors
stay by side: Chung on the left in blue, Hong on the right in red, whichever one you play.
