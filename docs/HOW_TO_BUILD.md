# How to build

These steps build the Cromite browser APK (`chrome_public_apk`) for arm64 Android devices, and for x64 Android emulators, on a Debian 13 amd64 machine. They run on the host, without containers.

The repository is in `~/cromite`, depot_tools in `~/depot_tools` and the Chromium checkout in `~/chromium/src`. The scripts in `tools/` expect `~/cromite` and `~/chromium/src`. The depot_tools location is this guide's choice.

## Prerequisites

- Debian 13 (trixie), amd64, with a user that can run `sudo`.
- Disk space. After every step up to the compile, a fresh Debian 13 machine used about 55 GB in total, including the operating system. The Chromium checkout is about 37 GB plus 2 GB of git history, and depot_tools is 1.3 GB. A build directory takes 3 to 4 GB after `gn gen` and grows during the compile. Chromium's Android build instructions ask for at least 100 GB free.

Install the base packages:

```
sudo apt-get update
sudo apt-get install -y git python3 curl lsb-release file xz-utils bzip2 unzip
```

## Get the sources

Clone this repository to `~/cromite` and fetch depot_tools:

```
git clone <url of this repository> ~/cromite
git clone https://chromium.googlesource.com/chromium/tools/depot_tools.git ~/depot_tools
```

[build/RELEASE](../build/RELEASE) holds the Chromium tag the patches apply to. Fetch only that tag, with two commits of history:

```
VERSION=$(cat ~/cromite/build/RELEASE)
mkdir -p ~/chromium/src && cd ~/chromium/src
git init
git remote add origin https://chromium.googlesource.com/chromium/src.git
git config --unset-all remote.origin.fetch
git config --add remote.origin.fetch +refs/tags/$VERSION:refs/tags/$VERSION
git fetch --depth 2 origin +refs/tags/$VERSION:refs/tags/$VERSION
git checkout $VERSION
```

## Install the build dependencies

```
cd ~/chromium/src
sudo DEBIAN_FRONTEND=noninteractive build/install-build-deps.sh --no-prompt --no-chromeos-fonts
```

The script accepts Debian 13 without `--unsupported`. `--lib32` is not needed: the arm64 and x64 builds use only 64-bit host toolchains and no 32-bit target toolchain. A 32-bit arm build would need it, and this guide does not cover one.

## Configure gclient

Write `~/chromium/.gclient`. The solution URL pins the commit of the tag, and `target_os` limits the checkout to Android dependencies. The `custom_deps` entries skip large dependencies the Android build does not use, and the `custom_hooks` entries replace Windows toolchain and case-insensitive file system hooks with no-ops.

```
cd ~/chromium/src
cat > ../.gclient <<EOF
solutions = [
  { "name"        : "src",
    "url"         : "https://chromium.googlesource.com/chromium/src.git@$(git rev-parse HEAD)",
    "deps_file"   : "DEPS",
    "managed"     : False,
    "custom_deps" : {
        "src/third_party/apache-windows-arm64": None,
        "src/third_party/updater/chrome_win_x86": None,
        "src/third_party/updater/chrome_win_x86_64": None,
        "src/third_party/updater/chromium_win_x86": None,
        "src/third_party/updater/chromium_win_x86_64": None,
        "src/third_party/gperf": None,
        "src/third_party/lighttpd": None,
        "src/third_party/lzma_sdk/bin/host_platform": None,
        "src/third_party/lzma_sdk/bin/win64": None,
        "src/third_party/perl": None,
        "src/tools/skia_goldctl/win": None,
        "src/third_party/screen-ai/windows_amd64": None,
        "src/third_party/screen-ai/windows_386": None,
        "src/third_party/cronet_android_mainline_clang/linux-amd64": None,
        "src/testing/libfuzzer/fuzzers/wasm_corpus": None,
    },
    "custom_hooks" : [
        { "name": "ciopfs_linux", "pattern": ".", "action": ["echo", "ciopfs_linux hook override"] },
        { "name": "win_toolchain", "pattern": ".", "action": ["echo", "win_toolchain hook override"] },
        { "name": "rc_win", "pattern": ".", "action": ["echo", "rc_win hook override"] },
        { "name": "rc_linux", "pattern": ".", "action": ["echo", "rc_linux hook override"] },
        { "name": "apache_win32", "pattern": ".", "action": ["echo", "apache_win32 hook override"] },
    ],
    "custom_vars": {
       "checkout_android_prebuilts_build_tools": True,
       "checkout_telemetry_dependencies": False,
       "codesearch": "Debug",
    },
  },
]
target_os = ["android"]
EOF
```

