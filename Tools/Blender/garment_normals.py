"""Face a garment's normals away from the body.

bmesh.ops.recalc_face_normals makes an open mesh's faces consistent but guesses which side is out, and on open garments
(trousers, a wrap skirt, a collar band) it guessed inward on some bodies (Compact, Male_Lean): the drape's collision then
pushed the skirt into the trousers and Unreal culled the outside. After recalculating, call face_outward(bm, body).
"""
from mathutils.bvhtree import BVHTree


def face_outward(bm, body):
    """Flip every face of bm if most face away from the bind-pose body (bm in world space). Returns True if flipped."""
    world = [body.matrix_world @ v.co for v in body.data.vertices]
    tree = BVHTree.FromPolygons(world, [tuple(p.vertices) for p in body.data.polygons])
    out = inward = 0
    for f in bm.faces:
        c = f.calc_center_median()
        loc = tree.find_nearest(c)[0]
        if loc is None:
            continue
        if f.normal.dot(c - loc) >= 0:
            out += 1
        else:
            inward += 1
    if inward > out:
        for f in bm.faces:
            f.normal_flip()
        bm.normal_update()
        return True
    return False
