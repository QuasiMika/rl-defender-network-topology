/*
 * Verteidiger-Matrix Gesamtauswertung, Lauf 20260820_005936, finale Fassung.
 * Nachbau der Vorlage aus 20260818_004656 (make_deck_v7.js) mit den Werten
 * dieses Laufs, jetzt inklusive Evaluationsteil (Frozen-vs-Frozen, 360
 * Zellen, alle 5 Seeds vollstaendig aus experiments/20260820_005936/
 * evaluation_episodes.csv, aufbereitet mit prep_deck_extra.py).
 *
 * Aufruf: node make_deck_gesamtauswertung_v3.js <analysis.json> <bild-dir> <ausgabe.pptx>
 */
const pptxgen = require("pptxgenjs");
const fs = require("fs");
const path = require("path");

const IN = process.argv[2];
const IMGDIR = process.argv[3];
const OUT = process.argv[4];
const d = JSON.parse(fs.readFileSync(IN, "utf8"));
const dt = JSON.parse(fs.readFileSync(path.join(IMGDIR, "defender_table.json"), "utf8"));
const at = JSON.parse(fs.readFileSync(path.join(IMGDIR, "attacker_table.json"), "utf8"));
const extra = JSON.parse(fs.readFileSync(path.join(IMGDIR, "deck_extra.json"), "utf8"));
const ev = extra.evaluation;
const vt = extra.verteidiger;

// ── Palette (identisch zur Vorlage) ─────────────────────────────────────────
const DARK = "1B1F26";
const INK = "23282F";
const MUTED = "6E7681";
const DEF = "1C6E8C";
const ATK = "B3382C";
const GOLD = "D99A2B";
const LINE = "DDE1E6";
const CARD = "F4F6F8";

const DEFS = ["flat", "hub_and_spoke", "dmz", "micro_segmented"];
const ATKS = ["chain", "flat", "hub_and_spoke", "dmz", "micro_segmented", "super"];
const KURZ = {
  flat: "Flat", hub_and_spoke: "Hub & Spoke", dmz: "DMZ",
  micro_segmented: "Micro-Seg.", chain: "Chain", super: "Super",
};

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";
pres.author = "Mika Oelhoff";
pres.title = "Verteidiger-Matrix";
const W = 13.3, H = 7.5, M = 0.7;

function titelZeile(s, text, unterzeile) {
  s.addText(text, { x: M, y: 0.42, w: W - 2 * M, h: 0.62, fontSize: 34, bold: true, color: INK, fontFace: "Cambria", margin: 0 });
  if (unterzeile) {
    s.addText(unterzeile, { x: M, y: 1.06, w: W - 2 * M, h: 0.54, fontSize: 14, color: MUTED, fontFace: "Calibri", margin: 0 });
  }
}
function fussnote(s, text) {
  s.addText(text, { x: M, y: H - 0.62, w: W - 2 * M, h: 0.3, fontSize: 10, color: MUTED, fontFace: "Calibri", italic: true, margin: 0 });
}
function heat(n) {
  if (n === null) return CARD;
  return ["F2DCDA", "EFD3C8", "EDE3CE", "DDE6DA", "C6DCD3", "A9CFC4"][n];
}

function tabellenFolie(tab, titel, unterzeile, gutWennFaellt, legende, hinweis, notiz) {
  const s = pres.addSlide();
  titelZeile(s, titel, unterzeile);
  const x0 = M + 1.75, y0 = 2.1, cw = 1.6, ch = 0.78;
  ATKS.forEach((a, j) => {
    s.addText(KURZ[a], { x: x0 + j * cw, y: y0 - 0.4, w: cw, h: 0.34, fontSize: 12, bold: true, color: MUTED, align: "center", fontFace: "Calibri", margin: 0 });
  });
  DEFS.forEach((t, i) => {
    const y = y0 + i * ch;
    s.addText(KURZ[t], { x: M, y: y, w: 1.65, h: ch, fontSize: 13, bold: true, color: INK, align: "right", valign: "middle", fontFace: "Calibri", margin: 0 });
    ATKS.forEach((a, j) => {
      const v = tab[t][a];
      const x = x0 + j * cw;
      const faellt = v && v.ende < v.start;
      const gut = v && (gutWennFaellt ? faellt : !faellt);
      s.addShape(pres.ShapeType.rect, { x: x, y: y, w: cw - 0.06, h: ch - 0.06, fill: { color: !v ? CARD : (gut ? "E9F0F3" : "FBEEEC") }, line: { color: "FFFFFF", width: 1.5 } });
      if (!v) {
        s.addText("–", { x: x, y: y, w: cw - 0.06, h: ch - 0.06, fontSize: 13, color: MUTED, align: "center", valign: "middle", margin: 0 });
        return;
      }
      s.addText([
        { text: Math.round(v.start).toLocaleString("de-DE"), options: { color: MUTED } },
        { text: "  →  ", options: { color: MUTED } },
        { text: Math.round(v.ende).toLocaleString("de-DE"), options: { bold: true, color: gut ? DEF : ATK } },
      ], { x: x, y: y + 0.1, w: cw - 0.06, h: 0.34, fontSize: 12, align: "center", fontFace: "Calibri", margin: 0 });
      s.addText(v.n_ep + " Episoden", { x: x, y: y + 0.44, w: cw - 0.06, h: 0.24, fontSize: 9, color: MUTED, align: "center", fontFace: "Calibri", margin: 0 });
    });
  });
  s.addText(legende, { x: M, y: 5.5, w: W - 2 * M, h: 0.35, fontSize: 13, color: INK, fontFace: "Calibri", margin: 0 });
  s.addText(hinweis, { x: M, y: 5.85, w: W - 2 * M, h: 0.7, fontSize: 12, color: MUTED, fontFace: "Calibri", margin: 0 });
  s.addNotes(notiz);
}

// =========================================================================
// 1 – Titel
// =========================================================================
{
  const s = pres.addSlide();
  s.background = { color: DARK };
  s.addText("Verteidiger-Matrix", { x: M, y: 2.25, w: 9.6, h: 0.95, fontSize: 46, bold: true, color: "FFFFFF", fontFace: "Cambria", margin: 0 });
  s.addText("Einfluss der Netzwerktopologie auf die Lerneffizienz", { x: M, y: 3.2, w: 9.6, h: 0.5, fontSize: 20, color: "C6CDD6", fontFace: "Calibri", margin: 0 });
  s.addText([
    { text: String(d.meta.n_runs) + " Trainingsläufe", options: { bold: true, color: "FFFFFF" } },
    { text: "   ·   ", options: { color: MUTED } },
    { text: String(d.meta.n_matchups) + " Matchups", options: { bold: true, color: "FFFFFF" } },
    { text: "   ·   ", options: { color: MUTED } },
    { text: "5 Seeds", options: { bold: true, color: "FFFFFF" } },
  ], { x: M, y: 4.05, w: 9.6, h: 0.4, fontSize: 15, fontFace: "Calibri", margin: 0 });
  s.addText("Lauf " + d.meta.experiment + "   ·   Kantenbilanz-Reward, volles Budget ohne Auto-Stop", { x: M, y: H - 1.05, w: 9.6, h: 0.32, fontSize: 12, color: MUTED, fontFace: "Calibri", margin: 0 });
  s.addShape(pres.ShapeType.roundRect, { x: 10.5, y: 2.25, w: 2.1, h: 2.2, rectRadius: 0.12, fill: { color: "252B33" }, line: { color: "3A424D", width: 1 } });
  s.addText("500.000", { x: 10.5, y: 2.6, w: 2.1, h: 0.7, fontSize: 30, bold: true, color: GOLD, align: "center", fontFace: "Cambria", margin: 0 });
  s.addText("Schritte je Lauf,\nfestes Budget", { x: 10.5, y: 3.35, w: 2.1, h: 0.7, fontSize: 12, color: "C6CDD6", align: "center", fontFace: "Calibri", margin: 0 });
  s.addNotes("Vollstaendige Matrix, 120 Laeufe, 24 Matchups, 5 Seeds je Matchup, Seeds 0-2 PC / 3-4 Laptop. Kein Auto-Stop: Konvergenz wird nachtraeglich auf der vollen Kurve bestimmt (Kapitel 3).");
}

