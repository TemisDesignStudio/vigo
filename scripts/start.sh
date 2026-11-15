#!/usr/bin/env sh
set -eu

project_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)

docker build --tag vigo:local "$project_root"
docker run --detach --name vigo --publish 8000:8000 --volume vigo-data:/data vigo:local
