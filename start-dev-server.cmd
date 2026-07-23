@echo off
cd /d C:\Users\kjseu\Projects\furiousdoctors
C:\Users\kjseu\AppData\Local\Python\pythoncore-3.14-64\python.exe -m http.server 8010 --bind 127.0.0.1 > .devserver.log 2> .devserver.err.log
