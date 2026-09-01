#!/usr/bin/env bash
set -euo pipefail

NODE_VERSION="22.23.2"
NODE_PLATFORM="darwin-arm64"
NODE_ARCHIVE="node-v${NODE_VERSION}-${NODE_PLATFORM}.tar.gz"
NODE_URL="https://nodejs.org/dist/v${NODE_VERSION}/${NODE_ARCHIVE}"
EXPECTED_SHA256="61130f394c1630d211dd50aecc4353d379480f36d3ac913cd85dbba1aed585c6"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNTIME_DIR="${REPO_ROOT}/.runtime"
DOWNLOAD_PATH="${TMPDIR:-/tmp}/${NODE_ARCHIVE}"

mkdir -p "${RUNTIME_DIR}"

echo "Downloading Node.js ${NODE_VERSION} for ${NODE_PLATFORM}..."
curl -L "${NODE_URL}" -o "${DOWNLOAD_PATH}"

ACTUAL_SHA256="$(shasum -a 256 "${DOWNLOAD_PATH}" | awk '{print $1}')"
if [[ "${ACTUAL_SHA256}" != "${EXPECTED_SHA256}" ]]; then
  echo "Checksum mismatch for ${NODE_ARCHIVE}" >&2
  echo "Expected: ${EXPECTED_SHA256}" >&2
  echo "Actual:   ${ACTUAL_SHA256}" >&2
  exit 1
fi

tar -xzf "${DOWNLOAD_PATH}" -C "${RUNTIME_DIR}"

echo "Installed:"
"${RUNTIME_DIR}/node-v${NODE_VERSION}-${NODE_PLATFORM}/bin/node" --version
"${RUNTIME_DIR}/node-v${NODE_VERSION}-${NODE_PLATFORM}/bin/npm" --version
