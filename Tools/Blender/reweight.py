"""Region + joint-chain skin weights for the T-posed fighter.

Blender's bone heat breaks down on this mesh's torso (layered clothing: shirt modelled
under the chest protector), so body weights are computed from anatomical regions with
smooth blends at each joint, then Laplacian-smoothed. Hands/fingers keep the bone-heat
result from build_rig.py because it was clean there.

All thresholds are in Blender metres for this specific T-pose mesh.
"""
import bpy
import rig_config as cfg

log = cfg.open_log("reweight")

arm = bpy.data.objects[cfg.ARMATURE_NAME]
mesh = bpy.data.objects[cfg.MESH_NAME]
me = mesh.data
mw = mesh.matrix_world
idx_name = {g.index: g.name for g in mesh.vertex_groups}


def ss(x, a, b):
    """Smoothstep from a to b."""
    if x <= a:
        return 0.0
    if x >= b:
        return 1.0
    t = (x - a) / (b - a)
    return t * t * (3 - 2 * t)


def chain(s, bones, joints):
    """Partition of unity along a bone chain.

    bones: n+1 names; joints: n (s_j, blend_radius) with increasing s_j.
    """
    out = {}
    carry = 1.0
    for k, name in enumerate(bones):
        if k < len(joints):
            sj, rj = joints[k]
            t = ss(s, sj - rj, sj + rj)
            w = carry * (1.0 - t)
            carry *= t
        else:
            w = carry
        if w > 1e-6:
            out[name] = out.get(name, 0.0) + w
    return out


def add(dst, src, f):
    if f <= 0:
        return
    for k, w in src.items():
        dst[k] = dst.get(k, 0.0) + w * f


HAND_PREFIXES = ("hand_", "index_", "middle_", "ring_", "pinky_", "thumb_", "lowerarm_")

TORSO_BONES = ["pelvis", "spine_01", "spine_02", "spine_03", "spine_04", "spine_05", "neck_01", "neck_02", "head"]
TORSO_JOINTS = [(0.99, 0.04), (1.07, 0.04), (1.15, 0.04), (1.23, 0.04), (1.31, 0.04),
                (1.39, 0.025), (1.43, 0.02), (1.475, 0.02)]

new_w = []
for v in me.vertices:
    x, y, z = mw @ v.co

    # --- bone-heat weights for the hands, filtered to hand-related groups ---
    heat_hand = {}
    for g in v.groups:
        n = idx_name[g.group]
        if n.startswith(HAND_PREFIXES) and g.weight > 0.0:
            n = n.replace("lowerarm_twist_01_", "lowerarm_").replace("lowerarm_twist_02_", "lowerarm_")
            heat_hand[n] = heat_hand.get(n, 0.0) + g.weight

    # --- torso / neck / head (chain parameter is height) ---
    r_xy = (x * x + (y - 0.03) ** 2) ** 0.5
    s = z
    if z < 1.47:
        wide = ss(r_xy, 0.07, 0.10)  # collar / shoulders are not neck
        s = z * (1 - wide) + min(z, 1.36) * wide
    torso = chain(s, TORSO_BONES, TORSO_JOINTS)
    side = "l" if x >= 0 else "r"
    clav = ss(abs(x), 0.07, 0.15) * ss(z, 1.28, 1.37)
    if clav > 0:
        torso = {k: w * (1 - clav) for k, w in torso.items()}
        torso[f"clavicle_{side}"] = torso.get(f"clavicle_{side}", 0.0) + clav

    # --- arms (T-pose: chain parameter is distance from the midline) ---
    arms = {}
    arm_total = 0.0
    for sd, sgn in (("l", 1), ("r", -1)):
        u = sgn * x
        # below the armpit, the torso side stays on the spine
        m = ss(u, 0.15, 0.21) * max(ss(z, 1.19, 1.27), ss(u, 0.21, 0.26))
        if m <= 0:
            continue
        a = chain(u, [f"clavicle_{sd}", f"upperarm_{sd}", f"lowerarm_{sd}", f"hand_{sd}"],
                  [(0.175, 0.045), (0.435, 0.045), (0.66, 0.025)])
        hm = ss(u, 0.645, 0.675)
        hh = {k: w for k, w in heat_hand.items() if k.endswith("_" + sd)}
        if hm > 0 and hh:
            tot = sum(hh.values())
            mixed = {}
            add(mixed, a, 1 - hm)
            add(mixed, {k: w / tot for k, w in hh.items()}, hm)
            a = mixed
        add(arms, a, m)
        arm_total += m
    arm_total = min(arm_total, 1.0)

    upper = {}
    add(upper, torso, 1 - arm_total)
    add(upper, arms, 1.0)

    # --- legs (chain parameter is depth below the hips) ---
    back = ss(y, 0.0, 0.10) * 0.08  # gluteal fold sits lower than the front hip crease
    legm = 1.0 - ss(z, 0.74 - back, 0.89 - back)
    final = {}
    if legm > 0:
        legs = {}
        lf = ss(x, -0.015, 0.015)
        for sd, f in (("l", lf), ("r", 1 - lf)):
            if f <= 0:
                continue
            lw = chain(-z, [f"thigh_{sd}", f"calf_{sd}"], [(-0.49, 0.045)])
            footm = 1.0 - ss(z, 0.065, 0.12)
            if footm > 0:
                ball = ss(-y, 0.065, 0.10)
                lw = {k: w * (1 - footm) for k, w in lw.items()}
                add(lw, {f"foot_{sd}": 1 - ball, f"ball_{sd}": ball}, footm)
            add(legs, lw, f)
        add(final, legs, legm)
    add(final, upper, 1 - legm)
    new_w.append(final)

