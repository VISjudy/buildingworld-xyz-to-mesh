"""Run through Blender MCP. Creates a separate scene, preserves existing scene."""
import bpy, bmesh, json, math
import numpy as np
from pathlib import Path
from mathutils import Vector

ROOT=Path('F:/codex/building')
OUT=ROOT/'work/experiments/lod2_xyz_baseline'
scene=bpy.data.scenes.new('BuildingWorld_XYZ_Prototype')
bpy.context.window.scene=scene
scene.unit_settings.system='METRIC'
scene['unit_note']='Coordinates assumed meters for display; input CRS and units unverified.'
scene['method']='XYZ-only geometric baseline; provisional ground; no GT evaluation.'

def mat(name,color):
    m=bpy.data.materials.new(name); m.diffuse_color=(*color,1); return m
roofmat=mat('BW_Roof_Fitted',(0.67,.25,.10))
wallmat=mat('BW_Walls_Completed',(.62,.72,.79))
basemat=mat('BW_Base_Assumed',(.22,.30,.38))
textmat=mat('BW_Labels',(.10,.16,.23))
pointmats=[mat('BW_Points_Height_'+str(i),c) for i,c in enumerate([
    (.12,.09,.40),(.15,.22,.55),(.13,.37,.59),(.12,.51,.55),(.17,.65,.45),(.41,.77,.30),(.69,.84,.17),(.95,.85,.12)])]

def collection(name):
    c=bpy.data.collections.new(name); scene.collection.children.link(c); return c
models=collection('01_Reconstructed_Buildings')
clouds=collection('02_Input_XYZ_Display')
overlays=collection('03_Aligned_Clouds_Toggle_On')
overlays.hide_viewport=True; overlays.hide_render=True
presentation=collection('04_Presentation')
def objmesh(name,vs,fs,col):
    mesh=bpy.data.meshes.new(name+'_Mesh'); mesh.from_pydata(vs,[],fs); mesh.update()
    ob=bpy.data.objects.new(name,mesh); col.objects.link(ob); return ob
def text(label,pos,size=1):
    data=bpy.data.curves.new(label,'FONT'); data.body=label; data.align_x='CENTER'; data.size=size; data.extrude=0
    ob=bpy.data.objects.new(label,data); presentation.objects.link(ob); ob.location=pos; ob.rotation_euler=(math.radians(70),0,0); data.materials.append(textmat)
    return ob

qa=[]
for index,number in enumerate(['10','1000','2000']):
    data=json.loads((OUT/(number+'_model.json')).read_text(encoding='utf8'))
    raw=np.loadtxt(ROOT/'data/inputs/LiDAR_xyz'/(number+'.xyz'))
    offset=Vector((index*27-27,0,-data['metrics']['provisional_base_z']))
    ob=objmesh('BW_'+number+'_LOD2_prototype',data['vertices'],data['faces'],models)
    ob.location=offset
    for m in [roofmat,wallmat,basemat]: ob.data.materials.append(m)
    for poly,sem in zip(ob.data.polygons,data['semantics']): poly.material_index={'roof':0,'wall':1,'ground_assumed':2}[sem]
    for key in ['source','id']: ob[key]=data[key]
    ob['ground_assumption']=data['metrics']['base_rule']
    ob['display_translation']=list(offset)
    ob['model_coordinates']='OBJ preserves source coordinates; this scene translates for display.'
    bm=bmesh.new(); bm.from_mesh(ob.data); bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces)); bm.to_mesh(ob.data)
    qa.append(dict(id=number,vertices=len(bm.verts),faces=len(bm.faces),nonmanifold_edges=sum(not e.is_manifold for e in bm.edges),boundary_edges=sum(e.is_boundary for e in bm.edges),volume=bm.calc_volume(signed=True)))
    bm.free()
    # Actual source positions visualized as small octahedra; no generated points.
    radius=.045
    octa=np.array([[1,0,0],[-1,0,0],[0,1,0],[0,-1,0],[0,0,1],[0,0,-1]])*radius
    pv=(raw[:,None,:]+octa[None,:,:]).reshape(-1,3)
    template=np.array([[0,2,4],[2,1,4],[1,3,4],[3,0,4],[2,0,5],[1,2,5],[3,1,5],[0,3,5]])
    pf=(template[None,:,:]+(np.arange(len(raw))*6)[:,None,None]).reshape(-1,3)
    pc=objmesh('BW_'+number+'_Input_Points',pv.tolist(),pf.tolist(),clouds)
    pc.location=offset+Vector((0,24,0)); pc['source']=str(ROOT/'data/inputs/LiDAR_xyz'/(number+'.xyz')); pc['points']=len(raw)
    for m in pointmats: pc.data.materials.append(m)
    bins=np.clip(((raw[:,2]-raw[:,2].min())/np.ptp(raw[:,2])*7.999).astype(int),0,7)
    pc.data.polygons.foreach_set('material_index',np.repeat(bins,8).astype(np.int32))
    aligned=bpy.data.objects.new('BW_'+number+'_Aligned_Input',pc.data); overlays.objects.link(aligned); aligned.location=offset
    text('XYZ '+number,(offset.x,15.7,.1),1.3)
    text(number+' | '+('GABLE' if number=='2000' else 'FLAT'),(offset.x,-12,.1),1.3)