// =========================================================================
// 2 – Was sich gegenueber MARLon/dem Referenzlauf geaendert hat
// =========================================================================
{
  const s = pres.addSlide();
  titelZeile(s, "Was diesen Lauf von MARLons Original unterscheidet", "Drei Eingriffe am geerbten Aufbau, siehe Kapitel 3.1");
  const karten = [
    ["Abwehrbonus", "Zustandsreward für Prävention statt nur Rückeroberung.",
      "Kantenbilanz: Beitrag(Z) = 0,00025 · Wert(Z) · (2f−1), f = Anteil kompromittierter Vorgänger. MARLons Original kannte nur die Zero-Sum-Kopplung; Prävention war im Reward unsichtbar."],
    ["Aktionsraum", "Verteidiger: 3 Aktionsarten statt 5, kein Port-Raten mehr.",
      "Reimage, Sperren, Freigeben je Knoten, Dienst stoppen/starten entfallen, Port und Richtung ergeben sich automatisch. MARLons Original hatte 12 Dimensionen; drei der geerbten Codefehler (Portliste, block_traffic, Verfügbarkeit) sind zudem behoben."],
    ["Maskierung", "Angreifer-Maske jetzt an tatsächlich entdeckte Kanten gebunden.",
      "CBS' eigene Maske kennt nur Zugangsdaten, keine Topologie. Eine eigene Kantenverfolgung schneidet die Maske zusätzlich auf das, was ScanHostDiscovery tatsächlich aufgedeckt hat."],
  ];
  const kw = (W - 2 * M - 2 * 0.4) / 3;
  karten.forEach((k, i) => {
    const x = M + i * (kw + 0.4);
    s.addShape(pres.ShapeType.roundRect, { x: x, y: 1.85, w: kw, h: 3.5, rectRadius: 0.1, fill: { color: CARD }, line: { color: LINE, width: 1 } });
    s.addText(k[0], { x: x + 0.3, y: 2.1, w: kw - 0.6, h: 0.4, fontSize: 19, bold: true, color: DEF, fontFace: "Cambria", margin: 0 });
    s.addText(k[1], { x: x + 0.3, y: 2.58, w: kw - 0.6, h: 0.8, fontSize: 14, bold: true, color: INK, fontFace: "Calibri", margin: 0 });
    s.addText(k[2], { x: x + 0.3, y: 3.45, w: kw - 0.6, h: 1.7, fontSize: 12, color: MUTED, fontFace: "Calibri", margin: 0 });
  });
  fussnote(s, "Alle sechs Angreifermodelle wurden auf dem korrigierten Kantensatz neu trainiert (500.000 Schritte je Topologie plus Super-Angreifer-Curriculum).");
  s.addNotes("Details und die drei geerbten MARLon-Fehler: thesis/MARLon_vs_Vorher_Modell.md und Kapitel 3.1 der Arbeit.");
}

// =========================================================================
// 3 – Konvergenz: ehrlicher Befund
// =========================================================================
{
  const s = pres.addSlide();
  titelZeile(s, "Konvergenz: ein bekanntes Kriterium an seiner Grenze",
    "Kapitel-3-Kriterium (σ/Spanne ≤ 0,05, Trend ≤ 0,05, W=15, Patience 10) nachträglich auf die volle Kurve angewendet");
  s.addShape(pres.ShapeType.roundRect, { x: M, y: 1.9, w: W - 2 * M, h: 1.55, rectRadius: 0.1, fill: { color: "FBF3E4" }, line: { color: "EBD6AB", width: 1 } });
  s.addText(d.meta.autostop_pct.toString().replace(".", ",") + " % (" + d.meta.autostop + "/" + d.meta.n_runs + ")", { x: M + 0.35, y: 2.1, w: 4.0, h: 0.75, fontSize: 30, bold: true, color: "8A6414", fontFace: "Cambria", margin: 0 });
  s.addText("Läufe erfüllen das Kriterium, im Median bereits ab Episode 33, dem frühestmöglichen Bereich.", { x: M + 4.3, y: 2.15, w: W - 2 * M - 4.6, h: 1.2, fontSize: 13, color: "5C4A0A", fontFace: "Calibri", margin: 0 });
  s.addText("Das ist keine überraschend gute Nachricht, sondern die in Kapitel 3.6 hergeleitete Eigenschaft des Kriteriums: Es misst die Restunruhe relativ zur bisherigen Spanne. Frühe Episoden mit SLA-Brüchen erzeugen eine sehr große Anfangsspanne, an der jede spätere, tatsächlich noch andauernde Verbesserung klein wirkt.", {
    x: M, y: 3.65, w: W - 2 * M, h: 0.85, fontSize: 13, color: INK, fontFace: "Calibri", margin: 0,
  });
  s.addText("Beispiel DMZ vs. DMZ: Episode 1 liegt bei −16.129, Episode 30 bereits bei etwa −1.800, nach der Spanne-Definition „ruhig“. Der Reward verbessert sich danach aber weiter bis auf −60 bis −250 gegen Episode 265. Das Kriterium trennt Trainingsende und tatsächliches Ende der Verbesserung nicht.", {
    x: M, y: 4.6, w: W - 2 * M, h: 0.8, fontSize: 12, color: MUTED, fontFace: "Calibri", margin: 0,
  });
  s.addText("Für die Auswertung heißt das: Der Konvergenzzeitpunkt in dieser Form eignet sich nicht als Maß der Lerneffizienz. Die folgenden Folien vergleichen Topologien deshalb am Reward-Niveau und an der Wirksamkeit, nicht an der Konvergenz.", {
    x: M, y: 5.55, w: W - 2 * M, h: 0.7, fontSize: 13, bold: true, color: DEF, fontFace: "Calibri", margin: 0,
  });
  s.addNotes("Wichtig fuers Meeting: Das ist kein Fehler dieses Laufs, sondern eine bereits in Kapitel 3.6 hergeleitete Eigenschaft, hier am neuen Reward bestaetigt.");
}

