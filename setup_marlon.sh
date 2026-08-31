#!/bin/bash
#
# Holt MARLon und wendet die Anpassungen dieser Arbeit an.
#
# MARLon (https://github.com/James-LG/MARLon) steht ohne Lizenz im Netz und darf
# deshalb nicht mitgeliefert werden. Dieses Skript laedt es beim Urheber,
# festgenagelt auf den Commit, gegen den entwickelt wurde, und spielt dann den
# Patch mit den Aenderungen dieser Arbeit ein (patches/marlon-thesis.patch).
#
# Aufruf:  ./setup_marlon.sh
#
set -euo pipefail

REPO="https://github.com/James-LG/MARLon.git"
COMMIT="210b96b"
ZIEL="$(cd "$(dirname "$0")" && pwd)/MARLon"
PATCH="$(cd "$(dirname "$0")" && pwd)/patches/marlon-thesis.patch"

if [ -d "$ZIEL" ]; then
  echo "FEHLER: $ZIEL existiert bereits."
  echo "        Zum Neuaufsetzen zuerst loeschen:  rm -rf MARLon"
  exit 1
fi

if [ ! -f "$PATCH" ]; then
  echo "FEHLER: Patch nicht gefunden: $PATCH"
  exit 1
fi

echo "1/3  MARLon holen (Commit $COMMIT) ..."
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
git clone --quiet "$REPO" "$TMP/marlon"
git -C "$TMP/marlon" checkout --quiet "$COMMIT"
rm -rf "$TMP/marlon/.git" "$TMP/marlon/.vscode"

echo "2/3  Anpassungen dieser Arbeit einspielen ..."
mv "$TMP/marlon" "$ZIEL"
# Der Patch wurde mit "diff -ruN a b" erzeugt, daher -p1.
if ! patch -s -p1 -d "$ZIEL" < "$PATCH"; then
  echo
  echo "FEHLER: Der Patch liess sich nicht anwenden."
  echo "        Vermutlich hat sich der Upstream-Stand geaendert."
  rm -rf "$ZIEL"
  exit 1
fi

echo "3/3  Pruefen ..."
mkdir -p "$ZIEL/models"
for f in marlon/baseline_models/env_wrappers/defend_wrapper.py \
         marlon/baseline_models/env_wrappers/attack_wrapper.py \
         marlon/convergence.py; do
  if [ ! -f "$ZIEL/$f" ]; then
    echo "FEHLER: erwartete Datei fehlt: $f"
    exit 1
  fi
done

echo
echo "Fertig. MARLon liegt unter ./MARLon und enthaelt die Anpassungen der Arbeit."
echo "Urheberrecht an MARLon: James La Novara-Gsell und Mitautoren, siehe README."
