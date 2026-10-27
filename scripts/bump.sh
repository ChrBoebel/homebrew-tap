#!/bin/bash
# Rewrites Casks/saywing.rb from the published arm64 and x86_64 latest.json files.
#
# Usage: scripts/bump.sh
#
# Reads <prefix>/latest.json (arm64) and <prefix>/x86_64/latest.json (Intel),
# checks that both describe the same version and build, that each URL matches the
# layout the cask interpolates, and that each sha256 is well formed. Then it
# rewrites the cask's version and both sha256 values in place. It never commits,
# pushes or downloads a DMG; run `brew audit --cask --strict --online` afterwards
# to verify the checksums against the real downloads.
#
# SAYWING_DOWNLOAD_PREFIX overrides the default prefix (any URL curl accepts,
# including file://, for testing).
set -euo pipefail

prefix="${SAYWING_DOWNLOAD_PREFIX:-https://www.christopherboebel.com/downloads/saywing}"
prefix="${prefix%/}"
# The URL template in the cask always uses the public prefix.
public_prefix="https://www.christopherboebel.com/downloads/saywing"
root="$(cd "$(dirname "$0")/.." && pwd)"
cask="${root}/Casks/saywing.rb"

work="$(mktemp -d "${TMPDIR:-/tmp}/saywing-bump.XXXXXX")"
trap 'rm -rf "$work"' EXIT

fail() {
  echo "bump.sh: $*" >&2
  exit 1
}

# field <file> <key>: prints a top-level string value of a JSON file.
field() {
  /usr/bin/plutil -extract "$2" raw -o - "$1" 2>/dev/null || fail "missing \"$2\" in $3"
}

read_feed() { # <arch> <subpath>
  local arch="$1" sub="$2" file="${work}/$1.json" url="${prefix}$2/latest.json"
  curl -fsSL --proto '=https,file' --max-time 60 -o "${file}" "${url}" || fail "could not fetch ${url}"
  local version build sha dmg feed_arch
  version="$(field "${file}" version "${url}")"
  build="$(field "${file}" build "${url}")"
  sha="$(field "${file}" sha256 "${url}")"
  dmg="$(field "${file}" url "${url}")"
  feed_arch="$(field "${file}" architecture "${url}")"
  [[ "${version}" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || fail "${arch}: version must be x.y.z, got \"${version}\""
  [[ "${build}" =~ ^[1-9][0-9]*$ ]] || fail "${arch}: build must be a positive integer, got \"${build}\""
  [[ "${sha}" =~ ^[0-9a-f]{64}$ ]] || fail "${arch}: sha256 must be 64 lowercase hex characters"
  [[ "${feed_arch}" == "${arch}" ]] || fail "${url} describes architecture \"${feed_arch}\", expected \"${arch}\""
  local expected="${public_prefix}${sub}/Saywing-${version}-${build}.dmg"
  [[ "${dmg}" == "${expected}" ]] || fail "${arch}: url is ${dmg}, but the cask would download ${expected}"
  printf '%s %s %s\n' "${version}" "${build}" "${sha}"
}

# Each assignment aborts the script (set -e) if read_feed fails. Inside read_feed every
# field is validated, so an unreadable field also fails even where errexit is not inherited.
arm="$(read_feed arm64 "")"
intel="$(read_feed x86_64 "/x86_64")"
read -r arm_version arm_build arm_sha <<<"${arm}"
read -r intel_version intel_build intel_sha <<<"${intel}"

if [[ "${arm_version},${arm_build}" != "${intel_version},${intel_build}" ]]
then
  fail "arm64 is ${arm_version},${arm_build} but x86_64 is ${intel_version},${intel_build}; publish both first"
fi

old_version="$(sed -nE 's/^  version "([^"]+)"$/\1/p' "${cask}")"
[[ -n "${old_version}" ]] || fail "could not find the version line in ${cask}"
new_version="${arm_version},${arm_build}"

VERSION="${new_version}" ARM="${arm_sha}" INTEL="${intel_sha}" /usr/bin/perl -0pi -e '
  my $n = 0;
  $n += s/^(  version ")[^"]+(")$/$1$ENV{VERSION}$2/m;
  $n += s/(on_arm do\n\s+sha256 ")[0-9a-f]{64}(")/$1$ENV{ARM}$2/;
  $n += s/(on_intel do\n\s+sha256 ")[0-9a-f]{64}(")/$1$ENV{INTEL}$2/;
  die "bump.sh: expected 3 replacements, made $n\n" unless $n == 3;
' "${cask}"

if [[ "${old_version}" == "${new_version}" ]]
then
  echo "Version unchanged (${new_version}); sha256 values refreshed from the feeds."
else
  echo "Bumped saywing ${old_version} -> ${new_version}"
fi
echo "  arm64:  ${arm_sha}"
echo "  x86_64: ${intel_sha}"
echo "Next: brew style chrboebel/tap && brew audit --cask --strict --online --arch all --tap chrboebel/tap"
