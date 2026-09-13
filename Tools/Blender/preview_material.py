"""Build M_Fighter_Customizable: a Blender preview of the Unreal recolour material.

Uses T_Fighter_BaseColor + T_Fighter_Masks (from make_masks.py). Each masked region is
replaced by  Colour * (luminance / region reference luminance)  so the original shading
and fabric detail survive the recolour. The same maths ports directly to a UE material.

After running: set_look(side="hong", belt=(r,g,b), collar=(r,g,b), skin_tone="MST06").
Colour rules (Docs/Character_Customization.md): the protector and helmet are only Chung blue
or Hong red; skin only uses real skin tones.
"""
import bpy
import numpy as np
import rig_config as cfg

log = cfg.open_log("preview_material")

PART_NAMES = ["Head", "BodySkin", "Helmet", "Protector", "Jacket", "Pants", "Belt", "Gloves", "FootGuards"]
base_img = bpy.data.images["T_Fighter_BaseColor"]
mask_img = bpy.data.images["T_Fighter_Masks"]
mask_img.colorspace_settings.name = 'Non-Color'
mask_img.alpha_mode = 'CHANNEL_PACKED'

# --- reference luminance per masked region (linear), used to normalise shading ---
W, H = base_img.size
b = np.empty(W * H * 4, dtype=np.float32)
base_img.pixels.foreach_get(b)
b = b.reshape(H, W, 4)[:, :, :3]
lin = np.where(b <= 0.04045, b / 12.92, ((b + 0.055) / 1.055) ** 2.4)
lum = lin @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
m = np.empty(W * H * 4, dtype=np.float32)
mask_img.pixels.foreach_get(m)
m = m.reshape(H, W, 4)
REF = {}
for ch, name in enumerate(["team", "belt", "collar"]):
    sel = lum[m[:, :, ch] > 0.5]
    # median, not mean: a few bright stitching/highlight pixels would skew a mean on dark cloth
    REF[name] = max(float(np.median(sel)) if sel.size else 0.05, 1e-3)
    log(name, "pixels", sel.size, "median lum", round(REF[name], 4),
        "p10/p90", [round(float(v), 4) for v in np.percentile(sel, [10, 90])] if sel.size else None)

mat = bpy.data.materials.get("M_Fighter_Customizable") or bpy.data.materials.new("M_Fighter_Customizable")
mat.use_nodes = True
nt = mat.node_tree
nt.nodes.clear()
N, L = nt.nodes, nt.links


def node(kind, x, y, label=None, **props):
    n = N.new(kind)
    n.location = (x, y)
    if label:
        n.name = n.label = label
    for k, v in props.items():
        setattr(n, k, v)
    return n


out = node("ShaderNodeOutputMaterial", 1800, 0)
bsdf = node("ShaderNodeBsdfPrincipled", 1500, 0)
bsdf.inputs["Roughness"].default_value = 0.8
L.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

t_base = node("ShaderNodeTexImage", -900, 200, image=base_img)
t_mask = node("ShaderNodeTexImage", -900, -300, image=mask_img)
sep = node("ShaderNodeSeparateColor", -600, -300)
L.new(t_mask.outputs["Color"], sep.inputs["Color"])
bw = node("ShaderNodeRGBToBW", -600, 400)
L.new(t_base.outputs["Color"], bw.inputs["Color"])


def tinted(param, ref, detail, y):
    """Colour param * clamp(lum / ref, 0, 3) ^ detail.

    detail < 1 compresses the shading ratio: dark cloth varies a lot relative to its
    median, so an uncompressed ratio would blotch a light replacement colour.
    """
    col = node("ShaderNodeRGB", -300, y, label=param)
    div = node("ShaderNodeMath", -300, y - 200, operation='DIVIDE')
    L.new(bw.outputs["Val"], div.inputs[0])
    div.inputs[1].default_value = ref
    clamp = node("ShaderNodeClamp", -100, y - 200)
    clamp.inputs["Max"].default_value = 3.0
    L.new(div.outputs["Value"], clamp.inputs["Value"])
    power = node("ShaderNodeMath", 0, y - 300, label=param + "Detail", operation='POWER')
    L.new(clamp.outputs["Result"], power.inputs[0])
    power.inputs[1].default_value = detail
    scale = node("ShaderNodeVectorMath", 100, y, operation='SCALE')
    L.new(col.outputs["Color"], scale.inputs[0])
    L.new(power.outputs["Value"], scale.inputs["Scale"])
    return scale.outputs["Vector"]