text('BuildingWorld | XYZ-only reconstruction',(0,-18,.1),1.65)
text('Fitted roof / completed walls / provisional base',(0,-21,.1),.85)
floor=objmesh('BW_Display_Ground',[[-46,-25,-.15],[46,-25,-.15],[46,41,-.15],[-46,41,-.15]],[[0,1,2,3]],presentation)
floor.data.materials.append(mat('BW_Display_Backdrop',(.87,.90,.92)))
camera_data=bpy.data.cameras.new('BW_Camera'); camera=bpy.data.objects.new('BW_Camera',camera_data); presentation.objects.link(camera)
target=Vector((0,9,2)); camera.location=(48,-77,83); camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
camera_data.type='ORTHO'; camera_data.ortho_scale=99; scene.camera=camera
scene.render.engine='BLENDER_WORKBENCH'
scene.display.shading.light='STUDIO'; scene.display.shading.studio_light='paint.sl'
scene.display.shading.color_type='MATERIAL'; scene.display.shading.show_shadows=True
scene.display.shading.show_cavity=True; scene.display.shading.cavity_type='BOTH'; scene.display.shading.show_object_outline=True
scene.display.shading.background_type='WORLD'; scene.world=bpy.data.worlds.new('BW_World'); scene.world.color=(.87,.90,.92)
scene.render.resolution_x=1800; scene.render.resolution_y=1250; scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'; scene.render.filepath=str(OUT/'blender_preview.png')
scene.view_settings.view_transform='Standard'
bpy.context.view_layer.update()
for area in bpy.context.screen.areas:
    if area.type=='VIEW_3D':
        space=area.spaces.active; space.shading.color_type='MATERIAL'; space.shading.light='STUDIO'; space.shading.show_cavity=True
        space.overlay.show_floor=False; space.overlay.show_axis_x=False; space.overlay.show_axis_y=False
        space.region_3d.view_rotation=camera.rotation_euler.to_quaternion(); space.region_3d.view_distance=105; space.region_3d.view_location=target; space.region_3d.view_perspective='ORTHO'
for o in bpy.context.selected_objects: o.select_set(False)
bpy.context.view_layer.objects.active=None
(OUT/'blender_mesh_qa.json').write_text(json.dumps(qa,indent=2),encoding='utf8')
# save_as_mainfile(copy=True) writes a deliverable without replacing the user's current file path.
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'buildingworld_xyz_prototype.blend'),copy=True)
result={'scene':scene.name,'saved':str(OUT/'buildingworld_xyz_prototype.blend'),'qa':qa}
