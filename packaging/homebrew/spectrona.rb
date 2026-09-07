class Spectrona < Formula
  desc "Local-first AI gateway and MCP security scanner"
  homepage "https://github.com/spectrona/spectrona"
  url "https://github.com/spectrona/spectrona/archive/refs/tags/v0.1.0.tar.gz"
  sha256 "REPLACE_WITH_RELEASE_SHA256"
  license "MIT"

  depends_on "python@3.11"

  def install
    libexec.install "spectrona-detection"
    libexec.install "mcp-inspector"
    libexec.install "policy-engine"
    libexec.install "runtime-guard"
    libexec.install "spectrona-cli"
    libexec.install "spectrona-gateway"
    (bin/"spectrona").write <<~SH
      #!/bin/bash
      export SPECTRONA_PYTHON="#{Formula["python@3.11"].opt_bin}/python3.11"
      exec "#{libexec}/spectrona-cli/bin/spectrona" "$@"
    SH
    chmod 0755, bin/"spectrona"
  end

  def post_install
    (var/"log").mkpath
  end

  service do
    run [opt_bin/"spectrona", "start", "--foreground"]
    keep_alive true
    log_path var/"log/spectrona.log"
    error_log_path var/"log/spectrona.err.log"
  end

  def caveats
    <<~EOS
      First-time setup:
        spectrona init

      Start the local gateway:
        spectrona start

      Run Spectrona as a background service:
        brew services start spectrona

      Dashboard:
        http://127.0.0.1:8787/ui

      Check and repair app integrations explicitly:
        spectrona integrations status
        spectrona integrations repair --confirm

      Store upstream provider keys without plaintext config:
        spectrona secrets set openai
        spectrona secrets set anthropic
    EOS
  end

  test do
    ENV["SPECTRONA_HOME"] = testpath/".spectrona"
    system bin/"spectrona", "init"
    assert_path_exists testpath/".spectrona/config.yaml"
    assert_path_exists testpath/".spectrona/policy.yaml"
    assert_match "Spectrona", shell_output("#{bin}/spectrona status")
  end
end