// =========================================================================
// 4 – Konvergenzepisode je Topologie (ersetzt die alte Balkenfolie)
// =========================================================================
{
  const s = pres.addSlide();
  titelZeile(s, "Mittlere Konvergenzepisode je verteidigter Topologie",
    "Mittel über die sechs Angreifer, alle liegen nah am frühestmöglichen Zeitpunkt (Episode 30)");
  const labels = DEFS.map((t) => KURZ[t]);
  const werte = DEFS.map((t) => {
    const eps = ATKS.map((a) => (d.convergence[t][a] || {}).mean_episodes).filter((x) => typeof x === "number");
    return eps.length ? Math.round((eps.reduce((x, y) => x + y, 0) / eps.length) * 10) / 10 : 0;
  });
  s.addChart(pres.ChartType.bar, [{ name: "Ø Konvergenzepisode", labels, values: werte }], {
    x: M, y: 1.85, w: 7.2, h: 4.2, barDir: "col", chartColors: [GOLD],
    showValue: true, dataLabelPosition: "outEnd", dataLabelColor: INK, dataLabelFontSize: 14, dataLabelFontBold: true,
    showLegend: false, showTitle: false, valAxisMaxVal: 45, valAxisMinVal: 0,
    catAxisLabelColor: INK, catAxisLabelFontSize: 13, valAxisLabelColor: MUTED, valAxisLabelFontSize: 11,
    valGridLine: { color: LINE, size: 1 }, catGridLine: { style: "none" },
  });
  s.addText("Alle vier Topologien liegen zwischen Episode 32 und 35 im Mittel, kein Unterschied, der über das Rauschen hinausginge.", {
    x: 8.3, y: 2.0, w: 4.3, h: 0.9, fontSize: 14, bold: true, color: INK, fontFace: "Calibri", margin: 0,
  });
  s.addText("Einzelne Ausreißer wie DMZ gegen Micro-Segmentation (44,8) oder Hub & Spoke gegen Micro-Segmentation (40,6) fallen kaum ins Gewicht.", {
    x: 8.3, y: 2.95, w: 4.3, h: 1.0, fontSize: 12, color: MUTED, fontFace: "Calibri", margin: 0,
  });
  s.addText("Das bestätigt Folie 3: Die Konvergenzepisode trennt die Topologien in diesem Aufbau nicht.", {
    x: 8.3, y: 4.1, w: 4.3, h: 0.6, fontSize: 12, italic: true, color: DEF, fontFace: "Calibri", margin: 0,
  });
  s.addNotes("Ersetzt die alte Auto-Stop-Balkenfolie: Counts waren hier uninformativ (120/120), die mittlere Episode ist die informativere Groesse.");
}

// =========================================================================
// 5 – Diagonalmuster
// =========================================================================
{
  const s = pres.addSlide();
  titelZeile(s, "Das Diagonalmuster kehrt sich um: Flat am schwersten",
    "Verteidiger-Reward gegen den eigenen Angreifer, je näher an null, desto besser der Ausgleich");
  const diag = DEFS.map((t) => [KURZ[t], Math.round((d.defender[t][t] || {}).median || 0)]);
  const kw = (W - 2 * M - 3 * 0.35) / 4;
  diag.forEach((r, i) => {
    const x = M + i * (kw + 0.35);
    s.addShape(pres.ShapeType.roundRect, { x: x, y: 2.0, w: kw, h: 2.05, rectRadius: 0.1, fill: { color: CARD }, line: { color: LINE, width: 1 } });
    s.addText(r[0], { x: x, y: 2.2, w: kw, h: 0.34, fontSize: 14, bold: true, color: MUTED, align: "center", fontFace: "Calibri", margin: 0 });
    s.addText(String(r[1]), { x: x, y: 2.62, w: kw, h: 0.85, fontSize: 36, bold: true, color: r[1] <= -400 ? ATK : INK, align: "center", fontFace: "Cambria", margin: 0 });
    s.addText("gegen sich selbst", { x: x, y: 3.5, w: kw, h: 0.3, fontSize: 11, color: MUTED, align: "center", fontFace: "Calibri", margin: 0 });
  });
  s.addText("Flat liegt bei −715 und damit um ein Vielfaches schlechter als die übrigen drei (−20 bis −152). Zum Vergleich: Gegen den neutralen Chain-Angreifer liegt Flat bei nur −182.", {
    x: M, y: 4.4, w: W - 2 * M, h: 0.6, fontSize: 15, color: INK, fontFace: "Calibri", margin: 0,
  });
  s.addText("Der Grund liegt im Aktionsverhalten (Folie 11): In Flat hat jeder Knoten neun eingehende Kanten, eine wahllose Sperre trifft dort selten eine echte Bedrohung. Der Verteidiger gibt das Sperren fast vollständig auf und verlässt sich auf Reimage, das kostet ihn die 715 Punkte, denn Reimage allein hält den Angreifer nicht klein. In den übrigen drei Topologien bleibt Sperren dagegen ein tragfähiges Werkzeug.", {
    x: M, y: 5.0, w: W - 2 * M, h: 1.0, fontSize: 13, color: MUTED, fontFace: "Calibri", margin: 0,
  });
  s.addNotes("Umgekehrtes Muster zum Referenzlauf: Dort war die Konvergenz die Kernfolie, hier ist es das Reward-Niveau der Diagonalen. Details zu Flat: Kapitel 3, Abwehrbonus-Abschnitt, und thesis/Umbau_alt_vs_neu.pptx.");
}

// =========================================================================
// 6 – Reward-Matrix mit Warnung
// =========================================================================
{
  const s = pres.addSlide();
  titelZeile(s, "Verteidiger-Reward, mit Vorsicht zu lesen", "Median der letzten 20 Episoden, über 5 Seeds gemittelt");
  const x0 = M + 1.75, y0 = 1.95, cw = 1.5, ch = 0.62;
  ATKS.forEach((a, j) => {
    s.addText(KURZ[a], { x: x0 + j * cw, y: y0 - 0.4, w: cw, h: 0.34, fontSize: 12, bold: true, color: MUTED, align: "center", fontFace: "Calibri", margin: 0 });
  });
  DEFS.forEach((t, i) => {
    const y = y0 + i * ch;
    s.addText(KURZ[t], { x: M, y: y, w: 1.65, h: ch, fontSize: 13, bold: true, color: INK, align: "right", valign: "middle", fontFace: "Calibri", margin: 0 });
    ATKS.forEach((a, j) => {
      const v = d.defender[t][a];
      const m = v ? Math.round(v.median) : null;
      s.addShape(pres.ShapeType.rect, { x: x0 + j * cw, y: y, w: cw - 0.06, h: ch - 0.06, fill: { color: m === null ? CARD : (m < -400 ? "F7E3E0" : "F7F8F9") }, line: { color: "FFFFFF", width: 1.5 } });
      s.addText(m === null ? "–" : m.toLocaleString("de-DE"), { x: x0 + j * cw, y: y + 0.12, w: cw - 0.06, h: 0.36, fontSize: 14, bold: Math.abs(m || 0) > 400, color: m === null ? MUTED : (m < 0 ? ATK : INK), align: "center", fontFace: "Calibri", margin: 0 });
    });
  });
  s.addShape(pres.ShapeType.roundRect, { x: M, y: 4.75, w: W - 2 * M, h: 1.5, rectRadius: 0.1, fill: { color: "FBF3E4" }, line: { color: "EBD6AB", width: 1 } });
  s.addText("Diese Zahlen sind zwischen Topologien nicht vergleichbar", { x: M + 0.35, y: 4.95, w: W - 2 * M - 0.7, h: 0.35, fontSize: 15, bold: true, color: "8A6414", fontFace: "Calibri", margin: 0 });
  s.addText("Der Verteidiger-Reward ist an den des Angreifers gekoppelt, und der erreichbare Punktevorrat unterscheidet sich je Topologie (235 gegenüber 145 in Micro-Segmentation). Zudem hängt die Episodenlänge über den Haltebonus mit hinein. Vergleichbar wird es erst durch Größen, die von der Reward-Skala unabhängig sind: Crown-Jewel-Quote und gehaltene Knoten (Folien 8–9).", {
    x: M + 0.35, y: 5.32, w: W - 2 * M - 0.7, h: 0.85, fontSize: 12, color: INK, fontFace: "Calibri", margin: 0,
  });
  s.addNotes("Spanne aller Medianwerte: -715 (flat/flat) bis -20 (micro/micro). Vorsicht bei Topologie-uebergreifenden Vergleichen, siehe Kapitel 3.9 Auswertungsgroessen.");
}

