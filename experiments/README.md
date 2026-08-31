# Versuchsläufe

Die Ordnernamen sind die Startzeitstempel der Läufe, wie
`run_experiment_matrix.py` sie vergibt. Dieselben Zeitstempel tauchen in den
Modell-Dateinamen, den `run_id`-Werten der CSVs und in `manifest.csv` wieder
auf, deshalb bleiben sie unverändert.

## `20260820_005936`, finaler Lauf

Grundlage **aller Zahlen der Arbeit**. Vollständige Matrix aus 4 verteidigten
Topologien × 6 Angreifern × 5 Seeds, je 500.000 Schritte, zusammen 60.211.200
Simulationsschritte. Dazu die Frozen-vs-Frozen-Evaluation über 360 Zellen und
9.000 Episoden.

Enthält den Verteidiger-Reward dieser Arbeit: Kantenbilanz-Abwehrbonus,
Haltebonus, additive SLA-Strafe, verkleinerter Aktionsraum.

| Datei | Inhalt |
|---|---|
| `combined_episodes.csv` | Trainingsepisoden aller 120 Läufe, 61.590 Zeilen |
| `evaluation_episodes.csv` | die 9.000 Evaluationsepisoden, zusätzlich Spalte `stufe` |
| `manifest.csv` | Übersicht aller Läufe mit Status |
| `deck/` | erzeugte Abbildungen und Kennzahlen des Auswertungs-Foliensatzes |
| `attackers/` | die eingefrorenen Angreifermodelle |
| `defenders/` | Trainings-Logs je Lauf (Modelle sind nicht im Repository) |

## `20260818_004656`, Referenzlauf

Der Stand **vor** dem Umbau des Verteidiger-Rewards, zum Vergleich aufbewahrt.
Hier war der Reward noch rein reaktiv, Prävention also nicht abbildbar. Wird in
der Arbeit für die Gegenüberstellung herangezogen, liefert aber keine der
Ergebniszahlen.

Gleiche Struktur wie oben; die Evaluationsdaten liegen hier noch getrennt nach
Rechner vor (`evaluation_pc_seed012.csv`, `evaluation_laptop_seed34.csv`).

## Was nicht im Repository liegt

Die trainierten **Verteidigermodelle** (`defenders/**/*.zip`, zusammen rund
800 MB). Für die Auswertung werden sie nicht gebraucht, wohl aber, um
`run_evaluation.py` erneut auszuführen.

Beim finalen Lauf entstand die Evaluation auf zwei Rechnern parallel, Seeds 0
bis 2 auf dem einen, 3 und 4 auf dem anderen. Die beiden Teildateien sind in
`evaluation_episodes.csv` zusammengeführt und deshalb nicht einzeln
mitgeliefert.
