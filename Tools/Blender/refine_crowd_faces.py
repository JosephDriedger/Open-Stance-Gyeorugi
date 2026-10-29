"""Stage crowd head detail from the next finer existing profile, retaining crowd rigs."""
import bpy,sys,json,hashlib,traceback
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).parent))
import audit_sparring_styles as review
import extend_garment_repairs as base
import repair_sparring_fit as fit
ROOT=base.ROOT;OUT=ROOT/'Resources/Models/CrowdFaceRefinement';OUT.mkdir(exist_ok=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(kind,level):
 source=ROOT/'Resources/Models/CharacterSuite'/kind/(level+'.blend')
 donor=source.with_name(('Gameplay_Far' if level=='Crowd_Near' else 'Crowd_Near')+'.blend')
 bpy.ops.wm.open_mainfile(filepath=str(donor));head=bpy.data.objects['Head']
 # Write mesh alone; do not import a second skeleton or its animations.
 temp=OUT/(kind+'_'+level+'_head.blend');meshname=head.data.name
 bpy.data.libraries.write(str(temp),{head.data},compress=True)
 bpy.ops.wm.open_mainfile(filepath=str(source));s=bpy.context.scene;r=bpy.data.objects['RIG_Body_'+kind]
 sig=base.signature(r);actions=base.actions();oldhead=bpy.data.objects['Head'];mats=list(oldhead.data.materials)
 oldtris=sum(len(p.vertices)-2 for p in oldhead.data.polygons)
 before=set(bpy.data.objects)
 with bpy.data.libraries.load(str(temp),link=False) as (a,z):z.meshes=[meshname]
 oldhead.data=z.meshes[0];indices=[p.material_index for p in oldhead.data.polygons];oldhead.data.materials.clear()
 for mat in mats:oldhead.data.materials.append(mat)
 for polygon,index in zip(oldhead.data.polygons,indices):polygon.material_index=index
 oldhead.vertex_groups.clear();oldhead.vertex_groups.new(name='head').add(list(range(len(oldhead.data.vertices))),1,'REPLACE')
 for o in list(bpy.data.objects):
  if o not in before:bpy.data.objects.remove(o,do_unlink=True)
 for action in list(bpy.data.actions):
  if action.name not in actions:bpy.data.actions.remove(action)
 states={o:o.data.pose_position for o in s.objects if o.type=='ARMATURE'}
 for o in states:o.data.pose_position='REST'
 bpy.context.view_layer.update();surface=fit.tree(oldhead,True)
 scale=(r.matrix_world@r.data.bones['head'].head_local).z/1.578;center=Vector((0,.002,1.65))*scale
 for o in s.objects:
  if o.type!='MESH' or not ('Scalp_Coverage' in o.name or o.name.startswith('Hair_Crew_Cut')):continue
  keys=o.data.shape_keys;inv=o.matrix_world.inverted()
  for block in (keys.key_blocks if keys else [o.data]):
   for v in (block.data if keys else block.vertices):
    p=o.matrix_world@v.co;axis=(p-center).normalized();hit=surface.ray_cast(center+axis*.35*scale,-axis,.35*scale)[0]
    if hit is not None:
     if 'Crew_Cut' in o.name:
      clearance=.0015*scale if 'Scalp_Coverage' in o.name else max(.001*scale,min(.003*scale,(p-hit).dot(axis)))
      v.co=inv@(hit+axis*clearance)
     elif (p-center).length<(hit-center).length+.004*scale:v.co=inv@(hit+axis*.004*scale)
  if keys:
   for v,k in zip(o.data.vertices,keys.key_blocks[0].data):v.co=k.co
 for o,state in states.items():o.data.pose_position=state
 bpy.context.view_layer.update();assert sig==base.signature(r) and actions==base.actions()
 s['CrowdFaceRefinement']='2026-10-22';d=OUT/kind;d.mkdir(exist_ok=True)
 bpy.context.preferences.filepaths.save_version=0;dest=d/source.name;bpy.ops.wm.save_as_mainfile(filepath=str(dest),compress=True)
 row={'passed':True,'source_sha256':sha(source),'file':dest.name,'sha256':sha(dest),'head_triangles_before':oldtris,'head_triangles_after':sum(len(p.vertices)-2 for p in oldhead.data.polygons),'rig_and_actions_preserved':True,'bones':len(r.data.bones)}
 (d/(level+'_validation.json')).write_text(json.dumps(row,indent=2))
 r.animation_data_create();r.animation_data.action=None
 for t in r.animation_data.nla_tracks:t.mute=True
 for prop in ['Wear_Helmet','Wear_Protector','Wear_Gloves','Wear_FootGuards','BlenderCloth']:r[prop]=False
 r['HairStyle']=3 if kind=='LeanTall' else 4 if kind=='Tall' else 0;review.build.refresh(r);review.audit.pose(r,'Neutral',scale)
 s.render.engine='CYCLES';s.cycles.samples=16;s.cycles.use_denoising=True
 for label,cam in [('Front',(.4,-1,1.9)),('Side',(1,-.1,1.8))]:review.render(s,r,scale,d,level+'_V3_'+label,cam,(0,0,1.65),.5,600,600)
 r.animation_data.action=bpy.data.actions['Crowd_Cheer'];s.frame_set(30)
 review.render(s,r,scale,d,level+'_V3_Cheer',(1.3,-4,1.8),(0,0,.96),2.35,480,540)
 with (OUT/'build.log').open('a') as f:f.write(kind+' '+level+' COMPLETE\n')
if __name__=='__main__':
 try:
  kinds=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else ['Medium']
  for kind in kinds:
   for level in ['Crowd_Near','Crowd_Far']:run(kind,level)
 except:(OUT/'error.log').write_text(traceback.format_exc());raise
