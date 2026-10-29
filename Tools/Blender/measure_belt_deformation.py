"""Quantify stretch/compression of saved simulation candidates for review."""
import bpy,sys,json,statistics
from pathlib import Path
root=Path(__file__).resolve().parents[2]/'Resources/Models/FinalRefinement'
args=sys.argv[sys.argv.index('--')+1:]
folder=Path(args[1]).resolve() if args[0]=='folder' else root/('ClothRefinement_'+args[0])
bpy.ops.wm.open_mainfile(filepath=str(folder/'Candidate.blend'))
s=bpy.context.scene;o=bpy.data.objects['SIM_Shared_Belt_Tails']
edges=[tuple(e.vertices) for e in o.data.edges]
rest=[(o.data.vertices[a].co-o.data.vertices[b].co).length for a,b in edges]
rows=[];previous=None
for frame in range(1,s.frame_end+1):
    s.frame_set(frame);ev=o.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh()
    current=[v.co.copy() for v in me.vertices]
    speed=max((p-q).length for p,q in zip(current,previous))*s.render.fps/s.render.fps_base if previous else 0
    if frame in [1,26,35,72,144,216,s.frame_end]:
        assert len(me.vertices)==len(o.data.vertices)
        ratios=sorted((me.vertices[a].co-me.vertices[b].co).length/d for (a,b),d in zip(edges,rest))
        rows.append({'frame':frame,'edge_ratio_min':ratios[0],'edge_ratio_median':statistics.median(ratios),
                     'edge_ratio_max':ratios[-1], 'edges_compressed_over_20_percent':sum(x<.8 for x in ratios),
                     'edges_stretched_over_20_percent':sum(x>1.2 for x in ratios),'edge_count':len(ratios),
                     'z_span_m':max(v.co.z for v in me.vertices)-min(v.co.z for v in me.vertices),'maximum_vertex_speed_m_per_s':speed})
    previous=current
    ev.to_mesh_clear()
(folder/'deformation_metrics.json').write_text(json.dumps(rows,indent=2))
print(json.dumps(rows,indent=2))
