"""Step 1 of the mocap-target build: export the chain rig and its two tails (no modifiers, rest pose) from a study candidate.

    blender --background Resources/Models/FinalRefinement/BoneChainBelt/<Kind>/Candidate.blend --python Tools/Blender/export_chain_tails.py -- <Kind> <out fbx> <log>
"""
import sys,traceback
kind,out,logpath=sys.argv[sys.argv.index('--')+1:][:3]
sys.path.insert(0,r'D:/Open-Stance-Gyeorugi/Tools/Blender')
f=open(logpath,'w')
try:
    import bpy,belt_bone_chain as b
    b.rig_object()['BlenderCloth']=False
    n=b.strip_keys();r=b.export_fbx(out,names=('Belt_Tail_Left','Belt_Tail_Right'),modifiers=False)
    f.write(f'removed {n} belt curves, export {list(r)} -> {out}\nDONE\n')
except Exception:
    f.write('ERROR '+traceback.format_exc())
f.close()
