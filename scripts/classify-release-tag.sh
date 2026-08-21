#!/usr/bin/env bash
# Classify a validator release tag for GitHub release and Docker workflows.
set -euo pipefail

allow_empty=false
publish_latest=false
publish_latest_if_stable=false
force_prerelease=false

while [ "$#" -gt 0 ]; do
  case "$1" in
    --allow-empty)
      allow_empty=true
      shift
      ;;
    --publish-latest)
      publish_latest=true
      shift
      ;;
    --publish-latest-if-stable)
      publish_latest_if_stable=true
      shift
      ;;
    --force-prerelease)
      force_prerelease=true
      shift
      ;;
    --)
      shift
      break
      ;;
    -*)
      echo "error: unknown option: $1" >&2
      exit 2
      ;;
    *)
      break
      ;;
  esac
done

[ "$#" -eq 1 ] || {
  echo "usage: $0 [--allow-empty] [--publish-latest] [--publish-latest-if-stable] [--force-prerelease] <tag>" >&2
  exit 2
}

tag="$1"
if [ -z "$tag" ]; then
  [ "$allow_empty" = true ] || {
    echo "error: release tag is required" >&2
    exit 1
  }
  printf '%s\n' \
    "tag=" \
    "publish=false" \
    "stable=false" \
    "prerelease=true" \
    "latest=false"
  exit 0
fi

if [[ ! "$tag" =~ ^v[0-9]+\.[0-9]+\.[0-9]+(-(preview|alpha|beta|rc)(\.[0-9]+)?)?$ ]]; then
  echo "error: release tag must look like v0.1.0 or v0.1.0-preview" >&2
  exit 1
fi

stable=false
prerelease=true
if [[ "$tag" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  stable=true
  prerelease=false
fi
if [ "$force_prerelease" = true ]; then
  prerelease=true
fi

if [ "$publish_latest" = true ] && [ "$stable" != true ]; then
  echo "error: a prerelease cannot be published as latest" >&2
  exit 1
fi

if [ "$publish_latest_if_stable" = true ] && [ "$stable" = true ]; then
  publish_latest=true
fi

printf '%s\n' \
  "tag=$tag" \
  "publish=true" \
  "stable=$stable" \
  "prerelease=$prerelease" \
  "latest=$publish_latest"
