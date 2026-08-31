# Einfluss der Netzwerktopologie auf RL-Verteidigungsagenten

Wie stark hängt es von der Struktur eines Netzes ab, was ein mit Reinforcement
Learning trainierter Verteidiger ausrichten kann? Um das messbar zu machen,
verteidigen PPO-Agenten vier Topologien mit **identischem Inventar**: gleiche
Knoten, gleiche Werte, gleiche Schwachstellen, gleiche Reward-Kapazität. Nur die
Erreichbarkeit zwischen den Knoten unterscheidet sich, die Topologie ist damit
die einzige unabhängige Variable. Gegner sind sechs eingefrorene Angreifer, fünf
davon je auf einer Topologie spezialisiert, einer gestuft über alle trainiert.

## Ergebnis

**Auf die Lerngeschwindigkeit ließ sich kein Einfluss der Topologie nachweisen,
auf das erreichte Ergebnis dagegen ein deutlicher.** Mit zunehmender
Segmentierung sinkt der Anteil der Episoden, in denen der Angreifer den Crown
Jewel erreicht, vom nahezu ungebremsten Zugriff im vollvermaschten Netz bis zur
weitgehenden Unterbindung in der Mikrosegmentierung.

| Verteidigte Topologie | ohne Verteidiger | Zufallsagent | trainiertes Modell | Restanteil |
|---|---:|---:|---:|---:|
| `flat` (vollvermascht) | 92,3 % | 88,4 % | **60,5 %** | 8,2 % |
| `hub_and_spoke` | 83,1 % | 53,5 % | **10,8 %** | 4,4 % |
| `dmz` | 94,8 % | 50,5 % | **8,1 %** | 3,6 % |
| `micro_segmented` | 83,3 % | 49,6 % | **2,8 %** | 4,5 % |

Crown-Jewel-Quote je Verteidigungsstufe, gemittelt über die sechs Angreifer.
*Restanteil* = Angreifer-Reward gegen das trainierte Modell, gemessen am
ungeschützten Netz; kleiner ist besser.

Den Mechanismus dahinter liefert das Aktionsverhalten: Wo die Struktur Engpässe
bietet, greifen Sperren. Im vollvermaschten Netz weicht der Angreifer jeder
Sperre aus, und auch dem trainierten Verteidiger bleibt kein wirksames Mittel.
Die beiden teilsegmentierten Topologien trennen sich untereinander kaum. Der auf
der verteidigten Topologie trainierte Angreifer ist durchweg der härteste
Gegner. Methodisch zeigt die Arbeit außerdem, dass der Reward allein die
Verteidigungsleistung nicht abbildet: Das von MARLon übernommene Reward-Design
ließ Prävention unsichtbar.

Die vollständige Arbeit: [`thesis/thesis.pdf`](thesis/thesis.pdf) (117 Seiten).

## Umfang

|  |  |
|---|---|
| Versuchsmatrix | 4 Topologien × 6 Angreifer × 5 Seeds |
| Trainingsläufe | 120, je 500.000 Schritte |
| Simulationsschritte | 60.211.200 |
| Evaluationsepisoden | 9.000 (360 Zellen × 25) |
| Vergleichsstufen | kein Verteidiger, Zufallsagent, trainiertes Modell |

## Was aus welcher Quelle stammt

**Von Microsoft (CyberBattleSim):** die Simulationsumgebung, das
Knoten-Schwachstellen-Modell, der Angreifer-Aktionsraum und die
Gym-Schnittstelle. MIT-lizenziert und deshalb hier mitgeliefert.

**Von MARLon (Kunz et al.):** die Mehragenten-Erweiterung, die CyberBattleSim
überhaupt erst um einen *lernenden* Verteidiger ergänzt, sowie die
Wrapper-Architektur für beide Seiten. MARLon steht ohne Lizenz im Netz, also
unter Vorbehalt aller Rechte, und wird deshalb **nicht mitgeliefert**:
`setup_marlon.sh` holt es beim Urheber auf einem festgepinnten Commit und
spielt anschließend `patches/marlon-thesis.patch` mit den Änderungen dieser
Arbeit ein.

**Eigener Beitrag dieser Arbeit:**

- **Vier Topologiedefinitionen mit festem Inventar** (`thesis_topology/`), damit
  die Topologie als einzige Variable isolierbar ist, samt Validator und
  Metriken.
- **Abwehrbonus als Kantenbilanz** im Verteidiger-Reward. MARLons Reward ist
  rein reaktiv und kann laut Paper höchstens null erreichen; Prävention war
  darin nicht darstellbar. Neu bewertet ein Zustandsterm, ob eine Sperre
  tatsächlich einen Angriffsweg schneidet:
  `Beitrag(Z) = 0,00025 · Wert(Z) · (2f − 1)` mit `f` als Anteil der
  kompromittierten Vorgänger von Knoten `Z`.
- **Haltebonus und Eviction-Strafe**, damit der Reward nicht nur misst, *ob* ein
  System kompromittiert wurde, sondern auch *wie lange*.
