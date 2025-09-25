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
        clickVendor = pypkgs.buildPythonPackage rec {
          pname = "click";
          version = "8.1";
          format = "wheel";
          src = pkgs.fetchurl {
            url = "https://files.pythonhosted.org/packages/86/3e/3a523bdd24510288b1b850428e01172116a29268378b1da9a8d0b894a115/click-8.1.0-py3-none-any.whl";
            sha256 = "sha256-GaS6pk2pJMXgzYiauo6UfygDCfGizglHo+OnvLfMctY=";
          };
          doCheck = false;
        };

      in
      {
        packages.default = pypkgs.buildPythonPackage {
          pname = "lib_cli_exit_tools";
          version = "1.1.1";
          pyproject = true;
          src = ../..;
          nativeBuildInputs = [ hatchlingVendor ];
          propagatedBuildInputs = [ clickVendor ];

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
            clickVendor
            pypkgs.pytest
            pkgs.ruff
            pkgs.nodejs
          ];
        };
      }
    );
}
