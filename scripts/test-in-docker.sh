#!/usr/bin/env bash
set -euo pipefail

IMAGE_PREFIX=${IMAGE_PREFIX:-transloadit-python-sdk-dev}
CACHE_ROOT=${CACHE_ROOT:-.docker-cache}
POETRY_CACHE_DIR="$CACHE_ROOT/pypoetry"
PIP_CACHE_DIR="$CACHE_ROOT/pip"
NPM_CACHE_DIR="$CACHE_ROOT/npm"
HOME_DIR="$CACHE_ROOT/home"
DEFAULT_MATRIX=("3.9" "3.10" "3.11" "3.12" "3.13")
declare -a PYTHON_MATRIX=()
declare -a CUSTOM_COMMAND=()

usage() {
  cat <<'EOF'
Usage: scripts/test-in-docker.sh [options] [-- command ...]

Options:
  -p, --python VERSION   Only run for the given Python version (repeatable)
  -h, --help             Show this help

Environment:
  PYTHON_VERSIONS        Space-separated Python versions to run (default CI matrix)
  SKIP_POETRY_RUN        Set to 1 to run the custom command without "poetry run"
  IMAGE_NAME             Override the Docker image name prefix
  CACHE_ROOT             Override the cache directory (default: .docker-cache)

Examples:
  scripts/test-in-docker.sh
  scripts/test-in-docker.sh --python 3.12
  scripts/test-in-docker.sh -- pytest tests/test_client.py
  SKIP_POETRY_RUN=1 scripts/test-in-docker.sh -- python -m pytest -k smartcdn
EOF
}

ensure_docker() {
  if ! command -v docker >/dev/null 2>&1; then
    echo "Docker is required to run this script." >&2
    exit 1
  fi

  if ! docker info >/dev/null 2>&1; then
    if [[ -z "${DOCKER_HOST:-}" && -S "$HOME/.colima/default/docker.sock" ]]; then
      export DOCKER_HOST="unix://$HOME/.colima/default/docker.sock"
    fi
  fi

  if ! docker info >/dev/null 2>&1; then
    echo "Docker daemon is not reachable. Start Docker (or Colima) and retry." >&2
    exit 1
  fi
}

configure_platform() {
  if [[ -z "${DOCKER_PLATFORM:-}" ]]; then
    local arch
    arch=$(uname -m)
    if [[ "$arch" == "arm64" || "$arch" == "aarch64" ]]; then
      DOCKER_PLATFORM=linux/amd64
    fi
  fi
}

