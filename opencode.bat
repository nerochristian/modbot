@echo off
if "%~1"=="" (
    code .
) else (
    code %*
)
