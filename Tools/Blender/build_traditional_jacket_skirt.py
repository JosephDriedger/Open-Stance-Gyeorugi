"""Replace the three short jacket skirt panels with one wrapped traditional skirt to mid-thigh, draped over the trousers.

A traditional wrap-front dobok jacket runs on below the belt as one piece to about mid-thigh, with short side slits; the
outer front flap ends at the overlap edge and the inner flap carries on underneath it. This builds that as one strip that
starts at the jacket's overlap edge, wraps once round the hips over the (new, wide) trousers and continues under itself
for the inner flap, cuts the side slits, drapes it with Blender cloth on the bind-pose body (band under the belt held,
gravity, collisions with the body and trousers, self collision for the two front layers), then skins it: pelvis at the
top, blending toward the trousers' own weights at the hem (the Unreal cloth adds the swing).

Run with build_traditional_trousers.py's output open:
    blender.exe -b <Candidate.blend> -P build_traditional_jacket_skirt.py -- <out folder>

The panel objects Jacket_Front_Left/Right and the SIM_Jacket_* proxies are removed; Jacket_Back keeps its modifiers and
drivers, is renamed Jacket_Skirt and gets the new mesh. Saves <out folder>/Candidate.blend and skirt_report.json.
"""
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

OUT = Path(sys.argv[sys.argv.index('--') + 1]) if '--' in sys.argv else None
scene = bpy.context.scene
rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and o.name.startswith('RIG_Body_'))
body = bpy.data.objects['Body']
pants = bpy.data.objects['Pants']
jacket = bpy.data.objects['Jacket']
belt = bpy.data.objects['Belt_Waistband']

LENGTH_BELOW_BELT = .13   # m: hem just below the hip (sparring photos)
TOP_EASE, HEM_EASE = .008, .012  # m outside the trousers at the top and at the hem: lies against them
HUG_BLEND = .045                 # m below the belt over which the skirt goes from the jacket hem's width onto the trousers
OVERLAP = math.radians(25)       # inner flap reaches this far past the overlap edge, under the outer flap
INNER_DROP = .012                # m: inner flap sits this far inside the outer one (closer and the drape pokes it through)
SNAPSHOT, SUNK_LIMIT = 6, .01          # drape snapshot interval (frames), share of skirt points allowed to touch the trousers
TORSO_REACH = .30                # m from the centre: anything further out at skirt height is an arm
MIN_GAP = .010                   # m: every skirt point starts at least this far outside the trousers (drape safety)
UNDER_BELT = .004                # m: the skirt top stays this far inside the belt band
SMOOTH_PASSES = 8                # Taubin passes over the draped skirt (evens the ragged hem)
SLIT = .10                       # m: side slits up from the hem
COLUMNS = 150
STEP = .012
DRAPE_FRAMES = int(__import__("os").environ.get("OPEN_STANCE_SKIRT_DRAPE", 60))  # 0 skips the drape (debug)

belt_z = [(belt.matrix_world @ v.co).z for v in belt.data.vertices]
top_z = min(belt_z) + .013
hem_z = min(belt_z) - LENGTH_BELOW_BELT
centre = Vector((0, sum((pants.matrix_world @ v.co).y for v in pants.data.vertices) / len(pants.data.vertices)))

# The overlap edge: the jacket's open boundary loop that runs diagonally from the neck down to the hem (the hem itself
# is a flat loop); the skirt's outer flap starts where it meets the hem.
bm = bmesh.new()
bm.from_mesh(jacket.data)
links = defaultdict(list)
for e in bm.edges:
    if e.is_boundary:
        a, b = (v.index for v in e.verts)
        links[a].append(b)
        links[b].append(a)
bm.verts.ensure_lookup_table()
loops, seen = [], set()
for start in links:
    if start in seen:
        continue
    stack, members = [start], []
    while stack:
        i = stack.pop()
        if i not in seen:
            seen.add(i)
            members.append(jacket.matrix_world @ bm.verts[i].co)
            stack += links[i]
    loops.append(members)
bm.free()
diagonal = max(loops, key=lambda pts: max(p.z for p in pts) - min(p.z for p in pts) if min(p.z for p in pts) < min(
    q.z for l in loops for q in l) + .02 else 0)
if 'OverlapEdgeVerts' in jacket:  # recorded by the jacket layer before it moved anything
    diagonal = [jacket.matrix_world @ jacket.data.vertices[i].co for i in jacket['OverlapEdgeVerts']]
