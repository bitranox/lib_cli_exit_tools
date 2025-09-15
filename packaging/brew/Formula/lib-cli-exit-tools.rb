class LibCliExitTools < Formula
  include Language::Python::Virtualenv

  desc "CLI exit handling helpers: clean signals, exit codes, and error printing"
  homepage "https://github.com/bitranox/lib_cli_exit_tools"
  url "https://github.com/bitranox/lib_cli_exit_tools/archive/refs/tags/v1.0.0.tar.gz"
  sha256 "<fill-me>"
  license "MIT"

  depends_on "python@3.10"

  # Vendor Python deps (fill versions/sha256 for an actual formula)
  resource "click" do
    url "https://files.pythonhosted.org/packages/60/6c/8ca2efa64cf75a977a0d7fac081354553ebe483345c734fb6b6515d96bbc/click-8.2.1.tar.gz"
    sha256 "27c491cc05d968d271d5a1db13e3b5a184636d9d930f148c50b038f0d0646202"
  end

  def install
    virtualenv_install_with_resources
  end

  test do
    assert_match version.to_s, shell_output("#{bin}/lib_cli_exit_tools --version")
  end
end

