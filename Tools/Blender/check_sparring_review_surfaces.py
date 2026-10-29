"""Read-only flat-color diagnostic for review findings; never saves models."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import bpy
import audit_sparring_styles as review

def flat(name, color):
    m=bpy.data.materials.new(name);m.use_nodes=True
    n=m.node_tree.nodes;n.clear()
    e=n.new('ShaderNodeEmission');e.inputs['Color'].default_value=(*color,1)
    out=n.new('ShaderNodeOutputMaterial');m.node_tree.links.new(e.outputs[0],out.inputs['Surface'])
    return m

out=review.OUT/'diagnostics';out.mkdir(exist_ok=True)
for kind,level in [('Female_Athletic','Gameplay_High'),('Tall','Preview')]:
    s,r,z,src=review.load(kind,level);review.select(r,0,1,0,0,1)
    cloth=flat('Review_Cloth_Green',(.1,.8,.1))
    gear=flat('Review_Protector_Blue',(.05,.15,.8))
    skin=flat('Review_Skin_Orange',(1,.3,.02))
    for o in s.objects:
        if o.type!='MESH':continue
        mat=None
        if o.name.startswith(tuple(p+'__' for p in review.build.PROTECTORS)):mat=gear
        elif o.name.startswith(('Jacket','Pants')):mat=cloth
        elif o.name.startswith('Body'):mat=skin
        if mat:
            for i in range(len(o.data.materials)):o.data.materials[i]=mat
    review.render(s,r,z,out,kind+'_Flat',(1.7,-4,1.65),(0,0,1.30),1.15,720,720)
    if kind=='Tall':review.render(s,r,z,out,kind+'_Shoulder',(.5,-1,1.84),(0,0,1.55),.65,720,720)
(out/'complete.txt').write_text('Read-only diagnostic complete')
