#!/usr/bin/env python3
"""
Erzeugt die Verlaufsdiagramme je verteidigter Topologie und eine Tabelle der
Angreifer-Rewards.

Anders als prep_analysis.py wird hier NICHT auf die Laenge des kuerzesten Seeds
gekuerzt. Stattdessen laeuft die Mittelung so weit, wie noch Seeds Daten
liefern, und es wird sichtbar gemacht, ab wann wie viele Seeds ausgestiegen
sind. Ein Seed steigt aus, wenn sein Lauf endet -- entweder durch Konvergenz
(Auto-Stop) oder weil das Schrittlimit erreicht wurde.

Aufruf:
    python prep_curves.py <experiment-dir> [ausgabe-verzeichnis]

Ausgabe:
    verlauf_<topologie>.png   je verteidigter Topologie, 2x3-Raster
    attacker_table.json       Kennzahlen fuer die Tabellenfolie
"""
from __future__ import annotations

import csv
import json
import os
import statistics
import sys
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

# Schrittlimit je Lauf; wer darunter endet, hat vorzeitig gestoppt.
STEP_LIMIT = 490_000
GLAETTUNG = 5

DEFS = ["flat", "hub_and_spoke", "dmz", "micro_segmented"]
ATKS = ["chain", "flat", "hub_and_spoke", "dmz", "micro_segmented", "super"]
KURZ = {
    "flat": "Flat", "hub_and_spoke": "Hub & Spoke", "dmz": "DMZ",
    "micro_segmented": "Micro-Segmentation", "chain": "Chain", "super": "Super",
}
# Sehr kurze Namen fuer das dichte 4x6-Raster der SLA-Abbildung.
ENG = {
    "flat": "Flat", "hub_and_spoke": "H&S", "dmz": "DMZ",
    "micro_segmented": "µSeg", "chain": "Chain", "super": "Super",
}

# Verteidiger-Aktionen. Die fuenf Kategorien summieren sich je Episode auf die
# Episodenlaenge, lassen sich also als Anteil darstellen. Reihenfolge = Stapel
# von unten nach oben: die wenigen wirksamen Aktionen unten, damit sie an der
# Grundlinie ablesbar bleiben; die dominierenden ungueltigen Zuege oben.
# def_start_svc ist ueberall 0 und deshalb nicht enthalten.
AKTIONEN = [
    ("def_reimage", "Reimage", "#2E9BC4"),
    # Bewusst NICHT gold: Gold ist in allen Abbildungen fuer den Ausstieg eines
    # konvergierten Seeds reserviert.
    ("def_stop_svc", "Dienst stoppen", "#C25E7A"),
    ("def_block", "Blockieren", "#8E6FB8"),
    ("def_allow", "Freigeben", "#3F7183"),
    ("def_invalid", "ungültig", "#454D57"),
]

# Palette wie im Foliensatz
DARK = "#1B1F26"
INK = "#23282F"
MUTED = "#6E7681"
DEF_C = "#2E9BC4"
ATK_C = "#D9584A"
GOLD = "#D99A2B"
GRID = "#333A44"