def mix(a, b_sock, fac_sock, x, y):
    mx = node("ShaderNodeMix", x, y, data_type='RGBA')
    L.new(fac_sock, mx.inputs["Factor"])
    L.new(a, mx.inputs[6])
    L.new(b_sock, mx.inputs[7])
    return mx.outputs[2]


c = t_base.outputs["Color"]

# Team colour is a side, not a choice: Chung (blue) is the baked texture, Hong (red) is one
# fixed red. TeamSide 0 = Chung, 1 = Hong; there is deliberately no free colour input.
team_side = node("ShaderNodeValue", 100, 1100, label="TeamSide")
team_fac = node("ShaderNodeMath", 250, 900, operation='MULTIPLY')
L.new(sep.outputs["Red"], team_fac.inputs[0])
L.new(team_side.outputs["Value"], team_fac.inputs[1])
c = mix(c, tinted("HongRed", REF["team"], 0.8, 900), team_fac.outputs["Value"], 400, 600)

c = mix(c, tinted("BeltColor", REF["belt"], 0.35, 400), sep.outputs["Green"], 600, 300)
c = mix(c, tinted("CollarColor", REF["collar"], 0.35, -100), sep.outputs["Blue"], 800, 0)

# Skin is limited to real skin tones: the multiplier maps the texture's measured skin colour
# onto a Monk Skin Tone reference colour (see SKIN_TONES), never an arbitrary tint.
skin = node("ShaderNodeRGB", 800, -400, label="SkinToneMultiplier")
skin_mul = node("ShaderNodeMix", 1000, -250, data_type='RGBA', blend_type='MULTIPLY')
skin_mul.inputs["Factor"].default_value = 1.0
L.new(c, skin_mul.inputs[6])
L.new(skin.outputs["Color"], skin_mul.inputs[7])
c = mix(c, skin_mul.outputs[2], t_mask.outputs["Alpha"], 1200, 0)
L.new(c, bsdf.inputs["Base Color"])


def srgb_to_linear(hex_colour):
    rgb = [int(hex_colour[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    return tuple(v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in rgb)


# World Taekwondo sides. Chung keeps the baked protector blue; Hong uses this red.
HONG_RED = srgb_to_linear("#C8102E")

# Monk Skin Tone scale (Google, CC BY 4.0): 10 reference colours spanning real human skin.
SKIN_TONES = {f"MST{i + 1:02d}": srgb_to_linear(h) for i, h in enumerate(
    ["#F6EDE4", "#F3E7DB", "#F7EAD0", "#EADABA", "#D7BD96", "#A07E56", "#825C43", "#604134", "#3A312A", "#292420"])}
SKIN_ALBEDO_SCALE = 0.6   # swatches are lit appearance; skin albedo peaks around 0.55-0.6 linear

skin_sel = m[:, :, 3] > 0.5
SKIN_REF = tuple(float(v) for v in np.median(lin[skin_sel], axis=0)) if skin_sel.any() else (0.35, 0.22, 0.16)
log("texture skin reference (linear):", [round(v, 4) for v in SKIN_REF])


def set_look(side="chung", belt=None, collar=None, skin_tone=None):
    """side: "chung" (blue) or "hong" (red). belt/collar: linear RGB or None for the original.
    skin_tone: a SKIN_TONES key ("MST01".."MST10") or None for the texture's own skin."""
    nodes = bpy.data.materials["M_Fighter_Customizable"].node_tree.nodes
    if side not in ("chung", "hong"):
        raise ValueError('side must be "chung" (blue) or "hong" (red)')
    nodes["TeamSide"].outputs[0].default_value = 1.0 if side == "hong" else 0.0
    nodes["HongRed"].outputs[0].default_value = (*HONG_RED, 1.0)
    for name, val, orig in (("BeltColor", belt, (0.002, 0.002, 0.002)), ("CollarColor", collar, (0.002, 0.002, 0.002))):
        nodes[name].outputs[0].default_value = (*(val if val is not None else orig), 1.0)
    if skin_tone is None:
        mult = (1.0, 1.0, 1.0)
    else:
        if skin_tone not in SKIN_TONES:
            raise ValueError(f"skin_tone must be one of {sorted(SKIN_TONES)}")
        target = [v * SKIN_ALBEDO_SCALE for v in SKIN_TONES[skin_tone]]
        mult = tuple(t / max(r, 1e-4) for t, r in zip(target, SKIN_REF))
    nodes["SkinToneMultiplier"].outputs[0].default_value = (*mult, 1.0)


set_look()

for n in PART_NAMES:
    obj = bpy.data.objects.get(f"{cfg.MESH_NAME}_{n}")
    if obj:
        obj.data.materials.clear()
        obj.data.materials.append(mat)
log("assigned M_Fighter_Customizable to parts")
log.close()
