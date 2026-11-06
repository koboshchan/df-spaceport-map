import json,pathlib,sys,datetime,traceback
from decoder import decode_payload
R=pathlib.Path(__file__).parent
def run():
    source=pathlib.Path(sys.argv[1]); receipt=pathlib.Path(sys.argv[2])
    rows=json.loads(receipt.read_text())
    results=[]
    for row in rows:
        p=source/(str(row["index"])+".bin")
        if not p.exists() or "decodedSHA256" not in row: continue
        try:
            d=decode_payload(p.read_bytes(),row["dxbcOffset"],row["decodedSHA256"])
            d["upstreamReceipt"]={k:row[k] for k in ("index","hash","archiveOffset","size","uncompressedSize","method") if k in row}
            results.append(d)
        except Exception as e:
            results.append({"index":row["index"],"status":"REJECTED","reason":str(e)})
    (R/"pilot-results.json").write_text(json.dumps(results,indent=2))
    print(json.dumps({"examined":len(results),"partialFraming":sum(x.get("status")=="PARTIAL_FRAMING_VERIFIED" for x in results),"rejected":sum(x.get("status")=="REJECTED" for x in results)}),flush=True)
if __name__=="__main__":
    try: run()
    except Exception: traceback.print_exc();sys.exit(1)
