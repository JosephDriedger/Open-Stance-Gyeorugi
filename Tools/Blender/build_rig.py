"""Rebuild the Meshy fighter rig as a UE5 Mannequin (Manny)-compatible skeleton.

Run after import_source.py. Replaces the imported armature, creates the new bones,
and binds the mesh with bone-heat weights. Bone heat is only trusted for the hands;
reweight.py replaces the rest of the body weights.

Joint positions were measured from this mesh's T-pose (see analyze_mesh.py) and are
specific to it: re-measure if the source model changes.
Blender space: Z up, character faces -Y, character's left is +X.
"""
import bpy
from mathutils import Vector
import rig_config as cfg

log = cfg.open_log("build_rig")

UP, FWD = (0, 0, 1), (0, -1, 0)

# name: (head, tail, parent, roll_vector, deform)
BONES = {}
def B(name, head, tail, parent, roll=FWD, deform=True):
    BONES[name] = (Vector(head), Vector(tail), parent, roll, deform)

# ---- center ----
B("root",     (0, 0, 0),         (0, 0.2, 0),        None,      UP, False)
B("pelvis",   (0, 0.020, 0.940), (0, 0.030, 0.990),  "root")
B("spine_01", (0, 0.030, 0.990), (0, 0.035, 1.070),  "pelvis")
B("spine_02", (0, 0.035, 1.070), (0, 0.040, 1.150),  "spine_01")
B("spine_03", (0, 0.040, 1.150), (0, 0.040, 1.230),  "spine_02")
B("spine_04", (0, 0.040, 1.230), (0, 0.035, 1.310),  "spine_03")
B("spine_05", (0, 0.035, 1.310), (0, 0.030, 1.390),  "spine_04")
B("neck_01",  (0, 0.030, 1.390), (0, 0.030, 1.430),  "spine_05")
B("neck_02",  (0, 0.030, 1.430), (0, 0.025, 1.475),  "neck_01")
B("head",     (0, 0.025, 1.475), (0, 0.025, 1.700),  "neck_02")

# ---- left arm ----
B("clavicle_l",  (0.025, -0.005, 1.375), (0.175, 0.025, 1.360), "spine_05", UP)
B("upperarm_l",  (0.175, 0.025, 1.360),  (0.435, 0.035, 1.352), "clavicle_l", UP)
B("lowerarm_l",  (0.435, 0.035, 1.352),  (0.660, 0.024, 1.363), "upperarm_l", UP)
B("hand_l",      (0.660, 0.024, 1.363),  (0.740, 0.020, 1.364), "lowerarm_l", UP)

def finger(prefix, meta_head, knuckle, tip, z, ratios=(0.47, 0.29, 0.24)):
    """meta_head/knuckle/tip are (x, y); z is the finger's height."""
    mh = Vector((meta_head[0], meta_head[1], z))
    k = Vector((knuckle[0], knuckle[1], z))
    t = Vector((tip[0], tip[1], z))
    B(f"{prefix}_metacarpal_l", mh, k, "hand_l", UP)
    j1 = k + (t - k) * ratios[0]
    j2 = j1 + (t - k) * ratios[1]
    B(f"{prefix}_01_l", k, j1, f"{prefix}_metacarpal_l", UP)
    B(f"{prefix}_02_l", j1, j2, f"{prefix}_01_l", UP)
    B(f"{prefix}_03_l", j2, t, f"{prefix}_02_l", UP)

finger("index",  (0.685, 0.006), (0.779, -0.004), (0.857, -0.001), 1.364)
finger("middle", (0.685, 0.016), (0.782, 0.013),  (0.867, 0.014),  1.365)
finger("ring",   (0.685, 0.026), (0.779, 0.030),  (0.859, 0.032),  1.364)
finger("pinky",  (0.683, 0.036), (0.774, 0.045),  (0.839, 0.049),  1.362)

B("thumb_01_l", (0.683, -0.006, 1.352), (0.728, -0.024, 1.348), "hand_l", UP)
B("thumb_02_l", (0.728, -0.024, 1.348), (0.772, -0.031, 1.348), "thumb_01_l", UP)
B("thumb_03_l", (0.772, -0.031, 1.348), (0.808, -0.031, 1.350), "thumb_02_l", UP)

# ---- left leg ----
B("thigh_l", (0.103, -0.005, 0.881), (0.140, 0.000, 0.490),  "pelvis")
B("calf_l",  (0.140, 0.000, 0.490),  (0.180, 0.050, 0.085),  "thigh_l")
B("foot_l",  (0.180, 0.050, 0.085),  (0.203, -0.090, 0.028), "calf_l", UP)
B("ball_l",  (0.203, -0.090, 0.028), (0.203, -0.160, 0.028), "foot_l", UP)

