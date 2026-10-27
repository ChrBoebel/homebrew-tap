# ChrBoebel Homebrew tap

Homebrew cask for [Saywing](https://github.com/ChrBoebel/saywing), a native macOS menu bar
app that reads a selected screen region aloud and transcribes dictation and meetings. All
recognition and speech run locally on your Mac.

## Install

```sh
brew install --cask chrboebel/tap/saywing
```

- Requires macOS 14 Sonoma or later.
- Apple Silicon and Intel Macs get separate DMGs (about 1 GB each); Homebrew picks the right
  one automatically.
- Installing by the fully qualified name trusts only this cask (Homebrew tap trust). To use
  the short name `saywing` after `brew tap chrboebel/tap`, first run
  `brew trust --cask chrboebel/tap/saywing`.
- Saywing is a menu bar app with no Dock icon. On first use it asks for the macOS permissions
  each feature needs: Screen Recording and Input Monitoring for reading aloud, Microphone and
  Accessibility for dictation, and Microphone plus system audio for meeting transcripts.

If you already installed Saywing from the DMG, Homebrew refuses to overwrite
`/Applications/Saywing.app`. If the installed version matches the cask, run
`brew install --cask --adopt chrboebel/tap/saywing`. Otherwise, quit Saywing and move the
existing app to the Trash first.

## Updates

Saywing updates itself with [Sparkle](https://sparkle-project.org). It checks for updates in
the background, shows the native update window and installs only after you confirm. Settings
-> General has the automatic-check toggle and a manual check button. The update feed and
archives are signed (Ed25519), and the app and DMG are Developer ID signed and notarized.

The cask therefore declares `auto_updates true`:

- `brew upgrade` skips Saywing unless you pass `--greedy`
  (`brew upgrade --cask --greedy saywing`).
- `brew list --versions` may show an older version than the app reports after a Sparkle
  update. That is expected; the app's own version is the one that counts.

## Uninstall

```sh
brew uninstall --cask saywing
```

This removes `/Applications/Saywing.app` and keeps your settings and downloaded models.

To remove the app's own data as well:

```sh
brew uninstall --zap --cask saywing
```

`--zap` deletes the following, all verified against the Saywing source:

| Path | Contents |
| --- | --- |
| `~/Library/Application Support/Saywing` | Downloaded dictation models (`DictationModels`; several GB if you installed the optional models) |
| `~/Library/Caches/com.christopherbobel.OpenScreenReader` | Sparkle's update download cache |
| `~/Library/HTTPStorages/com.christopherbobel.OpenScreenReader` | URL session storage of the in-app Sparkle update client |
| `~/Library/Preferences/com.christopherbobel.OpenScreenReader.plist` | Settings, Supertonic terms acceptance and Sparkle preferences |

The bundle identifier `com.christopherbobel.OpenScreenReader` is intentional: Saywing used to
be called OpenScreenReader, and the identifier stayed the same so existing settings carry over.

Saywing stores no screenshots, OCR text, transcripts or audio, so `--zap` has none of those to
remove. Meeting transcripts exist on disk only where you saved them yourself. The macOS privacy
permissions are not files; to reset them as well, run:

```sh
tccutil reset All com.christopherbobel.OpenScreenReader
```

### To confirm on a real install

The following were not verifiable from the code and are deliberately **not** in `zap` until
someone confirms them on a clean install (use and quit the app, then check):

- `~/Library/Saved Application State/com.christopherbobel.OpenScreenReader.savedState`: AppKit
  may create it for the Settings or meeting windows. One window explicitly opts out of
  restoration, and the folder did not exist on a Mac that had been running 0.1.17.
- `~/Library/HTTPStorages/com.christopherbobel.OpenScreenReader.binarycookies`: may be created
  next to the HTTPStorages folder; not seen so far.
- `~/Library/Application Support/Saywing Update Backups`: an empty folder seen on the
  maintainer's Mac. Neither the Saywing source nor Sparkle 2.10.0 contains this name, so it
  may come from something else.
- `~/Library/Application Support/OpenScreenReader`: used only by Debug builds and the
  development install scripts. Release builds never read or write it, so `zap` leaves it alone.
- Intel install footprint: confirm that it matches the Apple Silicon list above.

## License

The files in this tap (the cask, scripts and workflow) are licensed under the BSD 2-Clause License; see [LICENSE](LICENSE).

- **Saywing** is open source under the
  [Apache License 2.0](https://github.com/ChrBoebel/saywing/blob/main/LICENSE).
- **The bundled models have their own terms.** The Supertonic 3 speech model and voices are
  licensed under the BigScience OpenRAIL-M license, which includes use restrictions. Saywing
  asks you to accept these
  [model terms](https://github.com/ChrBoebel/saywing/blob/main/docs/licenses/SUPERTONIC-MODEL-TERMS.md)
  in the app before the read-aloud voice is used; installing with Homebrew does not accept them
  for you. Speech you share must be marked as machine-generated. Whisper is MIT-licensed, and the
  optional Qwen3-ASR model is Apache-2.0.
- Third-party code, runtimes and libraries keep their own licenses. Their notices ship inside
  the app and the DMG and are listed in
  [docs/licenses](https://github.com/ChrBoebel/saywing/tree/main/docs/licenses).

Homebrew downloads the same signed DMG that the Saywing website offers; this tap does not
repackage or modify it.

## Maintaining the cask

The cask pins a single `version "<version>,<build>"` and one sha256 per architecture. The
`on_arm` block downloads `.../downloads/saywing/Saywing-<version>-<build>.dmg`, and the
`on_intel` block downloads `.../downloads/saywing/x86_64/Saywing-<version>-<build>.dmg`.

The values in `Casks/saywing.rb` were taken from the live feeds on 2026-10-27
(`0.1.30,130`, channel `beta`). **Bump them as soon as the next signed release is published.**

### Bump to a new release

Once both architectures are published:

```sh
scripts/bump.sh
```

The script reads
`https://www.christopherboebel.com/downloads/saywing/latest.json` (arm64) and
`https://www.christopherboebel.com/downloads/saywing/x86_64/latest.json` (Intel). It fails
without changing anything if:

- the two feeds report different versions or builds;
- a feed's `architecture` does not match;
- a `url` does not match the path the cask builds from the version;
- a sha256 is malformed.

Otherwise it rewrites the version and both sha256 values in place. It does not download the
DMGs and never commits or pushes.

Then verify against the real downloads and open a pull request:

```sh
brew style chrboebel/tap
brew audit --cask --strict --online --arch all --tap chrboebel/tap   # downloads both DMGs
brew livecheck --cask chrboebel/tap/saywing                          # should report no newer version
git switch -c saywing-<version>
git commit -am "saywing <version>,<build>"
gh pr create --fill
```

`brew livecheck --cask chrboebel/tap/saywing` reads the arm64 `latest.json` and tells you
whether the cask is behind. `brew style chrboebel/tap` also lints `scripts/bump.sh` and the
workflow. To do that it installs `shellcheck`, `shfmt` and `actionlint` from homebrew/core on
first use.

To audit a working copy before it is tapped, link it in as `chrboebel/tap` (and remove the link
afterwards):

```sh
mkdir -p "$(brew --repository)/Library/Taps/chrboebel"
ln -s "$PWD" "$(brew --repository)/Library/Taps/chrboebel/homebrew-tap"
# ... brew style / brew audit as above ...
rm "$(brew --repository)/Library/Taps/chrboebel/homebrew-tap"
```

### CI

`.github/workflows/audit.yml` runs `brew style` and
`brew audit --cask --strict --online --arch all` on macOS for every pull request and every push
to `main`. It uses the Homebrew preinstalled on GitHub's macOS runners and only the
GitHub-owned `actions/checkout`, pinned by full commit SHA.
