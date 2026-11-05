"""Stage improved guard topology on each high-detail body without modifying originals."""
import bpy,sys,json,traceback
from pathlib import Path
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).parent))
import audit_sparring_styles as review
ROOT=review.ROOT; OUT=ROOT/'Resources/Models/FinalRefinement/GuardBodyVariantsV2';OUT.mkdir(exist_ok=True)
template=ROOT/'Resources/Models/FinalRefinement/FootguardLocalROMSmooth/Candidate.blend'
names=('FootGuards','FootGuards_PaddedInstep');report=dict(production_installed=False,presets=[],errors=[])
def geometry(obj):
    ev=obj.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=ev.to_mesh();mesh.calc_loop_triangles()
    points=[obj.matrix_world@v.co for v in mesh.vertices];tris=[tuple(t.vertices) for t in mesh.loop_triangles];ev.to_mesh_clear();return points,tris
for kind in (('Medium',) if '--one' in sys.argv else ('Medium','Compact','Stocky','LeanTall','Tall','Male_Athletic','Male_Lean','Female_Athletic','Female_Strong')):
    try:
        source=ROOT/f'Resources/Models/CharacterSuite/{kind}/Gameplay_High.blend'
        bpy.ops.wm.open_mainfile(filepath=str(source));s=bpy.context.scene;r=bpy.data.objects['RIG_Body_'+kind]
        r.animation_data_create();r.animation_data.action=None
        for track in r.animation_data.nla_tracks:track.mute=True
        r.data.pose_position='REST';signature=[(b.name,b.parent.name if b.parent else '') for b in r.data.bones]
        scale=(r.matrix_world@r.data.bones['head'].head_local).z/1.578
        for prop in ('Wear_Helmet','Wear_Protector','Wear_Gloves','Wear_FootGuards','Wear_Jacket','Wear_Pants','Wear_Hair'):r[prop]=True
        r['BlenderCloth']=False
        old=bpy.data.objects['FootGuards']
        targets={name:bpy.data.objects.get(name) for name in names}
        with bpy.data.libraries.load(str(template),link=False) as (src,dst):dst.objects=list(names)
        templates=dst.objects
        for index,obj in enumerate(templates):
            obj.name='TEMPLATE_Guard_'+str(index);s.collection.objects.link(obj)
            donor=next(m.object for m in obj.modifiers if m.type=='ARMATURE')
            if donor.name not in s.objects:s.collection.objects.link(donor)
            donor.data.pose_position='REST'
        bpy.context.view_layer.update()
        rows=[]
        for style,src in enumerate(templates):
            src_rig=next(m.object for m in src.modifiers if m.type=='ARMATURE')
            obj=targets[names[style]]
            if obj is None:
                obj=old.copy();obj.data=old.data.copy();s.collection.objects.link(obj);obj.name=names[style]
            obj.data=src.data.copy();obj.vertex_groups.clear()
            for vg in src.vertex_groups:obj.vertex_groups.new(name=vg.name)
            mappings={}
            for vg in src.vertex_groups:
                if vg.name not in src_rig.data.bones:continue
                a=src_rig.data.bones[vg.name];b=r.data.bones[vg.name]
                ratio=b.length/a.length if a.length>1e-6 else 1
                mappings[vg.name]=obj.matrix_world.inverted()@r.matrix_world@b.matrix_local@Matrix.Scale(ratio,4)@a.matrix_local.inverted()@src_rig.matrix_world.inverted()@src.matrix_world
            for target,v in zip(obj.data.vertices,src.data.vertices):
                target.co=sum((mappings[src.vertex_groups[g.group].name]@v.co*g.weight for g in v.groups),Vector())
                for g in v.groups:obj.vertex_groups[g.group].add([v.index],g.weight,'REPLACE')
            for mod in list(obj.modifiers):obj.modifiers.remove(mod)
            mod=obj.modifiers.new('Guard deformation','ARMATURE');mod.object=r
            for prop in ('hide_render','hide_viewport'):
                obj.driver_remove(prop);driver=obj.driver_add(prop).driver
                for variable,path in (('wear','["Wear_FootGuards"]'),('style','["FootGuardsStyle"]')):
                    v=driver.variables.new();v.name=variable;v.targets[0].id=r;v.targets[0].data_path=path
                driver.expression=f'not (wear and style=={style})'
            obj.data.update()
            assert len(obj.data.vertices)==12288
            assert all(len(v.groups)<=4 and abs(sum(g.weight for g in v.groups)-1)<1e-5 for v in obj.data.vertices)
        for obj in templates:bpy.data.objects.remove(obj,do_unlink=True)
        if src_rig!=r:bpy.data.objects.remove(src_rig,do_unlink=True)
        probe=bpy.data.objects['Body'].copy();probe.data=probe.data.copy();s.collection.objects.link(probe);probe.hide_render=True
        for mod in list(probe.modifiers):
            if mod.type=='MASK':probe.modifiers.remove(mod)
        r['FootGuardsStyle']=0;review.build.refresh(r);r.data.pose_position='REST';bpy.context.view_layer.update()
        bp,bt=geometry(probe);tree=BVHTree.FromPolygons(bp,bt,all_triangles=True)
        for style,name in enumerate(names):
            r['FootGuardsStyle']=style;review.build.refresh(r);r.data.pose_position='REST';bpy.context.view_layer.update()
            gp,gt=geometry(bpy.data.objects[name]);ds=[]
            for p in gp:
                hit,n,_,_=tree.find_nearest(p);ds.append((p-hit).dot(n))
            own=BVHTree.FromPolygons(gp,gt,all_triangles=True)
            overlaps=sum(a<b and not set(gt[a])&set(gt[b]) for a,b in own.overlap(own))
            rows.append(dict(style=name,minimum_vertex_clearance_m=min(ds),inside_1mm=sum(d<-.001 for d in ds),self_overlap_pairs=overlaps))
        bpy.data.objects.remove(probe,do_unlink=True)
        assert signature==[(b.name,b.parent.name if b.parent else '') for b in r.data.bones]
        dest=OUT/kind;dest.mkdir(exist_ok=True);r['FootGuardsStyle']=0;review.build.refresh(r);r.data.pose_position='REST'
        s.render.engine='CYCLES';s.cycles.samples=12;s.cycles.use_denoising=True
        review.render(s,r,scale,dest,'Rest_Full',(3,-5,2),(0,0,1),2.6,600,760)
        review.render(s,r,scale,dest,'Rest_Guards',(1,-1,.35),(0,-.05,.12),.55,600,600)
        bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(dest/'Gameplay_High_Staged.blend'),compress=True)
        report['presets'].append(dict(preset=kind,rig_preserved=True,checks=rows,rest_passed=all(x['inside_1mm']==0 and x['self_overlap_pairs']==0 for x in rows)))
    except Exception:report['errors'].append(dict(preset=kind,error=traceback.format_exc()))
    (OUT/'validation.json').write_text(json.dumps(report,indent=2))
