import pathlib,subprocess,sys,json,datetime,os
R=pathlib.Path(__file__).parent
(R/"started.json").write_text(json.dumps({"pid":os.getpid(),"utc":datetime.datetime.now(datetime.timezone.utc).isoformat()}))
with (R/"worker.log").open("a") as log:
    code=subprocess.call([sys.executable,"-m","unittest","-v","test_decoder"],cwd=R,stdout=log,stderr=log)
    if code==0:code=subprocess.call([sys.executable,str(R/"run_pilot.py"),"E:/df-v24-research-20261106/shader-reversal/decoded","E:/df-v24-research-20261106/shader-reversal/payload-receipt.json"],cwd=R,stdout=log,stderr=log)
(R/"exit.json").write_text(json.dumps({"code":code,"utc":datetime.datetime.now(datetime.timezone.utc).isoformat()}))
sys.exit(code)