# ---- twist bones (Manny layout): (twist name, main bone, t along main bone) ----
TWISTS = [
    ("upperarm_twist_01_l", "upperarm_l", 0.15),
    ("upperarm_twist_02_l", "upperarm_l", 0.50),
    ("lowerarm_twist_02_l", "lowerarm_l", 0.50),
    ("lowerarm_twist_01_l", "lowerarm_l", 0.85),
    ("thigh_twist_01_l",    "thigh_l",    0.15),
    ("thigh_twist_02_l",    "thigh_l",    0.50),
    ("calf_twist_02_l",     "calf_l",     0.50),
    ("calf_twist_01_l",     "calf_l",     0.85),
]
for tw, main, t in TWISTS:
    h, tl, _, roll, _ = BONES[main]
    d = tl - h
    B(tw, h + d * t, h + d * (t + 0.2), main, roll)

# ---- mirror left -> right ----
def mirror_name(n):
    return n[:-2] + "_r" if n.endswith("_l") else n

for name in [n for n in BONES if n.endswith("_l")]:
    h, t, par, roll, deform = BONES[name]
    B(mirror_name(name), (-h.x, h.y, h.z), (-t.x, t.y, t.z), mirror_name(par) if par else None, roll, deform)

# ---- IK helper bones (non-deforming, match Manny) ----
def copy_bone(new, src, parent):
    h, t, _, roll, _ = BONES[src]
    B(new, h, t, parent, roll, False)

B("ik_foot_root", (0, 0, 0), (0, 0.2, 0), "root", UP, False)
copy_bone("ik_foot_l", "foot_l", "ik_foot_root")
copy_bone("ik_foot_r", "foot_r", "ik_foot_root")
B("ik_hand_root", (0, 0, 0), (0, 0.2, 0), "root", UP, False)
copy_bone("ik_hand_gun", "hand_r", "ik_hand_root")
copy_bone("ik_hand_l", "hand_l", "ik_hand_gun")
copy_bone("ik_hand_r", "hand_r", "ik_hand_gun")

log("bones defined:", len(BONES))

# =====================================================================
# Replace the imported armature
# =====================================================================
if bpy.context.object and bpy.context.object.mode != 'OBJECT':
    bpy.ops.object.mode_set(mode='OBJECT')

mesh = next(o for o in bpy.data.objects if o.type == 'MESH')
coll = mesh.users_collection[0]

mw = mesh.matrix_world.copy()
mesh.parent = None
mesh.matrix_world = mw
for m in list(mesh.modifiers):
    if m.type == 'ARMATURE':
        mesh.modifiers.remove(m)
mesh.vertex_groups.clear()

for o in [o for o in bpy.data.objects if o.type == 'ARMATURE']:
    data = o.data
    bpy.data.objects.remove(o, do_unlink=True)
    if data.users == 0:
        bpy.data.armatures.remove(data)
for a in list(bpy.data.actions):
    if a.users == 0 or a.name.startswith("Armature|"):
        bpy.data.actions.remove(a)

mesh.name = cfg.MESH_NAME
mesh.data.name = cfg.MESH_NAME

arm_data = bpy.data.armatures.new(cfg.ARMATURE_NAME)
arm = bpy.data.objects.new(cfg.ARMATURE_NAME, arm_data)
coll.objects.link(arm)

def deselect_all():
    # refresh first: removed objects can leave stale entries in the view layer
    bpy.context.view_layer.update()
    for o in bpy.data.objects:
        if o.name in bpy.context.view_layer.objects:
            o.select_set(False)

deselect_all()
bpy.context.view_layer.objects.active = arm
arm.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')

eb = arm_data.edit_bones
for name, (h, t, par, roll, deform) in BONES.items():
    b = eb.new(name)
    b.head, b.tail = h, t
    b.use_deform = deform
for name, (h, t, par, roll, deform) in BONES.items():
    b = eb[name]
    if par:
        b.parent = eb[par]
        b.use_connect = ((eb[par].tail - b.head).length < 1e-4
                         and not name.startswith("ik_") and "twist" not in name)
    if roll:
        b.align_roll(Vector(roll))
bpy.ops.object.mode_set(mode='OBJECT')
log("armature created:", len(arm_data.bones))

arm.show_in_front = True
arm_data.display_type = 'OCTAHEDRAL'

# =====================================================================
# Bind with bone heat (twist bones excluded; reweight.py splits them in)
# =====================================================================
twist_names = {tw for tw, _, _ in TWISTS} | {mirror_name(tw) for tw, _, _ in TWISTS}
for b in arm_data.bones:
    if b.name in twist_names:
        b.use_deform = False

deselect_all()
mesh.select_set(True)
arm.select_set(True)
bpy.context.view_layer.objects.active = arm
log("parent_set ARMATURE_AUTO:", bpy.ops.object.parent_set(type='ARMATURE_AUTO'))

for b in arm_data.bones:
    if b.name in twist_names:
        b.use_deform = True
for n in twist_names:
    if n not in mesh.vertex_groups:
        mesh.vertex_groups.new(name=n)

log("vertex groups:", len(mesh.vertex_groups))
log.close()
