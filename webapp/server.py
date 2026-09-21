"""Loopback-only XYZ -> OBJ service. No external services or web dependencies."""
from pathlib import Path
import argparse,json,re,sys,uuid,time,subprocess,threading,mimetypes,hashlib
from urllib.parse import urlsplit,unquote
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from concurrent.futures import ThreadPoolExecutor
ROOT=Path(__file__).resolve().parents[1];WEB=ROOT/'webapp';JOBS=ROOT/'work/runtime/web_jobs';JOBS.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT));import pointcloud_to_mesh as engine
import numpy as np
POOL=ThreadPoolExecutor(max_workers=1);STATE={};LOCK=threading.Lock();MAX_BYTES=24*1024*1024
for previous in JOBS.iterdir():
    if previous.is_dir() and re.fullmatch(r'[a-f0-9]{32}',previous.name) and (previous/'result.json').is_file():
        try:
            cfg=json.loads((previous/'request.json').read_text(encoding='utf8'));saved=json.loads((previous/'result.json').read_text(encoding='utf8'))
            STATE[previous.name]={'id':previous.name,'name':cfg.get('name','input.xyz'),**saved}
        except (ValueError,OSError):pass

def examples():
    items={}
    release=ROOT/'releases/v0.5.1-batch02'
    for ident in ['1321','144','1048']:
        p=release/'models/rechecks'/f'{ident}.json'
        if p.exists():items['noise_'+ident]={'key':'noise_'+ident,'label':{'1321':'圈选 07 · 1321','144':'圈选 08 · 144','1048':'低坡对照 · 1048'}[ident],'source':ROOT/'data/inputs/xyz'/f'{ident}.xyz','model':p,'report':release/'reports/rechecks'/f'{ident}_validation.json','obj':p.with_suffix('.obj'),'group':'噪声与分面复查'}
    path=release/'reports/batch_results.json'
    if path.exists():
        data=json.loads(path.read_text(encoding='utf8'))
        for row in data['samples']:
            dest=release/'models'/row['directory'];key='b2_'+str(row['review_id'])
            items[key]={'key':key,'label':f"{row['review_id']:02d} · {row['source_id']}",'source':ROOT/row['source'],'model':dest/(row['source_id']+'.json'),'obj':dest/(row['source_id']+'.obj'),'report':release/'reports'/row['directory']/'validation.json','group':'第二批 · 新增 20 栋','status':row['status'],'points':row['points']}
    return items

def preview(source,model_path=None,report_path=None):
    data={'points':[],'point_indices':[],'point_count':0,'input_available':source.is_file()}
    if source.is_file():
        p=np.loadtxt(source,ndmin=2);ids=np.linspace(0,len(p)-1,min(len(p),22000),dtype=int)
        data.update(points=p[ids].tolist(),point_indices=ids.tolist(),point_count=len(p),bounds=[p.min(0).tolist(),p.max(0).tolist()])
    if model_path and model_path.exists():
        m=json.loads(model_path.read_text(encoding='utf8'))
        data['model']={k:m[k] for k in ['vertices','faces','semantics','topology','algorithm_version','noise_diagnostics','official_metrics'] if k in m}
    if report_path and report_path.exists():data['validation']=json.loads(report_path.read_text(encoding='utf8'))
    return data

def process_job(ident):
    directory=JOBS/ident
    with LOCK:STATE[ident]['status']='running'
    try:
        with (directory/'run.log').open('w',encoding='utf8') as log:
            p=subprocess.run([sys.executable,'-X','utf8',str(WEB/'worker.py'),str(directory)],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,timeout=600)
        result=json.loads((directory/'result.json').read_text(encoding='utf8'))
        if p.returncode and result.get('status')!='failed':raise RuntimeError('重建进程异常退出，请查看运行记录。')
    except subprocess.TimeoutExpired:result={'status':'failed','error':'计算超过 10 分钟，任务已停止。请先减少点数或拆分为单栋建筑。'}
    except Exception as e:result={'status':'failed','error':str(e)}
    with LOCK:STATE[ident].update(result)

