#!/usr/bin/env python3
"""Refresh public USI publication metadata from ORCID and Crossref.
No third-party Python packages required.
"""
from __future__ import annotations
import json, os, time, urllib.request, urllib.parse
from datetime import datetime, timezone
from pathlib import Path

ORCID = os.environ.get('ORCID_ID', '0000-0002-9507-1279')
OUT = Path(__file__).resolve().parents[1] / 'publications.json'
UA = 'USI-Urban-Systems-Intelligence/1.0 (mailto:sbharule@arp.iitkgp.ac.in)'

def get_json(url, accept='application/json'):
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': accept})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode('utf-8'))

def orcid_works():
    data = get_json(f'https://pub.orcid.org/v3.0/{ORCID}/works', 'application/vnd.orcid+json')
    rows=[]
    for group in data.get('group', []):
        ext=[]
        for ei in group.get('external-ids', {}).get('external-id', []):
            typ=(ei.get('external-id-type') or '').lower()
            val=ei.get('external-id-value')
            if typ and val: ext.append((typ,val))
        summary=(group.get('work-summary') or [{}])[0]
        title=((summary.get('title') or {}).get('title') or {}).get('value')
        year=(((summary.get('publication-date') or {}).get('year') or {}).get('value'))
        typ=summary.get('type')
        url=((summary.get('url') or {}).get('value'))
        rows.append({'title':title,'year':year,'type':typ,'url':url,'external_ids':ext})
    return rows

def crossref(doi):
    try:
        msg=get_json('https://api.crossref.org/works/'+urllib.parse.quote(doi, safe=''))['message']
    except Exception:
        return None
    title=(msg.get('title') or [None])[0]
    authors=[]
    for a in msg.get('author', []) or []:
        name=' '.join(x for x in [a.get('given'),a.get('family')] if x)
        if name: authors.append(name)
    year=None
    for key in ('published-print','published-online','issued','created'):
        dp=((msg.get(key) or {}).get('date-parts') or [])
        if dp and dp[0]: year=dp[0][0]; break
    venue=(msg.get('container-title') or [None])[0] or msg.get('publisher')
    return {'title':title,'authors':authors,'year':year,'venue':venue,'type':msg.get('type'),'doi':msg.get('DOI') or doi,'url':msg.get('URL') or f'https://doi.org/{doi}'}

def main():
    pubs=[]; seen=set()
    for work in orcid_works():
        ids=dict(work['external_ids'])
        doi=ids.get('doi')
        enriched=crossref(doi) if doi else None
        if enriched:
            item=enriched
        else:
            item={'title':work['title'],'authors':[],'year':work['year'],'venue':None,'type':work['type'],'doi':doi,'url':work['url'] or (f'https://doi.org/{doi}' if doi else None)}
        key=(item.get('doi') or item.get('title') or '').lower()
        if not key or key in seen: continue
        seen.add(key); pubs.append(item)
        time.sleep(0.08)
    pubs.sort(key=lambda p:(str(p.get('year') or ''), p.get('title') or ''), reverse=True)
    payload={'source':'ORCID + Crossref','orcid':ORCID,'generated_at':datetime.now(timezone.utc).isoformat(),'count':len(pubs),'publications':pubs}
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(f'Wrote {len(pubs)} works to {OUT}')

if __name__=='__main__':
    main()
