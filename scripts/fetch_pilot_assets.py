"""Download a fixed small Poly Haven kit; no open-ended search or generation."""
import argparse
import hashlib
import json
from pathlib import Path
from urllib.request import Request, urlopen

from dcc_harness.evidence import file_hash, write_json


def fetch(url):
    request = Request(url, headers={"User-Agent":"3D-Harness-Pilot/0.1 (local asset intake)"})
    with urlopen(request, timeout=60) as response:
        return response.read()


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("folder"); args = parser.parse_args()
    root = Path(args.folder); root.mkdir(parents=True,exist_ok=True)
    if (root / "manifest.json").exists():
        raise ValueError("Asset kit already pinned; verify it instead of replacing it")
    assets = []
    for name, channels in (("kloppenheim_06_puresky",[("hdri","hdr")]),
                           ("sandstone_blocks_05",[("Diffuse","jpg"),("Rough","jpg"),("nor_gl","jpg")])):
        metadata = json.loads(fetch("https://api.polyhaven.com/files/" + name))
        for channel, extension in channels:
            rec = metadata[channel]["1k"][extension]
            path = root / rec["url"].rsplit("/",1)[1]
            blob = fetch(rec["url"])
            if len(blob) != rec["size"] or hashlib.md5(blob).hexdigest() != rec["md5"]:
                raise ValueError(f"Asset integrity failed: {path.name}")
            with path.open("xb") as stream: stream.write(blob)
            assets.append({"asset":name,"channel":channel,"file":path.name,"source":f"https://polyhaven.com/a/{name}",
                           "download":rec["url"],"bytes":len(blob),"sha256":file_hash(path),"license":"CC0"})
    write_json(root / "manifest.json", {"provider":"Poly Haven","license_url":"https://polyhaven.com/license",
               "api_terms":"https://github.com/Poly-Haven/Public-API/blob/master/ToS.md","files":assets})
    print(json.dumps({"files":len(assets),"bytes":sum(a["bytes"] for a in assets)}))


if __name__ == "__main__": main()