// =========================================================================
// 7 / 8 – Reward-Tabellen beider Seiten
// =========================================================================
tabellenFolie(
  dt,
  "Verteidiger-Reward: Beginn und Ende des Trainings",
  "Mittel der ersten 10 gegen die letzten 20 Episoden je Lauf, über 5 Seeds gemittelt, volles Budget, kein Auto-Stop",
  false,
  "Blau = der Verteidiger verbessert sich im Lauf des Trainings. Rot = er verliert an Boden.",
  "Jede Zelle verbessert sich deutlich, auch wenn das Konvergenzkriterium das nicht anzeigt (Folie 3). Am stärksten fällt die Verbesserung dort aus, wo der Startwert extrem negativ ist: Flat gegen Flat startet bei −12.283 und landet bei −750, Hub & Spoke gegen sich selbst bei −9.352 auf −102. Kein einziges Matchup verschlechtert sich.",
  "Zahlen aus prep_curves.py, Datei defender_table.json des neuen Laufs."
);

tabellenFolie(
  at,
  "Angreifer-Reward: Beginn und Ende des Trainings",
  "Dieselbe Rechnung für die Gegenseite: Zeigt sie, dass der Verteidiger den Angreifer über die Zeit zurückdrängt?",
  true,
  "Blau = der Angreifer verliert im Lauf des Trainings an Boden. Rot = er hält sein Niveau oder verbessert sich.",
  "Über die Zero-Sum-Kopplung nahezu spiegelbildlich zur Verteidigerfolie: Wo der Verteidiger stark gewinnt, verliert der Angreifer entsprechend. Die stärksten Rückgänge liegen wieder auf der Diagonalen der schwierigen Fälle, allen voran Flat und Hub & Spoke gegen den eigenen Angreifer.",
  "Gegenstueck zur Verteidigerfolie, attacker_table.json des neuen Laufs."
);

// =========================================================================
// 9 – Angreifer-Erfolg (Crown Jewel)
// =========================================================================
{
  const s = pres.addSlide();
  titelZeile(s, "Wie weit kommt der Angreifer?", "Anteil der Episoden mit erreichtem Crown Jewel, je Matchup");
  const serien = ATKS.map((a) => ({
    name: KURZ[a], labels: DEFS.map((t) => KURZ[t]),
    values: DEFS.map((t) => (d.atkstats[t][a] ? d.atkstats[t][a].cj_pct : 0)),
  }));
  s.addChart(pres.ChartType.bar, serien, {
    x: M, y: 1.8, w: W - 2 * M, h: 4.0, barDir: "col", barGrouping: "clustered",
    chartColors: ["B9C0C8", "8FA3B3", "C2A05A", "7BA88F", "9C8AA5", ATK],
    showValue: false, showLegend: true, legendPos: "b", legendColor: INK, legendFontSize: 11, showTitle: false,
    valAxisMaxVal: 100, valAxisMinVal: 0, valAxisTitle: "Crown Jewel erreicht (%)", showValAxisTitle: true,
    valAxisTitleColor: MUTED, valAxisTitleFontSize: 11, catAxisLabelColor: INK, catAxisLabelFontSize: 12,
    valAxisLabelColor: MUTED, valAxisLabelFontSize: 10, valGridLine: { color: LINE, size: 1 }, catGridLine: { style: "none" },
  });
  fussnote(s, "Flat gegen den eigenen Angreifer: 99,9 %. Micro-Segmentation gegen DMZ dagegen 0,0 %, der DMZ-Angreifer findet dort keinen Weg zum Ziel.");
  s.addNotes("Ergaenzt das Reward-Niveau um die Frage, ob der Angreifer ueberhaupt vorankommt, unabhaengig von der Reward-Skala.");
}

// =========================================================================
// 10 – Gehaltene Knoten
// =========================================================================
{
  const s = pres.addSlide();
  titelZeile(s, "Wie viele Knoten hält der Angreifer?", "Mittel je Matchup, von zehn Knoten im Netz, Zeile = verteidigte Topologie, Spalte = Angreifer");
  const x0 = M + 1.75, y0 = 1.95, cw = 1.5, ch = 0.72;
  function heatKnoten(v) {
    if (v === null || v === undefined) return CARD;
    const stufen = [[2.0, "F4F6F8"], [3.0, "FBEDEA"], [4.0, "F6D9D3"], [5.5, "EDB9AF"], [7.0, "E0968A"], [99, "D07C6E"]];
    for (const [g, f] of stufen) if (v < g) return f;
    return "D07C6E";
  }
  ATKS.forEach((a, j) => { s.addText(KURZ[a], { x: x0 + j * cw, y: y0 - 0.42, w: cw, h: 0.36, fontSize: 12, bold: true, color: MUTED, align: "center", fontFace: "Calibri", margin: 0 }); });
  DEFS.forEach((t, i) => {
    const y = y0 + i * ch;
    s.addText(KURZ[t], { x: M, y: y, w: 1.65, h: ch, fontSize: 13, bold: true, color: INK, align: "right", valign: "middle", fontFace: "Calibri", margin: 0 });
    ATKS.forEach((a, j) => {
      const st = d.atkstats[t][a];
      const v = st ? st.max_owned : null;
      s.addShape(pres.ShapeType.rect, { x: x0 + j * cw, y: y, w: cw - 0.06, h: ch - 0.06, fill: { color: heatKnoten(v) }, line: { color: "FFFFFF", width: 1.5 } });
      s.addText(v === null ? "–" : v.toFixed(1), { x: x0 + j * cw, y: y + 0.06, w: cw - 0.06, h: 0.34, fontSize: 15, bold: true, color: INK, align: "center", fontFace: "Calibri", margin: 0 });
      s.addText(st ? "CJ " + st.cj_pct.toFixed(0) + " %" : "", { x: x0 + j * cw, y: y + 0.38, w: cw - 0.06, h: 0.26, fontSize: 10, color: MUTED, align: "center", fontFace: "Calibri", margin: 0 });
    });
  });
  s.addText("Flat gegen sich selbst hält der Angreifer im Mittel 8,1 von 10 Knoten, DMZ gegen sich selbst 5,6. Am wenigsten kommt er dort weiter, wo er auf eine fremde, stärker segmentierte Struktur trifft: 2,0 Knoten in mehreren Zellen mit Micro-Segmentation oder DMZ als Ziel.", {
    x: M, y: 5.15, w: W - 2 * M, h: 0.6, fontSize: 14, bold: true, color: ATK, fontFace: "Calibri", margin: 0,
  });
  fussnote(s, "Mittel über alle Episoden aller fünf Seeds. Der Einstiegsknoten WebServer ist von Beginn an übernommen und zählt mit. Zweite Zeile je Feld: Crown-Jewel-Quote.");
  s.addNotes("Ergaenzt die CJ-Folie um das Ausmass der Uebernahme.");
}