- **Umbau des Verteidiger-Aktionsraums** von zwölf auf vier Dimensionen
  (`[3, 10, 10, 10]`): Reimage, Sperren, Freigeben je Knoten. Dienst stoppen und
  starten entfallen; Port und Richtung ergeben sich aus dem Knoten, da ein
  Verteidiger die Dienste des eigenen Netzes kennt.
- **Invalid-Action-Masking** für den Angreifer nach Huang und Ontañón (2022),
  zusätzlich an die tatsächlich entdeckten Kanten gebunden. Die Maske von
  CyberBattleSim prüft nur Zugangsdaten, nicht Erreichbarkeit; eine eigene
  Kantenverfolgung schneidet sie auf das zu, was `ScanHostDiscovery` aufgedeckt
  hat.
- **Korrektur dreier geerbter Fehler** in MARLons Verteidiger: eine fest
  verdrahtete Portliste, `block_traffic` löschte die ALLOW-Regel statt BLOCK zu
  setzen, und `allow_traffic` schrieb durch einen Copy-Paste-Fehler immer nach
  `incoming`. Zusätzlich zählen gesperrte Ports jetzt gegen die Verfügbarkeit,
  und die SLA-Strafe ist additiv statt den Reward zu ersetzen.
- **Die gesamte Auswertung**: Versuchssteuerung, Frozen-vs-Frozen-Evaluation,
  Konvergenzkriterium, Abbildungen und Foliensätze.

## Verzeichnisstruktur

```
thesis/               LaTeX-Quellen und PDF; abbildungen/ erzeugt die Grafiken
                      aus den Rohdaten, pruefung/ rechnet jede Zahl der Arbeit nach
thesis_topology/      Topologie-Generator: die vier Vergleichsnetze
patches/              Änderungen dieser Arbeit an MARLon, als Patch
setup_marlon.sh       holt MARLon und wendet den Patch an
CyberBattleSim/       Fork von Microsofts CyberBattleSim (MIT)
experiments/          Rohdaten und Ergebnisse zweier Läufe
run_experiment_matrix.py   Phase 1 Angreifer-Vortraining, Phase 2 Verteidigermatrix
run_evaluation.py          Evaluation der eingefrorenen Politiken
prep_*.py, make_deck_*.js  Auswertung und Foliensätze
```

## Umgebung

Python 3.10 unter Linux (getestet in WSL 2).

| Paket | Version |
|---|---|
| torch | 2.11.0 |
| stable-baselines3 | 2.8.0 |
| sb3-contrib | 2.8.0 (MaskablePPO) |
| gymnasium | 0.29.1 |
| numpy | 1.26.4 |
| networkx | 3.2.1 |
| matplotlib | 3.10.8 |

Alles zusammen installiert die `requirements.txt` im Wurzelverzeichnis:

```bash
pip install -r requirements.txt
```

Sie bindet `CyberBattleSim/requirements.txt` ein (dort stehen gymnasium, numpy,
networkx, plotly, pandas und weitere) und ergänzt die Lernverfahren torch,
stable-baselines3 und sb3-contrib, die dort **nicht** aufgeführt sind. Wer nur
die Datei der Simulationsumgebung installiert, kann die Trainingsskripte nicht
starten.

Voraussetzungen ausserhalb von Python: `git` und `patch` für
`setup_marlon.sh`, sowie eine Netzverbindung, da MARLon beim Urheber geholt
wird. Unter Windows läuft das Skript in WSL oder Git Bash, nicht in
PowerShell.

> `MARLon/requirements.txt` stammt unverändert aus dem Upstream-Projekt und
> beschreibt **nicht** diese Umgebung (dort noch `gym`, SB3 1.3.0, torch 1.10).
> Für die Foliensätze zusätzlich Node.js mit `pptxgenjs` (`npm install`).

## Nachvollziehen

Die Rohdaten beider Läufe liegen im Repository. Alle Abbildungen und Zahlen
lassen sich daraus erzeugen, **ohne neu zu trainieren**, dafür genügen die
Schritte 3 bis 5.

