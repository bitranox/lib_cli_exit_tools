class LibCliExitTools < Formula
  include Language::Python::Virtualenv

  desc "CLI exit handling helpers: clean signals, exit codes, and error printing"
  homepage "https://github.com/bitranox/lib_cli_exit_tools"
  url "https://github.com/bitranox/lib_cli_exit_tools/archive/refs/tags/v0.1.0.tar.gz"
  sha256 "<fill-me>"
  license "MIT"

  depends_on "python@3.12"

  # Vendor Python deps (fill versions/sha256 for an actual formula)
  resource "click" do
    url "https://files.pythonhosted.org/packages/<path>/click-8.1.7.tar.gz"
    sha256 "<fill-me>"
  end

  def install
    virtualenv_install_with_resources
  end

  test do
    assert_match version.to_s, shell_output("#{bin}/lib_cli_exit_tools --version")
  end
end

