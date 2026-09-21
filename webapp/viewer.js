export class BuildingViewer {
  constructor(canvas) {
    this.canvas=canvas;this.gl=canvas.getContext('webgl',{antialias:true,alpha:false,preserveDrawingBuffer:true});
    if(!this.gl)throw new Error('浏览器不支持 WebGL，无法显示三维预览。');
    this.az=-.85;this.el=.62;this.zoom=1;this.pan=[0,0];this.mode='overlay';this.edges=true;this.noise=true;this.groups={};
    const gl=this.gl;const shader=(type,source)=>{const s=gl.createShader(type);gl.shaderSource(s,source);gl.compileShader(s);if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))throw new Error(gl.getShaderInfoLog(s));return s;};
    const p=gl.createProgram();gl.attachShader(p,shader(gl.VERTEX_SHADER,`attribute vec3 aPosition; attribute vec3 aNormal; attribute vec3 aColor; uniform mat4 uMatrix; uniform float uSize; varying vec3 vColor; varying vec3 vNormal; void main(){gl_Position=uMatrix*vec4(aPosition,1.); gl_PointSize=uSize;vColor=aColor;vNormal=aNormal;}`));
    gl.attachShader(p,shader(gl.FRAGMENT_SHADER,`precision mediump float;varying vec3 vColor;varying vec3 vNormal;uniform int uKind;uniform float uAlpha;void main(){if(uKind==1 && distance(gl_PointCoord,vec2(.5))>.5)discard;float light=uKind==0?(.40+.60*abs(dot(normalize(vNormal),normalize(vec3(.35,-.55,.8))))):1.;gl_FragColor=vec4(vColor*light,uAlpha);}`));gl.linkProgram(p);if(!gl.getProgramParameter(p,gl.LINK_STATUS))throw new Error(gl.getProgramInfoLog(p));this.program=p;
    this.attributes=['aPosition','aNormal','aColor'].map(k=>gl.getAttribLocation(p,k));this.uniforms=Object.fromEntries(['uMatrix','uSize','uKind','uAlpha'].map(k=>[k,gl.getUniformLocation(p,k)]));
    let drag=null;canvas.addEventListener('pointerdown',e=>{drag=[e.clientX,e.clientY];canvas.setPointerCapture(e.pointerId);});canvas.addEventListener('pointerup',()=>drag=null);canvas.addEventListener('pointercancel',()=>drag=null);
    canvas.addEventListener('pointermove',e=>{if(!drag)return;const dx=e.clientX-drag[0],dy=e.clientY-drag[1];drag=[e.clientX,e.clientY];if(e.shiftKey){this.pan[0]+=dx/canvas.clientWidth*2;this.pan[1]-=dy/canvas.clientHeight*2;}else{this.az-=dx*.008;this.el=Math.max(-1.5,Math.min(1.55,this.el+dy*.006));}this.render();});
    canvas.addEventListener('wheel',e=>{e.preventDefault();this.zoom=Math.max(.15,Math.min(8,this.zoom*Math.exp(-e.deltaY*.001)));this.render();},{passive:false});new ResizeObserver(()=>this.render()).observe(canvas);this.setData({points:[]});
  }
  reset(view='perspective'){this.pan=[0,0];this.zoom=1;this.az=-.85;this.el=.62;if(view==='top'){this.az=-Math.PI/2;this.el=Math.PI/2;}if(view==='front'){this.az=-Math.PI/2;this.el=0;}this.render();}
  buffer(key,data){const gl=this.gl;if(this.groups[key])gl.deleteBuffer(this.groups[key].buffer);const b=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,b);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(data),gl.STATIC_DRAW);this.groups[key]={buffer:b,count:data.length/9};}
  setData(data){
    this.data=data;const points=data.points||[],model=data.model;let lo=[Infinity,Infinity,Infinity],hi=[-Infinity,-Infinity,-Infinity];
    for(const p of [...(data.bounds||[]),...(model?.vertices||[]),...(!data.bounds?points:[])])for(let i=0;i<3;i++){lo[i]=Math.min(lo[i],p[i]);hi[i]=Math.max(hi[i],p[i]);}if(!isFinite(lo[0])){lo=[-1,-1,0];hi=[1,1,2];}
    const center=lo.map((x,i)=>(x+hi[i])/2),span=Math.max(...hi.map((x,i)=>x-lo[i]),.001);this.half=hi.map((x,i)=>(x-lo[i])/span);this.normalize=p=>p.map((x,i)=>(x-center[i])*2/span);
    const add=(a,p,n,c)=>a.push(...this.normalize(p),...n,...c);const raw=[],bad=[],tri=[],lines=[],grid=[];const excluded=new Set(model?.noise_diagnostics?.excluded_indices||[]);
    for(let j=0;j<points.length;j++){const p=points[j],h=(p[2]-lo[2])/Math.max(hi[2]-lo[2],.001);add(excluded.has(data.point_indices?.[j]??j)?bad:raw,p,[0,0,1],excluded.has(data.point_indices?.[j]??j)?[1,.30,.23]:[.22+.16*h,.56+.26*h,.63-.10*h]);}
    if(model){const adjacency=new Map(),normals=[];for(let fi=0;fi<model.faces.length;fi++){const f=model.faces[fi];if(f.length<3)continue;const a=model.vertices[f[0]],b=model.vertices[f[1]],c=model.vertices[f[2]];let u=b.map((x,i)=>x-a[i]),v=c.map((x,i)=>x-a[i]);let n=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]],len=Math.hypot(...n);n=n.map(x=>x/(len||1));normals[fi]=n;const color=(model.semantics[fi]||'').includes('roof')?[.83,.49,.25]:[.55,.67,.72];
      for(let j=1;j<f.length-1;j++)for(const id of [f[0],f[j],f[j+1]])add(tri,model.vertices[id],n,color);
      for(let j=0;j<f.length;j++){const e=[f[j],f[(j+1)%f.length]].sort((a,b)=>a-b),key=e.join(':');if(!adjacency.has(key))adjacency.set(key,{e,faces:[]});adjacency.get(key).faces.push(fi);}
    }for(const {e,faces} of adjacency.values()){const dot=faces.length===2?normals[faces[0]].reduce((s,x,i)=>s+x*normals[faces[1]][i],0):0;if(faces.length!==2||Math.abs(dot)<.9903)for(const id of e)add(lines,model.vertices[id],[0,0,1],[.93,.69,.39]);}}
    const bottom=(lo[2]-center[2])*2/span-.02;for(let x=-1.5;x<=1.501;x+=.15){for(const p of [[x,-1.5,bottom],[x,1.5,bottom],[-1.5,x,bottom],[1.5,x,bottom]])grid.push(...p,0,0,1,.13,.23,.28);}
    for(const [key,array] of Object.entries({points:raw,noise:bad,mesh:tri,edges:lines,grid}))this.buffer(key,array);this.render();
  }
  render(){const gl=this.gl,c=this.canvas,dpr=Math.min(devicePixelRatio||1,2),w=Math.max(1,Math.round(c.clientWidth*dpr)),h=Math.max(1,Math.round(c.clientHeight*dpr));if(c.width!==w||c.height!==h){c.width=w;c.height=h;}gl.viewport(0,0,w,h);gl.clearColor(.065,.125,.157,1);gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);gl.useProgram(this.program);gl.enable(gl.DEPTH_TEST);gl.depthFunc(gl.LEQUAL);gl.enable(gl.BLEND);gl.blendFunc(gl.SRC_ALPHA,gl.ONE_MINUS_SRC_ALPHA);
    const sa=Math.sin(this.az),ca=Math.cos(this.az),se=Math.sin(this.el),ce=Math.cos(this.el),aspect=w/h;
    const half=this.half||[1,1,1],sx=Math.abs(sa)*half[0]+Math.abs(ca)*half[1],sy=Math.abs(ca*se)*half[0]+Math.abs(sa*se)*half[1]+Math.abs(ce)*half[2];
    const z=this.zoom*.80/Math.max(sx/aspect,sy,.001);
    const R=[-sa*z/aspect,ca*z/aspect,0],U=[-ca*se*z,-sa*se*z,ce*z],D=[-ca*ce*.25,-sa*ce*.25,-se*.25];const matrix=new Float32Array([R[0],U[0],D[0],0,R[1],U[1],D[1],0,R[2],U[2],D[2],0,this.pan[0],this.pan[1],0,1]);gl.uniformMatrix4fv(this.uniforms.uMatrix,false,matrix);gl.uniform1f(this.uniforms.uSize,2.2*dpr);
    const draw=(key,primitive,kind,alpha=1)=>{const g=this.groups[key];if(!g||!g.count)return;gl.bindBuffer(gl.ARRAY_BUFFER,g.buffer);this.attributes.forEach((a,i)=>{gl.enableVertexAttribArray(a);gl.vertexAttribPointer(a,3,gl.FLOAT,false,36,i*12);});gl.uniform1i(this.uniforms.uKind,kind);gl.uniform1f(this.uniforms.uAlpha,alpha);gl.drawArrays(primitive,0,g.count);};draw('grid',gl.LINES,2,.5);
    if(this.mode!=='points'){gl.enable(gl.POLYGON_OFFSET_FILL);gl.polygonOffset(1,1);draw('mesh',gl.TRIANGLES,0,this.mode==='overlay'?.74:1);gl.disable(gl.POLYGON_OFFSET_FILL);if(this.edges)draw('edges',gl.LINES,2,.75);}
    if(this.mode!=='mesh'){draw('points',gl.POINTS,1,.95);if(this.noise){gl.disable(gl.DEPTH_TEST);draw('noise',gl.POINTS,1,1);}}
  }
}