## Sync and run the hooks

```
export PATH=$HOME/depot_tools:$PATH DEPOT_TOOLS_UPDATE=0
cd ~/chromium/src
gclient sync -D --no-history --nohooks
gclient runhooks
echo ../../../../../usr/bin > ~/depot_tools/python3_bin_reldir.txt
```

With `DEPOT_TOOLS_UPDATE=0`, depot_tools skips its bootstrap and never writes `python3_bin_reldir.txt`. Without that file every `gn` call fails with `python3_bin_reldir.txt not found. need to initialize depot_tools`. The `echo` line points depot_tools at the system Python.

`git am` needs a committer identity in the Chromium checkout. Set one for this checkout only:

```
git config user.email builder@localhost
git config user.name builder
```

## Fetch the profile data

The release arguments enable PGO (`chrome_pgo_phase = 2`) and use AFDO profiles. Download them:

```
cd ~/chromium/src
python3 tools/update_pgo_profiles.py --target=android-desktop-arm64 update --gs-url-base=chromium-optimization-profiles/pgo_profiles
python3 tools/update_pgo_profiles.py --target=android-desktop-x64 update --gs-url-base=chromium-optimization-profiles/pgo_profiles
python3 tools/update_pgo_profiles.py --target=android-arm32 update --gs-url-base=chromium-optimization-profiles/pgo_profiles
python3 v8/tools/builtins-pgo/download_profiles.py download --depot-tools third_party/depot_tools --check-v8-revision
python3 tools/download_optimization_profile.py --newest_state=chrome/android/profiles/newest.txt --local_state=chrome/android/profiles/local.txt --output_name=chrome/android/profiles/afdo.prof --gs_url_base=chromeos-prebuilt/afdo-job/llvm
python3 tools/download_optimization_profile.py --newest_state=chrome/android/profiles/arm.newest.txt --local_state=chrome/android/profiles/arm.local.txt --output_name=chrome/android/profiles/arm.afdo.prof --gs_url_base=chromeos-prebuilt/afdo-job/llvm
```

The arm64 build reads its PGO profile from `chrome/android/orderfiles/arm64/`, which `gclient sync` already fetched. The x64 build uses the `android-arm32` profile, because a Cromite patch changes how Chromium selects the profile for x64.

You can delete `third_party/angle/third_party/VK-GL-CTS/` to save space. The build does not use it.

## Apply the patches

Create a branch, then turn five sub-repositories into ordinary tracked directories so that patches can change files inside them. Each one gets its own commit whose message starts with `:NOEXPORT:`, and the export scripts in `tools/` skip those commits.

```
VERSION=$(cat ~/cromite/build/RELEASE)
cd ~/chromium/src
git checkout -b cromite-$VERSION

# $1 is the path git tracks as a submodule, $2 the directory that holds its .git
flatten() {
  [ ! -e "$1-bis" ] || { echo "$1-bis is left from an earlier attempt, resolve it first" >&2; return 1; }
  rm -rf "$2/.git" &&
  cp -r "$1" "$1-bis" &&
  git rm -rf -q "$1" || return 1
  git submodule deinit -f "$1" || true
  rm -rf "$1" &&
  mv "$1-bis" "$1" &&
  git add -f "$1" > /dev/null &&
  git commit -q -m ":NOEXPORT: $1 repo"
}
flatten v8 v8 &&
flatten third_party/devtools-frontend third_party/devtools-frontend/src &&
flatten third_party/skia third_party/skia &&
flatten third_party/perfetto third_party/perfetto &&
flatten third_party/boringssl/src third_party/boringssl/src &&
git prune
```

The function stops at the first step that fails, and the calls are chained, so a failed copy (for example on a full disk) never leads to deleting the original directory.

