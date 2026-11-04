{
  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
    flake-parts.url = "github:hercules-ci/flake-parts";
  };

  outputs =
    inputs@{
      flake-parts,
      nixpkgs,
      ...
    }:
    flake-parts.lib.mkFlake { inherit inputs; } {
      systems = [
        "aarch64-darwin"
      ];

      perSystem =
        { pkgs, ... }:
        {
          formatter = pkgs.nixfmt-tree;

          devShells.default = pkgs.mkShell {
            packages = with pkgs; [
              uv
              harfbuzz
              dejavu_fonts
              source-code-pro
              roboto-mono
            ];

            env = {
              UV_PYTHON = "${pkgs.python315}/bin/python3";
              UV_PYTHON_DOWNLOADS = "never";
              FONTMASK_DEJAVU_SANS = "${pkgs.dejavu_fonts}/share/fonts/truetype/DejaVuSans.ttf";
              FONTMASK_DEJAVU_MONO = "${pkgs.dejavu_fonts}/share/fonts/truetype/DejaVuSansMono.ttf";
              FONTMASK_SOURCE_CODE_PRO = "${pkgs.source-code-pro}/share/fonts/opentype/SourceCodePro-Regular.otf";
              FONTMASK_ROBOTO_MONO = "${pkgs.roboto-mono}/share/fonts/truetype/RobotoMono[wght].ttf";
            };
          };
        };
    };
}
