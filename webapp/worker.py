"""One bounded reconstruction job, shared by web and batch callers."""
from pathlib import Path
import sys,json,traceback,time
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts/buildingworld')]
import pointcloud_to_mesh as engine
from validate_detail import validate

def run(directory):
    directory=Path(directory);cfg=json.loads((directory/'request.json').read_text(encoding='utf8'));start=time.time()
    source=Path(cfg.get('source',directory/'input.xyz'))
    model=engine.reconstruct(source,directory/'model.obj',ground_z=cfg.get('ground_z'),noise_mode=cfg.get('noise','conservative'))
    result={'status':'complete','seconds':time.time()-start,'algorithm_version':engine.VERSION,'topology':model['topology'],'noise':model['noise_diagnostics'],'official_metrics':model['official_metrics']}
    try:
        report,_=validate(model,model)
        report['gates']['all_footprint_components_retained']=model['discarded_footprint_area']<=.01
        report['gates']['resolved_partition_adjacency']=not model.get('unresolved_partition_edges')
        report['accepted']=all(report['gates'].values())
        (directory/'validation.json').write_text(json.dumps(report,indent=2),encoding='utf8')
        result.update(validation=report,accepted=report['accepted'])
    except Exception as e:
        result.update(accepted=False,validation_error=str(e))
        (directory/'validation_error.txt').write_text(traceback.format_exc(),encoding='utf8')
    result['seconds']=time.time()-start
    (directory/'result.json').write_text(json.dumps(result,indent=2),encoding='utf8')
    return result

if __name__=='__main__':
    directory=Path(sys.argv[1])
    try:run(directory)
    except Exception as e:
        (directory/'result.json').write_text(json.dumps({'status':'failed','error':str(e),'error_type':type(e).__name__},indent=2),encoding='utf8')
        (directory/'failure.txt').write_text(traceback.format_exc(),encoding='utf8');raise