parse_python_versions() {
  local -a cli_versions=()
  local -a custom_cmd=()

  while [[ $# -gt 0 ]]; do
    case "$1" in
      -p|--python)
        if [[ $# -lt 2 ]]; then
          echo "Missing value for $1" >&2
          exit 1
        fi
        cli_versions+=("$2")
        shift 2
        ;;
      --python=*)
        cli_versions+=("${1#*=}")
        shift
        ;;
      -h|--help)
        usage
        exit 0
        ;;
      --)
        shift
        custom_cmd=("$@")
        break
        ;;
      *)
        custom_cmd+=("$1")
        shift
        ;;
    esac
  done

  if [[ ${#cli_versions[@]} -gt 0 ]]; then
    PYTHON_MATRIX=("${cli_versions[@]}")
  elif [[ -n "${PYTHON_VERSIONS:-}" ]]; then
    read -r -a PYTHON_MATRIX <<< "$PYTHON_VERSIONS"
  else
    PYTHON_MATRIX=("${DEFAULT_MATRIX[@]}")
  fi

  if [[ ${#PYTHON_MATRIX[@]} -eq 0 ]]; then
    PYTHON_MATRIX=("${DEFAULT_MATRIX[@]}")
  fi

  CUSTOM_COMMAND=("${custom_cmd[@]}")
}

build_image_for_version() {
  local version=$1
  local image_name=$2

  local -a build_args=()
  if [[ -n "${DOCKER_PLATFORM:-}" ]]; then
    build_args+=(--platform "$DOCKER_PLATFORM")
  fi
  build_args+=(-t "$image_name" --build-arg "PYTHON_VERSION=$version" -f Dockerfile .)

  echo "==> Building image $image_name (Python $version)"
  docker build "${build_args[@]}"
}

run_for_version() {
  local version=$1
  local image_name=$2

  local -a docker_args=(
    --rm
    --user "$(id -u):$(id -g)"
    -v "$PWD":/workspace
    -w /workspace
  )

  if [[ -n "${DOCKER_PLATFORM:-}" ]]; then
    docker_args+=(--platform "$DOCKER_PLATFORM")
  fi

  mkdir -p "$POETRY_CACHE_DIR" "$PIP_CACHE_DIR" "$NPM_CACHE_DIR" "$HOME_DIR"

  local container_home="/workspace/$HOME_DIR"
  docker_args+=(
    -e "HOME=$container_home"
    -e "PIP_CACHE_DIR=/workspace/$PIP_CACHE_DIR"
    -e "POETRY_CACHE_DIR=/workspace/$POETRY_CACHE_DIR"
    -e "NPM_CONFIG_CACHE=/workspace/$NPM_CACHE_DIR"
    -e "PYTHON_VERSION_UNDER_TEST=$version"
    -v "$PWD/$POETRY_CACHE_DIR":/workspace/"$POETRY_CACHE_DIR"
    -v "$PWD/$PIP_CACHE_DIR":/workspace/"$PIP_CACHE_DIR"
    -v "$PWD/$NPM_CACHE_DIR":/workspace/"$NPM_CACHE_DIR"
    -v "$PWD/$HOME_DIR":/workspace/"$HOME_DIR"
  )

  if [[ -f .env ]]; then
    docker_args+=(--env-file "$PWD/.env")
  fi

  local -a passthrough_envs=(TRANSLOADIT_KEY TRANSLOADIT_SECRET TRANSLOADIT_TEMPLATE_ID PYTHON_SDK_E2E)
  for var in "${passthrough_envs[@]}"; do
    if [[ -n "${!var:-}" ]]; then
      docker_args+=(-e "$var=${!var}")
    fi
  done

  if [[ "$version" == "3.12" && ${#CUSTOM_COMMAND[@]} -eq 0 ]]; then
    docker_args+=(-e TEST_NODE_PARITY=1)
  fi

  local run_cmd
  if [[ ${#CUSTOM_COMMAND[@]} -gt 0 ]]; then
    printf -v user_cmd '%q ' "${CUSTOM_COMMAND[@]}"
    if [[ "${SKIP_POETRY_RUN:-0}" == "1" ]]; then
      run_cmd="set -euo pipefail; poetry install; ${user_cmd}"
    else
      run_cmd="set -euo pipefail; poetry install; poetry run ${user_cmd}"
    fi
  else
    if [[ "$version" == "3.12" ]]; then
      run_cmd='set -euo pipefail; poetry install; poetry run pytest --cov=transloadit --cov-report=xml --cov-report=json --cov-report=html --cov-report=term-missing --cov-fail-under=65 tests'
    else
      run_cmd='set -euo pipefail; poetry install; poetry run pytest tests'
    fi
  fi

  echo "==> Running Python $version: $run_cmd"
  docker run "${docker_args[@]}" "$image_name" bash -lc "$run_cmd"
}

main() {
  parse_python_versions "$@"
  ensure_docker
  configure_platform

  mkdir -p "$CACHE_ROOT"

  for version in "${PYTHON_MATRIX[@]}"; do
    image_name="${IMAGE_NAME:-$IMAGE_PREFIX}-${version//./}"
    build_image_for_version "$version" "$image_name"
    run_for_version "$version" "$image_name"
  done
}

main "$@"
