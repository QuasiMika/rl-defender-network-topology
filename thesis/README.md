# Bachelorarbeit, LaTeX-Projekt

Dokumentklasse: KOMA-Script (`scrreprt`) über `htwg-report.cls`, Deutsch,
`biblatex` mit `biber`.

## Kompilieren

### Weg A, ohne latexmk (kein Perl nötig)

In PowerShell oder cmd im Ordner `thesis\`:

```bat
.\build.bat
```

Das Skript ruft `pdflatex → biber → pdflatex → pdflatex` auf, alles native
`.exe`, kein Perl. Ergebnis: `thesis.pdf`.

### Weg B, mit latexmk

`latexmk` ist ein Perl-Skript. MiKTeX bringt es mit, braucht aber einen
Perl-Interpreter. Fehlt der, erscheint *„MiKTeX could not find the script
engine 'perl'"*. Abhilfe: [Strawberry Perl](https://strawberryperl.com)
installieren, danach:

```bash
latexmk -pdf thesis.tex
latexmk -c            # Build-Dateien aufräumen
```

## Struktur

```
thesis.tex              Hauptdatei: Präambel, Metadaten, Reihenfolge der Teile
htwg-report.cls         Dokumentklasse der HTWG-Vorlage
frontmatter/            Titelseite, Kurzfassung und Abstract, Abkürzungen, Erklärung
chapters/               01_einleitung bis 06_fazit, A_anhang
literatur.bib           Literaturdatenbank (biblatex)
abbildungen/            Grafiken und die gen_*.py, die sie aus den Rohdaten erzeugen
cover/                  Titelblatt-Elemente der Vorlage
pruefung/               Skripte, die jede Zahl der Arbeit gegen die Rohdaten nachrechnen
```

`graphicspath` zeigt auf `abbildungen/`. Wie die Abbildungen neu erzeugt
werden, steht in der README im Wurzelverzeichnis.

## Bekannte, harmlose Warnungen

Der Lauf meldet siebenmal `Label 'acro:SLA@cref' multiply defined` sowie rund
zwanzig `Overfull \hbox`. Ersteres stammt aus dem Zusammenspiel von `acro` und
`cleveref` bei mehrfach verwendeten Abkürzungen, Letzteres sind einzelne
Zeilen, die minimal über den Satzspiegel ragen. Beides wirkt sich nicht auf
Querverweise, Abkürzungen oder Zitate aus.
