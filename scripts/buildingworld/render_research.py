"""Blender BACKGROUND renderer. Factory scene only; never touches the open GUI scene.

blender --background --factory-startup --python render_research.py -- --request request.json
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
import bpy
from mathutils import Vector


def obj_read(path):
    vertices,faces=[],[]
    for raw in Path(path).read_text(encoding='utf-8').splitlines():
        t=raw.split()
        if not t:continue
        if t[0]=='v':vertices.append(tuple(map(float,t[1:4])))
        if t[0]=='f':faces.append([int(x.split('/')[0])-1 for x in t[1:]])
    return vertices,faces


def render(request):
    out=Path(request['output']);out.mkdir(parents=True,exist_ok=False)
    scene=bpy.context.scene
    scene.render.engine='BLENDER_WORKBENCH'
    scene.display.shading.light='STUDIO'
    scene.display.shading.color_type='OBJECT'
    scene.display.shading.show_shadows=True
    scene.display.shading.show_cavity=True
    scene.display.shading.cavity_type='BOTH'
    scene.display.shading.show_object_outline=True
    scene.display.shading.background_type='WORLD'
    scene.world.color=(.92,.94,.96)
    scene.render.resolution_x=int(request.get('width',480));scene.render.resolution_y=int(request.get('height',420));scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG'
    scene.render.film_transparent=False
    camera_data=bpy.data.cameras.new('ResearchCamera');camera=bpy.data.objects.new('ResearchCamera',camera_data)
    scene.collection.objects.link(camera);scene.camera=camera;camera_data.type='ORTHO'
    def visible(ob, value):
        ob.hide_render=not value
        ob.hide_set(not value)
    for o in scene.objects:
        if o!=camera:visible(o,False)
    records=[]
    for sample in request['samples']:
        bid=sample['id']
        points=[]
        if sample.get('points'):
            for raw in Path(sample['points']).read_text().splitlines():
                if raw.strip():points.append(tuple(map(float,raw.split()[:3])))
        models={name:obj_read(path) for name,path in sample['models'].items() if path and Path(path).is_file()}
        allv=points+[q for v,f in models.values() for q in v]
        low=[min(p[i] for p in allv) for i in range(3)];high=[max(p[i] for p in allv) for i in range(3)]
        center=Vector([(a+b)/2 for a,b in zip(low,high)])
        diagonal=Vector([b-a for a,b in zip(low,high)]).length
        extent=max(diagonal,1e-3);camera_data.ortho_scale=extent*1.15
        camera_data.clip_start=extent*.01;camera_data.clip_end=extent*10
        sample_objects={}
        for name,(vertices,faces) in models.items():
            m=bpy.data.meshes.new(bid+'_'+name);m.from_pydata([Vector(v)-center for v in vertices],[],faces);m.update()
            ob=bpy.data.objects.new(m.name,m);scene.collection.objects.link(ob);ob.color=(.56,.65,.73,1);visible(ob,False);sample_objects[name]=ob
        if points:
            radius=extent*.002
            stride=max(1,len(points)//5000)
            verts=[];faces=[]
            for p in points[::stride]:
                q=Vector(p)-center;i=len(verts)
                verts.extend([q+Vector((radius,0,-radius/2)),q+Vector((-radius,0,-radius/2)),q+Vector((0,radius,radius)),q+Vector((0,-radius,radius))])
                faces.extend([(i,i+1,i+2),(i,i+3,i+1),(i,i+2,i+3),(i+1,i+3,i+2)])
            m=bpy.data.meshes.new(bid+'_points');m.from_pydata(verts,[],faces);m.update()
            ob=bpy.data.objects.new(m.name,m);scene.collection.objects.link(ob);ob.color=(.05,.38,.66,1);visible(ob,False);sample_objects['input']=ob
        views={'oblique':Vector((1,-1,.8)), 'opposite':Vector((-1,1,.8)), 'top':Vector((0,0,1))}
        if request.get('seven_views',False):
            views.update(front=Vector((0,-1,0)),back=Vector((0,1,0)),left=Vector((-1,0,0)),right=Vector((1,0,0)))
        if request.get('view_names'):
            views={name:views[name] for name in request['view_names']}
        for view,direction in views.items():
            camera.location=direction.normalized()*extent*3
            camera.rotation_euler=(-camera.location).to_track_quat('-Z','Y').to_euler()
            for name,ob in sample_objects.items():
                visible(ob,True)
                scene.render.filepath=str(out/f'{bid}_{view}_{name}.png');bpy.ops.render.render(write_still=True)
                visible(ob,False)
            if 'input' in sample_objects and 'current' in sample_objects:
                visible(sample_objects['input'],True);visible(sample_objects['current'],True)
                scene.render.filepath=str(out/f'{bid}_{view}_overlay.png');bpy.ops.render.render(write_still=True)
                visible(sample_objects['input'],False);visible(sample_objects['current'],False)
        records.append({'id':bid,'display_origin':list(center),'ortho_scale':camera_data.ortho_scale,
                        'source_hashes':{n:hashlib.sha256(Path(p).read_bytes()).hexdigest() for n,p in sample['models'].items() if p and Path(p).is_file()},
                        'views':list(views),'point_render_decimated':len(points)>5000})
        # Keep objects hidden in this transient process; no .blend or user file is overwritten.
    (out/'render_manifest.json').write_text(json.dumps({'blender':bpy.app.version_string,'same_camera_per_sample':True,
        'render_engine':'workbench','samples':records},indent=2),encoding='utf-8')


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--request',required=True)
    a=ap.parse_args(sys.argv[sys.argv.index('--')+1:]);render(json.loads(Path(a.request).read_text(encoding='utf-8')))
