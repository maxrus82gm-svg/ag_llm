# Local development candidate — NOT INSTALLED

These two manifests are a reviewable starting point, not a verified ChatGPT
installation or distributable release. Absolute paths intentionally bind this
candidate to the already installed Python environment and the reviewed adapter.
No cache/config/marketplace was modified. Installing a copied package alone
will not make this candidate portable: vendor dependencies and Web Alarm code,
and define the adapter's trusted installation root in a separate implementation.

The adapter always creates a disposable fixture. It has no production server
URL, workspace selector, file-reader, write tool, model API or ChatGPT-send tool.
Do not substitute the legacy Ultra MCP server: that exposes model/file-agent
operations, outside this smoke's scope.

Official local marketplace authoring route:
https://developers.openai.com/plugins/build/plugins

For a local executor only. Availability in an ordinary ChatGPT Chat, as opposed
to Work/Codex, remains a distinct manual end-to-end gate.
