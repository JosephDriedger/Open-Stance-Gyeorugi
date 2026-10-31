# Combat data

How the sparring rules read their numbers (GDD 16.3, 16.6). Code is in `Source/OpenStance/{Public,Private}/Combat`.

## MoveData

One row per technique per target, in the Unreal Data Table `/Game/Combat/DT_MoveData` of the C++ row struct
`FOpenStanceMoveRow`. The row name is the move id, for example `SideKick_Trunk` or `SpinSide_Head`.

| Field | Meaning |
| --- | --- |
| `Technique`, `Target`, `bJump` | The row's key: which Skill Stick gesture it answers, aimed at the trunk or the head, grounded or jumping. Two rows may not share a key. |
| `GestureNotation`, `DisplayName` | Text for review and the move list; the game does not read them. |
| `bSpinning`, `Limb` | Spinning techniques score the higher values; punches trace the glove, kicks the foot guard. |
| `LeftLegMontage`, `RightLegMontage` | Captured montage for each physical leg. |
| `PlaceholderMontage` | Stand-in for either leg until the capture exists (GDD 16.4). |
| `StartupSeconds`, `ActiveSeconds`, `RecoverySeconds` | Phase timing; the recovery is the punishable window. |
| `CancelWindowSeconds` | Seconds into recovery from which the move may be cancelled; negative means never. |
| `StaminaCost` | Spent when the move starts (GDD 8.9). |
| `Points` | 1, 2, 3, 4 or 6 (GDD 8.3). |
| `ReachCm`, `Impact` | How far the trace reaches at a 175 cm fighter, and the strength compared with the protector's threshold. |
| `Reaction`, `SelfFallChance` | How the defender reacts (GDD 8.10), and the chance Attack Recovery ends in a fall. |

Head and body targets are separate rows, so a head kick has its own timing, points and animation. The leg that throws
a kick (lead or back, by stance) is chosen at runtime and only selects the montage: `ResolveMontage` returns the
montage for that leg, then the placeholder if allowed, then nothing. Combat code asks for timing, cost, points and
reach from the row and never names an animation, so swapping a placeholder for mocap is a table edit.

The Milestone 1 seed holds side/cut, roundhouse and spin side, each to the trunk and the head (six rows), on
placeholder montages. The starting numbers are provisional and tuned in playtests. Techniques without an approved input
(GDD 9.4) have no row.

## Runtime state

`FOpenStanceFighterState` holds stance, guard, the four held modifiers, the jump-primed flag, combat state, stamina,
score and penalties. `FOpenStanceMatchStatus` holds the match state, round and clock. Gameplay owns both. The HUD's
`UOpenStanceMatchModel` and the debug overlay only read them, so the rules run with no screen.

## CSV review and validation

The reviewed source of truth is `Data/Combat/DT_MoveData.csv` in Git. To rebuild the table and check it:

```
UnrealEditor-Cmd.exe OpenStance.uproject -unattended -nullrhi -ExecCmds="py D:/Open-Stance-Gyeorugi/Tools/Unreal/create_move_data_table.py [seed] [replace] [production] quit"
```

`seed` first rewrites the CSV from the moves built into the game module, `replace` overwrites an existing table, and
`production` fails any row still on a placeholder. Problems go to `Saved/Logs/create_move_data_table.txt`, one per
line. The checks are:

- no animation at all (neither a placeholder nor both legs' montages), and montage paths that do not exist;
- a phase of zero or negative length, a cancel window after the recovery ends, negative cost or reach, a fall chance
  outside 0 to 1;
- a point value that does not match the technique and target, a punch to the head (illegal, cannot score), a spinning
  flag or strike limb that does not match the technique, and two rows with the same key.

The same checks run in code as `FOpenStanceMoveData::Validate`, covered by the `OpenStance.MoveData.*` automation tests:

```
UnrealEditor-Cmd.exe OpenStance.uproject -ExecCmds="Automation RunTests OpenStance; Quit" -nullrhi -unattended -nosplash
```

## Units and naming

- Distances are centimetres (Unreal units, FBX `UnitScaleFactor 1`, matching the MetaHuman export); times are seconds.
- Asset prefixes: `DT_` data tables, `AM_` montages. Placeholder montages are
  `/Game/Animation/Moves/Placeholder/AM_Placeholder_<Technique>`; captured ones belong beside them in
  `/Game/Animation/Moves/`.

## Git and Perforce

| In Git | In Perforce |
| --- | --- |
| C++ row struct, validators and tests, `Data/Combat/DT_MoveData.csv`, the scripts in `Tools/Unreal`, this document | `Content/`: `DT_MoveData.uasset`, montages, animation sequences, blueprints |

The CSV is how a table change is reviewed in Git; the `.uasset` is rebuilt from it with the script above and checked in
to Perforce.
