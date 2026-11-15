$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot

docker build --tag vigo:local $projectRoot
docker run --detach --name vigo --publish 8000:8000 --volume vigo-data:/data vigo:local
