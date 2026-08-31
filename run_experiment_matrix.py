#!/usr/bin/env python3
"""
Orchestriert die komplette Experiment-Matrix fuer die Bachelorarbeit, wie mit
der Professorin abgestimmt.

Phase 1 - Attacker-Pretraining (kein Defender, je Topologie ein Modell):
    5 solo-trainierte Attacker: chain, flat, hub_and_spoke, dmz, micro_segmented
    1 Super-Attacker: sequenziell ueber alle 5 Topologien in derselben
    Reihenfolge trainiert (ein Modell, Gewichte werden zwischen den Stufen
    weitergereicht).

Phase 2 - Defender-Matrix:
    Fuer jede der 4 Vergleichstopologien (flat, hub_and_spoke, dmz,
    micro_segmented) wird ein Defender gegen jeden der 6 Attacker aus Phase 1
    trainiert (Attacker eingefroren) -> 4 x 6 = 24 Laeufe.
    Chain und der reine Solo-Lauf sind kein Vergleichsfall der Arbeit und
    werden daher nicht als Defender-Topologie verwendet, nur als
    Attacker-Herkunft.

Alle Modelle + CSV-Trainingslogs landen gebuendelt unter
experiments/<timestamp>/{attackers,defenders}/... plus einer manifest.csv
als Gesamtuebersicht und einer combined_episodes.csv, die die
Episode-Zeilen aller Laeufe dieses Experiments zusammenfuehrt (fuer Plots
ueber die gesamte Matrix).

Wiederaufnahme: jeder Lauf legt bei Erfolg eine _DONE-Markerdatei in seinem
eigenen Ordner an. Ein Neustart mit --experiment-dir <ordner> ueberspringt
bereits abgeschlossene Laeufe und macht nur mit den fehlenden weiter.

Bekannte Einschraenkung: BaselineMarlonAgent.learn() setzt SB3s
reset_num_timesteps nicht auf False, d.h. der num_timesteps-Zaehler (nur
fuer Logging/LR-Schedules relevant) startet pro Super-Attacker-Stufe neu bei
0. Die Modellgewichte selbst werden trotzdem korrekt von Stufe zu Stufe
weitertrainiert (ueber das geladene .zip), das betrifft nur die Zeitstempel
in den Trainings-Logs der einzelnen Stufen.

Nutzung
-------
    python3 run_experiment_matrix.py                     # volle Matrix, 300k/300k
    python3 run_experiment_matrix.py --dry-run            # nur Plan anzeigen
    python3 run_experiment_matrix.py --attacker-steps 50000 --defender-steps 50000
                                                            # schneller Testlauf
    python3 run_experiment_matrix.py --experiment-dir experiments/20260710_140000
                                                            # abgebrochenen Lauf fortsetzen

Fuer einen kurzen Konfigurations-Testlauf mit kleineren Defaults:
run_experiment_matrix_test.py (identischer Ablauf, eigener experiments_test/-Ordner).
"""

import experiment_matrix_lib as lib

if __name__ == "__main__":
    lib.main(
        doc=__doc__,
        default_attacker_steps=500_000,
        default_defender_steps=500_000,
        experiments_dirname="experiments",
        new_experiment_label="Neues Experiment",
    )