// =========================================================================
// 11 – Verlauf je verteidigter Topologie
// =========================================================================
DEFS.forEach((t) => {
  const bild = path.join(IMGDIR, "verlauf_" + t + ".png");
  if (!fs.existsSync(bild)) return;
  const s = pres.addSlide();
  s.background = { color: DARK };
  s.addImage({ path: bild, x: 0.18, y: 0.16, w: W - 0.36, h: H - 0.32 });
  s.addNotes("Je Angreifer ein Feld, Mittel ueber 5 Seeds, geglaettet. Kein Auto-Stop in diesem Lauf: alle Seeds tragen ueber die volle Laenge bei, keine Ausstiegs-Markierungen zu erwarten.");
});

// =========================================================================
// 11b – Verlauf des Abwehrbonus
// =========================================================================
{
  const bild = path.join(IMGDIR, "abwehrbonus_verlauf.png");
  if (fs.existsSync(bild)) {
    const s = pres.addSlide();
    s.background = { color: DARK };
    s.addImage({ path: bild, x: 0.18, y: 0.16, w: W - 0.36, h: H - 0.32 });
    s.addNotes("Zustandsreward-Anteil aus der Kantenbilanz-Formel (Kapitel 3, Folie 2), getrennt vom Gesamtreward betrachtet. Alle vier Kurven starten stark negativ und naehern sich Null oder leicht positiven Werten an; DMZ und Micro-Segmentation liegen am Ende nahe 0, Flat bleibt mit rund -14 klar am negativsten, dieselbe Topologie, die auch beim Gesamtreward und in der Evaluation am schlechtesten abschneidet (Folie 5).");
  }
}

// =========================================================================
// 11c – Verlauf der Crown-Jewel-Quote im Training, je verteidigter Topologie
// =========================================================================
DEFS.forEach((t) => {
  const bild = path.join(IMGDIR, "cj_verlauf_" + t + ".png");
  if (!fs.existsSync(bild)) return;
  const s = pres.addSlide();
  s.background = { color: DARK };
  s.addImage({ path: bild, x: 0.18, y: 0.16, w: W - 0.36, h: H - 0.32 });
  s.addNotes("Anteil der 5 Seeds je Episode, die den Crown Jewel erreicht haben, geglaettet (Fenster 15, da binaere Groesse ueber nur 5 Seeds). Selbst-Matchup mit Stern markiert. Ergaenzt die Evaluations-Crown-Jewel-Matrix (Folie 24) um den Trainingsverlauf: in Micro-Segmentation faellt die Quote gegen den eigenen Angreifer bis auf 0, in Flat bleibt sie durchgehend nahe 100 -- konsistent mit den eingefrorenen Endwerten dort.");
});

// =========================================================================
// 12 – Aktionsverhalten (neuer 3-Aktionen-Raum)
// =========================================================================
{
  const s = pres.addSlide();
  titelZeile(s, "Sperren wird früh gelernt, dann größtenteils wieder aufgegeben",
    "Anteil der Schritte je Aktionsart, über alle 120 Läufe gemittelt");
  const karten = [
    ["16 % → 2 %", "Sperren (Episode 1–25 gegen ab 101)", "Zu Beginn sperrt der Verteidiger noch häufig. Über das Training sinkt der Anteil auf ein Achtel, konsistent mit dem Befund, dass Sperren nur in bestimmten Topologien dauerhaft lohnt (Folie 5)."],
    ["38 % → 62 %", "Ungültige Aktionen", "Steigt über das Training deutlich, wie schon im alten Aktionsraum. Eine ungültige Aktion kostet nichts und überspringt den Zug, der günstigste Weg, nichts zu tun."],
    ["88,1 %", "Episoden mit mindestens einer aktiven Sperre", "Trotz des Rückgangs bleibt Sperren kein Randphänomen: In der großen Mehrheit der Episoden ist zu jedem Zeitpunkt mindestens ein Knoten aktiv abgeschirmt."],
  ];
  const kw = (W - 2 * M - 2 * 0.4) / 3;
  karten.forEach((k, i2) => {
    const x = M + i2 * (kw + 0.4);
    s.addShape(pres.ShapeType.roundRect, { x: x, y: 2.0, w: kw, h: 3.3, rectRadius: 0.1, fill: { color: CARD }, line: { color: LINE, width: 1 } });
    s.addText(k[0], { x: x + 0.3, y: 2.25, w: kw - 0.6, h: 0.6, fontSize: 26, bold: true, color: i2 === 2 ? GOLD : DEF, fontFace: "Cambria", margin: 0 });
    s.addText(k[1], { x: x + 0.3, y: 2.9, w: kw - 0.6, h: 0.36, fontSize: 15, bold: true, color: INK, fontFace: "Calibri", margin: 0 });
    s.addText(k[2], { x: x + 0.3, y: 3.35, w: kw - 0.6, h: 1.7, fontSize: 12, color: MUTED, fontFace: "Calibri", margin: 0 });
  });
  s.addText("Der neue Aktionsraum hat nur noch drei Arten (Reimage, Sperren, Freigeben) statt vormals fünf. „Freigeben“ dominiert mit 36,8 % über alle Läufe, ein neues Muster gegenüber dem alten Aktionsraum, plausibel als Reaktion auf eigene frühere Sperren, aber nicht weiter aufgeschlüsselt in diesem Durchgang.", {
    x: M, y: 5.5, w: W - 2 * M, h: 0.95, fontSize: 12, color: MUTED, fontFace: "Calibri", margin: 0,
  });
  s.addNotes("Zahlen aus combined_episodes.csv, Mittel ueber alle 120 Laeufe des neuen 3-Aktionen-Raums. Vergleich zum alten 5-Aktionen-Raum nur qualitativ, da Kategorien nicht 1:1 uebereinstimmen.");
}

DEFS.forEach((t) => {
  const bild = path.join(IMGDIR, "aktionen_" + t + ".png");
  if (!fs.existsSync(bild)) return;
  const s = pres.addSlide();
  s.background = { color: DARK };
  s.addImage({ path: bild, x: 0.18, y: 0.16, w: W - 0.36, h: H - 0.32 });
  s.addNotes("Gestapelte Anteile je Episode. def_stop_svc/def_start_svc existieren im neuen Aktionsraum nicht mehr und liegen konstant bei 0.");
});

