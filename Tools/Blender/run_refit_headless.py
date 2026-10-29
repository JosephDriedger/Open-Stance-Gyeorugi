"""Headless driver: refit one body type's belt chain to its real gear and export <Kind>_BeltFollowerFit.fbx.

    blender --background Resources/Models/FinalRefinement/BoneChainBelt/<Kind>/Candidate.blend --python Tools/Blender/run_refit_headless.py -- <Kind> <log file>

Blender's stdout is empty under the Store install, so progress goes to the log file given as the last argument.
"""
import sys,time,json,traceback
kind,logpath=sys.argv[sys.argv.index('--')+1:][:2]
sys.path.insert(0,r'D:/Open-Stance-Gyeorugi/Tools/Blender')
f=open(logpath,'w')
def log(*a):
    f.write(' '.join(str(x) for x in a)+'\n');f.flush()
try:
    import bpy,belt_bone_chain as b,refit_belt_to_gear as r
    b.rig_object()['BlenderCloth']=False
    t=time.time();res=r.refit(kind,log);log('refit',round(time.time()-t,1),json.dumps(res))
    out=r'D:/Open-Stance-Gyeorugi/Resources/Models/FinalRefinement/BoneChainBelt/%s/%s_BeltFollowerFit.fbx'%(kind,kind)
    r.export(out);log('exported',out)
    tl=bpy.data.objects['Belt_Tail_Left'];pts=[tl.matrix_world@v.co for v in tl.data.vertices]
    log('tail L bbox',[[round(min(p[i] for p in pts),3) for i in range(3)],[round(max(p[i] for p in pts),3) for i in range(3)]])
    log('DONE')
except Exception:
    log('ERROR',traceback.format_exc())
f.close()