A run that stops can leave a `<path>-bis` copy behind, and the function refuses to start while one exists, because copying into it again would nest the directory. If the original directory is still there, delete the `-bis` copy. If the original is gone, the `-bis` copy is the only one, so move it back to the original path. Then fix the cause and run the remaining calls. If `git status` shows the sub-repository entry as already deleted, finish that path by hand with `git add -f <path>` and a commit whose message starts with `:NOEXPORT:`.

Each `git submodule deinit` prints `error: pathspec '<path>' did not match any file(s) known to git`, because `git rm` has already removed the submodule entry. The `|| true` ignores it. `git add` also prints CRLF warnings for some vendored files. Both are harmless.

Then apply every `.patch` entry of [build/cromite_patches_list.txt](../build/cromite_patches_list.txt) in list order with `git am`. The `sed` call adds a `FILE:<patch name>` line to each commit message. The export scripts in `tools/` read that line to map a commit back to its patch file. The loop skips patches that are already on the branch, so you can run it again after a failure.

```
for file in $(cat ~/cromite/build/cromite_patches_list.txt); do
  [[ $file == *.patch ]] || continue
  git log --format=%B $VERSION..HEAD | grep -qxF "FILE:$(basename $file)" && continue
  echo "Applying $file"
  sed "0,/^---/s//FILE:$(basename $file)\n---/" ~/cromite/build/patches/$file | git am || { echo "FAILED: $file"; break; }
done
```

Do not run other git commands in `~/chromium/src` while the loop runs. Two git processes writing the index at once make `git am` fail with `fatal: unable to write index file`. If a patch fails, run `git am --abort`, check that the working tree is clean, and run the loop again.

When the loop finishes, `git rev-list --count $VERSION..HEAD` equals the number of `.patch` lines in the list plus 5.

## Environment variables

`build/cromite.gn_args` reads these variables with `getenv()`. GN reads them on every `gn gen` and again whenever the build regenerates its ninja files, so set them in every shell that runs `gn` or the build. Keep them in a file and source it, for example `~/cromite-build.env`:

```
export TARGET_ISDEBUG=false
export CROMITE_PREF_HASH_SEED_BIN=<64 hex characters>
```