```bash
# 0. Abhängigkeiten und MARLon (einmalig, Voraussetzung für alles Weitere)
pip install -r requirements.txt
./setup_marlon.sh

# 1. Angreifer-Vortraining und Verteidigermatrix           [~2,5 h / ~24 h]
python3 run_experiment_matrix.py --dry-run    # zeigt nur den Plan
python3 run_experiment_matrix.py

# 2. Evaluation der eingefrorenen Politiken                [~9 h]
#    (braucht die Modelle aus Schritt 1, siehe "Daten im Repository")
python3 run_evaluation.py experiments/20260820_005936 --workers 6

# 3. Rohdaten zusammenführen und Kennzahlen berechnen      [~1 min]
python3 aggregate_experiment.py experiments/20260820_005936
python3 prep_analysis.py   experiments/20260820_005936 experiments/20260820_005936/deck/analysis.json
python3 prep_konvergenz.py experiments/20260820_005936 experiments/20260820_005936/deck/analysis.json
python3 prep_deck_extra.py experiments/20260820_005936 experiments/20260820_005936/deck/deck_extra.json

# 4. Abbildungen der Arbeit                                [~2 min]
python3 thesis/abbildungen/gen_lernkurven.py experiments/20260820_005936 thesis/abbildungen
python3 thesis/abbildungen/gen_cj.py         experiments/20260820_005936 thesis/abbildungen
python3 thesis/abbildungen/gen_matrizen.py   experiments/20260820_005936 thesis/abbildungen

# 5. Foliensatz der Gesamtauswertung                       [~1 min]
python3 prep_curves.py      experiments/20260820_005936 experiments/20260820_005936/deck
python3 prep_abwehrbonus.py experiments/20260820_005936 experiments/20260820_005936/deck
python3 prep_cj_verlauf.py  experiments/20260820_005936 experiments/20260820_005936/deck
node make_deck_gesamtauswertung_v3.js \
     experiments/20260820_005936/deck/analysis.json \
     experiments/20260820_005936/deck \
     experiments/20260820_005936/defender_matrix_gesamtauswertung.pptx
```

Die Laufzeiten in Schritt 1 und 2 gelten für zwei parallel rechnende Maschinen
(6 bzw. 7 Prozesse). Die Arbeit selbst wird mit `pdflatex → biber → pdflatex ×2`
gesetzt, unter Windows über `thesis/build.bat`.

Jede im Text genannte Zahl lässt sich unabhängig nachrechnen:

```bash
python3 thesis/pruefung/pruefe_training.py     # Tabellen aus Kapitel 4
python3 thesis/pruefung/pruefe_restanteil.py   # Wirksamkeit der Evaluation
python3 thesis/pruefung/pruefe_konvergenz.py   # Konvergenzkriterium
```

## Daten im Repository

`experiments/20260820_005936/` enthält den Lauf, auf dem alle Zahlen der Arbeit
beruhen, `20260818_004656` den Referenzlauf vor dem Reward-Umbau.

| Datei | Inhalt |
|---|---|
| `combined_episodes.csv` | eine Zeile je Episode und Agent, 61.590 Zeilen, 31 Spalten (Reward, Episodenlänge, Aktionszähler, SLA-Brüche, Crown Jewel, gehaltene Knoten) |
| `evaluation_episodes.csv` | dasselbe Schema für die 9.000 Evaluationsepisoden, zusätzlich die Spalte `stufe` |
| `manifest.csv` | Übersicht aller Läufe mit Status und Modellpfaden |
| `deck/` | erzeugte Abbildungen und Kennzahlen des Foliensatzes |
| `attackers/` | die eingefrorenen Angreifermodelle |

**Nicht enthalten** sind die trainierten Verteidigermodelle (rund 800 MB). Für
die Auswertung werden sie nicht gebraucht, wohl aber, um `run_evaluation.py`
erneut auszuführen.

## Lizenz

Der Code dieser Arbeit steht unter der MIT-Lizenz (siehe `LICENSE`). Die
Bachelorarbeit selbst, ihre Abbildungen und die Messdaten sind davon
ausgenommen; Näheres regelt der zweite Teil der `LICENSE`.

## Herkunft

- **CyberBattleSim**, Microsoft Corporation, MIT-Lizenz
  ([Projektseite](https://github.com/microsoft/CyberBattleSim), Lizenztext unter
  `CyberBattleSim/LICENSE`)
- **MARLon**, Kunz et al., *A Multiagent CyberBattleSim for RL Cyber Operation
  Agents*, CSCI 2022,
  [DOI 10.1109/CSCI58124.2022.00161](https://doi.org/10.1109/CSCI58124.2022.00161);
  Quellcode unter [github.com/James-LG/MARLon](https://github.com/James-LG/MARLon).
  Das Projekt führt keine Lizenz, weshalb hier nur der eigene Patch liegt und der
  Code beim Urheber geholt wird. Das Urheberrecht daran liegt bei den Autoren.
- **Invalid-Action-Masking** nach Huang und Ontañón, *A Closer Look at Invalid
  Action Masking in Policy Gradient Algorithms*, FLAIRS 2022,
  [DOI 10.32473/flairs.v35i.130584](https://doi.org/10.32473/flairs.v35i.130584)
- Die LaTeX-Vorlage basiert auf einer HTWG-Vorlage von Markus Funke
  (MIT-Lizenz, `thesis/LICENSE-htwg-template`)

## Zitieren

Siehe `CITATION.cff`, oder direkt:

```bibtex
@thesis{topologie-rl-verteidigung-2026,
  title  = {Einfluss der Netzwerktopologie auf Reinforcement-Learning-basierte
            Verteidigungsagenten in simulierten Cyberangriffsszenarien},
  school = {Hochschule Konstanz Technik, Wirtschaft und Gestaltung},
  type   = {Bachelorarbeit},
  year   = {2026},
}
```
