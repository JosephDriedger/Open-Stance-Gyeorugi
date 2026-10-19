# Menu system

The whole menu is written in C++ in `Source/OpenStance/Public/Menu` and `Private/Menu`. It is a port of the HTML prototype (`Docs/Prototype/menu_prototype.html`, which follows GDD 7.5 to 7.8). There are no Widget Blueprints, no CommonUI and no data assets: the project opens straight into it.

Press Play on `L_MainMenu` (the project's default map), or run `OpenStance.Menu.Show <Screen>` in the console (for example `OpenStance.Menu.Show Controls`) to jump to a screen.

## How it is built

| Layer | Classes | Job |
| --- | --- | --- |
| Game framework | `AOpenStanceMenuGameMode`, `AOpenStanceMenuPlayerController` | The menu level's game mode (no pawn); the controller opens the title screen. |
| Flow | `UOpenStanceMenuSubsystem` (a local-player subsystem) | The current screen, the back stack, dialogs, the pause menu and what the player has chosen (`FOpenStanceMenuSession`). Screens ask it to navigate and never open each other. |
| Screens | `UOpenStanceScreen` and one subclass per page | A UMG widget whose layout is written in C++ (`BuildContent`). The base adds the backdrop, the 1920 x 1080 canvas scaled to the viewport, the hint bar, the slide-in and the shared keys. |
| Widgets | `SOpenStanceFrame`, `SOpenStanceInteractive` and the items built on it, `SOpenStanceArt` (backdrop, fighter figure, controller diagram, stick icons), `OpenStanceMenuWidgets` (builders for tags, cards, glyphs, hint bar) | Slate. Every box, button and tag is one `SOpenStanceFrame` with different arguments; drawing goes through `OpenStanceMenuPaint` (polygons with per-vertex colour, so cut corners and angled gradients work). |
| Data | `OpenStanceMenuContent` (words and tables), `UOpenStanceMatchModel` (what the HUD shows), `UOpenStanceUserSettings` (options) | Kept apart from the screens so the real roster, rules and gameplay replace the placeholders in one place each. |

Sizes use the prototype's units: `OpenStanceMenu::U(1.0f)` is 1% of the stage width (19.2 px on the 1920 canvas), so numbers from the prototype's CSS can be used as they are. Colours and fonts are in `OpenStanceMenuTheme`.

## Input

B, Escape or Backspace goes back. LB and RB (Q and E, Page Up and Down, `[` and `]`) change tabs. A, Enter or Space presses. Left and right (D-pad, left stick or arrows) change a value row. The mouse hovers to focus and clicks to press. In a match the menu button or Escape pauses; while the match model is in demo mode A scores a random technique.

## Connecting gameplay

- Bind `UOpenStanceMenuSubsystem::OnMatchRequested`. It carries the chosen mode, both fighters and the setup rows (ruleset, difficulty, arena, bracket size) when a match starts.
- Fill `UOpenStanceMatchModel` (`AddPoints`, `SetStamina`, `AddGamJeom`, `SetCall`, `SetClock`) and set `bDemoMode = false`. The HUD only reads it. The model raises `OnFinished` and the HUD then opens Results.
- `UOpenStanceUserSettings` is registered through `GameUserSettingsClassName` in `DefaultEngine.ini`. Video options use the engine's own settings; audio levels, the controls options and the accessibility toggles are stored but nothing consumes them yet.

## Adding a screen

1. Add a value to `EOpenStanceMenuScreen` and a subclass of `UOpenStanceScreen` that implements `BuildContent` and `GetHints`.
2. Register the class in `UOpenStanceMenuSubsystem::GetScreenClass`.
3. Open it with `Menu->ShowScreen(...)`. Call `SetDefaultFocus` with the first item from `BuildContent`.
4. Add a line to `Tools/Unreal/capture_menu.py` so it gets a screenshot.

## Checking it

`Tools/Unreal/capture_menu.py` renders every screen offscreen to `Saved/Screenshots/Menu/` at the prototype's 1600 x 900, with the same file names as `Docs/Prototype/shots`. It needs no window:

```
C:\UE_5.8.0\Engine\Binaries\Win64\UnrealEditor-Cmd.exe D:\Open-Stance-Gyeorugi\OpenStance.uproject -RenderOffscreen -unattended -ExecCmds="py D:/Open-Stance-Gyeorugi/Tools/Unreal/capture_menu.py quit"
```

## Where it differs from the prototype, and why

- **Fonts.** The prototype uses Barlow Condensed and Barlow. The engine's Roboto Condensed and Roboto stand in (no licence or packaging work), drawn at 90% for the display faces because they are wider. To use Barlow, add the TTF files and change `GetCompositeFont` in `OpenStanceMenuTheme.cpp`; nothing else depends on the face.
- **Focused hub tile.** In the prototype the `.tile` focus rule replaces the tile's colour gradient with a flat panel, so a focused tile is dark with a white frame. The port reproduces that.
- **Tournament flow.** After a tournament match the Results page offers View bracket where a friendly match offers Rematch, so the bracket is reachable. The bracket itself still shows the prototype's example pairings.
- **Placeholders.** Fighter names, ratings, the career calendar, the bracket and the referee screens use the prototype's example content. Everything the design tags Future opens as an information page with the amber Future tag.
- **Python.** The screen enum is `EOpenStanceMenuScreen`, not `EOpenStanceScreen`, because Python drops the prefix and the name would collide with the `UOpenStanceScreen` widget class.
- **Level.** `Content/Maps/L_MainMenu.umap` is new content (Perforce); `Tools/Unreal/build_menu_level.py` rebuilds it.