// =========================================================================
// 13 – SLA-Brueche
// =========================================================================
{
  const bild = path.join(IMGDIR, "sla_matrix.png");
  if (fs.existsSync(bild)) {
    const s = pres.addSlide();
    s.background = { color: DARK };
    s.addImage({ path: bild, x: 0.18, y: 0.16, w: W - 0.36, h: H - 0.32 });
    s.addNotes("Anders als im Referenzlauf treten SLA-Brueche jetzt in allen 24 Matchups auf, seit gesperrte Ports auf die Verfuegbarkeit zaehlen (Kapitel 3.6). Am staerksten betroffen: die drei Selbst-Matchups flat/flat, hub_and_spoke/hub_and_spoke, dmz/dmz.");
  }
}

// =========================================================================
// Trenner: ab hier Evaluation
// =========================================================================
if (ev) {
  const s = pres.addSlide();
  s.background = { color: DARK };
  s.addText("Ab hier: Evaluation", { x: M, y: 0.85, w: W - 2 * M, h: 0.75, fontSize: 36, bold: true, color: "FFFFFF", fontFace: "Cambria", margin: 0 });
  s.addText("Die bisherigen Folien zeigen, wie der Reward sich im Training entwickelt. Die folgenden zeigen, ob die fertig gelernte Politik etwas nützt.", {
    x: M, y: 1.62, w: W - 2 * M, h: 0.5, fontSize: 15, color: "B8C0C9", fontFace: "Calibri", margin: 0,
  });
  const karten = [
    ["Beide Agenten eingefroren",
     "Es wird nichts mehr gelernt, nur noch gespielt. Gemessen wird die fertige Politik, nicht ihr Zustandekommen."],
    ["Drei Stufen je Lauf",
     "Kein Verteidiger als Obergrenze, ein Zufallsagent als Vergleich, das trainierte Modell. Der Angreifer ist in allen drei Stufen derselbe und stammt aus demselben Lauf-Ordner."],
    ["Umfang",
     "4 Topologien × 6 Angreifer × 5 Seeds × 3 Stufen = 360 Zellen, je 25 Episoden mit höchstens 2000 Schritten. Insgesamt 9000 Episoden, auf zwei Maschinen parallel gerechnet."],
  ];
  const kw = (W - 2 * M - 2 * 0.4) / 3;
  karten.forEach((k, i) => {
    const x = M + i * (kw + 0.4);
    s.addShape(pres.ShapeType.roundRect, { x: x, y: 2.45, w: kw, h: 2.6, rectRadius: 0.1, fill: { color: "252A33" }, line: { color: "3A414C", width: 1 } });
    s.addText(k[0], { x: x + 0.3, y: 2.7, w: kw - 0.6, h: 0.45, fontSize: 16, bold: true, color: GOLD, fontFace: "Cambria", margin: 0 });
    s.addText(k[1], { x: x + 0.3, y: 3.2, w: kw - 0.6, h: 1.65, fontSize: 12, color: "B8C0C9", fontFace: "Calibri", margin: 0 });
  });
  s.addText("Warum das nötig ist: Ein gutes Reward-Niveau am Ende des Trainings sagt nicht automatisch, dass die Politik den Angreifer auch wirksam bremst. Dafür muss man beide Seiten einfrieren und einfach nur noch gegeneinander spielen lassen.", {
    x: M, y: 5.3, w: W - 2 * M, h: 0.6, fontSize: 13, color: "8B94A0", fontFace: "Calibri", italic: true, margin: 0,
  });
  s.addNotes("Uebergangsfolie. Alle 360 Zellen sind jetzt vollstaendig: 216 auf dem Desktop (Seeds 0-2), 144 auf dem Laptop (Seeds 3-4), zusammengefuehrt in evaluation_episodes.csv.");
}

// =========================================================================
// Wirksamkeit: Angreifer-Reward-Restanteil
// =========================================================================
if (ev) {
  const s = pres.addSlide();
  titelZeile(s, "Bringt der Verteidiger etwas? Angreifer-Reward",
    "Restanteil je Matchup: welchen Anteil seines Rewards der Angreifer gegen den Verteidiger noch erreicht, gemessen am ungeschützten Netz");

  const ms = ev.je_matchup_stufe;
  const x0 = M + 1.75, y0 = 1.95, cw = 1.5, ch = 0.72;

  function heatRest(v) {
    if (v === null || v === undefined) return CARD;
    const stufen = [[5, "CFE3EC"], [10, "DDEAF1"], [15, "EDF2F5"], [20, "FBEDEA"], [30, "F3D5CE"], [1e9, "E3A99C"]];
    for (const [g, f] of stufen) if (v < g) return f;
    return "E3A99C";
  }

  ATKS.forEach((a, j) => { s.addText(KURZ[a], { x: x0 + j * cw, y: y0 - 0.42, w: cw, h: 0.36, fontSize: 12, bold: true, color: MUTED, align: "center", fontFace: "Calibri", margin: 0 }); });

  DEFS.forEach((t, i) => {
    const y = y0 + i * ch;
    s.addText(KURZ[t], { x: M, y: y, w: 1.65, h: ch, fontSize: 13, bold: true, color: INK, align: "right", valign: "middle", fontFace: "Calibri", margin: 0 });
    ATKS.forEach((a, j) => {
      const e = ms[t] ? ms[t][a] : null;
      let rt = null, rz = null;
      if (e && e.keiner) {
        if (e.trainiert !== null) rt = 100 * e.trainiert / e.keiner;
        if (e.zufaellig !== null) rz = 100 * e.zufaellig / e.keiner;
      }
      s.addShape(pres.ShapeType.rect, { x: x0 + j * cw, y: y, w: cw - 0.06, h: ch - 0.06, fill: { color: heatRest(rt) }, line: { color: "FFFFFF", width: 1.5 } });
      s.addText(rt === null ? "–" : rt.toFixed(1) + " %", { x: x0 + j * cw, y: y + 0.06, w: cw - 0.06, h: 0.34, fontSize: 15, bold: true, color: INK, align: "center", fontFace: "Calibri", margin: 0 });
      s.addText(rz === null ? "" : "Zufall " + rz.toFixed(0) + " %", { x: x0 + j * cw, y: y + 0.38, w: cw - 0.06, h: 0.26, fontSize: 10, color: MUTED, align: "center", fontFace: "Calibri", margin: 0 });
    });
  });

  s.addText("Der trainierte Verteidiger drückt den Angreifer-Reward überall auf 0,5 bis 12 % des ungeschützten Werts, spürbar unter dem Zufallsagenten (9 bis 21 %). Am deutlichsten der Gewinn in Micro-Segmentation: +16,4 Prozentpunkte gegenüber Zufall, gemittelt über alle sechs Angreifer.", {
    x: M, y: 5.05, w: W - 2 * M, h: 0.55, fontSize: 14.5, bold: true, color: DEF, fontFace: "Calibri", margin: 0,
  });
  s.addText("Anders als im Referenzlauf vor dem Reward-Fix liegen trainiertes Modell und Zufallsagent hier nicht dicht beieinander: Der Restanteil des trainierten Modells ist in jeder der 24 Zellen niedriger als der des Zufallsagenten.", {
    x: M, y: 5.55, w: W - 2 * M, h: 0.55, fontSize: 11.5, color: MUTED, fontFace: "Calibri", margin: 0,
  });
  fussnote(s, "Restanteil = Angreifer-Reward mit Verteidiger geteilt durch den ohne Verteidiger, Median über Episoden und über alle fünf Seeds. Beide Agenten sind eingefroren, 25 Episoden je Zelle.");
  s.addNotes("Kernfolie fuer die Frage nach dem Nutzen. Deutlich anderes Bild als beim Referenzlauf: Dort lagen trainiert und zufaellig dicht beieinander, hier trennt sich das Training klar vom Zufallsagenten.");
}

