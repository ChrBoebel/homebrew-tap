#!/usr/bin/env python3
"""Open a reviewed cask bump from a published, matching two-architecture release."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import urllib.request

PREFIX = 'https://www.christopherboebel.com/downloads/saywing'
TAP = 'ChrBoebel/homebrew-tap'
SOURCE = 'ChrBoebel/saywing'
ROOT = Path(__file__).resolve().parents[1]


def command(*args):
    return subprocess.check_output(args, text=True).strip()


def api(path):
    result = subprocess.run(['gh', 'api', path], text=True, capture_output=True)
    if result.returncode:
        if 'HTTP 404' in result.stderr:
            return None
        raise RuntimeError(result.stderr.strip())
    return json.loads(result.stdout)


def feed(suffix):
    with urllib.request.urlopen(PREFIX + suffix + '/latest.json', timeout=60) as response:
        return json.load(response)


def identity(cask):
    match = re.search(r'^  version "([0-9]+\.[0-9]+\.[0-9]+),([1-9][0-9]*)"$', cask, re.M)
    if not match:
        raise ValueError('Cannot identify the current cask version')
    return match.groups()


def candidate_release(arm, intel, cask):
    for metadata in (arm, intel):
        if not isinstance(metadata.get('version'), str) or not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+', metadata['version']):
            raise ValueError('Invalid release version')
        if not isinstance(metadata.get('build'), str) or not re.fullmatch(r'[1-9][0-9]*', metadata['build']):
            raise ValueError('Invalid release build')
    if (arm.get('version'), arm.get('build')) != (intel.get('version'), intel.get('build')):
        return None  # One architecture may still be publishing.
    version, build = arm.get('version'), arm.get('build')
    for metadata, arch, suffix in [(arm, 'arm64', ''), (intel, 'x86_64', '/x86_64')]:
        if metadata.get('architecture') != arch:
            raise ValueError('Unexpected feed architecture')
        if not re.fullmatch(r'[0-9a-f]{64}', str(metadata.get('sha256', ''))):
            raise ValueError('Invalid SHA-256')
        if metadata.get('url') != f'{PREFIX}{suffix}/Saywing-{version}-{build}.dmg':
            raise ValueError('Unexpected download URL')
    old_version, old_build = identity(cask)
    if int(build) < int(old_build):
        return None
    if int(build) == int(old_build):
        hashes = re.findall(r'sha256 "([0-9a-f]{64})"', cask)
        if version != old_version or hashes != [arm['sha256'], intel['sha256']]:
            raise ValueError('Refusing to replace an existing build or its checksums')
        return None
    if tuple(map(int, version.split('.'))) < tuple(map(int, old_version.split('.'))):
        raise ValueError('Refusing a version downgrade')
    return version, build


def plan(arm, intel, cask, release):
    candidate = candidate_release(arm, intel, cask)
    if not candidate or not release or release.get('draft') or not release.get('published_at'):
        return None
    version, build = candidate
    if release.get('tag_name') != f'v{version}-build{build}':
        raise ValueError('GitHub release does not match the public feeds')
    return candidate


def audit(branch, sha):
    runs = json.loads(command('gh', 'run', 'list', '--repo', TAP, '--workflow', 'audit.yml',
                              '--event', 'workflow_dispatch', '--commit', sha,
                              '--limit', '1', '--json', 'databaseId'))
    if not runs:
        # GITHUB_TOKEN-created PR runs require approval. Explicit dispatch runs
        # the existing read-only audit on this exact branch without a new PAT.
        command('gh', 'workflow', 'run', 'audit.yml', '--repo', TAP, '--ref', branch)


def run(dry_run=False):
    cask_path = ROOT / 'Casks/saywing.rb'
    before = cask_path.read_text()
    arm, intel = feed(''), feed('/x86_64')
    # Validate feed-derived data before using it in a GitHub API path.
    candidate = candidate_release(arm, intel, before)
    if not candidate:
        print('No newer matching release in both feeds; nothing to do.')
        return
    version, build = candidate
    release = api(f'repos/{SOURCE}/releases/tags/v{version}-build{build}')
    if not plan(arm, intel, before, release):
        print('Waiting for the matching published GitHub release.')
        return
    branch = f'codex/bump-saywing-{version}-{build}'
    if dry_run:
        print(f'Would create or recover {branch} for {version}, build {build}.')
        return
    prs = api(f'repos/{TAP}/pulls?state=all&head=ChrBoebel:{branch}&base=main')
    if prs:
        pr = prs[0]
        if pr['state'] == 'open':
            audit(branch, pr['head']['sha'])
        print('Existing PR:', pr['html_url'])
        return
    subprocess.run(['bash', str(ROOT / 'scripts/bump.sh')], check=True)
    after = cask_path.read_text()
    if identity(after) != candidate or re.findall(r'sha256 "([0-9a-f]{64})"', after) != [arm['sha256'], intel['sha256']]:
        raise ValueError('Feeds changed during preparation; retry with a fresh checkout')
    remote = command('git', 'ls-remote', '--heads', 'origin', branch)
    if remote:
        command('git', 'fetch', 'origin', branch)
        if command('git', 'diff', '--name-only', 'HEAD...FETCH_HEAD') != 'Casks/saywing.rb':
            raise ValueError('Existing bump branch contains unexpected changes')
        if command('git', 'show', 'FETCH_HEAD:Casks/saywing.rb') != after.strip():
            raise ValueError('Existing bump branch differs; maintainer review needed')
        sha = command('git', 'rev-parse', 'FETCH_HEAD')
    else:
        command('git', 'switch', '-c', branch)
        command('git', 'config', 'user.name', 'github-actions[bot]')
        command('git', 'config', 'user.email', '41898282+github-actions[bot]@users.noreply.github.com')
        command('git', 'add', '--', 'Casks/saywing.rb')
        command('git', 'commit', '-m', f'saywing {version},{build}')
        command('git', '-c', 'credential.helper=', '-c', 'credential.helper=!gh auth git-credential',
                'push', 'origin', f'HEAD:refs/heads/{branch}')
        sha = command('git', 'rev-parse', 'HEAD')
    body = (f'Bump Saywing to {version} (build {build}) from the matching public arm64 and Intel feeds.\n\n'
            f'Release: https://github.com/{SOURCE}/releases/tag/v{version}-build{build}\n\n'
            'The separate read-only online audit checks both DMG downloads and checksums. '
            'This PR remains open for maintainer review; it is never automatically approved or merged.\n')
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md') as note:
        note.write(body)
        note.flush()
        print(command('gh', 'pr', 'create', '--repo', TAP, '--base', 'main', '--head', branch,
                      '--title', f'Bump Saywing to {version} (build {build})', '--body-file', note.name))
    audit(branch, sha)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run', action='store_true', help='Read and validate only; do not write to GitHub')
    args = parser.parse_args()
    os.chdir(ROOT)
    run(args.dry_run)
