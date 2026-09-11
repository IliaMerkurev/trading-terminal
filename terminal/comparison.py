"""Compare saved semantics and versions, not just a headline return."""
from terminal.data import digest


def flatten(value,prefix=''):
    if isinstance(value,dict):
        result={}
        for key,item in value.items():result.update(flatten(item,f'{prefix}.{key}' if prefix else key))
        return result
    return {prefix:value}


def compare_runs(store,run_ids):
    if not isinstance(run_ids,list) or not 2<=len(run_ids)<=8 or len(set(run_ids))!=len(run_ids):
        raise ValueError('Select two to eight different completed runs')
    rows=[];contracts=[]
    for run_id in run_ids:
        run=store.get(run_id)
        if run['status']!='completed':raise ValueError('Only completed results can be compared')
        summary=run['summary'];manifest=run['manifest']
        contract={'strategy_sha256':digest(manifest['strategy']),'profile':manifest['profile'],
                  'dataset':manifest['dataset'],'runtime':manifest['runtime'],'metric_version':summary['metric_version'],
                  'engine':summary['engine'],'engine_version':summary['engine_version']}
        if 'research' in manifest:contract['research']=manifest['research']
        contracts.append(flatten(contract))
        rows.append({'id':run_id,'created_at':run['created_at'],'summary':summary,'strategy_sha256':contract['strategy_sha256']})
    keys=sorted(set().union(*(c.keys() for c in contracts)))
    differences=[{'field':key,'values':[c.get(key) for c in contracts]} for key in keys if any(c.get(key)!=contracts[0].get(key) for c in contracts[1:])]
    return {'runs':rows,'differences':differences,'same_contract':not differences,
            'note':'Matching metadata is not an independent correctness check. Imported results are not re-executed or authenticated by this application.'}