// =========================================================================
// Wirksamkeit: gehaltene Knoten
// =========================================================================
if (ev) {
  const s = pres.addSlide();
  titelZeile(s, "Bringt der Verteidiger etwas? Gehaltene Knoten",
    "Vom Angreifer gehaltene Knoten je Matchup, von zehn im Netz, gegen das trainierte Modell, Zeile = verteidigte Topologie, Spalte = Angreifer");

  const mk = ev.je_matchup_knoten;
  const x0 = M + 1.75, y0 = 1.95, cw = 1.5, ch = 0.78;
  function heatK(v) {
    if (v === null || v === undefined) return CARD;
    const st = [[1.5, "DCEAF1"], [2.5, "E9F1F5"], [4, "F4F6F8"], [6, "FBEDEA"], [8, "F2D3CC"], [1e9, "E0A092"]];
    for (const [g, f] of st) if (v < g) return f;
    return "E0A092";
  }
  ATKS.forEach((a, j) => { s.addText(KURZ[a], { x: x0 + j * cw, y: y0 - 0.42, w: cw, h: 0.36, fontSize: 12, bold: true, color: MUTED, align: "center", fontFace: "Calibri", margin: 0 }); });

  DEFS.forEach((t, i) => {
    const y = y0 + i * ch;
    s.addText(KURZ[t], { x: M, y: y, w: 1.65, h: ch, fontSize: 13, bold: true, color: INK, align: "right", valign: "middle", fontFace: "Calibri", margin: 0 });
    ATKS.forEach((a, j) => {
      const e = (mk[t] || {})[a] || {};
      s.addShape(pres.ShapeType.rect, { x: x0 + j * cw, y: y, w: cw - 0.06, h: ch - 0.06, fill: { color: heatK(e.trainiert) }, line: { color: "FFFFFF", width: 1.5 } });
      s.addText(e.trainiert === null || e.trainiert === undefined ? "–" : e.trainiert.toFixed(1), { x: x0 + j * cw, y: y + 0.06, w: cw - 0.06, h: 0.36, fontSize: 15, bold: true, color: INK, align: "center", fontFace: "Cambria", margin: 0 });
      const zeile2 = (e.keiner != null ? "ohne " + e.keiner.toFixed(0) : "") + (e.zufaellig != null ? " · Zuf " + e.zufaellig.toFixed(0) : "");
      s.addText(zeile2, { x: x0 + j * cw, y: y + 0.42, w: cw - 0.06, h: 0.3, fontSize: 9, color: MUTED, align: "center", fontFace: "Calibri", margin: 0 });
    });
  });

  s.addText("Fast überall drückt das Training den Angreifer auf 2 von 10 Knoten, den Einstiegsknoten mitgezählt. Nur in Flat gegen den eigenen Angreifer bleibt es bei 7,0 Knoten, dieselbe Schwäche, die schon im Trainingsteil auffiel (Folie 5).", {
    x: M, y: 5.3, w: W - 2 * M, h: 0.5, fontSize: 14, bold: true, color: DEF, fontFace: "Calibri", margin: 0,
  });
  fussnote(s, "Median über 25 Episoden je Zelle und über alle fünf Seeds. Der Einstiegsknoten WebServer ist von Beginn an übernommen und zählt mit. Zweite Zeile: Median ohne Verteidiger bzw. gegen den Zufallsagenten.");
  s.addNotes("Bestaetigt die Flat-Schwaeche aus dem Trainingsteil unabhaengig von der Reward-Skala: Auch mit eingefrorener Politik haelt der Angreifer dort 7 von 10 Knoten.");
}

// =========================================================================
// Wirksamkeit: Crown Jewel
// =========================================================================
if (ev) {
  const s = pres.addSlide();
  titelZeile(s, "Bringt der Verteidiger etwas? Crown Jewel",
    "Anteil der Episoden mit erreichtem Datenbankserver, gegen das trainierte Modell, Zeile = verteidigte Topologie, Spalte = Angreifer");

  const mc = ev.je_matchup_cj;
  const x0 = M + 1.75, y0 = 1.95, cw = 1.5, ch = 0.78;
  function heatC(v) {
    if (v === null || v === undefined) return CARD;
    const st = [[5, "DCEAF1"], [20, "E9F1F5"], [40, "F4F6F8"], [60, "FBEDEA"], [85, "F2D3CC"], [1e9, "E0A092"]];
    for (const [g, f] of st) if (v < g) return f;
    return "E0A092";
  }
  ATKS.forEach((a, j) => { s.addText(KURZ[a], { x: x0 + j * cw, y: y0 - 0.42, w: cw, h: 0.36, fontSize: 12, bold: true, color: MUTED, align: "center", fontFace: "Calibri", margin: 0 }); });

  DEFS.forEach((t, i) => {
    const y = y0 + i * ch;
    s.addText(KURZ[t], { x: M, y: y, w: 1.65, h: ch, fontSize: 13, bold: true, color: INK, align: "right", valign: "middle", fontFace: "Calibri", margin: 0 });
    ATKS.forEach((a, j) => {
      const e = (mc[t] || {})[a] || {};
      s.addShape(pres.ShapeType.rect, { x: x0 + j * cw, y: y, w: cw - 0.06, h: ch - 0.06, fill: { color: heatC(e.trainiert) }, line: { color: "FFFFFF", width: 1.5 } });
      s.addText(e.trainiert === null || e.trainiert === undefined ? "–" : e.trainiert.toFixed(1) + " %", { x: x0 + j * cw, y: y + 0.06, w: cw - 0.06, h: 0.36, fontSize: 15, bold: true, color: INK, align: "center", fontFace: "Cambria", margin: 0 });
      const zeile2 = (e.keiner != null ? "ohne " + e.keiner.toFixed(0) : "") + (e.zufaellig != null ? " · Zuf " + e.zufaellig.toFixed(0) : "");
      s.addText(zeile2, { x: x0 + j * cw, y: y + 0.42, w: cw - 0.06, h: 0.3, fontSize: 9, color: MUTED, align: "center", fontFace: "Calibri", margin: 0 });
    });
  });

  s.addText("Micro-Segmentation hält den eigenen Angreifer bei 0,0 % Crown-Jewel-Quote, das andere Extrem ist wieder Flat gegen sich selbst mit 99,2 %. Dieselbe Diagonale wie bei Reward und Knoten, jetzt an einer dritten, von der Reward-Skala unabhängigen Größe bestätigt.", {
    x: M, y: 5.3, w: W - 2 * M, h: 0.5, fontSize: 14, bold: true, color: DEF, fontFace: "Calibri", margin: 0,
  });
  fussnote(s, "Der Crown Jewel beendet die Episode nicht. Anteil über 25 Episoden je Zelle und alle fünf Seeds.");
  s.addNotes("Dritte unabhaengige Bestaetigung der Flat-Schwaeche und der Micro-Segmentation-Staerke, nach Reward-Niveau und gehaltenen Knoten.");
}

