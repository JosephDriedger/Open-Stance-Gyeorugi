"""Bake composed skin and eye colors to ordinary portable albedo maps."""
import bpy,sys,json,traceback,math
import numpy as np
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'Resources/Models/UpdatedBuild';OUT.mkdir(exist_ok=True)
TEX=OUT/'Textures';TEX.mkdir(exist_ok=True)
try:
 bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Resources/Models/CharacterVariations/Male_Athletic/Character.blend'))
 scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=1;scene.cycles.device='CPU';scene.render.bake.margin=8
 report=[]
 for name in ['Body','Head']:
  o=bpy.data.objects[name];bpy.ops.object.select_all(action='DESELECT');o.hide_set(False);o.hide_viewport=False;o.select_set(True);bpy.context.view_layer.objects.active=o
  for m in o.modifiers:m.show_render=False;m.show_viewport=False
  # MetaHuman body UVs occupy tile 1002; an ordinary PNG bake targets 1001.
  # Shift the entire tile, preserving its layout and repeated source sampling.
  uv=o.data.uv_layers.active
  tile=(math.floor(min(d.uv.x for d in uv.data)),math.floor(min(d.uv.y for d in uv.data)))
  for d in uv.data:d.uv.x-=tile[0];d.uv.y-=tile[1]
  records=[]
  for mat in o.data.materials:
   if not mat or not mat.use_nodes:continue
   nodes=mat.node_tree.nodes;links=mat.node_tree.links;bs=next(n for n in nodes if n.type=='BSDF_PRINCIPLED');output=next(n for n in nodes if n.type=='OUTPUT_MATERIAL');old=output.inputs['Surface'].links[0].from_socket
   emit=nodes.new('ShaderNodeEmission');color=bs.inputs['Base Color']
   if color.is_linked:links.new(color.links[0].from_socket,emit.inputs['Color'])
   else:emit.inputs['Color'].default_value=color.default_value
   links.new(emit.outputs[0],output.inputs['Surface'])
   size=2048 if 'Skin' in mat.name else 1024
   image=bpy.data.images.new('Export_'+mat.name,width=size,height=size,alpha=False);image.colorspace_settings.name='sRGB'
   target=nodes.new('ShaderNodeTexImage');target.image=image;nodes.active=target
   records.append((mat,output,old,emit,target,image))
  bpy.ops.object.bake(type='EMIT',use_clear=True)
  for mat,output,old,emit,target,image in records:
   image.filepath_raw=str(TEX/(mat.name+'.png'));image.file_format='PNG';image.save()
   px=np.empty(len(image.pixels),dtype=np.float32);image.pixels.foreach_get(px)
   if 'Skin' in mat.name:assert float(px.reshape(-1,4)[:,:3].max())>.05,'Empty skin bake: '+mat.name
   mat.node_tree.links.new(old,output.inputs['Surface']);mat.node_tree.nodes.remove(emit);mat.node_tree.nodes.remove(target)
   report.append({'material':mat.name,'file':image.filepath_raw,'size':list(image.size),'uv_layer':o.data.uv_layers.active.name})
 (OUT/'material_bake.json').write_text(json.dumps(report,indent=2));(OUT/'materials.log').write_text('COMPLETE')
except:(OUT/'materials.log').write_text(traceback.format_exc());raise
