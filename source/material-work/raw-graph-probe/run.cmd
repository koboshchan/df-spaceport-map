@echo off
cd /d E:\df-v25-build-20261106\material-work\raw-graph-probe
dotnet bin\Release\net10.0\RawProbe.dll > run.log 2>&1
echo %errorlevel% > exit-code.txt