// =========================================================================
// Was die Verteidigung kostet
// =========================================================================
if (vt) {
  const s = pres.addSlide();
  titelZeile(s, "Was die Verteidigung kostet",
    "Dieselben Evaluationsepisoden von der Verteidigerseite: große Zahl = trainiertes Modell, kleine = Zufallsagent");

  const spalten = [
    ["Sperren je Episode", "block", (x) => x.toFixed(0)],
    ["Reimages je Episode", "reimage", (x) => x.toFixed(1)],
    ["Episoden mit SLA-Bruch", "sla_ep_pct", (x) => x.toFixed(1) + " %"],
    ["Verteidiger-Reward", "reward", (x) => x.toFixed(0)],
  ];
  const x0 = M + 1.9, y0 = 2.05, cw = 2.1, ch = 0.85;

  spalten.forEach((sp, j) => {
    s.addText(sp[0], { x: x0 + j * cw, y: y0 - 0.62, w: cw - 0.06, h: 0.56, fontSize: 11, bold: true, color: MUTED, align: "center", valign: "bottom", fontFace: "Calibri", margin: 0 });
  });
  DEFS.forEach((t, i) => {
    const y = y0 + i * ch;
    s.addText(KURZ[t], { x: M, y: y, w: 1.8, h: ch, fontSize: 13, bold: true, color: INK, align: "right", valign: "middle", fontFace: "Calibri", margin: 0 });
    spalten.forEach((sp, j) => {
      const e = vt[t] || {};
      const tr = e.trainiert ? e.trainiert[sp[1]] : null;
      const zu = e.zufaellig ? e.zufaellig[sp[1]] : null;
      let fuell = CARD;
      if (tr !== null && zu !== null && zu !== 0) {
        const faktor = Math.abs(zu) < 1e-9 ? 1 : Math.abs(tr / zu);
        if (faktor < 0.5 || faktor > 2) fuell = "E8F1F6";
      }
      s.addShape(pres.ShapeType.rect, { x: x0 + j * cw, y: y, w: cw - 0.06, h: ch - 0.06, fill: { color: fuell }, line: { color: "FFFFFF", width: 1.5 } });
      s.addText(tr === null ? "–" : sp[2](tr), { x: x0 + j * cw, y: y + 0.06, w: cw - 0.06, h: 0.4, fontSize: 17, bold: true, color: INK, align: "center", fontFace: "Cambria", margin: 0 });
      s.addText(zu === null ? "" : "Zufall " + sp[2](zu), { x: x0 + j * cw, y: y + 0.48, w: cw - 0.06, h: 0.28, fontSize: 10, color: MUTED, align: "center", fontFace: "Calibri", margin: 0 });
    });
  });

  s.addText("Der Zufallsagent sperrt im Median 648 bis 654 Mal je Episode, praktisch bei jedem Schritt, und bricht damit fast immer die SLA (99,7 bis 100 % der Episoden). Das trainierte Modell sperrt fast nie mehr (0 bis 19) und verlässt sich stattdessen auf gezielte Reimages.", {
    x: M, y: 5.7, w: W - 2 * M, h: 0.55, fontSize: 14, bold: true, color: DEF, fontFace: "Calibri", margin: 0,
  });
  s.addText("Damit erklärt sich auch der Reward-Abstand von rund dem Hundertfachen: Nicht weniger Aktivität, sondern die richtige Aktivität. Auffällig: In Hub & Spoke und Micro-Segmentation reimaged das trainierte Modell sogar häufiger als der Zufallsagent (103 bzw. 103,5 gegenüber 34).", {
    x: M, y: 6.15, w: W - 2 * M, h: 0.55, fontSize: 11.5, color: MUTED, fontFace: "Calibri", margin: 0,
  });
  fussnote(s, "Median über alle Episoden je Topologie und Stufe, 25 Episoden je Zelle, alle fünf Seeds und sechs Angreifer, n = 750 je Zelle.");
  s.addNotes("Erklaert den riesigen Reward-Unterschied zwischen zufaellig und trainiert: Der Zufallsagent blockt praktisch permanent und reisst die SLA fast immer, das trainierte Modell hat gelernt, Sperren gezielt statt wahllos einzusetzen.");
}

// =========================================================================
// 14 – Fazit
// =========================================================================
{
  const s = pres.addSlide();
  s.background = { color: DARK };
  s.addText("Was die Matrix zeigt", { x: M, y: 0.75, w: W - 2 * M, h: 0.7, fontSize: 32, bold: true, color: "FFFFFF", fontFace: "Cambria", margin: 0 });
  const punkte = [
    ["Flat ist die mit Abstand am schwersten zu verteidigende Topologie",
      "Verteidiger-Reward −715 gegen sich selbst im Training, 7,0 von 10 Knoten und 99,2 % Crown-Jewel-Quote in der Evaluation: drei unabhängige Größen zeigen dieselbe Schwäche."],
    ["Das Konvergenzkriterium trennt die Topologien nicht, aus bekanntem Grund",
      "120 von 120 Läufen „konvergieren“ im Median bei Episode 33, dem frühestmöglichen Zeitpunkt. Große Anfangsspannen durch SLA-Brüche lassen jede spätere Verbesserung klein wirken, wie in Kapitel 3.6 hergeleitet."],
    ["Die gelernte Politik ist klar wirksamer als bloßes Sperren",
      "Der Zufallsagent sperrt praktisch jeden Schritt und reißt dabei fast immer die SLA (bis zu 100 % der Episoden). Das trainierte Modell sperrt selten, reimaged gezielter und drückt den Angreifer-Restanteil in jeder der 24 Zellen unter den des Zufallsagenten."],
  ];
  punkte.forEach((p, i) => {
    const y = 1.6 + i * 1.5;
    s.addShape(pres.ShapeType.ellipse, { x: M, y: y + 0.04, w: 0.42, h: 0.42, fill: { color: GOLD }, line: { color: GOLD, width: 1 } });
    s.addText(String(i + 1), { x: M, y: y + 0.04, w: 0.42, h: 0.42, fontSize: 15, bold: true, color: DARK, align: "center", valign: "middle", fontFace: "Calibri", margin: 0 });
    s.addText(p[0], { x: M + 0.7, y: y, w: W - 2 * M - 0.7, h: 0.4, fontSize: 17, bold: true, color: "FFFFFF", fontFace: "Cambria", margin: 0 });
    s.addText(p[1], { x: M + 0.7, y: y + 0.42, w: W - 2 * M - 0.7, h: 0.95, fontSize: 12.5, color: "B8C0C9", fontFace: "Calibri", margin: 0 });
  });
  s.addText("Offen: Kapitel 4 und 5 der Arbeit noch zu schreiben · Aktionsverteilung „Freigeben“ (36,8 %) im Training noch nicht weiter aufgeschlüsselt · warum das trainierte Modell in Hub & Spoke und Micro-Segmentation häufiger reimaged als der Zufallsagent, noch nicht untersucht", {
    x: M, y: H - 0.85, w: W - 2 * M, h: 0.55, fontSize: 11, color: MUTED, fontFace: "Calibri", italic: true, margin: 0,
  });
}

pres.writeFile({ fileName: OUT }).then(() => console.log("geschrieben: " + OUT));
