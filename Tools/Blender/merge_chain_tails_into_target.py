"""Step 2 of the mocap-target build: put the belt chain into a runtime/mocap character FBX.

The Gameplay_High_Sparring.fbx files carry the study belt: two static tails weighted to the pelvis. This imports that FBX
and the chain export from export_chain_tails.py, adds belt_l_01..08 / belt_r_01..08 to the character's own skeleton,
replaces the static tails with the chain-skinned ones (same names, parent, transform and material), and writes a new FBX
with the original export settings (embedded textures, no modifiers applied, -Z forward, Y up). The source FBX is never
modified; work on a copy so Blender's `.fbm` texture folder does not appear in the library.

    blender --background --factory-startup --python Tools/Blender/merge_chain_tails_into_target.py -- <source fbx> <tails fbx> <out fbx> <log>
"""
import sys,traceback,json
src,tails_fbx,out,logpath=sys.argv[sys.argv.index('--')+1:][:4]
f=open(logpath,'w')
def log(*a):
    f.write(' '.join(str(x) for x in a)+'\n');f.flush()
try:
    import bpy
    def load(path):
        before=set(bpy.data.objects);bpy.ops.import_scene.fbx(filepath=path);bpy.context.view_layer.update()
        return [o for o in bpy.data.objects if o not in before]
    char=load(src);rig=next(o for o in char if o.type=='ARMATURE');log('character rig',rig.name,len(rig.data.bones),'bones')
    extra=load(tails_fbx);donor=next(o for o in extra if o.type=='ARMATURE');new_tails=[o for o in extra if o.type=='MESH']
    log('donor rig',donor.name,len(donor.data.bones),'bones; tails',[o.name for o in new_tails])
    chain=[b for b in donor.data.bones if b.name.startswith('belt_')];assert len(chain)==16,len(chain)
    # same skeleton, same import: the two rigs must coincide for bone positions to transfer directly
    for name in ('pelvis','head','hand_l'):
        a=rig.matrix_world@rig.data.bones[name].head_local;d=donor.matrix_world@donor.data.bones[name].head_local
        assert (a-d).length<1e-4,(name,a,d)
    log('rigs coincide')
    for o in bpy.data.objects:o.select_set(False)
    rig.select_set(True);bpy.context.view_layer.objects.active=rig  # the imports moved the active object
    bpy.ops.object.mode_set(mode='EDIT')
    eb=rig.data.edit_bones;Wi=rig.matrix_world.inverted();Wd=donor.matrix_world
    for b in sorted(chain,key=lambda b:len(b.parent_recursive)):
        e=eb.new(b.name);e.head=Wi@(Wd@b.head_local);e.tail=Wi@(Wd@b.tail_local);e.roll=0
        e.parent=eb[b.parent.name];e.use_connect=b.use_connect
        # same roll as the donor: align the bone's Z the way the donor's does
        e.align_roll(Wi.to_3x3()@(Wd.to_3x3()@(b.matrix_local.to_3x3()@__import__('mathutils').Vector((0,0,1)))))
    bpy.ops.object.mode_set(mode='OBJECT')
    log('bones now',len(rig.data.bones))
    # swap the tails
    report={}
    olds={side:next(o for o in char if o.type=='MESH' and o.name.startswith(f'Belt_Tail_{side}')) for side in ('Left','Right')}
    for new in new_tails:
        side='Left' if 'Left' in new.name else 'Right'
        old=olds[side]
        keep_name=old.name;mats=list(old.data.materials);collections=list(old.users_collection)
        # the chain tails must sit where the tails they replace were (same study geometry): flag any variant where they do not
        wo=[old.matrix_world@v.co for v in old.data.vertices]
        lo=[min(p[i] for p in wo) for i in range(3)]+[max(p[i] for p in wo) for i in range(3)]
        new.parent=rig;new.matrix_parent_inverse=old.matrix_parent_inverse.copy();new.matrix_basis=old.matrix_basis.copy()
        for m in new.modifiers:
            if m.type=='ARMATURE':m.object=rig
        new.data.materials.clear()
        for m in mats:new.data.materials.append(m)
        for c in new.users_collection:c.objects.unlink(new)
        for c in collections:c.objects.link(new)
        wn=[new.matrix_world@v.co for v in new.data.vertices];ln=[min(p[i] for p in wn) for i in range(3)]+[max(p[i] for p in wn) for i in range(3)]
        dev=max(abs(x-y) for x,y in zip(lo,ln));log('tail',side,'bbox deviation from the static tail it replaces (m):',round(dev,4))
        assert dev<0.02,('chain tail does not match the tail it replaces',side,dev)
        bpy.data.objects.remove(old,do_unlink=True);new.name=keep_name
        report[keep_name]={'bbox_dev_m':round(dev,4),'verts':len(new.data.vertices),'groups':len(new.vertex_groups),'uv':[l.name for l in new.data.uv_layers],'mats':[m.name for m in new.data.materials]}
    log('tails swapped',json.dumps(report))
    for o in extra:
        if o.type=='ARMATURE' or o not in new_tails:bpy.data.objects.remove(o,do_unlink=True)
    bpy.ops.object.select_all(action='DESELECT');rig.select_set(True)
    for o in bpy.data.objects:
        if o.type=='MESH' and o.parent==rig:o.select_set(True)
    bpy.context.view_layer.objects.active=rig
    log('exporting',sum(1 for o in bpy.data.objects if o.select_get()),'objects')
    bpy.ops.export_scene.fbx(filepath=out,use_selection=True,object_types={'ARMATURE','MESH'},use_mesh_modifiers=False,add_leaf_bones=False,
        bake_anim=False,path_mode='COPY',embed_textures=True,axis_forward='-Z',axis_up='Y',apply_scale_options='FBX_SCALE_NONE')
    log('DONE',out)
except Exception:
    log('ERROR',traceback.format_exc())
f.close()
