#!/usr/bin/env sh
set -eu

if [ "$#" -ne 2 ]; then
  echo "Usage: $0 <compose-project> <absolute-legacy-root>" >&2
  exit 64
fi

project="$1"
legacy_root="${2%/}"

case "$legacy_root" in
  /*) ;;
  *)
    echo "The legacy root must be an absolute path on the Docker host." >&2
    exit 64
    ;;
esac

data_source="$legacy_root/data"
logs_source="$legacy_root/logs"
data_volume="${project}_inboxpilot_data"
logs_volume="${project}_inboxpilot_logs"

for source_dir in "$data_source" "$logs_source"; do
  if ! docker run --rm -v /:/host:ro alpine:3.20 test -d "/host$source_dir"; then
    echo "Missing source directory on the Docker host: $source_dir" >&2
    exit 66
  fi
done

docker volume create "$data_volume" >/dev/null
docker volume create "$logs_volume" >/dev/null

for volume in "$data_volume" "$logs_volume"; do
  if ! docker run --rm -v "$volume:/target" alpine:3.20 sh -c '[ -z "$(ls -A /target)" ]'; then
    echo "Refusing to overwrite non-empty volume: $volume" >&2
    exit 73
  fi
done

containers="$(docker ps -q \
  --filter "label=com.docker.compose.project=$project" \
  --filter "label=com.docker.compose.service=frontend" \
  --filter "label=com.docker.compose.service=mail-agent" \
  --filter "label=com.docker.compose.service=oauth-onboarding")"

restore_legacy_containers() {
  if [ -n "$containers" ]; then
    docker start $containers >/dev/null 2>&1 || true
  fi
}
trap restore_legacy_containers HUP INT TERM EXIT

if [ -n "$containers" ]; then
  docker stop $containers >/dev/null
fi

copy_and_verify() {
  source_dir="$1"
  volume="$2"
  docker run --rm \
    -v "$source_dir:/source:ro" \
    -v "$volume:/target" \
    alpine:3.20 sh -c 'cp -a /source/. /target/'

  docker run --rm \
    -v "$source_dir:/source:ro" \
    -v "$volume:/target:ro" \
    alpine:3.20 diff -qr /source /target >/dev/null
}

if ! copy_and_verify "$data_source" "$data_volume"; then
  restore_legacy_containers
  exit 74
fi

if ! copy_and_verify "$logs_source" "$logs_volume"; then
  restore_legacy_containers
  exit 74
fi

trap - HUP INT TERM EXIT
echo "State copied to $data_volume and $logs_volume."
echo "Start the image-based stack now; legacy application containers remain stopped."
