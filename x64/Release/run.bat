@echo off
del projs\*.tiff
3D2R.exe 3.stl -o out.tiff 720 y
move *.tiff projs
if "%~1" neq "" (
    python3 %1
)