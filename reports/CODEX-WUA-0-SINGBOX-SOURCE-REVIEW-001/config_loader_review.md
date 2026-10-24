# Configuration loader / ownership of inputs

`cmd/sing-box/cmd.go:67` / `preRun`: CLI -c is an array, -C adds directories, -D changes cwd (and can create it), absent -c/-C uses `config.json`. `preRun` reads SUDO_USER/UID/GID for file manager context; not proof of a safe Windows process token. A future exact invocation must specify one protected absolute config, no config-directory/stdin/default search, pinned cwd and reviewed environment. This TASK does not create such launcher or alter environment.

`cmd/sing-box/cmd_run.go:52` / `readConfig/readConfigAndMerge`: `readConfigAt` reads stdin or file, `readConfig` reads .json directory members and sorts, `readConfigAndMerge` uses external badjson.MergeJSON; run loop handles SIGHUP with check/recreate. Multiple-file merge/parser edge cases belong partly to missing sing module. Atomic immutable config binding, safe roots/ACLs and TOCTOU remain external requirements, not supplied by a hash in our report.

`option/options.go:31` / `Options.UnmarshalJSONContext`: top-level typed options calls DisallowUnknownFields and checkOptions duplicate tags. Nested option registry/UnmarshallExcludedContext uses dependency code: no blanket unknown-field guarantee claimed. Source tests guard current top-level field set against inserted Sneaky field. Native schema was not invented and native config parsing was NOT RUN.

Existing broker family=V2Ray remains immutable. A future user-approved sing-box mapping would require exact registry/option schema review, lossless field policy, dependencies, disabled-only output and negative source/config controls. It is not an automatic translation or permission to load user profiles.
