# Art asset inventory and production checklist

The inventory is `Docs/Art_Asset_Inventory.csv`, one row per asset (GDD 15, 18.1, 20). Open it in Excel or Sheets; it is plain
CSV so changes review in Git. `py -3 Tools/build_asset_inventory.py` rebuilds it from the project: it walks `Content/` (so run it
on a machine with Perforce synced) and the tracked source folders, and keeps what people have typed into the manual columns.

## Columns

| Column | Filled by |
| --- | --- |
| Category, Name, Type, Unreal path, Source path, Version control, Origin, Status, Notes | the script, from folders and naming |
| Revision (Perforce changelist or Git commit), Milestone, Acceptance owner, Review, Usage rights | the team, by hand; kept on every rebuild |

Status says what an asset is, never that it is final: **Generated** (made by a project script, not hand-authored art),
**Generated (working)** (exports kept for the Blender refit, not shipped), **Test asset**, **Placeholder**, **Reference**,
**Plan**, **Engine**, **Test data**. A row moves to **Production** when its acceptance owner has signed it off, which is how
the placeholder replacements and the credits and licence list are tracked. Perforce was not reachable when the CSV was
first built, so every Revision, owner, review and rights cell starts blank rather than guessed.

## What is in it (590 rows)

| Category | Rows | Notes |
| --- | --- | --- |
| Fighter characters | 5 | Five MetaHuman body types |
| Fighter gear and wardrobe | 122 | Seven-piece gear per body type, hidden face maps, shared materials and textures |
| Fighter belt | 31 | Belt bone chains and physics assets |
| Fighter animation | 18 | Hand poses and expressions, hand-keyed; no mocap yet |
| Fighter export | 15 | Working exports for the Blender refit |
| Referees, referee outfits, referee export | 14, 78, 18 | Six referees in uniform |
| Environment meshes, materials, textures | 64, 144, 61 | Arena and venue props; each mesh and texture links its `Resources/Environment` source |
| Levels | 9 | Arena, dojang and Career venues, main menu |
| Combat data | 1 | `DT_MoveData` (see Combat_Data.md) |
| Source folders, reference art, UI, fonts | 2, 1, 3, 1 | Fighter and environment source, reference images, the menu prototype, controller glyphs and menu art (drawn in C++, no texture files), the Roboto fonts |
| Mocap and audio plans | 1 each | The shot list and the audio recording list, linked rather than restated |

The existing character, gear, referee and venue assets above are generated and counted as such; they are not listed as unfinished.

## Linked lists

- Mocap: `Docs/Open_Stance_Mocap_Shot_List.docx` (plan), `Docs/Mocap_Record.md` (recording day), `Docs/Mocap_Test.md` (limited
  test), `Docs/Vicon_Nexus_Test.md` (historical lab detail). No captured motion is in the project yet; the MotionBuilder
  character is preparation.
- Audio: `Docs/Open_Stance_Audio_Recording_List.docx`. There are no audio files in `Content/` or `Resources/`.

## Gaps

Each of these was checked against the repository (no matching file in `Content/`, `Resources/` or `Source/`):

1. **Achievement and trophy icons** (GDD 5.7): none exist.
2. **Easter-egg capture and props** (GDD 6.5): the extra motion capture shot and the props (the rag, the bullet-time camera
   orbit's content, the crowd signs) have no assets.
3. **Audio**: no voice, effects, ambience or music files.
4. **Captured fight animation**: no mocap clip is imported; every kick will run on placeholder montages.
5. **Placeholder montages** `AM_Placeholder_SideKick`, `AM_Placeholder_Roundhouse` and `AM_Placeholder_SpinSide`: `DT_MoveData`
   points at them and they do not exist yet; `create_move_data_table.py` reports them.
6. **Controller glyphs as textures**: the menu draws its icons in code. If licensed glyph art replaces them, add rows then.

## Using it

- Replacing a placeholder: set Status to Production, fill Review and Revision, and update the row's Usage rights.
- Release credits and licences: filter on Usage rights (MetaHuman characters carry Epic's MetaHuman licence; the fonts ship with
  the engine) and on any row still blank before release.
