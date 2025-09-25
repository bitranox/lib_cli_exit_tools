class LibCliExitTools < Formula
  include Language::Python::Virtualenv

  desc "CLI exit handling helpers: clean signals, exit codes, and error printing"
  homepage "https://github.com/bitranox/lib_cli_exit_tools"
  url "https://github.com/bitranox/lib_cli_exit_tools/archive/refs/tags/v1.3.0.tar.gz"
k3cc316e7d0b09dd79e617cb3e91b14ee414b7e6695b108a326d9d3ccd08dd9"
  license "MIT"

  depends_on "python@3.10"

  # Vendor Python deps (fill versions/sha256 for an actual formula)
  resource "click" do
    url "https://files.pythonhosted.org/packages/46/61/de6cd827efad202d7057d93e0fed9294b96952e188f7384832791c7b2254/click-8.3.0.tar.gz"
k3cc316e7d0b09dd79e617cb3e91b14ee414b7e6695b108a326d9d3ccd08dd9"
  end

  resource "rich-click" do
    url "https://files.pythonhosted.org/packages/29/c2/f08b5e7c1a33af8a115be640aa0796ba01c4732696da6d2254391376b314/rich_click-1.9.1.tar.gz"
ab87be0f5a4c171b43778922b5ed1f99611a0db5a4bf4d0f36770c18ef848d4"
  end

  def install
    virtualenv_install_with_resources
  end

  test do
    assert_match version.to_s, shell_output("#{bin}/lib_cli_exit_tools --version")
  end
end

