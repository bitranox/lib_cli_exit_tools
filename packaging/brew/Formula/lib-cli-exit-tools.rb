class LibCliExitTools < Formula
  include Language::Python::Virtualenv

  desc "CLI exit handling helpers: clean signals, exit codes, and error printing"
  homepage "https://github.com/bitranox/lib_cli_exit_tools"
  url "https://github.com/bitranox/lib_cli_exit_tools/archive/refs/tags/v1.0.2.tar.gz"
k3cc316e7d0b09dd79e617cb3e91b14ee414b7e6695b108a326d9d3ccd08dd9"
  license "MIT"

  depends_on "python@3.10"

  # Vendor Python deps (fill versions/sha256 for an actual formula)
  resource "click" do
    url "https://files.pythonhosted.org/packages/60/6c/8ca2efa64cf75a977a0d7fac081354553ebe483345c734fb6b6515d96bbc/click-8.2.1.tar.gz"
k3cc316e7d0b09dd79e617cb3e91b14ee414b7e6695b108a326d9d3ccd08dd9"
  end

  def install
    virtualenv_install_with_resources
  end

  test do
    assert_match version.to_s, shell_output("#{bin}/lib_cli_exit_tools --version")
  end
end

