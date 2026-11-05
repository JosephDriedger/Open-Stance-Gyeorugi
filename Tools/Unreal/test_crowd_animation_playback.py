"""Verify imported crowd clips actually move both LODs in an unsaved PIE world."""
import unreal,json,time,uuid,traceback
from pathlib import Path
ROOT=Path('D:/Open-Stance-Gyeorugi');OUT=ROOT/'Resources/Models/FinalRefinement/CrowdPlayback_20261102';OUT.mkdir(exist_ok=True)
EAL=unreal.EditorAssetLibrary;levels=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
scratch='/Game/__CharacterValidation__/CrowdPlayback_'+uuid.uuid4().hex
report=dict(production_assets_saved=False,checks=[],errors=[],scope='Medium Near/Far skeletal playback of five clips in headless PIE; no rendered crowd density/performance acceptance.')
def imported(source,ui):
    task=unreal.AssetImportTask();task.filename=str(ROOT/'Resources/Models/CharacterSuite/Medium'/source);task.destination_path=scratch;task.destination_name=Path(source).stem;task.automated=True;task.save=False;task.options=ui
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);return [EAL.load_asset(p) for p in task.imported_object_paths]
class Test:
    def __init__(self):
        self.state='setup';self.until=0;self.busy=False;self.started=time.time();self.callback=unreal.register_slate_post_tick_callback(self.tick)
    def finish(self):
        unreal.unregister_slate_post_tick_callback(self.callback)
        unreal.EditorLevelLibrary.editor_end_play()
        levels.load_level('/Game/Maps/L_MainMenu')
        report['scratch_deleted']=EAL.delete_directory(scratch) if EAL.does_directory_exist(scratch) else True
        report['passed']=len(report['checks'])==10 and not report['errors'] and all(c['maximum_sampled_bone_motion_cm']>.01 and c['time_advanced'] for c in report['checks'])
        (OUT/'validation.json').write_text(json.dumps(report,indent=2));unreal.SystemLibrary.quit_editor()
    def tick(self,delta):
        if self.busy or time.time()<self.until:return
        self.busy=True
        try:
            if time.time()-self.started>120:raise RuntimeError('Crowd playback timeout')
            self.step()
        except Exception:report['errors'].append(traceback.format_exc());self.finish()
        finally:self.busy=False
    def step(self):
        if self.state=='setup':
            unreal.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
            meshes=[];skeleton=None
            for lod in ('Near','Far'):
                ui=unreal.FbxImportUI();ui.import_mesh=True;ui.import_as_skeletal=True;ui.mesh_type_to_import=unreal.FBXImportType.FBXIT_SKELETAL_MESH;ui.automated_import_should_detect_type=False;ui.import_animations=False;ui.import_materials=False;ui.import_textures=False;ui.create_physics_asset=False
                if skeleton:ui.skeleton=skeleton
                mesh=next(a for a in imported('Crowd_'+lod+'.fbx',ui) if isinstance(a,unreal.SkeletalMesh));skeleton=mesh.get_editor_property('skeleton');meshes.append((lod,mesh))
            clips=[]
            for label in ('StandingIdle','SeatedIdle','SeatedClap','Cheer','Wave'):
                ui=unreal.FbxImportUI();ui.import_mesh=False;ui.import_animations=True;ui.skeleton=skeleton;ui.mesh_type_to_import=unreal.FBXImportType.FBXIT_ANIMATION;ui.automated_import_should_detect_type=False
                anim=next(a for a in imported('Crowd_'+label+'.fbx',ui) if isinstance(a,unreal.AnimSequence));clips.append((label,anim))
            self.animation_by_label=dict(clips)
            levels.load_level('/Game/Maps/L_MainMenu')
            for i,(lod,mesh) in enumerate(meshes):
                for j,(label,anim) in enumerate(clips):
                    actor=unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.SkeletalMeshActor,unreal.Vector(i*200,j*200,0));actor.set_actor_label('CrowdTest_'+lod+'_'+label)
                    comp=actor.skeletal_mesh_component;comp.set_skeletal_mesh_asset(mesh);comp.set_editor_property('visibility_based_anim_tick_option',unreal.VisibilityBasedAnimTickOption.ALWAYS_TICK_POSE_AND_REFRESH_BONES);comp.play_animation(anim,True)
            self.state='start';self.until=time.time()+1
        elif self.state=='start':
            unreal.EditorLevelLibrary.editor_play_simulate();self.state='collect';self.until=time.time()+3
        elif self.state=='collect':
            self.world=unreal.EditorLevelLibrary.get_game_world();assert self.world
            self.components={a.get_actor_label():a.skeletal_mesh_component for a in unreal.GameplayStatics.get_all_actors_of_class(self.world,unreal.SkeletalMeshActor) if a.get_actor_label().startswith('CrowdTest_')};assert len(self.components)==10
            for name,c in self.components.items():
                assert all(c.does_socket_exist(b) for b in ('hand_l','hand_r','head')),name
                c.play_animation(self.animation_by_label[name.split('_',2)[2]],True)
            self.state='sample';self.until=time.time()+.4
        elif self.state=='sample':
            self.before={name:([c.get_socket_location(b) for b in ('hand_l','hand_r','head')],c.get_position()) for name,c in self.components.items()}
            self.state='check';self.until=time.time()+.65
        elif self.state=='check':
            for name,c in self.components.items():
                points,t=self.before[name];now=[c.get_socket_location(b) for b in ('hand_l','hand_r','head')]
                report['checks'].append(dict(actor=name,maximum_sampled_bone_motion_cm=max((a-b).length() for a,b in zip(now,points)),time_advanced=abs(c.get_position()-t)>.001))
            self.finish()
_test=Test()
