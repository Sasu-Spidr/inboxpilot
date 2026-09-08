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
secrets_source="$legacy_root/secrets"
data_volume="${project}_inboxpilot_data"
logs_volume="${project}_inboxpilot_logs"
secrets_volume="${project}_inboxpilot_runtime_secrets"

if docker volume inspect "$data_volume" >/dev/null 2>&1 && \
   docker volume inspect "$logs_volume" >/dev/null 2>&1 && \
   docker volume inspect "$secrets_volume" >/dev/null 2>&1 && \
   docker run --rm -v "$data_volume:/data:ro" alpine:3.20 \
     test -f /data/.inboxpilot-image-migration-complete; then
  # Older executions may have written the marker before these runtime
  # directories became mandatory. Repairing empty directories is safe and
  # keeps retries idempotent without overwriting migrated state.
  docker run --rm -v "$data_volume:/data" alpine:3.20 \
    mkdir -p /data/tokens /data/state
  echo "Migration already completed for $project."
  exit 0
fi

for source_dir in "$data_source" "$logs_source" "$secrets_source"; do
  if ! docker run --rm -v /:/host:ro alpine:3.20 test -d "/host$source_dir"; then
    echo "Missing source directory on the Docker host: $source_dir" >&2
    exit 66
  fi
done

docker volume create \
  --label "com.docker.compose.project=$project" \
  --label "com.docker.compose.volume=inboxpilot_data" \
  "$data_volume" >/dev/null
docker volume create \
  --label "com.docker.compose.project=$project" \
  --label "com.docker.compose.volume=inboxpilot_logs" \
  "$logs_volume" >/dev/null
docker volume create \
  --label "com.docker.compose.project=$project" \
  --label "com.docker.compose.volume=inboxpilot_runtime_secrets" \
  "$secrets_volume" >/dev/null

for volume in "$data_volume" "$logs_volume" "$secrets_volume"; do
  if ! docker run --rm -v "$volume:/target" alpine:3.20 sh -c '[ -z "$(ls -A /target)" ]'; then
    echo "Refusing to overwrite non-empty volume: $volume" >&2
    exit 73
  fi
done

containers="$(
  for service in frontend mail-agent oauth-onboarding; do
    docker ps -q \
      --filter "label=com.docker.compose.project=$project" \
      --filter "label=com.docker.compose.service=$service"
  done | sort -u
)"

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

if ! copy_and_verify "$secrets_source" "$secrets_volume"; then
  restore_legacy_containers
  exit 74
fi

docker run --rm -v "$data_volume:/data" alpine:3.20 sh -c \
  'mkdir -p /data/tokens /data/state && touch /data/.inboxpilot-image-migration-complete'

trap - HUP INT TERM EXIT
echo "State copied to $data_volume, $logs_volume and $secrets_volume."
echo "Start the image-based stack now; legacy application containers remain stopped."
