import bpy,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import repair_hair_surface as hair
import setup_blender_cloth as cloth
OUT=hair.OUT
def repair(scene):
 hair_rows=hair.repair(scene);cloth_rows=cloth.setup(scene)
 scene['HairClothRevision']='2026-10-16'
 text=bpy.data.texts.get('LIVE_CLOTH_README') or bpy.data.texts.new('LIVE_CLOTH_README')
 text.write('BlenderCloth on the body rig enables live dynamics for sleeves, trousers, lower jacket panels and belt tails. Simulation is off by default for reliable posing and FBX export. Start at frame 1 and play sequentially. Clear/bake caches after animation or wardrobe changes. Existing baked sample clips must use the dedicated cloth demo or have their ClothBake shape-key animation cleared before enabling live simulation, to avoid double motion. FBX carries the skeleton and baked animation, not a live Blender solver. Use Unreal Chaos Cloth for runtime reactions to arbitrary movement.\n')
 return {'hair':hair_rows,'cloth':cloth_rows}
