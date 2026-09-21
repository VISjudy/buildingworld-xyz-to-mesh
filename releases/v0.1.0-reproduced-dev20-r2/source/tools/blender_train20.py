"""Separate overview and individual inspection scenes; source coordinates kept."""
import bpy,bmesh,json,math
import numpy as np
from pathlib import Path
from mathutils import Vector
ROOT=Path('F:/codex/building');OUT=ROOT/'work/experiments/train20_review'
batch=json.loads((OUT/'batch_results.json').read_text(encoding='utf8'))
overview=bpy.data.scenes.new('BuildingWorld_Train20_Review');bpy.context.window.scene=overview
def mat(name,col):
    m=bpy.data.materials.new(name);m.diffuse_color=(*col,1);return m
roof=mat('T20_roof',(.68,.29,.12));wall=mat('T20_facade',(.58,.69,.77));ground=mat('T20_ground',(.23,.32,.39));ink=mat('T20_ink',(.10,.19,.25))
pm=[mat('T20_height_'+str(i),c) for i,c in enumerate([(.035,.08,.15),(.05,.16,.26),(.045,.25,.32),(.05,.33,.38),(.10,.39,.30),(.25,.42,.10)])]
def col(scene,name):
    c=bpy.data.collections.new(name);scene.collection.children.link(c);return c
def obj(name,vertices,faces,c):
    data=bpy.data.meshes.new(name+'_mesh');data.from_pydata(vertices,[],faces);data.update();ob=bpy.data.objects.new(name,data);c.objects.link(ob);return ob
def label(s,c,position,size=1):
    data=bpy.data.curves.new(s,'FONT');data.body=s;data.size=size;data.align_x='CENTER';data.materials.append(ink)
    ob=bpy.data.objects.new(s,data);c.objects.link(ob);ob.location=position;return ob
def configure(scene,target,location,scale,resolution):
    scene.render.engine='BLENDER_WORKBENCH';scene.display.shading.light='STUDIO';scene.display.shading.studio_light='paint.sl';scene.display.shading.color_type='MATERIAL'
    scene.display.shading.show_cavity=True;scene.display.shading.cavity_type='BOTH';scene.display.shading.show_shadows=True
    scene.world=bpy.data.worlds.new(scene.name+'_world');scene.world.color=(.9,.93,.95);scene.display.shading.background_type='WORLD'
    scene.view_settings.view_transform='Standard';scene.render.resolution_x=resolution[0];scene.render.resolution_y=resolution[1];scene.render.resolution_percentage=100
    ca=bpy.data.cameras.new(scene.name+'_camera');camera=bpy.data.objects.new(ca.name,ca);scene.collection.objects.link(camera)
    camera.location=location;camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler();ca.type='ORTHO';ca.ortho_scale=scale;scene.camera=camera
    return camera
