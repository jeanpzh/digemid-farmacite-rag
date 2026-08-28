#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
GPU_BACKEND="${GPU_BACKEND:-auto}"
PRINT_COMMAND=false
COMPOSE_ARGS=()

for argument in "$@"; do
    if [[ "$argument" == "--print-command" ]]; then
        PRINT_COMMAND=true
    else
        COMPOSE_ARGS+=("$argument")
    fi
done

detect_gpu_backend() {
    case "$GPU_BACKEND" in
        cpu)
            printf '%s\n' cpu
            ;;
        nvidia)
            printf '%s\n' nvidia
            ;;
        amd)
            printf '%s\n' amd
            ;;
        auto)
            if command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi -L >/dev/null 2>&1; then
                printf '%s\n' nvidia
            elif [[ -e /dev/kfd && -d /dev/dri ]]; then
                printf '%s\n' amd
            else
                printf '%s\n' cpu
            fi
            ;;
        *)
            printf 'Unsupported GPU_BACKEND: %s (use auto, cpu, nvidia, or amd)\n' "$GPU_BACKEND" >&2
            return 2
            ;;
    esac
}

GPU_BACKEND_SELECTED="$(detect_gpu_backend)"
COMPOSE_FILES=("-f" "$ROOT_DIR/docker-compose.yml")

case "$GPU_BACKEND_SELECTED" in
    nvidia)
        COMPOSE_FILES+=("-f" "$ROOT_DIR/docker-compose.gpu.yml")
        ;;
    amd)
        COMPOSE_FILES+=("-f" "$ROOT_DIR/docker-compose.amd.yml")
        ;;
    cpu)
        # CPU uses the base compose file without an override.
        ;;
esac

if [[ "$PRINT_COMMAND" == true ]]; then
    printf 'GPU backend: %s\n' "$GPU_BACKEND_SELECTED"
    printf 'Compose files:'
    printf ' %s' "${COMPOSE_FILES[@]}"
    printf '\n'
    exit 0
fi

command -v docker >/dev/null 2>&1 || {
    printf 'Docker is required but was not found in PATH.\n' >&2
    exit 1
}

if [[ -f "$ROOT_DIR/.env" ]]; then
    ENV_FILE="$ROOT_DIR/.env"
elif [[ -f "$ROOT_DIR/.env.example" ]]; then
    ENV_FILE="$ROOT_DIR/.env.example"
else
    printf 'Neither .env nor .env.example exists at %s.\n' "$ROOT_DIR" >&2
    exit 1
fi

printf 'Starting Archerfish with %s backend using %s\n' "$GPU_BACKEND_SELECTED" "$ENV_FILE"
cd "$ROOT_DIR"
exec docker compose --env-file "$ENV_FILE" "${COMPOSE_FILES[@]}" up -d --build --wait "${COMPOSE_ARGS[@]}"
