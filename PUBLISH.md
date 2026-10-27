# Publishing the tap

Maintainer checklist for making `ChrBoebel/homebrew-tap` public and, later, proposing Saywing to
`homebrew/cask`. Nothing here has been run yet: the repository exists only locally.

## When

Publish **after the new signed release is live**, not before:

1. The release workflow has published the new version for **both** architectures, and both
   `https://www.christopherboebel.com/downloads/saywing/latest.json` and
   `https://www.christopherboebel.com/downloads/saywing/x86_64/latest.json` report the same new
   `version` and `build`.
2. Both DMGs download, are notarized, and pass Gatekeeper on a Mac.
3. The cask has been bumped to that release (below) and the audit passes.

The local commit currently pins `0.1.30,130`, the build the feeds served on 2026-10-27. Do not
publish the tap with those values once a newer release exists.

## Before the first push

- Decide on a license for the tap's own files (cask, script, workflow). There is no
  `LICENSE` file yet. Homebrew's own taps use BSD-2-Clause; Apache-2.0 would match Saywing.
- Check the "to confirm on a real install" list in `README.md`.

## 1. Bump and verify locally

```sh
cd /Users/christopherbobel/.bb/thread-storage/thr_bfan2pauct/homebrew-tap

scripts/bump.sh

# Audit through a temporary tap link (brew audit no longer accepts file paths).
taps="$(brew --repository)/Library/Taps/chrboebel"
mkdir -p "$taps" && ln -s "$PWD" "$taps/homebrew-tap"
brew style chrboebel/tap
brew audit --cask --strict --online --arch all --tap chrboebel/tap   # downloads both DMGs
brew livecheck --cask chrboebel/tap/saywing
rm "$taps/homebrew-tap"        # remove the link before testing the real tap

git add -A
GIT_AUTHOR_EMAIL=ChrBoebel@users.noreply.github.com \
GIT_COMMITTER_EMAIL=ChrBoebel@users.noreply.github.com \
  git commit -m "saywing <version>,<build>"
```

## 2. Create the public repository and push

```sh
gh auth status                     # must be logged in as ChrBoebel
gh repo create ChrBoebel/homebrew-tap \
  --public \
  --description "Homebrew tap for Saywing" \
  --homepage "https://github.com/ChrBoebel/saywing" \
  --source . --remote origin --push
```

The repository must be named `homebrew-tap` so that `chrboebel/tap` resolves to it.

After the push:

```sh
gh run list --repo ChrBoebel/homebrew-tap --workflow audit.yml   # the push to main triggers it
gh run watch --repo ChrBoebel/homebrew-tap
```

Recommended repository settings:

- Protect `main` and require the **Audit casks / audit** check.
- Under Settings -> Actions, allow only GitHub-owned actions, which is all this workflow uses.
- Disable the wiki and projects if you don't need them.

From then on, change the cask only through pull requests (`scripts/bump.sh`, push a branch,
`gh pr create`), as described in `README.md`.

## 3. Test the install on a Mac

Ideally use a Mac or user account without Saywing. Otherwise, quit Saywing and move
`/Applications/Saywing.app` aside first, or use `--adopt` if the versions match.

```sh
brew tap | grep chrboebel || true          # must not be a local symlink any more
brew update
brew info --cask chrboebel/tap/saywing     # version, both URLs, auto_updates, macOS requirement
brew install --cask chrboebel/tap/saywing

# Verify what landed
spctl --assess --type execute -vv /Applications/Saywing.app      # accepted, Notarized Developer ID
codesign --verify --deep --strict /Applications/Saywing.app
defaults read /Applications/Saywing.app/Contents/Info.plist CFBundleShortVersionString
open -a Saywing                              # menu bar icon appears; Gatekeeper prompt is the normal one

# Exercise the app briefly (read a region, accept the Supertonic terms, check for updates),
# quit it, then confirm the README's "to confirm" paths:
id=com.christopherbobel.OpenScreenReader
for p in "Application Support/Saywing" "Application Support/Saywing Update Backups" \
         "Caches/$id" "HTTPStorages/$id" "HTTPStorages/$id.binarycookies" \
         "Preferences/$id.plist" "Saved Application State/$id.savedState"; do
  [ -e "$HOME/Library/$p" ] && echo "present  ~/Library/$p" || echo "absent   ~/Library/$p"
done

brew uninstall --cask saywing                # app gone, data kept
brew install --cask chrboebel/tap/saywing
brew uninstall --zap --cask saywing          # also deletes downloaded dictation models
```

Repeat on an Intel Mac if one is available. Update `zap` and the README with anything the check
turns up, through a pull request.

## 4. Later: submitting to homebrew/cask

The tap works on its own. Moving the cask to the official `homebrew/cask` repository (so that
`brew install --cask saywing` works without a tap) depends on Homebrew's acceptance policy
(local Homebrew 7.0.10 docs, `Package-Acceptance-Policy.md` and `Acceptable-Casks.md`, reviewed
2026-08-25):

- **Notability.** Normal threshold for the upstream GitHub repo: at least **30 forks, 30
  watchers or 75 stars**. A **self-submission** by the repository owner (or by a committer whose
  email is at the `homepage` or `url` domain) needs at least **90 forks, 90 watchers or 225
  stars**. On 2026-10-27 `ChrBoebel/saywing` had 0 forks, 0 watchers and 1 star, and
  `brew audit --new` fails with "GitHub repository not notable enough". Repositories under 30
  days old are normally ineligible; `ChrBoebel/saywing` was created on 2026-09-04, so it has
  passed that bar.
- **Notability exceptions** (reviewed case by case, not guaranteed): substantial,
  independently verifiable public interest with multiple user requests for inclusion; or a
  submitter who is an established Homebrew maintainer or prolific contributor. The easiest route
  is usually for an independent user to submit it once the project is notable.
- **Other requirements**, which the cask already meets or must keep meeting: a working
  `livecheck` without `skip`; downloads published by the developer; passes Homebrew's
  Gatekeeper checks (Developer ID and notarized); works on the latest major macOS. The
  unversioned token `saywing` should track the channel recommended for most users. If a
  separate stable channel appears later, concurrent beta builds would go in `saywing@beta`.

When eligible, the submission steps are:

```sh
brew tap --force homebrew/cask
cp Casks/saywing.rb "$(brew --repository homebrew/cask)/Casks/s/saywing.rb"
cd "$(brew --repository homebrew/cask)"
HOMEBREW_NO_INSTALL_FROM_API=1 brew install --cask saywing
brew uninstall --cask saywing
brew audit --new --cask saywing
brew style --fix --cask saywing
brew lgtm --online
# then fork Homebrew/homebrew-cask, commit on a new branch and open the PR
# (see Homebrew's "How to Open a Homebrew Pull Request"); fill in the template.
```

Once the cask is accepted, open a pull request on this tap that deletes `Casks/saywing.rb` and
adds a `tap_migrations.json` entry, `{"saywing": "homebrew/cask"}`, so existing installs move to
the official cask. Link the two pull requests to each other, as described in Homebrew's
`Migrating-A-Formula-To-A-Tap.md`.
