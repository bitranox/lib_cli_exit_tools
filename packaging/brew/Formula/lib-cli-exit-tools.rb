class LibCliExitTools < Formula
  include Language::Python::Virtualenv

  desc "CLI exit handling helpers: clean signals, exit codes, and error printing"
  homepage "https://github.com/bitranox/lib_cli_exit_tools"
  url "https://github.com/bitranox/lib_cli_exit_tools/archive/refs/tags/v1.6.0.tar.gz"
  sha256 "7546f92ac8efbd214c1d55ff75881616636cab151f373b13f4efc1e33975c1d5"
  license "MIT"

  depends_on "python@3.13"

  # Vendor Python deps (fill versions/sha256 for an actual formula)
  resource "click" do
    url "https://files.pythonhosted.org/packages/96/d3/f04c7bfcf5c1862a2a5b845c6b2b360488cf47af55dfa79c98f6a6bf98b5/click-8.1.7.tar.gz"
    sha256 "ca9853ad459e787e2192211578cc907e7594e294c7ccc834310722b41b9ca6de"
  end

  resource "rich-click" do
    url "https://files.pythonhosted.org/packages/0c/4d/e8fcbd785a93dc5d7aef38f8aa4ade1e31b0c820eb2e8ff267056eda70b1/rich_click-1.9.2.tar.gz"
    sha256 "1c4212f05561be0cac6a9c1743e1ebcd4fe1fb1e311f9f672abfada3be649db6"
  end

  def install
    virtualenv_install_with_resources
  end

  test do
    assert_match version.to_s, shell_output("#{bin}/lib_cli_exit_tools --version")
  end
end
