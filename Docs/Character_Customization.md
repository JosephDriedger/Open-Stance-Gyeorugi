# Character Customization

How fighters in Open Stance are customized, and the rules every tool, material and menu must follow.

## Structure

A fighter is assembled from:

| Layer | Source | Customizable |
| --- | --- | --- |
| Body, head, face, hair, eyes | MetaHuman (MetaHuman Creator, UE 5.8) | Body type, face, hairstyle, skin tone, hair colour, eye colour |
| Dobok (jacket, pants) and belt | Fighter model, refit to MetaHuman bodies (`Tools/Blender/fit_to_body.py`) | Belt rank colour, collar colour |
| Sparring gear: helmet, chest protector (hogu), gloves, foot guards | Fighter model, refit to MetaHuman bodies | Side colour only (see below) |

Gear is a removable layer. Match views show the full gear; menu and career-mode views (e.g. a
fighter profile) show the fighter in dobok without gear.

## Colour rules

### Chest protector and helmet: side colours only

The chest protector and helmet colour is **not a player choice**. It shows which side the fighter
is on, as in World Taekwondo competition:

| Side | Colour | Value |
| --- | --- | --- |
| Chung (청) | Blue | The protector blue baked into `T_Fighter_BaseColor.png` |
| Hong (홍) | Red | sRGB `#C8102E` |

- There are exactly two states. Do not add colour pickers, extra team colours or tints for these parts.
- Implementation: a single `TeamSide` parameter (0 = Chung, 1 = Hong) driving mask channel R
  of `T_Fighter_Masks.png`. The Hong red is a fixed value, not an exposed colour parameter.
- The side is assigned by the match (who is Chung/Hong), not by the fighter's saved appearance.
- Menu and career screens show the fighter without gear, so no side colour applies there.

### Skin: real skin tones only

- In game, skin comes from the MetaHuman skin-tone picker, which samples a chart of real human
  skin tones. Only values from that picker may be used; no free RGB tint on skin.
- Freckles and accent regions (redness/saturation/lightness sliders) stay within their default
  clamped ranges.
- Blender previews of the original fighter model use the Monk Skin Tone scale
  (Google, CC BY 4.0), `MST01`–`MST10`, via `set_look(skin_tone="MST06")` in
  `Tools/Blender/preview_material.py`. It does not accept arbitrary colours.

### Hair: natural hair colours only

MetaHuman hair colour has two systems: a natural pigment model and dye colours. Only the
pigment model may be used.

| Allowed | MetaHuman groom parameter (material name) |
| --- | --- |
| Hair pigment | `Melanin` (`hairMelanin`), `Redness` (`hairRedness`), chosen on the Hair Color chart |
| Greying | `Whiteness` (`WhiteAmount`) |
| Lightness | `Lightness` (`LightAmount`) |
| Ombre, regions, highlights | Only their melanin/redness values (`OmbreMelanin`/`OmbreRedness`, `RegionMelanin`/`RegionRedness`, `HighlightsMelanin`/`HighlightsRedness`) |

| Not allowed | Parameter |
| --- | --- |
| Dye colours | `DyeColor` (`HairDye`), `OmbreColor` (`OmbreHairDye`), `RegionsColor` (`RegionhairDye`), `HighlightsColor` (`HighlightsHairDye`): leave at their neutral/white defaults |

Eyebrows, eyelashes and facial hair follow the same rule as hair. For eyelashes this means
`Melanin`, `Redness` and `Lightness` only, with `DyeColor` left white.

### Eyes: changeable, natural eye colours

Eye colour is a player choice, limited to natural human eye colours (the same principle as skin
and hair).

| Allowed | MetaHuman iris parameter (eye material name) |
| --- | --- |
| Iris colour | `PrimaryColorU` / `PrimaryColorV` (`Iris Primary Color Hue` / value), set from the natural presets below |
| Two-tone irises (e.g. hazel, central heterochromia) | `SecondaryColorU` / `SecondaryColorV` from the same presets, `ColorBlend`, `ColorBlendSoftness`, `BlendMethod` |
| Iris structure | `IrisPattern`, `IrisRotation`, `ShadowDetails`, `LimbalRingSize`, `LimbalRingSoftness` |
| Left and right eye | Set independently (`EyeLeft` / `EyeRight`), but default to matching |

| Not allowed | Parameter |
| --- | --- |
| Free tints | `GlobalTint` (stays white), `LimbalRingColor` (stays black), sclera `bUseCustomTint` (stays off), cornea `LimbusColor` (stays white) |
| Oversaturation | `GlobalSaturation` above its default (2.0) |

Natural presets. Values are coordinates on MetaHuman's iris colour chart
(`/MetaHumanCharacter/Lookdev_UHM/Eye/Textures/T_iris_color_picker`, exported to
`Resources/Models/MetaHuman/T_iris_color_picker.png`). The chart itself only spans natural iris
colours: U runs blue-grey → green → hazel → brown, V runs dark → light. Chart swatches look muted
because the eye material applies `GlobalSaturation` (default 2.0) on top.

| Preset | Primary U, V | Chart swatch (sRGB) | Secondary U, V | Notes |
| --- | --- | --- | --- | --- |
| Dark brown | 0.82, 0.15 | `#392819` | — | Most common worldwide |
| Brown | 0.75, 0.45 | `#5B432B` | — | |
| Amber | 0.65, 0.75 | `#6C5639` | — | Golden brown |
| Hazel | 0.42, 0.60 | `#4F5344` | 0.72, 0.45 | Green outer, brown inner; `ColorBlend` 0.5 |
| Green | 0.40, 0.60 | `#4C5446` | — | |
| Blue | 0.15, 0.55 | `#454D5B` | — | |
| Grey | 0.08, 0.85 | `#606570` | — | |

Check each preset once in MetaHuman Creator's Eyes tool (the chart's V axis could be flipped in the
picker); adjust the table if a preset renders lighter or darker than its name.

### Belt and collar

- Belt (mask channel G): rank colours. The rank list is still to be defined.
- Collar (mask channel B): dobok collar colour (black dan collar, red-black poom collar, or white).

## Body types

Body shape comes from MetaHuman body types. The dobok and gear are refit to each body so they
follow the body instead of using separate morph targets. The `BodyHeavy` / `BodyMuscular` /
`BodySlim` shape keys on the original fighter model are only for that model's previews.

## Where these rules are enforced

| Place | Enforcement |
| --- | --- |
| `Tools/Blender/preview_material.py` | `set_look(side="chung"\|"hong", ..., skin_tone="MST01".."MST10")`; no free team or skin colour |
| Unreal fighter gear material | `TeamSide` scalar only; Hong red is a constant |
| Character creator / career UI | Skin: MetaHuman tone chart only. Hair: pigment chart, greying and lightness only; no dye controls. Eyes: natural iris presets (per eye), no tint controls |
| Match setup | Assigns Chung/Hong per fighter |