class Handler(BaseHTTPRequestHandler):
    server_version='BuildingWorldLocal/1.0'
    def log_message(self,fmt,*args):print(time.strftime('%H:%M:%S'),fmt%args,flush=True)
    def send_json(self,value,status=200):
        data=json.dumps(value,ensure_ascii=False,allow_nan=False).encode('utf8');self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
    def send_file(self,path,download=False):
        if not path.is_file():return self.send_json({'error':'文件尚未生成。'},404)
        data=path.read_bytes();self.send_response(200);self.send_header('Content-Type',('text/plain' if path.suffix=='.obj' else mimetypes.guess_type(str(path))[0]) or 'application/octet-stream');self.send_header('Content-Length',str(len(data)))
        if download:self.send_header('Content-Disposition','attachment; filename="'+path.name+'"')
        self.end_headers();self.wfile.write(data)
    def do_GET(self):
        try:self.get()
        except (BrokenPipeError,ConnectionResetError):pass
        except Exception as e:self.send_json({'error':str(e)},500)
    def get(self):
        path=unquote(urlsplit(self.path).path)
        if path=='/api/health':return self.send_json({'status':'ok','algorithm_version':engine.VERSION,'local_only':True})
        if path=='/api/examples':return self.send_json([{k:v for k,v in e.items() if k in ('key','label','group','status','points')} for e in examples().values()])
        match=re.fullmatch(r'/api/examples/([a-z0-9_]+)(?:/(obj|report))?',path)
        if match:
            e=examples().get(match[1])
            if not e:return self.send_json({'error':'找不到这个样例。'},404)
            if match[2]:return self.send_file(e['obj' if match[2]=='obj' else 'report'],True)
            return self.send_json({**preview(e['source'],e['model'],e['report']),'label':e['label'],'obj_url':f"/api/examples/{e['key']}/obj",'report_url':f"/api/examples/{e['key']}/report"})
        match=re.fullmatch(r'/api/jobs/([a-f0-9]{32})(?:/(preview|obj|report))?',path)
        if match:
            ident=match[1];directory=JOBS/ident
            with LOCK:state=dict(STATE.get(ident,{}))
            if not state:return self.send_json({'error':'找不到任务；服务重启后请重新上传。'},404)
            if match[2]=='preview':return self.send_json(preview(directory/'input.xyz',directory/'model.json',directory/'validation.json'))
            if match[2] in ('obj','report'):
                return self.send_file(directory/('model.obj' if match[2]=='obj' else 'result.json'),True)
            return self.send_json(state)
        if path.startswith('/review/'):
            base=(ROOT/'releases/v0.5.1-batch02').resolve();file=(base/path[len('/review/'):]).resolve()
            if not file.is_relative_to(base):return self.send_json({'error':'路径不允许。'},403)
            return self.send_file(file)
        static={'/':'index.html','/app.js':'app.js','/viewer.js':'viewer.js','/style.css':'style.css'}
        if path=='/BUILDING_RECONSTRUCTION_ALGORITHM.md':return self.send_file(ROOT/'docs/BUILDING_RECONSTRUCTION_ALGORITHM.md')
        if path in static:return self.send_file(WEB/static[path])
        return self.send_json({'error':'找不到页面。'},404)
    def do_POST(self):
        if urlsplit(self.path).path!='/api/jobs':return self.send_json({'error':'找不到接口。'},404)
        origin=self.headers.get('Origin')
        if origin and origin!=f'http://{self.headers.get("Host")}':return self.send_json({'error':'只接受本地网页提交。'},403)
        if self.headers.get('Content-Type','').split(';')[0]!='application/json':return self.send_json({'error':'需要 JSON 上传。'},415)
        try:
            length=int(self.headers.get('Content-Length','0'))
            if length<=0 or length>MAX_BYTES:return self.send_json({'error':'文件为空或大于 24 MB。'},413)
            request=json.loads(self.rfile.read(length).decode('utf-8-sig'))
            text=request.get('text');name=str(request.get('name','input.xyz'))[:180]
            if not isinstance(text,str) or not text.strip():return self.send_json({'error':'请上传包含 XYZ 三列的点云文件。'},400)
            import io
            p=np.loadtxt(io.StringIO(text),ndmin=2)
            if p.shape[1]!=3 or len(p)<20 or len(p)>300000 or not np.isfinite(p).all():return self.send_json({'error':'需要 20–300000 个有限 XYZ 点，每行恰好三列。'},400)
            if min(np.ptp(p,axis=0)[:2])<1e-4:return self.send_json({'error':'XY 范围退化，无法推断建筑轮廓。'},400)
            noise=request.get('noise','conservative')
            if noise not in ('conservative','off'):return self.send_json({'error':'未知噪声处理选项。'},400)
            ground=request.get('ground_z')
            if ground is not None:
                ground=float(ground)
                if not np.isfinite(ground) or ground>=p[:,2].max():return self.send_json({'error':'底高必须为有限数，并低于点云最高处。'},400)
            with LOCK:
                if sum(v['status'] in ('queued','running') for v in STATE.values())>=6:return self.send_json({'error':'任务队列已满，请等待当前任务完成。'},429)
            ident=uuid.uuid4().hex;directory=JOBS/ident;directory.mkdir()
            (directory/'input.xyz').write_text(text,encoding='utf8');(directory/'request.json').write_text(json.dumps({'name':name,'ground_z':ground,'noise':noise}),encoding='utf8')
            state={'id':ident,'name':name,'status':'queued','points':len(p),'created_at':time.time()}
            with LOCK:STATE[ident]=state
            POOL.submit(process_job,ident);return self.send_json(state,202)
        except (ValueError,TypeError,json.JSONDecodeError) as e:return self.send_json({'error':'点云格式或参数无效：'+str(e)},400)
        except Exception as e:return self.send_json({'error':str(e)},500)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=8765);args=parser.parse_args()
    print(f'BuildingWorld local: http://127.0.0.1:{args.port} | engine {engine.VERSION}',flush=True)
    ThreadingHTTPServer(('127.0.0.1',args.port),Handler).serve_forever()
