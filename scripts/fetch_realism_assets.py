"""Fetch a bounded, hash-pinned Poly Haven kit for the realism comparison."""
import argparse
import hashlib
import json
from pathlib import Path
from urllib.request import Request, urlopen

def fetch(url):
    with urlopen(Request(url,headers={'User-Agent':'3D-Harness-Realism-Evaluation/0.3.1'}),timeout=60) as response:
        return response.read()

def main():
    p=argparse.ArgumentParser();p.add_argument('out');a=p.parse_args()
    root=Path(a.out);root.mkdir(parents=True,exist_ok=False)
    records=[]; metadata={}
    def save(asset,channel,record,destination):
        blob=fetch(record['url'])
        assert len(blob)==record['size'] and hashlib.md5(blob).hexdigest()==record['md5'],destination
        path=root/destination;path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('xb') as f:f.write(blob)
        records.append({'asset':asset,'channel':channel,'path':destination,'bytes':len(blob),
            'sha256':hashlib.sha256(blob).hexdigest(),'download':record['url'],
            'source':'https://polyhaven.com/a/'+asset,'license':'CC0'})
    for asset in ('red_brick','weathered_brown_planks','forest_ground_04','fern_02','kloofendal_48d_partly_cloudy'):
        info=json.loads(fetch('https://api.polyhaven.com/info/'+asset))
        files=json.loads(fetch('https://api.polyhaven.com/files/'+asset))
        metadata[asset]={'info':info,'files':files}
        if asset=='fern_02':
            rec=files['blend']['2k']['blend'];save(asset,'model',rec,asset+'/fern_02_2k.blend')
            for relative,dependency in rec['include'].items():save(asset,relative,dependency,asset+'/'+relative)
        elif asset=='kloofendal_48d_partly_cloudy':
            rec=files['hdri']['2k']['hdr'];save(asset,'hdri',rec,asset+'/'+rec['url'].rsplit('/',1)[1])
        else:
            for channel in ('Diffuse','Rough','nor_gl','Displacement'):
                choices=files[channel]['2k'];ext='jpg' if 'jpg' in choices else 'png' if 'png' in choices else 'exr'
                rec=choices[ext];save(asset,channel,rec,asset+'/'+rec['url'].rsplit('/',1)[1])
    (root/'metadata.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
    (root/'manifest.json').write_text(json.dumps({'provider':'Poly Haven','license_url':'https://polyhaven.com/license',
        'api_terms':'https://github.com/Poly-Haven/Public-API/blob/master/ToS.md','files':records},indent=2),encoding='utf-8')
    print('PINNED_ASSETS',len(records),sum(r['bytes'] for r in records))

if __name__=='__main__':main()
