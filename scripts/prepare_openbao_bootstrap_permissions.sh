#!/usr/bin/env sh
set -eu

root="${1:-}"
if [ -z "$root" ]; then
  echo "Usage: $0 /etc/inboxpilot/<environment>" >&2
  exit 64
fi

case "$root" in
  /etc/inboxpilot/dev|/etc/inboxpilot/prod) ;;
  *) echo "Refusing unexpected bootstrap root: $root" >&2; exit 64 ;;
esac

for zone in frontend worker; do
  directory="$root/$zone"
  test -d "$directory"
  test -f "$directory/role_id"
  test -f "$directory/secret_id"

  chown 100:1000 "$directory" "$directory/role_id" "$directory/secret_id"
  chmod 0700 "$directory"
  chmod 0600 "$directory/role_id" "$directory/secret_id"
done

echo "OpenBao bootstrap permissions prepared for non-root agents in $root."
