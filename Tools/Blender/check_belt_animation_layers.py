import bpy,json
bpy.ops.wm.open_mainfile(filepath='D:/Open-Stance-Gyeorugi/Resources/Models/Animation/Physics/SecondaryCloth_Kick_Study.blend')
r=bpy.data.objects['RIG_Body_Medium'];r['BlenderCloth']=False;r.update_tag()
for frame in [1,26,35,72]:
 bpy.context.scene.frame_set(frame)
 for name in ['Belt_Tail_Left','Belt_Tail_Right','SIM_Jacket_Front_Left_Collider']:
  o=bpy.data.objects.get(name)
  if not o or not o.data.shape_keys:continue
  keys=o.data.shape_keys;ad=keys.animation_data
  print(frame,name,'ACTIVE_SHAPES',[(k.name,round(k.value,4)) for k in keys.key_blocks if abs(k.value)>.001],'NLA',len(ad.nla_tracks) if ad else 0)
