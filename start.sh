#!/usr/bin/env bash

set -euo pipefail

cleanup_done=0

cleanup_falkordb() {
  echo "Checking for orphaned FalkorDB containers..."
  local falkor_containers=$(docker ps -a --filter "ancestor=falkordb/falkordb-server" --filter "ancestor=falkordb/falkordb-browser" -q 2>/dev/null)
  if [[ -n "$falkor_containers" ]]; then
    echo "Stopping and removing orphaned FalkorDB containers..."
    docker stop $falkor_containers 2>/dev/null || true
    docker rm -v $falkor_containers 2>/dev/null || true
  fi
}

cleanup() {
  if [[ "$cleanup_done" -eq 1 ]]; then
    return 0
  fi
  cleanup_done=1
  

  trap '' SIGINT SIGTERM
  
  echo ""
  echo "--- Stopping and cleaning up ---"
  
  if ! docker compose down -v --remove-orphans --rmi local; then
    echo "Standard cleanup failed, attempting forced stop..."
    docker compose stop -t 0 2>/dev/null || true
    docker compose kill 2>/dev/null || true
    docker compose rm -f -v 2>/dev/null || true
  fi

  cleanup_falkordb

  docker image prune -f >/dev/null 2>&1 || true
  docker rmi -f smart_finance_agent-app:latest 2>/dev/null || true
  
  echo "Cleanup complete."
  exit 0
}

trap cleanup SIGINT SIGTERM

echo "Performing initial cleanup..."
docker compose down -v --remove-orphans --rmi local 2>/dev/null || true
cleanup_falkordb
docker image prune -f 


docker rmi -f smart_finance_agent-app:latest 2>/dev/null || true

echo "Building and starting services..."
docker compose up -d --build


docker image prune -f

echo "Application Start!"
echo "Following logs from all containers (Ctrl+C to stop and cleanup)..."

docker compose logs -f