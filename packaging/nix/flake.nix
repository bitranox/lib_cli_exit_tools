{
  description = "bitranox_template_py_cli Nix flake";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-24.05";
  inputs.flake-utils.url = "github:numtide/flake-utils";

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };
        lib = pkgs.lib;
        pypkgs = pkgs.python310Packages;

        hatchlingVendor = pypkgs.buildPythonPackage rec {
          pname = "hatchling";
          version = "1.25.0";
          format = "wheel";
          src = pkgs.fetchurl {
            url = "https://files.pythonhosted.org/packages/py3/h/hatchling/hatchling-1.25.0-py3-none-any.whl";
            hash = "sha256-tHlI5F1NlzA0WE3UyznBS2pwInzyh6t+wK15g0CKiCw";
          };
          propagatedBuildInputs = [
            pypkgs.packaging
            pypkgs.tomli
            pypkgs.pathspec
            pypkgs.pluggy
            pypkgs."trove-classifiers"
            pypkgs.editables
          ];
          doCheck = false;
        };
        richClickVendor = pypkgs.buildPythonPackage rec {
          pname = "rich-click";
          version = "1.9.1";
          format = "wheel";
          src = pkgs.fetchurl {
            url = "https://files.pythonhosted.org/packages/a8/77/e9144dcf68a0b3f3f4386986f97255c3d9f7c659be58bb7a5fe8f26f3efa/rich_click-1.9.1-py3-none-any.whl";
            sha256 = "sha256-6mEUqeCBt9aMwHsxUHA5j4BvAbsODEnaVvEp5nKHeBc=";
          };
          doCheck = false;
        };

      in
      {
        packages.default = pypkgs.buildPythonPackage {
          pname = "lib_cli_exit_tools";
          version = "1.2.0";
          pyproject = true;
          src = ../..;
          nativeBuildInputs = [ hatchlingVendor ];
          propagatedBuildInputs = [ richClickVendor ];

          meta = with pkgs.lib; {
            description = "Rich-powered logging helpers for colorful terminal output";
            homepage = "https://github.com/bitranox/bitranox_template_py_cli";
            license = licenses.mit;
            maintainers = [];
            platforms = platforms.unix ++ platforms.darwin;
          };
        };

        devShells.default = pkgs.mkShell {
          packages = [
            pkgs.python310
            hatchlingVendor
            richClickVendor
            pypkgs.pytest
            pkgs.ruff
            pkgs.nodejs
          ];
        };
      }
    );
}
