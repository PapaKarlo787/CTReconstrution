@echo off
del projs\*.tiff
3D2R.exe 1.stl 0.stl 3.stl 1.stl -o out.tiff 100 y 
move *.tiff projs
if "%~1" neq "" (
    python3 %1
)