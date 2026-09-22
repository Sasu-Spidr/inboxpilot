#!/usr/bin/env bash
set -Eeuo pipefail

required=(
  DOCKER_CONTEXT DEPLOY_ENVIRONMENT COMPOSE_PROJECT COMPOSE_OVERLAY IMAGE_TAG
  BAO_ADDR FRONTEND_BASE_URL OAUTH_BASE_URL OAUTH_PUBLIC_URL
)
for name in "${required[@]}"; do
  if [[ -z "${!name:-}" ]]; then
    echo "Missing required deployment variable: $name" >&2
    exit 65
  fi
done

if [[ "$DEPLOY_ENVIRONMENT" == "dev" && -z "${TRAEFIK_BASIC_AUTH_HASH:-}" ]]; then
  echo "Missing required dev variable: TRAEFIK_BASIC_AUTH_HASH" >&2
  exit 65
fi

export INBOXPILOT_BOOTSTRAP_ROOT="/etc/inboxpilot/$DEPLOY_ENVIRONMENT"
export TURNSTILE_SITE_KEY="${TURNSTILE_SITE_KEY:-}"
export PUBLIC_SIGNUP_ENABLED="${PUBLIC_SIGNUP_ENABLED:-false}"
export ADMIN_MFA_REQUIRED="${ADMIN_MFA_REQUIRED:-true}"
export LOGIN_RATE_LIMIT_15M="${LOGIN_RATE_LIMIT_15M:-6}"
export REGISTER_RATE_LIMIT_1H="${REGISTER_RATE_LIMIT_1H:-3}"
export SESSION_MAX_AGE_SECONDS="${SESSION_MAX_AGE_SECONDS:-86400}"

compose() {
  docker --context "$DOCKER_CONTEXT" compose \
    -p "$COMPOSE_PROJECT" \
    -f docker-compose.yml \
    -f "$COMPOSE_OVERLAY" \
    "$@"
}

container_id() {
  compose ps -q "$1"
}

wait_healthy() {
  local service="$1"
  local timeout_seconds="${2:-180}"
  local deadline=$((SECONDS + timeout_seconds))
  local id status

  while (( SECONDS < deadline )); do
    id="$(container_id "$service")"
    if [[ -n "$id" ]]; then
      status="$(docker --context "$DOCKER_CONTEXT" inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$id" 2>/dev/null || true)"
      case "$status" in
        healthy) echo "$service is healthy."; return 0 ;;
        unhealthy|exited|dead) echo "$service entered state $status." >&2; return 1 ;;
      esac
    fi
    sleep 5
  done

  echo "Timed out waiting for $service to become healthy." >&2
  return 1
}

deploy_tag() {
  local tag="$1"
  export IMAGE_TAG="$tag"

  # OpenBao agents must be ready before any secret-consuming service starts.
  compose up -d --pull always bao-agent-frontend bao-agent-worker || return 1
  wait_healthy bao-agent-frontend 180 || return 1
  wait_healthy bao-agent-worker 180 || return 1

  compose up -d --pull always || return 1
  wait_healthy mail-agent 180 || return 1
  wait_healthy oauth-onboarding 180 || return 1
  wait_healthy frontend 180 || return 1
}

frontend_id="$(container_id frontend)"
if [[ -z "$frontend_id" ]]; then
  echo "Cannot determine the currently deployed frontend; rollback target is unknown." >&2
  exit 69
fi

previous_image="$(docker --context "$DOCKER_CONTEXT" inspect --format '{{.Config.Image}}' "$frontend_id")"
previous_tag="${previous_image##*:}"
if [[ -z "$previous_tag" || "$previous_tag" == "$previous_image" ]]; then
  echo "Cannot extract the previous immutable image tag." >&2
  exit 69
fi

target_tag="$IMAGE_TAG"
echo "Deploying immutable image tag $target_tag to project $COMPOSE_PROJECT."
if deploy_tag "$target_tag"; then
  echo "Deployment completed and all application services are healthy."
  exit 0
fi

echo "Deployment failed; rolling project $COMPOSE_PROJECT back to its previous image tag." >&2
if ! deploy_tag "$previous_tag"; then
  echo "Rollback to the previous image tag also failed; manual intervention is required." >&2
  exit 70
fi

echo "Rollback completed successfully; the requested deployment remains failed." >&2
exit 1