- `TARGET_ISDEBUG`. With `true`, the arguments switch to a debug build: `is_debug`, DCHECKs and unstripped debug info on, official build and static analysis off. Any other value gives the release configuration this guide describes.
- `CROMITE_PREF_HASH_SEED_BIN`. Chromium uses this value as the seed for the hashes that protect tracked preferences (`chrome/browser/prefs/chrome_pref_service_factory.cc`). Generate it once with `python3 -c 'import secrets; print(secrets.token_hex(32))'` and keep it private. Use the same value for every build that you install over an earlier one, so that the hashes stored in existing profiles still match. If the variable is unset, the seed is empty, as in Chromium's own non-Google builds. GN also writes the value into generated files under `out/`, so do not publish build directories.
- `USE_KEYSTORE` and `KEYSTORE_PASSWORD`. These select release signing. Leave them unset. See [What this guide does not cover](#what-this-guide-does-not-cover).

## Generate the build directories

Put the Chromium clang and depot_tools on `PATH`, load the environment and pass the contents of `build/cromite.gn_args` to `gn gen`. `target_os` has to come first, because the file tests it:

```
export PATH=$HOME/chromium/src/third_party/llvm-build/Release+Asserts/bin:$HOME/depot_tools:$PATH DEPOT_TOOLS_UPDATE=0
. ~/cromite-build.env
cd ~/chromium/src
ARGS=$(cat ~/cromite/build/cromite.gn_args)
```

### Release

```
gn gen --args="target_os = \"android\" $ARGS target_cpu = \"arm64\" " out/release-arm64
```

For an x64 emulator build, use `target_cpu = \"x64\"` and a separate directory such as `out/release-x64`.

### Development

A development directory turns off PGO, LTO and symbols, so it compiles and links faster. Add these arguments after the release arguments:

```
FAST="is_official_build=false chrome_pgo_phase=0 use_thin_lto=false symbol_level=0 blink_symbol_level=0 generate_linker_map=false use_debug_fission=false enable_android_secondary_abi=true enable_check_raw_ptr_fields=false enable_check_raw_ref_fields=false android_static_analysis=\"off\" enable_r8_tracerefs=true is_debug=false treat_warnings_as_errors=true"
gn gen --args="target_os = \"android\" $ARGS target_cpu = \"arm64\" $FAST " out/fast-arm64
```

| Argument | Release | Development | Reason |
|---|---|---|---|
| `is_official_build` | true | false | No official build optimizations. |
| `chrome_pgo_phase` | 2 | 0 | No PGO. |
| `use_thin_lto` | true | false | No link-time optimization. |
| `symbol_level` | 1 | 0 | No debug symbols. |
| `blink_symbol_level` | 1 | 0 | `cromite.gn_args` sets it explicitly, so it does not follow `symbol_level`. |
| `use_debug_fission` | true | false | `cromite.gn_args` enables it, and it requires `symbol_level >= 1`. With `symbol_level=0`, `gn gen` fails the assert in `build/config/compiler/compiler.gni`. |
| `generate_linker_map` | true | false | The linker map is a release artifact. Skipping it saves link time. |
| `enable_android_secondary_abi` | true (default of an official build) | true | `//chrome/android:validate_expectations` depends on targets that exist only with a secondary ABI. Without it, `gn gen` fails with unresolved dependencies. |
| `enable_check_raw_ptr_fields`, `enable_check_raw_ref_fields` | false (default of an official build) | false | Non-official builds turn on these clang plugin checks. Release builds never run them, so with them on the development build would fail on code that the release build accepts. |
| `android_static_analysis` | off (default of an official build) | off | A non-official build defaults to `build_server`, which only works when the build is started through `autoninja`. Started through `siso.py`, the Java dependency checks fail with `AUTONINJA_BUILD_ID is not set`. |
| `enable_r8_tracerefs` | true | true | Its default is derived from `android_static_analysis`, so setting that to `off` would turn it off. Set it explicitly to keep the release behavior. |
| `is_debug` | false | false | Same as release. |
| `treat_warnings_as_errors` | true | true | Same as release. |

To compare the effective arguments of two directories, run `gn args out/<dir> --list --short` for each and diff the output. For example, the development build links with mold instead of lld and turns on Java asserts.

## Build

```
python3 ~/depot_tools/siso.py ninja -C out/release-arm64 chrome_public_apk --offline
```

Use the same command with `out/fast-arm64` or `out/release-x64`. Run it in a shell where `PATH`, `DEPOT_TOOLS_UPDATE` and the environment file are set as above. `--offline` runs every step locally.

The APK is written to `out/<dir>/apks/ChromePublic.apk`, with package name `xyz.serenitty.browser`.

## Steps of upstream's build to skip

Upstream Cromite builds inside its own Ubuntu container images and runs some steps that fail or do nothing here:

- Do not run `tools/clang/scripts/update.py --package=objdump`. At this Chromium version, clang and llvm-objdump come from a dependency in DEPS, and that command deletes `third_party/llvm-build/Release+Asserts` down to the objdump tools. If you ran it, run `gclient sync -D --no-history --nohooks` again to restore the toolchain.
- Do not pass `--android` to `install-build-deps.sh`. The flag no longer exists.
- Do not download the `win64` and `linux` PGO profiles, the Windows clang package or the `rc` tool. They are only for Windows and Linux builds.
- Skip goma, ninjatracing, kythe, the clangd indexer, the patched ninja 1.8.2 and the vpython pre-warm. The APK build does not use them.
- Skip the separate `sync_rollup_libs.py` step for devtools-frontend. `gclient runhooks` already runs it.
- Upstream also builds `chrome_public_bundle`. The APK target does not need it.

## What this guide does not cover

- Release signing. `cromite.gn_args` reads a keystore from a fixed path inside upstream's build container when `USE_KEYSTORE` is set, and this fork has no release key set up yet. With `USE_KEYSTORE` unset, the build signs the APK with Chromium's default debug key. Android does not install a debug-signed APK over a release-signed Cromite. Uninstalling the installed browser deletes its data, so export bookmarks and anything else you need before you uninstall it.
- The System WebView, 32-bit arm builds, and Windows or Linux builds.
