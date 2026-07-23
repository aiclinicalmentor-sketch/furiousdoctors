$ErrorActionPreference = "Stop"

$repo = "C:\Users\kjseu\Projects\furiousdoctors"
$python = "C:\Users\kjseu\AppData\Local\Python\pythoncore-3.14-64\python.exe"
$port = 8008

Set-Location $repo
& $python -m http.server $port --bind 127.0.0.1
