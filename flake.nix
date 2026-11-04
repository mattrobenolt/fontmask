{
  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
  outputs = { self, nixpkgs }:
    let
      system = "aarch64-darwin";
      pkgs = import nixpkgs { inherit system; };
    in {
      devShells.${system}.default = pkgs.mkShell {
        packages = [
          (pkgs.python3.withPackages (ps: [
            ps.fonttools
            ps.brotli
            ps.uharfbuzz
            ps.pytest
          ]))
          pkgs.harfbuzz
          pkgs.dejavu_fonts
          pkgs.source-code-pro
          pkgs.roboto-mono
        ];
        shellHook = ''
          export PYTHONPATH="$PWD/src''${PYTHONPATH:+:$PYTHONPATH}"
          export FONTMASK_DEJAVU_SANS="${pkgs.dejavu_fonts}/share/fonts/truetype/DejaVuSans.ttf"
          export FONTMASK_DEJAVU_MONO="${pkgs.dejavu_fonts}/share/fonts/truetype/DejaVuSansMono.ttf"
          export FONTMASK_SOURCE_CODE_PRO="${pkgs.source-code-pro}/share/fonts/opentype/SourceCodePro-Regular.otf"
          export FONTMASK_ROBOTO_MONO="${pkgs.roboto-mono}/share/fonts/truetype/RobotoMono[wght].ttf"
        '';
      };
    };
}
