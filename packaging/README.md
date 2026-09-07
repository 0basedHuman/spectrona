# Spectrona Packaging

This directory contains local release and Homebrew packaging helpers.

## Build A Release Archive

```bash
python3 packaging/build_release.py --output-dir dist
```

The command writes:

- `dist/spectrona-<version>.tar.gz`
- `dist/spectrona-<version>.release.json`

Use the manifest `sha256` value to replace `REPLACE_WITH_RELEASE_SHA256` in
`packaging/homebrew/spectrona.rb` after the archive is published at the formula
URL.

## Publish Flow

```bash
python3 packaging/build_release.py --output-dir dist
gh release create v0.1.0 dist/spectrona-0.1.0.tar.gz
brew tap-new spectrona/tap
cp packaging/homebrew/spectrona.rb "$(brew --repository spectrona/tap)/Formula/spectrona.rb"
brew install spectrona/tap/spectrona
brew services start spectrona
```

The formula is consent-based: installing Spectrona does not rewrite Claude,
Codex, VS Code, or MCP app configs. Users opt in through the dashboard,
`spectrona integrations repair --confirm`, or specific `spectrona protect` /
`spectrona mcp protect` commands.