def glaetten(werte, w=GLAETTUNG):
    if len(werte) < w:
        return list(werte)
    out = []
    for i in range(len(werte)):
        a = max(0, i - w // 2)
        b = min(len(werte), i + w // 2 + 1)
        out.append(sum(werte[a:b]) / (b - a))
    return out


def lade(root):
    """run_id -> (topologie, angreifer, seed); dazu die Episodenreihen."""
    meta = {}
    for r in csv.DictReader(open(os.path.join(root, "manifest.csv"))):
        if r["phase"] != "defender_matrix" or not r["csv_log"]:
            continue
        teile = r["csv_log"].replace("\\", "/").split("/")
        seed = next((t for t in teile if t.startswith("seed")), "seed?")
        rid = os.path.basename(r["csv_log"])[len("training_log_"):-len(".csv")]
        meta[rid] = (r["topology"], r["attacker_name"], seed)

    reihen = defaultdict(lambda: defaultdict(list))   # rid -> agent -> [(ep, reward)]
    aktionen = defaultdict(list)                      # rid -> [(ep, {feld: wert})]
    sla = defaultdict(list)                           # rid -> [(ep, sla_break_steps)]
    letzter_step = defaultdict(int)
    pfad = os.path.join(root, "combined_episodes.csv")
    for r in csv.DictReader(open(pfad)):
        if r["phase"] != "defender_matrix" or not r["episode_reward"]:
            continue
        rid = r["run_id"]
        reihen[rid][r["agent"]].append((int(r["episode"]), float(r["episode_reward"])))
        letzter_step[rid] = max(letzter_step[rid], int(r["timestep"] or 0))
        if r["agent"] == "defender" and r.get("def_invalid"):
            aktionen[rid].append((int(r["episode"]),
                                  {f: float(r[f] or 0) for f, _lbl, _c in AKTIONEN}))
            sla[rid].append((int(r["episode"]), float(r.get("def_sla_break_steps") or 0)))
    for rid in sla:
        sla[rid] = [v for _ep, v in sorted(sla[rid])]
    return meta, reihen, letzter_step, aktionen, sla


def matchup_daten(meta, reihen, letzter_step, topo, atk):
    """Mittelkurven ueber Seeds + Ausstiegspunkte."""
    seeds = []
    for rid, (t, a, s) in meta.items():
        if t == topo and a == atk and rid in reihen:
            d = sorted(reihen[rid].get("defender", []))
            an = sorted(reihen[rid].get("attacker", []))
            if d:
                seeds.append({
                    "seed": s,
                    "def": [v for _, v in d],
                    "atk": [v for _, v in an],
                    "n_ep": len(d),
                    "autostop": letzter_step[rid] < STEP_LIMIT,
                })
    if not seeds:
        return None
    seeds.sort(key=lambda x: x["seed"])
    max_ep = max(s["n_ep"] for s in seeds)

    def mittel(key):
        """
        Mittel ueber die Seeds, die an dieser Stelle etwas beizutragen haben.

        Fortgeschrieben wird NUR ein Seed, der KONVERGIERT ist: Das
        Konvergenzkriterium sagt genau aus, dass sein Wert stabil bleibt, also
        ist der letzte Wert die beste Schaetzung fuer jede weitere Episode.

        Ein Seed, der am SCHRITTLIMIT endet, ist nicht stabil -- er war noch in
        Bewegung, haeufig sogar divergent. Sein letzter Wert wird deshalb nicht
        fortgeschrieben; der Seed faellt aus dem Mittel heraus.

        Rueckgabe: (kurve, beitragend) -- beitragend zaehlt laufende plus
        fortgeschriebene Seeds, ist also die Zahl, auf der der Mittelwert
        tatsaechlich beruht.
        """
        kurve, beitragend = [], []
        for i in range(max_ep):
            werte = []
            for s in seeds:
                reihe = s[key]
                if not reihe:
                    continue
                if i < len(reihe):
                    werte.append(reihe[i])
                elif s["autostop"]:
                    werte.append(reihe[-1])      # stabil, fortgeschrieben
                # sonst: am Schrittlimit geendet -> faellt heraus
            if not werte:
                break
            kurve.append(statistics.mean(werte))
            beitragend.append(len(werte))
        return kurve, beitragend

    dk, dn = mittel("def")
    ak, _ = mittel("atk")
    return {
        "def": glaetten(dk), "atk": glaetten(ak), "n": dn,
        "stops": [(s["n_ep"], s["autostop"], s["seed"]) for s in seeds],
        "n_seeds": len(seeds),
    }


def zeichne(root, out_dir, meta, reihen, letzter_step):
    for topo in DEFS:
        fig, achsen = plt.subplots(2, 3, figsize=(13.0, 6.1), facecolor=DARK)
        fig.subplots_adjust(left=0.055, right=0.985, top=0.90, bottom=0.13,
                            wspace=0.20, hspace=0.42)
        for k, atk in enumerate(ATKS):
            ax = achsen[k // 3][k % 3]
            ax.set_facecolor(DARK)
            for sp in ax.spines.values():
                sp.set_color(GRID)
            ax.tick_params(colors=MUTED, labelsize=7.5)
            ax.grid(True, color=GRID, linewidth=0.6, alpha=0.7)
            ax.set_axisbelow(True)

            d = matchup_daten(meta, reihen, letzter_step, topo, atk)
            if not d:
                ax.text(0.5, 0.5, "keine Daten", color=MUTED, ha="center",
                        transform=ax.transAxes, fontsize=9)
                ax.set_title(KURZ[atk], color=MUTED, fontsize=10, pad=6)
                continue

            ax.axhline(0, color=MUTED, linewidth=0.7, alpha=0.6)

            # Bereich, in dem der Mittelwert nicht mehr auf allen Seeds beruht
            voll = d["n_seeds"]
            erster_abfall = next((i for i, n in enumerate(d["n"]) if n < voll), None)
            if erster_abfall is not None:
                ax.axvspan(erster_abfall + 1, len(d["def"]),
                           color="#FFFFFF", alpha=0.055, zorder=0)

            # Volle Deckkraft nur dort, wo alle Seeds beitragen.
            def zeichne_reihe(reihe, farbe):
                if not reihe:
                    return
                xs = list(range(1, len(reihe) + 1))
                ax.plot(xs, reihe, color=farbe, linewidth=1.5, alpha=0.42)
                bis = erster_abfall if erster_abfall is not None else len(reihe)
                bis = min(bis, len(reihe))
                if bis > 1:
                    ax.plot(xs[:bis], reihe[:bis], color=farbe, linewidth=1.8)

            zeichne_reihe(d["def"], DEF_C)
            zeichne_reihe(d["atk"], ATK_C)

            # Ausstiegspunkte der Seeds
            for ep, autostop, _s in d["stops"]:
                ax.axvline(ep, color=GOLD if autostop else MUTED,
                           linestyle="--" if autostop else ":",
                           linewidth=1.0, alpha=0.85 if autostop else 0.55)

            stops = sum(1 for _, a, _ in d["stops"] if a)
            rest = d["n"][-1] if d["n"] else 0
            titel = "%s   %d/%d vorzeitig beendet" % (KURZ[atk], stops, voll)
            if rest < voll:
                titel += "   ·   zuletzt %d Seed%s" % (rest, "" if rest == 1 else "s")
            ax.set_title(titel, color="#E6EAF0", fontsize=9.5, pad=6, loc="left")
            if k // 3 == 1:
                ax.set_xlabel("Episode", color=MUTED, fontsize=8)
            if k % 3 == 0:
                ax.set_ylabel("Reward", color=MUTED, fontsize=8)

        fig.suptitle("Reward-Verlauf — Verteidiger auf %s" % KURZ[topo],
                     color="#FFFFFF", fontsize=15, x=0.055, ha="left", y=0.975)
        legende = [
            Line2D([0], [0], color=DEF_C, lw=2, label="Verteidiger"),
            Line2D([0], [0], color=ATK_C, lw=2, label="Angreifer"),
            Line2D([0], [0], color="#9AA4AE", lw=2, alpha=0.45,
                   label="blass: Mittel beruht nicht mehr auf allen 5 Seeds"),
            Line2D([0], [0], color=GOLD, lw=1.2, ls="--",
                   label="Seed vorzeitig beendet (Auto-Stop) → Wert wird fortgeschrieben"),
            Line2D([0], [0], color=MUTED, lw=1.2, ls=":",
                   label="Seed endet am Schrittlimit → fällt aus dem Mittel"),
        ]
        fig.legend(handles=legende, loc="lower center", ncol=5, frameon=False,
                   labelcolor="#B8C0C9", fontsize=8.0, bbox_to_anchor=(0.5, 0.005))
        pfad = os.path.join(out_dir, "verlauf_%s.png" % topo)
        fig.savefig(pfad, dpi=170, facecolor=DARK)
        plt.close(fig)
        print("  " + pfad)


def aktions_daten(meta, aktionen, letzter_step, topo, atk):
    """Anteil je Aktionsart und Episode, gemittelt nach denselben Seed-Regeln."""
    seeds = []
    for rid, (t, a, s) in meta.items():
        if t == topo and a == atk and rid in aktionen:
            folge = [w for _ep, w in sorted(aktionen[rid])]
            if folge:
                seeds.append({"reihe": folge, "seed": s,
                              "autostop": letzter_step[rid] < STEP_LIMIT})
    if not seeds:
        return None
    seeds.sort(key=lambda x: x["seed"])
    max_ep = max(len(s["reihe"]) for s in seeds)
    anteile = {f: [] for f, _l, _c in AKTIONEN}
    beitragend = []
    for i in range(max_ep):
        proben = []
        for s in seeds:
            if i < len(s["reihe"]):
                proben.append(s["reihe"][i])
            elif s["autostop"]:
                proben.append(s["reihe"][-1])
        if not proben:
            break
        beitragend.append(len(proben))
        for f, _l, _c in AKTIONEN:
            werte = []
            for p in proben:
                gesamt = sum(p[g] for g, _l2, _c2 in AKTIONEN)
                werte.append(100.0 * p[f] / gesamt if gesamt else 0.0)
            anteile[f].append(statistics.mean(werte))
    for f in anteile:
        anteile[f] = glaetten(anteile[f], 3)
    return {
        "anteile": anteile, "n": beitragend, "n_seeds": len(seeds),
        "stops": [(len(s["reihe"]), s["autostop"], s["seed"]) for s in seeds],
    }


def zeichne_aktionen(out_dir, meta, aktionen, letzter_step):
    for topo in DEFS:
        fig, achsen = plt.subplots(2, 3, figsize=(13.0, 6.4), facecolor=DARK)
        fig.subplots_adjust(left=0.055, right=0.985, top=0.90, bottom=0.185,
                            wspace=0.20, hspace=0.40)
        for k, atk in enumerate(ATKS):
            ax = achsen[k // 3][k % 3]
            ax.set_facecolor(DARK)
            for sp in ax.spines.values():
                sp.set_color(GRID)
            ax.tick_params(colors=MUTED, labelsize=7.5)
            ax.set_axisbelow(True)

            d = aktions_daten(meta, aktionen, letzter_step, topo, atk)
            if not d:
                ax.text(0.5, 0.5, "keine Daten", color=MUTED, ha="center",
                        transform=ax.transAxes, fontsize=9)
                continue

            n = len(d["anteile"][AKTIONEN[0][0]])
            x = list(range(1, n + 1))
            ax.stackplot(x, *[d["anteile"][f] for f, _l, _c in AKTIONEN],
                         colors=[c for _f, _l, c in AKTIONEN], linewidth=0)
            ax.set_xlim(1, max(n, 2))
            ax.set_ylim(0, 100)

            voll = d["n_seeds"]
            abfall = next((i for i, m in enumerate(d["n"]) if m < voll), None)
            # Abschnitt ohne volle Seed-Zahl abdunkeln, ueber dem Stapel
            if abfall is not None:
                ax.axvspan(abfall + 1, n, color=DARK, alpha=0.42, zorder=3)

            # Ausstiegspunkte wie in den Reward-Kurven kennzeichnen
            for ep, autostop, _s in d["stops"]:
                ax.axvline(ep, color=GOLD if autostop else "#C3CAD2",
                           linestyle="--" if autostop else ":",
                           linewidth=1.0, alpha=0.9 if autostop else 0.7, zorder=4)

            stops = sum(1 for _, a2, _ in d["stops"] if a2)
            rest = d["n"][-1] if d["n"] else 0
            titel = "%s   %d/%d vorzeitig beendet" % (KURZ[atk], stops, voll)
            if rest < voll:
                titel += "   ·   zuletzt %d Seed%s" % (rest, "" if rest == 1 else "s")
            ax.set_title(titel, color="#E6EAF0", fontsize=9.5, pad=6, loc="left")
            if k // 3 == 1:
                ax.set_xlabel("Episode", color=MUTED, fontsize=8)
            if k % 3 == 0:
                ax.set_ylabel("Anteil der Schritte (%)", color=MUTED, fontsize=8)

        fig.suptitle("Aktionsverteilung des Verteidigers — auf %s" % KURZ[topo],
                     color="#FFFFFF", fontsize=15, x=0.055, ha="left", y=0.975)
        from matplotlib.patches import Patch
        legende = [Patch(facecolor=c, label=l) for _f, l, c in reversed(AKTIONEN)]
        legende += [
            Line2D([0], [0], color=GOLD, lw=1.2, ls="--",
                   label="Seed vorzeitig beendet (Auto-Stop) → Wert wird fortgeschrieben"),
            Line2D([0], [0], color="#C3CAD2", lw=1.2, ls=":",
                   label="Seed endet am Schrittlimit → fällt aus dem Mittel"),
        ]
        fig.legend(handles=legende, loc="lower center", ncol=4, frameon=False,
                   labelcolor="#B8C0C9", fontsize=8.0, bbox_to_anchor=(0.5, 0.005))
        pfad = os.path.join(out_dir, "aktionen_%s.png" % topo)
        fig.savefig(pfad, dpi=170, facecolor=DARK)
        plt.close(fig)
        print("  " + pfad)


def zeichne_sla(out_dir, meta, aktionen, letzter_step, sla):
    """Eine Abbildung mit allen 24 Matchups: SLA-Bruchschritte je Episode."""
    fig, achsen = plt.subplots(4, 6, figsize=(13.0, 6.3), facecolor=DARK,
                               sharex=False)
    fig.subplots_adjust(left=0.075, right=0.985, top=0.885, bottom=0.135,
                        wspace=0.30, hspace=0.62)
    for i, topo in enumerate(DEFS):
        for j, atk in enumerate(ATKS):
            ax = achsen[i][j]
            ax.set_facecolor(DARK)
            for sp in ax.spines.values():
                sp.set_color(GRID)
            ax.tick_params(colors=MUTED, labelsize=6.5)
            ax.grid(True, color=GRID, linewidth=0.5, alpha=0.6)
            ax.set_axisbelow(True)

            seeds = [(sla[rid], letzter_step[rid] < STEP_LIMIT)
                     for rid, (t, a, _s) in meta.items()
                     if t == topo and a == atk and rid in sla and sla[rid]]
            if not seeds:
                ax.set_xticks([]); ax.set_yticks([])
                continue
            max_ep = max(len(r) for r, _ in seeds)
            kurve = []
            for k in range(max_ep):
                werte = []
                for reihe, autostop in seeds:
                    if k < len(reihe):
                        werte.append(reihe[k])
                    elif autostop:
                        werte.append(reihe[-1])
                if not werte:
                    break
                kurve.append(statistics.mean(werte))
            kurve = glaetten(kurve, 3)
            ax.fill_between(range(1, len(kurve) + 1), kurve, color="#B3382C", alpha=0.55)
            ax.plot(range(1, len(kurve) + 1), kurve, color="#E0705F", linewidth=1.0)
            ax.set_ylim(bottom=0)
            gesamt = sum(sum(r) for r, _ in seeds)
            farbe = "#E0705F" if gesamt else "#7A828B"
            ax.set_title("%s → %s   Σ%s" % (ENG[topo], ENG[atk],
                                            format(int(gesamt), ",d").replace(",", ".")),
                         color=farbe, fontsize=7.5, pad=3, loc="left")
            if j == 0:
                ax.set_ylabel("Schritte", color=MUTED, fontsize=6.5)
            if i == 3:
                ax.set_xlabel("Episode", color=MUTED, fontsize=6.5)

    fig.suptitle("SLA-Brüche im Verlauf — Schritte unterhalb der 60-%-Verfügbarkeit",
                 color="#FFFFFF", fontsize=15, x=0.075, ha="left", y=0.965)
    fig.text(0.075, 0.045,
             "Zeile = verteidigte Topologie, Spalte = Angreifer. Σ = Summe aller "
             "SLA-Bruchschritte über alle fünf Seeds. Ein Bruch beendet die Episode nicht.",
             color="#8A929B", fontsize=8.0, ha="left")
    pfad = os.path.join(out_dir, "sla_matrix.png")
    fig.savefig(pfad, dpi=170, facecolor=DARK)
    plt.close(fig)
    print("  " + pfad)


def _kennzahlen(reihe):
    return {
        "start": round(statistics.mean(reihe[:10]), 1),
        "ende": round(statistics.mean(reihe[-20:]), 1),
        "median": round(statistics.median(reihe), 1),
        "n_ep": len(reihe),
    }


def reward_tabellen(root, meta, reihen, letzter_step, out_dir):
    """Kennzahlen je Matchup fuer beide Seiten: Anfang, Ende, Median."""
    for wer, key, name in (("Angreifer", "atk", "attacker_table.json"),
                           ("Verteidiger", "def", "defender_table.json")):
        tab = {}
        for topo in DEFS:
            tab[topo] = {}
            for atk in ATKS:
                d = matchup_daten(meta, reihen, letzter_step, topo, atk)
                tab[topo][atk] = _kennzahlen(d[key]) if d and d[key] else None
        pfad = os.path.join(out_dir, name)
        json.dump(tab, open(pfad, "w"), indent=1)
        print("  " + pfad)


def main():
    if len(sys.argv) < 2:
        raise SystemExit("Nutzung: python prep_curves.py <experiment-dir> [out-dir]")
    root = sys.argv[1].rstrip("/\\")
    out_dir = sys.argv[2] if len(sys.argv) > 2 else root
    os.makedirs(out_dir, exist_ok=True)
    meta, reihen, letzter_step, aktionen, sla = lade(root)
    print("%d Defender-Laeufe geladen" % len(meta))
    zeichne(root, out_dir, meta, reihen, letzter_step)
    zeichne_aktionen(out_dir, meta, aktionen, letzter_step)
    zeichne_sla(out_dir, meta, aktionen, letzter_step, sla)
    reward_tabellen(root, meta, reihen, letzter_step, out_dir)


if __name__ == "__main__":
    main()