presentation=col(overview,'T20_labels');qa=[]
for row in batch['samples']:
    idx=row['review_id'];ident=row['source_id'];dest=OUT/row['directory'];prefix=f'T20_{idx:02d}_{ident}'
    raw=np.loadtxt(row['source']);lo=raw.min(0);hi=raw.max(0);center=(lo+hi)/2;center[2]=lo[2]
    scale=10/max(hi-lo);x=((idx-1)%4-1.5)*33;y=(4-(idx-1)//4)*27
    c=col(overview,f'{idx:02d}_train_{ident}');c['source']=row['source'];c['status']=row['status'];c['accepted']=row['accepted']
    model=None
    if row['status']=='mesh_exported':
        model=json.loads((dest/(ident+'.json')).read_text(encoding='utf8'))
        ob=obj(prefix+'_MESH',model['vertices'],model['faces'],c)
        for material in [roof,wall,ground]:ob.data.materials.append(material)
        for face,sem in zip(ob.data.polygons,model['semantics']):face.material_index=2 if 'ground' in sem else (0 if 'roof' in sem else 1)
        ob.scale=(scale,)*3;ob.location=Vector((x+8,y,0))-Vector(center)*scale
        ob['source']=row['source'];ob['obj_file']=str(dest/(ident+'.obj'));ob['review_id']=idx;ob['accepted']=row['accepted'];ob['display_only_scale']=scale
        ob['failed_gates']=', '.join(k for k,v in row.get('gates',{}).items() if not v)
        bm=bmesh.new();bm.from_mesh(ob.data)
        qa.append({'review_id':idx,'source_id':ident,'vertices':len(bm.verts),'faces':len(bm.faces),'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges),'boundary_edges':sum(e.is_boundary for e in bm.edges),'signed_volume':bm.calc_volume(signed=True)})
        bm.free()
    # Display subset uses actual input positions. Full cloud also available in
    # the individual scene as a vertex-only object (toggle collection / Edit).
    rng=np.random.default_rng(20260920);sample=raw[rng.choice(len(raw),min(3500,len(raw)),replace=False)]
    radius=.055/scale;tet=np.array([[1,1,1],[-1,-1,1],[-1,1,-1],[1,-1,-1]])*radius
    pv=(sample[:,None,:]+tet).reshape(-1,3);template=np.array([[0,2,1],[0,1,3],[0,3,2],[1,2,3]])
    pf=(template[None,:,:]+(np.arange(len(sample))*4)[:,None,None]).reshape(-1,3)
    pc=obj(prefix+'_XYZ_DISPLAY',pv.tolist(),pf.tolist(),c);pc.scale=(scale,)*3;pc.location=Vector((x-8,y,0))-Vector(center)*scale
    for m in pm:pc.data.materials.append(m)
    bins=np.clip(((sample[:,2]-lo[2])/max(hi[2]-lo[2],1e-12)*5.999).astype(int),0,5);pc.data.polygons.foreach_set('material_index',np.repeat(bins,4).astype(np.int32))
    pc['source_points']=len(raw);pc['display_points']=len(sample);pc['source']=row['source']
    label(f'{idx:02d} / {ident} | REVIEW',(presentation),(x,y-7.2,.03),1.05)
    label('XYZ                 MESH',presentation,(x,y-9.2,.03),.7)
    individual=bpy.data.scenes.new(f'Inspect_{idx:02d}_train_{ident}');individual['source']=row['source'];individual['note']='Mesh and cloud use identical display transform. Toggle ALIGNED_XYZ to compare.'
    ic=col(individual,'01_MESH');overlay=col(individual,'02_ALIGNED_XYZ_TOGGLE');full=col(individual,'03_FULL_XYZ_VERTICES_TOGGLE');full.hide_viewport=True;full.hide_render=True
    if model:
        copy=bpy.data.objects.new(prefix+'_inspect_mesh',ob.data);ic.objects.link(copy);copy.scale=(scale,)*3;copy.location=-Vector(center)*scale
    cloud=bpy.data.objects.new(prefix+'_aligned_xyz',pc.data);overlay.objects.link(cloud);cloud.scale=(scale,)*3;cloud.location=-Vector(center)*scale
    fullcloud=obj(prefix+'_ALL_SOURCE_POINTS',raw.tolist(),[],full);fullcloud.scale=(scale,)*3;fullcloud.location=-Vector(center)*scale;fullcloud.show_in_front=True
    configure(individual,(0,0,3),(19,-27,24),19,(1300,1000))
    individual.render.image_settings.file_format='PNG';individual.render.filepath=str(dest/'blender_view.png')
label('BUILDINGWORLD / 20 TRAINING SAMPLES',presentation,(0,-14,.03),1.9)
label('XYZ + inferred mesh | fixed samples | review required | no GT score',presentation,(0,-17,.03),.9)
camera=configure(overview,(0,49,2),(0,-101,260),165,(1850,1800))
overview.render.image_settings.file_format='PNG';overview.render.filepath=str(OUT/'blender_overview.png')
overview['algorithm_version']=batch['engine_version'];overview['review_catalogue']=str(OUT/'index.html')
bpy.context.window.scene=overview;bpy.context.view_layer.update()
for area in bpy.context.screen.areas:
    if area.type=='VIEW_3D':
        sp=area.spaces.active;sp.shading.color_type='MATERIAL';sp.shading.show_cavity=True;sp.overlay.show_floor=False;sp.overlay.show_axis_x=False;sp.overlay.show_axis_y=False
        sp.region_3d.view_rotation=camera.rotation_euler.to_quaternion();sp.region_3d.view_distance=170;sp.region_3d.view_location=(0,49,0);sp.region_3d.view_perspective='ORTHO'
(OUT/'blender_mesh_qa.json').write_text(json.dumps(qa,indent=2),encoding='utf8')
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'buildingworld_train20.blend'),copy=True)
result={'scene':overview.name,'file':str(OUT/'buildingworld_train20.blend'),'models':len(qa),'individual_scenes':20,'qa':qa}
