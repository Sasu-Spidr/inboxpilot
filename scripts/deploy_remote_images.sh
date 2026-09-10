#!/usr/bin/env sh
set -eu

environment="${1:-}"
case "$environment" in
  dev)
    project="spidr-mail-dev"
    legacy_root="/opt/spidr-mail-dev"
    override="docker-compose.dev.yml"
    frontend_container="spidr-mail-dev-frontend-1"
    ;;
  prod)
    project="spidr-mail"
    legacy_root="/opt/spidr-mail"
    override="docker-compose.prod.yml"
    frontend_container=""
    ;;
  *)
    echo "Usage: $0 <dev|prod>" >&2
    exit 64
    ;;
esac

required="VPS_HOST VPS_USER VPS_SSH_PORT IMAGE_TAG GHCR_TOKEN GHCR_USER FRONTEND_BASE_URL OAUTH_BASE_URL OAUTH_PUBLIC_URL BAO_ADDR"
for name in $required; do
  eval "value=\${$name:-}"
  if [ -z "$value" ]; then
    echo "Missing required variable: $name" >&2
    exit 65
  fi
done

repo_root="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
runtime_env="$repo_root/.env"
if [ -e "$runtime_env" ]; then
  echo "Refusing to overwrite $runtime_env" >&2
  exit 73
fi

ssh_target="$VPS_USER@$VPS_HOST"
ssh_cmd="ssh -p $VPS_SSH_PORT $ssh_target"
deployment_succeeded=false

cleanup_and_rollback() {
  status=$?
  rm -f "$runtime_env"
  if [ "$status" -ne 0 ] && [ "$deployment_succeeded" != true ]; then
    echo "Deployment failed; restoring the legacy $environment stack." >&2
    $ssh_cmd "cd '$legacy_root' && docker compose up -d --remove-orphans" >/dev/null 2>&1 || true
  fi
  exit "$status"
}
trap cleanup_and_rollback EXIT HUP INT TERM

$ssh_cmd "test -s '$legacy_root/.env' && cat '$legacy_root/.env'" > "$runtime_env"
chmod 600 "$runtime_env"

set_runtime_value() {
  key="$1"
  value="$2"
  escaped="$(printf '%s' "$value" | sed "s/'/'\\\\''/g")"
  sed -i "/^${key}=/d" "$runtime_env"
  printf "%s='%s'\n" "$key" "$escaped" >> "$runtime_env"
}

set_runtime_value IMAGE_TAG "$IMAGE_TAG"
set_runtime_value FRONTEND_BASE_URL "$FRONTEND_BASE_URL"
set_runtime_value OAUTH_BASE_URL "$OAUTH_BASE_URL"
set_runtime_value OAUTH_PUBLIC_URL "$OAUTH_PUBLIC_URL"
set_runtime_value BAO_ADDR "$BAO_ADDR"
set_runtime_value INBOXPILOT_BOOTSTRAP_ROOT "/etc/inboxpilot/$environment"

if [ "$environment" = dev ]; then
  basic_auth_hash="$($ssh_cmd "docker inspect --format '{{ index .Config.Labels \"traefik.http.middlewares.inboxpilot-dev-auth.basicauth.users\" }}' '$frontend_container'")"
  if [ -z "$basic_auth_hash" ]; then
    echo "Unable to recover the existing dev basic-auth hash." >&2
    exit 69
  fi
  set_runtime_value TRAEFIK_BASIC_AUTH_HASH "$basic_auth_hash"
fi

printf '%s' "$GHCR_TOKEN" | docker login ghcr.io --username "$GHCR_USER" --password-stdin >/dev/null
export DOCKER_HOST="ssh://$VPS_USER@$VPS_HOST:$VPS_SSH_PORT"

sh "$repo_root/scripts/migrate_compose_state_to_volumes.sh" "$project" "$legacy_root"

docker compose --env-file "$runtime_env" -p "$project" \
  -f "$repo_root/docker-compose.yml" -f "$repo_root/$override" pull
docker compose --env-file "$runtime_env" -p "$project" \
  -f "$repo_root/docker-compose.yml" -f "$repo_root/$override" \
  up -d --pull never --wait --wait-timeout 180

docker run --rm -v "${project}_inboxpilot_data:/data:ro" alpine:3.20 \
  sh -c 'test -d /data/tokens && test -d /data/state'

deployment_succeeded=true
trap - EXIT HUP INT TERM
rm -f "$runtime_env"
echo "$environment deployment completed with image tag $IMAGE_TAG."
