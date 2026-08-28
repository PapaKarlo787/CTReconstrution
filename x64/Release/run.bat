@echo off
del projs\*.tiff
3D2R.exe 0.stl 1.stl 0.stl -o out.tiff 720 y
move *.tiff projs
if "%~1" neq "" (
    python3 %1
)