log("computed raw weights")

# --- Laplacian smoothing (hands locked so finger separation stays crisp) ---
nbrs = [[] for _ in me.vertices]
for e in me.edges:
    a, b = e.vertices
    nbrs[a].append(b)
    nbrs[b].append(a)
lock = [abs((mw @ v.co).x) > 0.64 for v in me.vertices]

for _ in range(6):
    nxt = []
    for i, w in enumerate(new_w):
        if lock[i] or not nbrs[i]:
            nxt.append(w)
            continue
        acc = {}
        for j in nbrs[i]:
            add(acc, new_w[j], 1.0 / len(nbrs[i]))
        mixed = {}
        add(mixed, w, 0.5)
        add(mixed, acc, 0.5)
        nxt.append(mixed)
    new_w = nxt
log("smoothed")

# Belt / protector line stays on the pelvis: fade out smoothed-in thigh influence above the hip crease.
for i, v in enumerate(me.vertices):
    keep = 1.0 - ss((mw @ v.co).z, 0.86, 0.91)
    if keep >= 1.0:
        continue
    w = new_w[i]
    moved = 0.0
    for k in list(w):
        if k.startswith("thigh_"):
            moved += w[k] * (1 - keep)
            w[k] *= keep
    if moved > 0:
        w["pelvis"] = w.get("pelvis", 0.0) + moved

# --- split limb weights onto twist bones: (t along main bone, group) with linear hats ---
TWIST_SPLIT = {}
for sd in ("l", "r"):
    TWIST_SPLIT[f"upperarm_{sd}"] = [(0.15, f"upperarm_twist_01_{sd}"), (0.50, f"upperarm_twist_02_{sd}"), (0.85, f"upperarm_{sd}")]
    TWIST_SPLIT[f"lowerarm_{sd}"] = [(0.15, f"lowerarm_{sd}"), (0.50, f"lowerarm_twist_02_{sd}"), (0.85, f"lowerarm_twist_01_{sd}")]
    TWIST_SPLIT[f"thigh_{sd}"] = [(0.15, f"thigh_twist_01_{sd}"), (0.50, f"thigh_twist_02_{sd}"), (0.85, f"thigh_{sd}")]
    TWIST_SPLIT[f"calf_{sd}"] = [(0.15, f"calf_{sd}"), (0.50, f"calf_twist_02_{sd}"), (0.85, f"calf_twist_01_{sd}")]
seg = {}
for main in TWIST_SPLIT:
    b = arm.data.bones[main]
    seg[main] = (arm.matrix_world @ b.head_local, arm.matrix_world @ b.tail_local)


def hat(t, nodes):
    if t <= nodes[0][0]:
        return {nodes[0][1]: 1.0}
    if t >= nodes[-1][0]:
        return {nodes[-1][1]: 1.0}
    for (t0, g0), (t1, g1) in zip(nodes, nodes[1:]):
        if t0 <= t <= t1:
            a = (t - t0) / (t1 - t0)
            return {g0: 1 - a, g1: a}


MAX_INF = 4
MIN_W = 0.02
final_w = []
for v, w in zip(me.vertices, new_w):
    co = mw @ v.co
    out = {}
    for g, val in w.items():
        if g in TWIST_SPLIT:
            h, t = seg[g]
            d = t - h
            tt = max(0.0, min(1.0, (co - h).dot(d) / d.length_squared))
            add(out, hat(tt, TWIST_SPLIT[g]), val)
        else:
            out[g] = out.get(g, 0.0) + val
    out = {k: x for k, x in out.items() if x >= MIN_W}
    out = dict(sorted(out.items(), key=lambda kv: -kv[1])[:MAX_INF])
    tot = sum(out.values())
    final_w.append({k: x / tot for k, x in out.items()} if tot > 0 else {"pelvis": 1.0})

# --- write groups ---
all_idx = list(range(len(me.vertices)))
for g in mesh.vertex_groups:
    g.remove(all_idx)
groups = {g.name: g for g in mesh.vertex_groups}
for b in arm.data.bones:
    if b.use_deform and b.name not in groups:
        groups[b.name] = mesh.vertex_groups.new(name=b.name)
by_group = {}
for i, w in enumerate(final_w):
    for g, val in w.items():
        by_group.setdefault((g, round(val, 3)), []).append(i)
for (g, val), ids in by_group.items():
    groups[g].add(ids, val, 'REPLACE')

counts = {}
for w in final_w:
    for g, val in w.items():
        if val > 0.5:
            counts[g] = counts.get(g, 0) + 1
log("dominant-vertex counts:", dict(sorted(counts.items())))
log.close()
