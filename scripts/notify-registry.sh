#!/usr/bin/env bash
set -euo pipefail

IMAGE_NAME=${IMAGE_NAME:-transloadit-python-sdk-dev}
CACHE_ROOT=${CACHE_ROOT:-.docker-cache}
POETRY_CACHE_DIR="$CACHE_ROOT/pypoetry"
PIP_CACHE_DIR="$CACHE_ROOT/pip"
HOME_DIR="$CACHE_ROOT/home"

usage() {
  cat <<'EOF'
Usage: scripts/notify-registry.sh [options]

Options:
  --repository <pypi|test-pypi>   Publish to the chosen repository (default: pypi)
  --dry-run                       Build the package but skip publishing
  -h, --help                      Show this help text

Environment:
  PYPI_TOKEN          API token with upload rights for pypi.org (required for --repository pypi)
  PYPI_TEST_TOKEN     API token with upload rights for test.pypi.org (required for --repository test-pypi)
  These variables can optionally be defined in .env
EOF
}

err() {
  echo "notify-registry: $*" >&2
}

ensure_docker() {
  if ! command -v docker >/dev/null 2>&1; then
    err "Docker is required to run this script."
    exit 1
  fi

  if ! docker info >/dev/null 2>&1; then
    if [[ -z "${DOCKER_HOST:-}" && -S "$HOME/.colima/default/docker.sock" ]]; then
      export DOCKER_HOST="unix://$HOME/.colima/default/docker.sock"
    fi
  fi

  if ! docker info >/dev/null 2>&1; then
    err "Docker daemon is not reachable. Start Docker (or Colima) and retry."
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

run_outside_container() {
  ensure_docker
  configure_platform

  mkdir -p "$CACHE_ROOT" "$POETRY_CACHE_DIR" "$PIP_CACHE_DIR" "$HOME_DIR"

  local build_args=()
  if [[ -n "${DOCKER_PLATFORM:-}" ]]; then
    build_args+=(--platform "$DOCKER_PLATFORM")
  fi
  build_args+=(-t "$IMAGE_NAME" -f Dockerfile .)

  docker build "${build_args[@]}"

  local docker_args=(
    --rm
    --user "$(id -u):$(id -g)"
    -e HOME=/workspace/$HOME_DIR
    -e POETRY_CACHE_DIR=/workspace/$POETRY_CACHE_DIR
    -e PIP_CACHE_DIR=/workspace/$PIP_CACHE_DIR
    -v "$PWD":/workspace
    -v "$PWD/$POETRY_CACHE_DIR":/workspace/"$POETRY_CACHE_DIR"
    -v "$PWD/$PIP_CACHE_DIR":/workspace/"$PIP_CACHE_DIR"
    -v "$PWD/$HOME_DIR":/workspace/"$HOME_DIR"
    -w /workspace
  )

  if [[ -n "${DOCKER_PLATFORM:-}" ]]; then
    docker_args+=(--platform "$DOCKER_PLATFORM")
  fi

  if [[ -f .env ]]; then
    docker_args+=(--env-file "$PWD/.env")
  fi

  if [[ -n "${PYPI_TOKEN:-}" ]]; then
    docker_args+=(-e "PYPI_TOKEN=${PYPI_TOKEN}")
  fi
  if [[ -n "${PYPI_TEST_TOKEN:-}" ]]; then
    docker_args+=(-e "PYPI_TEST_TOKEN=${PYPI_TEST_TOKEN}")
  fi

  exec docker run "${docker_args[@]}" "$IMAGE_NAME" bash -lc "set -euo pipefail; scripts/notify-registry.sh --inside-container \"$@\""
}

load_env_var() {
  local var_name=$1
  if [[ -n "${!var_name:-}" ]]; then
    return 0
  fi

  if [[ -f .env ]]; then
    # shellcheck disable=SC1091
    source .env || err "Failed to source .env"
  fi
}

verify_repo_state() {
  if [[ -n "$(git status --porcelain)" ]]; then
    err "Git working tree is not clean. Commit or stash changes before publishing."
    exit 1
  fi
}

verify_versions_consistent() {
  local version python_version header_version
  version=$(poetry version -s)
  python_version=$(python -c "import transloadit; print(transloadit.__version__)")
  header_version=$(grep -oE 'python-sdk:[0-9]+\.[0-9]+\.[0-9]+' tests/test_request.py | tail -n1 | cut -d: -f2)

  if [[ "$version" != "$python_version" ]]; then
    err "Version mismatch: pyproject.toml=$version but transloadit/__init__.py=$python_version"
    exit 1
  fi
  if [[ "$version" != "$header_version" ]]; then
    err "Version mismatch: tests/test_request.py expects $header_version but pyproject.toml has $version"
    exit 1
  fi
  if ! grep -q "### ${version}/" CHANGELOG.md; then
    err "CHANGELOG.md does not contain an entry for ${version}"
    exit 1
  fi
}

publish_inside_container() {
  local repository="pypi"
  local dry_run=0

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --repository)
        if [[ $# -lt 2 ]]; then
          err "Missing value for --repository"
          exit 1
        fi
        repository=$2
        shift 2
        ;;
      --dry-run)
        dry_run=1
        shift
        ;;
      --inside-container)
        shift
        ;;
      -h|--help)
        usage
        exit 0
        ;;
      *)
        err "Unknown option: $1"
        usage
        exit 1
        ;;
    esac
  done

  case "$repository" in
    pypi|test-pypi) ;;
    *)
      err "Invalid repository '${repository}'. Expected 'pypi' or 'test-pypi'."
      exit 1
      ;;
  esac

  if [[ "$repository" == "pypi" ]]; then
    load_env_var "PYPI_TOKEN"
    if [[ -z "${PYPI_TOKEN:-}" ]]; then
      err "PYPI_TOKEN is not set. Export it or add it to .env before publishing."
      exit 1
    fi
    export POETRY_PYPI_TOKEN_PYPI="$PYPI_TOKEN"
  else
    load_env_var "PYPI_TEST_TOKEN"
    if [[ -z "${PYPI_TEST_TOKEN:-}" ]]; then
      err "PYPI_TEST_TOKEN is not set. Export it or add it to .env before publishing to test-pypi."
      exit 1
    fi
    export POETRY_PYPI_TOKEN_TEST_PYPI="$PYPI_TEST_TOKEN"
    poetry config repositories.test-pypi https://test.pypi.org/legacy/ >/dev/null
  fi

  verify_repo_state
  verify_versions_consistent

  rm -rf dist
  poetry build

  if [[ "$dry_run" == "1" ]]; then
    err "Dry run complete. Built artifacts in dist/ but skipped publishing."
    exit 0
  fi

  if [[ "$repository" == "pypi" ]]; then
    poetry publish --no-interaction --no-ansi
    err "Published package to pypi.org."
  else
    poetry publish --no-interaction --no-ansi -r test-pypi
    err "Published package to test.pypi.org."
  fi
}

main() {
  if [[ "${1:-}" != "--inside-container" ]]; then
    run_outside_container "$@"
    return
  fi

  publish_inside_container "$@"
}

main "$@"
