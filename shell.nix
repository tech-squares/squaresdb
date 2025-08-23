{ pkgs ? import <nixpkgs> {} }:
pkgs.mkShellNoCC {
    packages = with pkgs; [
      nodejs_22 # npm
    ];
    shellHook = ''
    . ../../bin/activate
    '';
}
