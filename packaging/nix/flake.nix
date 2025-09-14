{
  description = "lib_cli_exit_tools Nix flake";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-24.05";
  inputs.flake-utils.url = "github:numtide/flake-utils";

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };
        pypkgs = pkgs.python312Packages;
      in
      {
        packages.default = pypkgs.buildPythonPackage {
          pname = "lib_cli_exit_tools";
          version = "0.1.0";
          pyproject = true;
          # Build from the repository root (two levels up from packaging/nix)
          src = ../..;
          # For pinned releases, swap src for fetchFromGitHub with a rev/sha256.
          # src = pkgs.fetchFromGitHub {
          #   owner = "bitranox";
          #   repo = "lib_cli_exit_tools";
          #   rev = "v0.1.0";
          #   sha256 = "<fill-me>";
          # };

          nativeBuildInputs = [ pypkgs.hatchling ];
          propagatedBuildInputs = [ pypkgs.click ];

          meta = with pkgs.lib; {
            description = "CLI exit handling helpers: clean signals, exit codes, and error printing";
            homepage = "https://github.com/bitranox/lib_cli_exit_tools";
            license = licenses.mit;
            maintainers = [];
            platforms = platforms.unix ++ platforms.darwin;
          };
        };

        devShells.default = pkgs.mkShell {
          packages = [
            pkgs.python312
            pypkgs.hatchling
            pypkgs.click
            pypkgs.pytest
            pkgs.ruff
            pkgs.nodejs
          ];
        };
      }
    );
}