edge = min(diagonal, key=lambda p: p.z)
edge_angle = math.atan2(edge.y - centre.y, edge.x - centre.x)
direction = -1 if edge.x > 0 else 1                 # wrap from the edge across the front centre and round the back

# What the skirt hangs over, per height and angle: the trousers, and the jacket's own hem (the skirt carries the jacket
# body on down, so it starts at least as wide as the hem above it).
pants_points = [pants.matrix_world @ v.co for v in pants.data.vertices]
trouser_points = list(pants_points)
jacket_hem = min(p.z for p in (jacket.matrix_world @ v.co for v in jacket.data.vertices)
                 if math.hypot(p.x, p.y - centre.y) < TORSO_REACH)
# torso only: on short-armed bodies the bind-pose sleeves hang down to the hem's height (they threw a skirt point 47 cm out)
pants_points += [p for p in (jacket.matrix_world @ v.co for v in jacket.data.vertices)
                 if p.z < jacket_hem + .03 and math.hypot(p.x, p.y - centre.y) < TORSO_REACH]


BINS = 180


def outline(z, band=.015, points=None):
    """Trouser reach from the centre in BINS angle bins at height z (gaps filled from neighbours, smoothed)."""
    reach = [0.0] * BINS
    for p in (pants_points if points is None else points):
        if abs(p.z - z) < band:
            k = int((math.atan2(p.y - centre.y, p.x - centre.x) + math.pi) / (2 * math.pi) * BINS) % BINS
            reach[k] = max(reach[k], math.hypot(p.x - centre.x, p.y - centre.y))
    for _ in range(BINS):
        if all(reach):
            break
        reach = [r or max(reach[i - 1], reach[(i + 1) % BINS]) for i, r in enumerate(reach)]
    for _ in range(4):
        reach = [(reach[i - 1] + 2 * reach[i] + reach[(i + 1) % BINS]) / 4 for i in range(BINS)]
    return reach


span = 2 * math.pi + OVERLAP
angles = [edge_angle + direction * span * c / (COLUMNS - 1) for c in range(COLUMNS)]
inner_from = int(COLUMNS * 2 * math.pi / span)   # columns past this are the inner flap, under the outer one
rows = []
z = top_z
while z > hem_z + STEP * .5:
    rows.append(z)
    z -= STEP
rows.append(hem_z)
samples = {z: outline(z) for z in rows[::3] + [rows[-1]]}
# the trousers alone (no jacket hem): what the skirt lies against below the belt
trouser_samples = {z: outline(z, points=trouser_points) for z in rows[::3] + [rows[-1]]}
sample_z = sorted(samples)
# Belt band reach per angle: the skirt top tucks just inside it.
belt_reach = [0.0] * BINS
for v in belt.data.vertices:
    p = belt.matrix_world @ v.co
    k = int((math.atan2(p.y - centre.y, p.x - centre.x) + math.pi) / (2 * math.pi) * BINS) % BINS
    belt_reach[k] = max(belt_reach[k], math.hypot(p.x - centre.x, p.y - centre.y))
for _ in range(BINS):
    if all(belt_reach):
        break
    belt_reach = [r or max(belt_reach[i - 1], belt_reach[(i + 1) % BINS]) for i, r in enumerate(belt_reach)]


def reach_at(z, angle, table=None):
    table = samples if table is None else table
    lo = max([q for q in sample_z if q <= z] or [sample_z[0]])
    hi = min([q for q in sample_z if q >= z] or [sample_z[-1]])
    t = 0 if hi == lo else (z - lo) / (hi - lo)
    k = int(((angle + math.pi) % (2 * math.pi)) / (2 * math.pi) * BINS) % BINS
    return table[lo][k] * (1 - t) + table[hi][k] * t


bm = bmesh.new()
grid = []
for j, z in enumerate(rows):
    ease = TOP_EASE + (HEM_EASE - TOP_EASE) * ((top_z - z) / (top_z - hem_z)) ** 1.5
    row = []
    for c, a in enumerate(angles):
        # One piece with the jacket: it leaves the belt at the jacket hem's width and within HUG_BLEND lies against the
        # trousers (a straight drop from the top read as a separate boxy skirt). The belt is fitted over this next.
        hug = reach_at(z, a, trouser_samples) + ease
        t = min(1.0, max(0.0, (top_z - z) / HUG_BLEND))
        t = t * t * (3 - 2 * t)
        r = (reach_at(top_z, a) + TOP_EASE) * (1 - t) + hug * t
        r -= INNER_DROP if c > inner_from else 0
        row.append(bm.verts.new((centre.x + r * math.cos(a), centre.y + r * math.sin(a), z)))
    grid.append(row)
