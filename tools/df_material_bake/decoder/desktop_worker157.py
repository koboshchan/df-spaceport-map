import pathlib,subprocess,sys,json,datetime,os
R=pathlib.Path(__file__).parent
(R/"started157.json").write_text(json.dumps({"pid":os.getpid(),"utc":datetime.datetime.now(datetime.timezone.utc).isoformat()}))
with (R/"worker157.log").open("a") as log:
    code=subprocess.call([sys.executable,"-m","unittest","-v","test_decoder"],cwd=R,stdout=log,stderr=log)
    if code==0:code=subprocess.call([sys.executable,str(R/"run_pilot.py"),"E:/df-v25-build-20261106/material-work/raw-graph-probe/decoded","E:/df-v25-build-20261106/material-work/raw-graph-probe/payload-receipt.json"],cwd=R,stdout=log,stderr=log)
(R/"exit157.json").write_text(json.dumps({"code":code,"utc":datetime.datetime.now(datetime.timezone.utc).isoformat()}))
sys.exit(code)
