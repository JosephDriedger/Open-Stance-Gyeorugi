"""Preview-only strand geometry study; no replacement of character masters."""
import bpy,sys,math,random
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).parent))
import audit_sparring_styles as a
out=a.ROOT/'Resources/Models/FinalRefinement/StrandGeometryReview';out.mkdir(exist_ok=True)
s,r,scale,source=a.load('Medium','Gameplay_High')
style=3;prefix='Hair_Chin_Length_Bob__'
core=bpy.data.objects[prefix+'Scalp_Coverage'];old=bpy.data.objects[prefix+'Combed_Hair_Fibers']
for prop in ['hide_render','hide_viewport']:old.driver_remove(prop)
old.hide_render=True;old.hide_viewport=True
assert len(core.data.vertices)==4736
cols,rows=128,37;rng=random.Random(63)
verts=[];fits=[];faces=[]
def surface(values,u,v):
    u=u%1;v=max(.001,min(.999,v));x=u*cols;y=v*(rows-1);i=int(x);j=int(y);fu=x-i;fv=y-j
    return core.matrix_world@(values[j*cols+i].co.lerp(values[j*cols+(i+1)%cols].co,fu).lerp(values[(j+1)*cols+i].co.lerp(values[(j+1)*cols+(i+1)%cols].co,fu),fv))
def point(values,u,v,offset):
    p=surface(values,u,v);du=surface(values,u+.001,v)-surface(values,u-.001,v)
    dv=surface(values,u,v+.001)-surface(values,u,v-.001);normal=dv.cross(du).normalized()
    if normal.dot(p-Vector((0,0,1.65))*scale)<0:normal=-normal
    return p+normal*offset,normal,du.normalized()
for strand in range(1800):
    u=rng.random();start=rng.uniform(.02,.6);end=min(.999,start+rng.uniform(.38,.8));wave=rng.uniform(-.0018,.0018)
    radius=rng.uniform(.00010,.00024)*scale;start_index=len(verts)
    for j in range(21):
        t=j/20;v=start+(end-start)*t;uu=u+wave*math.sin(t*4)
        taper=min(1,t/.12,(1-t)/.15)*.85+.15
        for key,target in [('Basis',verts),('HelmetFit',fits)]:
            p,n,tangent=point(core.data.shape_keys.key_blocks[key].data,uu,v,(.00035+.0004*math.sin(t*math.pi))*scale)
            for side in range(3):
                angle=side*math.tau/3;target.append(p+(n*math.cos(angle)+tangent*math.sin(angle))*radius*taper)
        if j:
            for side in range(3):
                b=start_index+j*3;faces.append((b-3+side,b-3+(side+1)%3,b+(side+1)%3,b+side))
mesh=bpy.data.meshes.new('Preview strand geometry');mesh.from_pydata(verts,[],faces);mesh.update()
o=bpy.data.objects.new(prefix+'Preview_Strands',mesh);s.collection.objects.link(o)
o.vertex_groups.new(name='head').add(list(range(len(verts))),1,'REPLACE');o.modifiers.new('Head attachment','ARMATURE').object=r
mat=core.data.materials[0].copy();mat.name='Preview_Strand_Hair';mesh.materials.append(mat)
for p in mesh.polygons:p.use_smooth=True
o.shape_key_add(name='Basis');key=o.shape_key_add(name='HelmetFit')
for v,p in zip(key.data,fits):v.co=p
d=key.driver_add('value').driver;v=d.variables.new();v.name='helmet';v.targets[0].id=r;v.targets[0].data_path='["Wear_Helmet"]';d.expression='1 if helmet else 0'
group=o.vertex_groups.new(name='Helmet_Exposed_Strands')
group.add([i for i,p in enumerate(fits) if p.z<1.545*scale],1,'REPLACE')
mask=o.modifiers.new('Hide strands covered by helmet','MASK');mask.vertex_group=group.name
for prop in ['show_viewport','show_render']:
    driver=mask.driver_add(prop).driver;v=driver.variables.new();v.name='helmet';v.targets[0].id=r;v.targets[0].data_path='["Wear_Helmet"]';driver.expression='helmet'
r['HairStyle']=style;s.cycles.samples=24
for helmet in [False,True]:
    r['Wear_Helmet']=helmet;a.build.refresh(r)
    a.render(s,r,scale,out,'Bob_'+str(int(helmet)),(.5,1,1.84),(0,0,1.64),.54,600,650)
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(out/'Preview_Bob.blend'),compress=True)