# Side slits: columns nearest straight left and right (angles 0 and pi) stay unjoined below the slit top.
slit_columns = set()
for target in (0.0, math.pi):
    slit_columns.add(min(range(COLUMNS - 1), key=lambda c: abs((angles[c] - target + math.pi) % (2 * math.pi) - math.pi)))
for j in range(len(rows) - 1):
    for c in range(COLUMNS - 1):
        if c in slit_columns and rows[j + 1] < hem_z + SLIT:
            continue
        bm.faces.new((grid[j][c], grid[j][c + 1], grid[j + 1][c + 1], grid[j + 1][c]))
# The outline above is smoothed, which rounds off a sharply bulging seat, so on some bodies the skirt started inside the
# trousers and the drape threw it through them (moving it 12-14 cm). Guarantee a gap to the unsmoothed trouser surface:
# per 1-degree, 1 cm cell the trousers' widest reach, dilated to the neighbouring cells, plus MIN_GAP.
floor = defaultdict(float)
for p in pants_points:
    cell = (int((math.atan2(p.y - centre.y, p.x - centre.x) + math.pi) / (2 * math.pi) * 360) % 360, int(p.z * 100))
    floor[cell] = max(floor[cell], math.hypot(p.x - centre.x, p.y - centre.y))
pushed = 0
for row in grid:
    for c, v in enumerate(row):
        # the outer flap stays INNER_DROP outside the inner one, or the two start intersecting and self collision throws them
        gap = MIN_GAP + (0.0 if c > inner_from else INNER_DROP)
        a = math.atan2(v.co.y - centre.y, v.co.x - centre.x)
        k, zc = int((a + math.pi) / (2 * math.pi) * 360) % 360, int(v.co.z * 100)
        need = max((floor.get(((k + dk) % 360, zc + dz), 0.0) for dk in range(-3, 4) for dz in (-1, 0, 1)), default=0.0)
        r = math.hypot(v.co.x - centre.x, v.co.y - centre.y)
        if need and r < need + gap:
            scale = (need + gap) / max(r, 1e-6)
            v.co.x, v.co.y = centre.x + (v.co.x - centre.x) * scale, centre.y + (v.co.y - centre.y) * scale
            pushed += 1
bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
sys.path.insert(0, str(Path(__file__).resolve().parent))
from garment_normals import face_outward
normals_flipped = face_outward(bm, body)
for f in bm.faces:
    f.smooth = True
skirt_mesh = bpy.data.meshes.new('Jacket_Skirt')
bm.to_mesh(skirt_mesh)
bm.free()
drape = bpy.data.objects.new('Jacket_Skirt_Drape', skirt_mesh)
scene.collection.objects.link(drape)
report = {'pushed_clear_of_trousers': pushed, 'top_z': round(top_z, 3), 'hem_z': round(hem_z, 3), 'edge': [round(c, 3) for c in edge],
          'edge_angle_deg': round(math.degrees(edge_angle), 1), 'vertices': len(skirt_mesh.vertices),
          'slit_columns': sorted(slit_columns), 'normals_flipped': normals_flipped}

# --- drape on the bind-pose body over the trousers ---------------------------------------------------------------------
pose_position = rig.data.pose_position
rig.data.pose_position = 'REST'
contacts = []
for source, thickness in ((body, .006), (pants, .004)):
    proxy = source.copy()
    proxy.data = source.data.copy()
    proxy.name = source.name + '_SkirtContact'
    scene.collection.objects.link(proxy)
    for modifier in list(proxy.modifiers):
        if modifier.type != 'ARMATURE':
            proxy.modifiers.remove(modifier)
    if proxy.data.shape_keys:
        proxy.shape_key_clear()
    proxy.modifiers.new('Contact', 'COLLISION')
    proxy.collision.thickness_outer = thickness
    proxy.collision.cloth_friction = 5
    contacts.append(proxy)
muted = []
for obj in scene.objects:
    if obj in contacts:
        continue
    for modifier in obj.modifiers:
        if modifier.type == 'COLLISION' and modifier.show_viewport:
            modifier.show_viewport = False
            muted.append(modifier)
pin = drape.vertex_groups.new(name='Drape_Band')
for v in skirt_mesh.vertices:
    band = max(0.0, min(1.0, (v.co.z - (top_z - .03)) / .02))
    # The free front edges (outer flap edge, inner flap end) curl in a free drape; a soft hold keeps them hanging straight.
    edge_hold = .6 if v.index % COLUMNS < 3 or v.index % COLUMNS >= COLUMNS - 3 else 0.0
    pin.add([v.index], max(band, edge_hold), 'REPLACE')
