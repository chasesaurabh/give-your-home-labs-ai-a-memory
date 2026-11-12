"""Recalculate mechanical study summaries from retained synthetic responses.

No model call and no automatic semantic grading. Manual fact-recovery counts
are labeled separately and are not whole-answer accuracy or a safety score.
"""
from pathlib import Path
from collections import Counter
import argparse,hashlib,json,re,statistics

DEFAULT=Path(__file__).resolve().parents[1]/'experiments/memory-study-2026-11-12'

def read_lines(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()]

def summarize(root):
    root=root.resolve()
    manifest=json.loads((root/'SHA256.json').read_text(encoding='utf-8'))
    for item in manifest['files']:
        path=(root/item['path']).resolve()
        if not path.is_relative_to(root):raise ValueError('Manifest path leaves the dataset.')
        raw=path.read_bytes()
        if len(raw)!=item['bytes'] or hashlib.sha256(raw).hexdigest()!=item['sha256']:
            raise ValueError(f'Evidence differs from manifest: {item["path"]}')
    prepared=json.loads((root/'prepared.json').read_text(encoding='utf-8'))
    requests={(r['case_id'],r['condition']):r for r in prepared['requests']}
    if len(requests)!=96:raise ValueError('Expected32cases in three conditions.')
    selected=[r for r in requests.values() if r['condition']=='selected' and r['required_ids']]
    complete=sum(set(r['required_ids'])<=set(r['selected_ids']) for r in selected)
    annotations=json.loads((root/'case-annotations.json').read_text(encoding='utf-8'))['annotations']
    sensitivity_plan=json.loads((root/'sensitivity-prepared.json').read_text(encoding='utf-8'))
    result=dict(scope='Observed synthetic study. Timing and ID membership are mechanical; neither proves factual support.',
        verified_payloads=len(manifest['files']),
        retrieval=dict(all_required_records_supplied=complete,fact_bearing_cases=len(selected),absent_fact_cases_excluded=4),
        baseline={},sensitivity={})
    for profile in ('2b','9b','27b','122b'):
        rows=read_lines(root/f'baseline/{profile}.jsonl')
        keys=[(r['case_id'],r['condition']) for r in rows]
        if len(keys)!=96 or set(keys)!=set(requests):raise ValueError(f'Incomplete/duplicate baseline: {profile}')
        for row in rows:
            planned=requests[(row['case_id'],row['condition'])]
            if row['request']['messages']!=planned['messages']:raise ValueError('Request differs from frozen messages.')
            if row['selected_ids']!=planned['selected_ids']:raise ValueError('Selected IDs differ from frozen plan.')
            if row['request']['model']!='memory-'+profile:raise ValueError('Unexpected model alias.')
        conditions={}
        for condition in ('none','selected','oracle'):
            subset=[r for r in rows if r['condition']==condition]
            invalid=[]
            for row in subset:
                choices=row.get('response',{}).get('choices',[])
                answer=choices[0]['message'].get('content','') if choices else ''
                cited=set(re.findall(r'\[memory:\s*([^\]]+?)\s*\]',answer or '',re.I))
                if cited-set(row['selected_ids']):invalid.append(row['case_id'])
            labels=[r for r in annotations if r['profile']==profile and r['condition']==condition]
            if len(labels)!=32 or any(type(r['requested_fact_recovered']) is not bool for r in labels):
                raise ValueError('Incomplete case annotations.')
            conditions[condition]=dict(requests=len(subset),
                statuses=dict(Counter(r['status'] for r in subset)),
                finish_reasons=dict(Counter(r.get('response',{}).get('choices',[{}])[0].get('finish_reason') for r in subset)),
                median_complete_request_seconds=statistics.median(r['wall_seconds'] for r in subset),
                invalid_citation_answer_cases=invalid,
                manually_annotated_requested_fact_recovery=sum(r['requested_fact_recovered'] for r in labels),
                interpretation='Fact recovery can coexist with unsupported additions; read case annotations and original answers.')
        result['baseline'][profile]=conditions
        extra=read_lines(root/f'sensitivity/{profile}.jsonl')
        expected={(r['case']['case_id'],r['seed']) for r in sensitivity_plan['requests']}
        if len(extra)!=24 or {(r['case_id'],r['seed']) for r in extra}!=expected:
            raise ValueError('Incomplete sensitivity run.')
        result['sensitivity'][profile]=dict(requests=len(extra),seeds=sorted({r['seed'] for r in extra}),
            statuses=dict(Counter(r['status'] for r in extra)),
            finish_reasons=dict(Counter(r.get('response',{}).get('choices',[{}])[0].get('finish_reason') for r in extra)),
            interpretation='Post-baseline exploratory subset, not held out or a new overall ranking.')
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,default=DEFAULT)
    args=parser.parse_args()
    print(json.dumps(summarize(args.input),indent=2))
