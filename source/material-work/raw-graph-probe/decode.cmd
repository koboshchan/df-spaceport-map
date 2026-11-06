@echo off
cd /d E:\df-v25-build-20261106\material-work\raw-graph-probe
python decode_priority.py > decode.log 2>&1
echo %errorlevel% > decode-exit.txt