cloth = drape.modifiers.new('Drape', 'CLOTH')
s = cloth.settings
s.quality = 14
s.mass = .25 / len(skirt_mesh.vertices)
s.tension_stiffness = s.compression_stiffness = 400
s.shear_stiffness = 60
s.bending_stiffness = 10
s.air_damping = 2
s.vertex_group_mass = pin.name
cloth.collision_settings.use_collision = True
cloth.collision_settings.collection = None
cloth.collision_settings.distance_min = .004
cloth.collision_settings.use_self_collision = True
cloth.collision_settings.self_distance_min = .003
cloth.point_cache.frame_start = 1
cloth.point_cache.frame_end = DRAPE_FRAMES
frame = scene.frame_current


def trouser_floor(p):
    a = math.atan2(p.y - centre.y, p.x - centre.x)
    k, zc = int((a + math.pi) / (2 * math.pi) * 360) % 360, int(p.z * 100)
    return max((floor.get(((k + dk) % 360, zc + dz), 0.0) for dk in range(-3, 4) for dz in (-1, 0, 1)), default=0.0)


# Sunk is measured against the real trouser surface (rest pose, as the drape runs): a point counts when it is
# behind it (touching is fine: anything closer than MIN_GAP is pushed back out after the drape). The dilated per-cell floor used to place the skirt overstates the surface beside a bulging
# seat or thigh, and on Compact and Male_Lean it called a skirt resting correctly on the trousers sunk after 6 frames.
_pants_world = [pants.matrix_world @ v.co for v in pants.data.vertices]
sunk_tree = BVHTree.FromPolygons(_pants_world, [tuple(p.vertices) for p in pants.data.polygons])


def snapshot():
    depsgraph = bpy.context.evaluated_depsgraph_get()
    mesh = bpy.data.meshes.new_from_object(drape.evaluated_get(depsgraph), depsgraph=depsgraph)
    points = [v.co.copy() for v in mesh.vertices]
    bpy.data.meshes.remove(mesh)
    sunk = 0
    for p in points:
        loc, normal, _, dist = sunk_tree.find_nearest(p, .05)
        if loc is not None and (p - loc).dot(normal) < 0:
            sunk += 1
    return points, sunk


# On some bodies the skirt slowly sinks into the trousers as the drape runs (clean after 3 frames, half through after 30)
# while on others it settles in a few cm and stays. Keep a snapshot every SNAPSHOT frames and use the last one that
# still clears the trousers.
chosen, chosen_frame = [v.co.copy() for v in skirt_mesh.vertices], 0
for f in range(1, DRAPE_FRAMES + 1):
    scene.frame_set(f)
    if f % SNAPSHOT == 0 or f == DRAPE_FRAMES:
        points, sunk = snapshot()
        report.setdefault('drape_sunk', []).append((f, sunk))
        if sunk > SUNK_LIMIT * len(points):
            break
        chosen, chosen_frame = points, f
moved = max((p - v.co).length for p, v in zip(chosen, skirt_mesh.vertices))
# The drape leaves a ragged, rippled hem: Taubin smoothing (shrink then inflate, so no volume is lost) evens it; the
# band under the belt stays put. The push-out below then restores MIN_GAP over the trousers.
skirt_links = defaultdict(list)
for e in skirt_mesh.edges:
    skirt_links[e.vertices[0]].append(e.vertices[1])
    skirt_links[e.vertices[1]].append(e.vertices[0])
held = {v.index for v in skirt_mesh.vertices if v.co.z > top_z - .03}
for _ in range(SMOOTH_PASSES):
    for factor in (.5, -.53):
        chosen = [p if i in held or not skirt_links[i] else
                  p + (sum((chosen[j] for j in skirt_links[i]), Vector()) / len(skirt_links[i]) - p) * factor
                  for i, p in enumerate(chosen)]
for v, p in zip(skirt_mesh.vertices, chosen):
    v.co = p
# Anything closer than MIN_GAP to the trousers is moved out along the real trouser surface's normal (pushing out to the
# dilated per-cell floor re-roughened a smoothed hem: it moved nearly every point onto that blocky outline).
pushed_out = 0
for v in skirt_mesh.vertices:
    loc, normal, _, dist = sunk_tree.find_nearest(v.co, .05)
    if loc is not None and (v.co - loc).dot(normal) < MIN_GAP:
        v.co = loc + normal * MIN_GAP
        pushed_out += 1
