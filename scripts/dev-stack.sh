#!/usr/bin/env bash

set -u

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
make_command="${MAKE:-make}"
targets=(lab-payment lab-checkout backend frontend)
labels=(
  "payment lab service (8102)"
  "checkout lab service (8101)"
  "FastAPI backend (8000)"
  "Next.js frontend (3000)"
)
pids=()
cleaning_up=0

group_alive() {
  kill -0 -- "-$1" 2>/dev/null
}

cleanup() {
  local status=$?
  local attempts=0
  local any_alive=0
  local pid

  trap - EXIT INT TERM HUP
  if (( cleaning_up )); then
    exit "$status"
  fi
  cleaning_up=1

  if (( ${#pids[@]} == 0 )); then
    exit "$status"
  fi

  printf '\n[dev] Stopping TraceLens local services...\n'
  for pid in "${pids[@]}"; do
    kill -TERM -- "-$pid" 2>/dev/null || true
  done

  while (( attempts < 50 )); do
    any_alive=0
    for pid in "${pids[@]}"; do
      if group_alive "$pid"; then
        any_alive=1
        break
      fi
    done
    (( any_alive == 0 )) && break
    sleep 0.1
    (( attempts += 1 ))
  done

  for pid in "${pids[@]}"; do
    if group_alive "$pid"; then
      kill -KILL -- "-$pid" 2>/dev/null || true
    fi
  done
  for pid in "${pids[@]}"; do
    wait "$pid" 2>/dev/null || true
  done

  printf '[dev] TraceLens local stack stopped.\n'
  exit "$status"
}

trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM HUP

for index in "${!targets[@]}"; do
  target="${targets[$index]}"
  printf '[dev] Starting %s via make %s\n' "${labels[$index]}" "$target"
  python3 -c 'import os, sys; os.setsid(); os.execvp(sys.argv[1], sys.argv[1:])' \
    "$make_command" --no-print-directory -C "$repo_root" "$target" &
  pids+=("$!")
done

printf '[dev] All services launched. Press Ctrl+C to stop the stack.\n'

while :; do
  for index in "${!pids[@]}"; do
    pid="${pids[$index]}"
    if ! kill -0 "$pid" 2>/dev/null; then
      child_status=0
      wait "$pid" || child_status=$?
      printf '\n[dev] %s exited with status %d; stopping the stack.\n' \
        "${labels[$index]}" "$child_status"
      exit "$child_status"
    fi
  done
  sleep 0.5
done