report['pushed_out_after_drape'] = pushed_out
report['drape_frames_used'] = chosen_frame
drape.modifiers.remove(cloth)
for modifier in muted:
    modifier.show_viewport = True
for proxy in contacts:
    data = proxy.data
    bpy.data.objects.remove(proxy, do_unlink=True)
    bpy.data.meshes.remove(data)
rig.data.pose_position = pose_position
scene.frame_set(frame)
report['drape_max_move_cm'] = round(moved * 100, 1)

# --- weights: pelvis at the band, blending toward the trousers' weights at the hem -------------------------------------
bone_names = set(rig.data.bones.keys())
pants.data.calc_loop_triangles()
p_tris = [tuple(t.vertices) for t in pants.data.loop_triangles]
p_tree = BVHTree.FromPolygons(pants_points, p_tris, all_triangles=True)
p_groups = {g.index: g.name for g in pants.vertex_groups}
p_weights = [{p_groups[g.group]: g.weight for g in v.groups if p_groups[g.group] in bone_names} for v in pants.data.vertices]
weights = []
for v in skirt_mesh.vertices:
    _, _, face, _ = p_tree.find_nearest(v.co)
    mix = defaultdict(float)
    for i in p_tris[face]:
        for name, w in p_weights[i].items():
            mix[name] += w / 3
    # Same weights as the trousers right under it: both garments then deform alike and the drape gap holds (a skirt that
    # leans on the pelvis lets the thighs push through it in a bent-knee stance). The Unreal cloth adds the swing.
    follow = 1.0
    blend = defaultdict(float)
    blend['pelvis'] += 1 - follow
    total = sum(mix.values()) or 1
    for name, w in mix.items():
        blend[name] += follow * w / total
    top4 = sorted(blend.items(), key=lambda kv: -kv[1])[:4]
    norm = sum(w for _, w in top4)
    weights.append({n: w / norm for n, w in top4})

# --- weave UVs round the hips, 20 per metre ----------------------------------------------------------------------------
weave = skirt_mesh.uv_layers.new(name='UVWeave')
plain = skirt_mesh.uv_layers.new(name='UVMap')
column_of = {}
for poly in skirt_mesh.polygons:
    for li in poly.loop_indices:
        vi = skirt_mesh.loops[li].vertex_index
        c = vi % COLUMNS
        u = c / (COLUMNS - 1) * span * .2
        z = skirt_mesh.vertices[vi].co.z
        weave.data[li].uv = (u / .05, z / .05)
        plain.data[li].uv = (u, z)
weave.active_render = True
skirt_mesh.uv_layers.active = weave

# --- swap into the jacket's back panel object; drop the front panels and their simulation proxies ----------------------
target = bpy.data.objects['Jacket_Back']
old = target.data
for group in list(target.vertex_groups):
    target.vertex_groups.remove(group)
target.data = skirt_mesh
for material in old.materials:
    skirt_mesh.materials.append(material)
target.name = 'Jacket_Skirt'
target['SkirtColumns'] = COLUMNS  # mesh keeps build order: column 0 is the outer flap's edge (build_traditional_collar.py)
groups = {}
for i, mix in enumerate(weights):
    for name, w in mix.items():
        if w > 1e-4:
            groups.setdefault(name, target.vertex_groups.new(name=name)).add([i], w, 'REPLACE')
live_pin = target.vertex_groups.new(name='LiveCloth_Pin')
for v in skirt_mesh.vertices:
    live_pin.add([v.index], max(0.0, min(1.0, (v.co.z - (top_z - .05)) / .04)), 'REPLACE')
bpy.data.objects.remove(drape, do_unlink=True)
removed = []
for name in ('Jacket_Front_Left', 'Jacket_Front_Right', 'SIM_Jacket_Back_Collider', 'SIM_Jacket_Front_Left_Collider',
             'SIM_Jacket_Front_Right_Collider'):
    obj = bpy.data.objects.get(name)
    if obj:
        bpy.data.objects.remove(obj, do_unlink=True)
        removed.append(name)
if old.users == 0:
    bpy.data.meshes.remove(old)
report.update({'removed': removed, 'groups': len(groups)})
print('SKIRT DONE', json.dumps(report), flush=True)
if OUT:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'skirt_report.json').write_text(json.dumps(report, indent=1))
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'Candidate.blend'), compress=True)
result = report
