/*
 * Erzeugt die Ergebnispraesentation der Verteidiger-Matrix aus analysis.json.
 *
 * Aufruf:  node make_deck.js <analysis.json> <ausgabe.pptx>
 *
 * analysis.json entsteht aus prep_analysis.py.
 */
const pptxgen = require("pptxgenjs");
const fs = require("fs");

const IN = process.argv[2] || "analysis.json";
const OUT = process.argv[3] || "defender_matrix.pptx";
const d = JSON.parse(fs.readFileSync(IN, "utf8"));

// Zusatzdaten aus prep_deck_extra.py. Fehlen sie, entfallen die beiden
// zugehoerigen Folien, statt das ganze Deck scheitern zu lassen.
let extra = null;
try {
  extra = JSON.parse(fs.readFileSync("deck_extra.json", "utf8"));
} catch (e) {
  console.log("Hinweis: deck_extra.json fehlt, zwei Folien entfallen.");
}

// ── Palette ───────────────────────────────────────────────────────────────
const DARK = "1B1F26";   // Titel- und Abschlussfolien
const INK = "23282F";    // Fliesstext auf hell
const MUTED = "6E7681";  // Beschriftungen
const DEF = "1C6E8C";    // Verteidiger
const ATK = "B3382C";    // Angreifer
const GOLD = "D99A2B";   // Hervorhebung
const LINE = "DDE1E6";
const CARD = "F4F6F8";

const DEFS = ["flat", "hub_and_spoke", "dmz", "micro_segmented"];
const ATKS = ["chain", "flat", "hub_and_spoke", "dmz", "micro_segmented", "super"];
const KURZ = {
  flat: "Flat", hub_and_spoke: "Hub & Spoke", dmz: "DMZ",
  micro_segmented: "Micro-Seg.", chain: "Chain", super: "Super",
};

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";           // 13.3 x 7.5
pres.author = "Mika Oelhoff";
pres.title = "Verteidiger-Matrix";
const W = 13.3, H = 7.5, M = 0.7;

// ── Helfer ────────────────────────────────────────────────────────────────
function titelZeile(s, text, unterzeile) {
  s.addText(text, {
    x: M, y: 0.42, w: W - 2 * M, h: 0.62,
    fontSize: 34, bold: true, color: INK, fontFace: "Cambria", margin: 0,
  });
  if (unterzeile) {
    s.addText(unterzeile, {
      x: M, y: 1.06, w: W - 2 * M, h: 0.54,
      fontSize: 14, color: MUTED, fontFace: "Calibri", margin: 0,
    });
  }
}

function fussnote(s, text) {
  s.addText(text, {
    x: M, y: H - 0.62, w: W - 2 * M, h: 0.3,
    fontSize: 10, color: MUTED, fontFace: "Calibri", italic: true, margin: 0,
  });
}

// Farbe fuer die Konvergenz-Heatmap (0..5 Auto-Stops)
function heat(n) {
  if (n === null) return CARD;
  return ["F2DCDA", "EFD3C8", "EDE3CE", "DDE6DA", "C6DCD3", "A9CFC4"][n];
}

/*
 * Tabellenfolie "Anfang gegen Ende" fuer eine der beiden Seiten.
 * gutWennFaellt: true fuer den Angreifer (fallender Reward = Erfolg der
 * Verteidigung), false fuer den Verteidiger (steigender Reward = Erfolg).
 */
function tabellenFolie(datei, titel, unterzeile, gutWennFaellt, legende, hinweis, notiz) {
  const at = JSON.parse(fs.readFileSync(datei, "utf8"));
  const s = pres.addSlide();
  titelZeile(s, titel, unterzeile);

  const x0 = M + 1.75, y0 = 2.1, cw = 1.6, ch = 0.78;
  ATKS.forEach((a, j) => {
    s.addText(KURZ[a], {
      x: x0 + j * cw, y: y0 - 0.4, w: cw, h: 0.34,
      fontSize: 12, bold: true, color: MUTED, align: "center", fontFace: "Calibri", margin: 0,
    });
  });
  DEFS.forEach((t, i) => {
    const y = y0 + i * ch;
    s.addText(KURZ[t], {
      x: M, y: y, w: 1.65, h: ch,
      fontSize: 13, bold: true, color: INK, align: "right", valign: "middle",
      fontFace: "Calibri", margin: 0,
    });
    ATKS.forEach((a, j) => {
      const v = at[t][a];
      const x = x0 + j * cw;
      const faellt = v && v.ende < v.start;
      const gut = v && (gutWennFaellt ? faellt : !faellt);
      s.addShape(pres.ShapeType.rect, {
        x: x, y: y, w: cw - 0.06, h: ch - 0.06,
        fill: { color: !v ? CARD : (gut ? "E9F0F3" : "FBEEEC") },
        line: { color: "FFFFFF", width: 1.5 },
      });
      if (!v) {
        s.addText("–", {
          x: x, y: y, w: cw - 0.06, h: ch - 0.06,
          fontSize: 13, color: MUTED, align: "center", valign: "middle", margin: 0,
        });
        return;
      }
      s.addText(
        [
          { text: Math.round(v.start).toLocaleString("de-DE"), options: { color: MUTED } },
          { text: "  →  ", options: { color: MUTED } },
          { text: Math.round(v.ende).toLocaleString("de-DE"), options: { bold: true, color: gut ? DEF : ATK } },
        ],
        { x: x, y: y + 0.1, w: cw - 0.06, h: 0.34, fontSize: 12, align: "center", fontFace: "Calibri", margin: 0 }
      );
      s.addText(v.n_ep + " Episoden", {
        x: x, y: y + 0.44, w: cw - 0.06, h: 0.24,
        fontSize: 9, color: MUTED, align: "center", fontFace: "Calibri", margin: 0,
      });
    });
  });
  s.addText(legende, {
    x: M, y: 5.5, w: W - 2 * M, h: 0.35,
    fontSize: 13, color: INK, fontFace: "Calibri", margin: 0,
  });
  s.addText(hinweis, {
    x: M, y: 5.85, w: W - 2 * M, h: 0.7,
    fontSize: 12, color: MUTED, fontFace: "Calibri", margin: 0,
  });
  s.addNotes(notiz);
}

// =========================================================================
// 1 – Titel
// =========================================================================
{
  const s = pres.addSlide();
  s.background = { color: DARK };
  s.addText("Verteidiger-Matrix", {
    x: M, y: 2.25, w: 9.6, h: 0.95,
    fontSize: 46, bold: true, color: "FFFFFF", fontFace: "Cambria", margin: 0,
  });
  s.addText("Einfluss der Netzwerktopologie auf die Lerneffizienz", {
    x: M, y: 3.2, w: 9.6, h: 0.5,
    fontSize: 20, color: "C6CDD6", fontFace: "Calibri", margin: 0,
  });
  s.addText(
    [
      { text: String(d.meta.n_runs) + " Trainingsläufe", options: { bold: true, color: "FFFFFF" } },
      { text: "   ·   ", options: { color: MUTED } },
      { text: String(d.meta.n_matchups) + " Matchups", options: { bold: true, color: "FFFFFF" } },
      { text: "   ·   ", options: { color: MUTED } },
      { text: "5 Seeds", options: { bold: true, color: "FFFFFF" } },
    ],
    { x: M, y: 4.05, w: 9.6, h: 0.4, fontSize: 15, fontFace: "Calibri", margin: 0 }
  );
  s.addText("Lauf " + d.meta.experiment + "   ·   nach Topologie-Redesign", {
    x: M, y: H - 1.05, w: 9.6, h: 0.32,
    fontSize: 12, color: MUTED, fontFace: "Calibri", margin: 0,
  });
  // Kennzahl rechts
  s.addShape(pres.ShapeType.roundRect, {
    x: 10.5, y: 2.25, w: 2.1, h: 2.2, rectRadius: 0.12,
    fill: { color: "252B33" }, line: { color: "3A424D", width: 1 },
  });
  s.addText(String(d.meta.autostop_pct).replace(".", ",") + " %", {
    x: 10.5, y: 2.6, w: 2.1, h: 0.7,
    fontSize: 34, bold: true, color: GOLD, align: "center", fontFace: "Cambria", margin: 0,
  });
  s.addText("der Läufe\nkonvergiert", {
    x: 10.5, y: 3.35, w: 2.1, h: 0.7,
    fontSize: 12, color: "C6CDD6", align: "center", fontFace: "Calibri", margin: 0,
  });
  s.addNotes("Vollstaendige Matrix, 120 Laeufe, 24 Matchups, 5 Seeds je Matchup. Auto-Stop bedeutet: das Konvergenzkriterium hat gegriffen.");
}

// =========================================================================
// 2 – Was sich geaendert hat
// =========================================================================
{
  const s = pres.addSlide();
  titelZeile(s, "Was sich gegenüber dem letzten Lauf geändert hat",
    "Zwei Eingriffe am Reward — alle Ergebnisse davor sind damit hinfällig");

  const karten = [
    ["Farmen unterbunden", "Eine Rückeroberung zählt wieder wie die erste Übernahme.",
      "CyberBattleSim schrieb den Knotenwert nur beim ersten Besitz gut und behielt den Vermerk über ein Reimage hinweg. Der Verteidiger konnte denselben Knoten wieder und wieder aufsetzen und jedes Mal dessen Wert vereinnahmen."],
    ["Haltebonus", "Je Schritt ein Tausendstel des Werts gehaltener Knoten.",
      "Der Reward misst damit nicht mehr nur, ob ein System kompromittiert wurde, sondern auch wie lange. Ohne diesen Zusatz stünde ein zwei Schritte gehaltener Knoten gleich mit einem über die ganze Episode gehaltenen."],
    ["Folge", "Die Reward-Skala ist um zwei Größenordnungen geschrumpft.",
      "Das schlechteste Matchup lag vorher bei -31889, jetzt bei -216. Zugleich konvergieren die Läufe dreimal schneller: 58 statt 194 Episoden im Median."],
  ];
  const kw = (W - 2 * M - 2 * 0.4) / 3;
  karten.forEach((k, i) => {
    const x = M + i * (kw + 0.4);
    s.addShape(pres.ShapeType.roundRect, {
      x: x, y: 1.85, w: kw, h: 3.5, rectRadius: 0.1,
      fill: { color: CARD }, line: { color: LINE, width: 1 },
    });
    s.addText(k[0], {
      x: x + 0.3, y: 2.1, w: kw - 0.6, h: 0.4,
      fontSize: 19, bold: true, color: i === 2 ? MUTED : DEF, fontFace: "Cambria", margin: 0,
    });
    s.addText(k[1], {
      x: x + 0.3, y: 2.58, w: kw - 0.6, h: 0.8,
      fontSize: 14, bold: true, color: INK, fontFace: "Calibri", margin: 0,
    });
    s.addText(k[2], {
      x: x + 0.3, y: 3.45, w: kw - 0.6, h: 1.6,
      fontSize: 12, color: MUTED, fontFace: "Calibri", margin: 0,
    });
  });
  fussnote(s, "Alle Angreifermodelle wurden neu trainiert, einschließlich des sequenziell aufgebauten Super-Angreifers.");
  s.addNotes("Wichtig fuers Meeting: Die Zahlen sind nicht mit dem Lauf vom 16.08. vergleichbar. Der Fehler steckte in MARLons Eviction-Strafe, nicht in der Topologiemodellierung.");
}

// =========================================================================
// 3 – Konvergenzmatrix (Kernbefund)
// =========================================================================
{
  const s = pres.addSlide();
  titelZeile(s, "Konvergenz: wie oft der Verteidiger stabil wird",
    "Auto-Stops von 5 Seeds je Matchup — Zeile = verteidigte Topologie, Spalte = Angreifer");

  const x0 = M + 1.75, y0 = 1.95, cw = 1.5, ch = 0.72;
  // Spaltenkoepfe
  ATKS.forEach((a, j) => {
    s.addText(KURZ[a], {
      x: x0 + j * cw, y: y0 - 0.42, w: cw, h: 0.36,
      fontSize: 12, bold: true, color: MUTED, align: "center", fontFace: "Calibri", margin: 0,
    });
  });
  s.addText("Angreifer", {
    x: x0, y: y0 - 0.78, w: cw * 6, h: 0.3,
    fontSize: 11, color: ATK, align: "center", fontFace: "Calibri", bold: true, margin: 0,
  });

  DEFS.forEach((t, i) => {
    const y = y0 + i * ch;
    s.addText(KURZ[t], {
      x: M, y: y, w: 1.65, h: ch,
      fontSize: 13, bold: true, color: INK, align: "right", valign: "middle",
      fontFace: "Calibri", margin: 0,
    });
    let summe = 0;
    ATKS.forEach((a, j) => {
      const v = d.convergence[t][a];
      const n = v ? v.autostop : null;
      summe += n || 0;
      s.addShape(pres.ShapeType.rect, {
        x: x0 + j * cw, y: y, w: cw - 0.06, h: ch - 0.06,
        fill: { color: heat(n) }, line: { color: "FFFFFF", width: 1.5 },
      });
      s.addText(n === null ? "–" : n + "/5", {
        x: x0 + j * cw, y: y + 0.06, w: cw - 0.06, h: 0.34,
        fontSize: 15, bold: true, color: INK, align: "center", fontFace: "Calibri", margin: 0,
      });
      const me = v && v.mean_episodes != null ? Math.round(v.mean_episodes) + " Ep." : "kein Stopp";
      s.addText(me, {
        x: x0 + j * cw, y: y + 0.38, w: cw - 0.06, h: 0.26,
        fontSize: 10, color: MUTED, align: "center", fontFace: "Calibri", margin: 0,
      });
    });
    // Zeilensumme
    s.addText(summe + "/30", {
      x: x0 + 6 * cw + 0.12, y: y, w: 1.0, h: ch,
      fontSize: 15, bold: true, valign: "middle",
      color: summe >= 20 ? DEF : INK, fontFace: "Cambria", margin: 0,
    });
  });

  s.addText("Nach dem Reward-Fix konvergieren 118 von 120 Läufen. Die Konvergenz trennt die Topologien damit nicht mehr — der Unterschied muss aus dem Reward-Niveau und der Wirksamkeit kommen.", {
    x: M, y: 5.15, w: W - 2 * M, h: 0.4,
    fontSize: 14, bold: true, color: DEF, fontFace: "Calibri", margin: 0,
  });
  fussnote(s, "Dunkleres Grün = mehr Seeds konvergiert. Zweite Zeile je Feld: mittlere Episodenzahl bis zum Stopp.");
  s.addNotes("Diese Folie war im letzten Lauf die Kernfolie. Sie ist es nicht mehr: Fast alle Zellen sind gleich. Das ist selbst das Ergebnis, denn vorher verhinderte das Farmen ein Plateau.");
}

// =========================================================================
// 4 – Konvergenz je Topologie (Balken)
// =========================================================================
{
  const s = pres.addSlide();
  titelZeile(s, "Lerneffizienz nach verteidigter Topologie",
    "Summe der Auto-Stops über alle sechs Angreifer, maximal 30 — nahezu ausgereizt");

  const labels = DEFS.map((t) => KURZ[t]);
  const werte = DEFS.map((t) =>
    ATKS.reduce((acc, a) => acc + ((d.convergence[t][a] || {}).autostop || 0), 0)
  );
  s.addChart(pres.ChartType.bar, [{ name: "Konvergierte Läufe", labels: labels, values: werte }], {
    x: M, y: 1.75, w: 7.2, h: 4.2,
    barDir: "col", chartColors: [DEF, DEF, GOLD, DEF],
    varyColors: true,
    showValue: true, dataLabelPosition: "outEnd",
    dataLabelColor: INK, dataLabelFontSize: 14, dataLabelFontBold: true,
    showLegend: false, showTitle: false,
    valAxisMaxVal: 30, valAxisMinVal: 0,
    catAxisLabelColor: INK, catAxisLabelFontSize: 13,
    valAxisLabelColor: MUTED, valAxisLabelFontSize: 11,
    valGridLine: { color: LINE, size: 1 },
    catGridLine: { style: "none" },
  });

  // Aus den Daten gerechnet statt fest verdrahtet, damit nichts veraltet.
  const punkte = DEFS.map((t) => {
    const summe = ATKS.reduce((acc, a) => acc + ((d.convergence[t][a] || {}).autostop || 0), 0);
    const eps = ATKS.map((a) => (d.convergence[t][a] || {}).mean_episodes)
                    .filter((x) => typeof x === "number");
    const mittel = eps.length ? Math.round(eps.reduce((x, y) => x + y, 0) / eps.length) : null;
    return [KURZ[t] + " " + summe + "/30",
            mittel ? ("Im Mittel " + mittel + " Episoden bis zum Stopp.") : "Keine Konvergenz."];
  }).sort((a, b) => parseInt(b[0].match(/(\d+)\/30/)[1]) - parseInt(a[0].match(/(\d+)\/30/)[1]));
  punkte.forEach((p, i) => {
    const y = 1.95 + i * 1.0;
    s.addText(p[0], {
      x: 8.3, y: y, w: 4.3, h: 0.3,
      fontSize: 15, bold: true, color: i === 0 ? GOLD : INK, fontFace: "Calibri", margin: 0,
    });
    s.addText(p[1], {
      x: 8.3, y: y + 0.3, w: 4.3, h: 0.55,
      fontSize: 12, color: MUTED, fontFace: "Calibri", margin: 0,
    });
  });
  s.addNotes("Der Engpass in Hub & Spoke bringt dem Verteidiger nichts, sobald er selbst uebernehmbar ist.");
}

// =========================================================================
// 5 – Das Diagonalmuster
// =========================================================================
{
  const s = pres.addSlide();
  titelZeile(s, "Der Spezialist schlägt jede Topologie",
    "Verteidiger-Reward gegen den eigenen Angreifer — je negativer, desto mehr erreicht er");

  // Gemessen am Reward statt an der Konvergenz: Nach dem Fix konvergiert
  // fast alles, das Diagonalmuster zeigt sich jetzt im Niveau.
  const diag = DEFS.map((t) => [KURZ[t], Math.round((d.defender[t][t] || {}).median || 0)]);
  const kw = (W - 2 * M - 3 * 0.35) / 4;
  diag.forEach((r, i) => {
    const x = M + i * (kw + 0.35);
    s.addShape(pres.ShapeType.roundRect, {
      x: x, y: 2.0, w: kw, h: 2.05, rectRadius: 0.1,
      fill: { color: CARD }, line: { color: LINE, width: 1 },
    });
    s.addText(r[0], {
      x: x, y: 2.2, w: kw, h: 0.34,
      fontSize: 14, bold: true, color: MUTED, align: "center", fontFace: "Calibri", margin: 0,
    });
    s.addText(String(r[1]), {
      x: x, y: 2.62, w: kw, h: 0.85,
      fontSize: 40, bold: true, color: r[1] <= -180 ? ATK : INK, align: "center",
      fontFace: "Cambria", margin: 0,
    });
    s.addText("gegen sich selbst", {
      x: x, y: 3.5, w: kw, h: 0.3,
      fontSize: 11, color: MUTED, align: "center", fontFace: "Calibri", margin: 0,
    });
  });

  s.addText("Zum Vergleich: Gegen den Chain-Angreifer, der auf einer neutralen Kette trainiert wurde, liegt derselbe Wert bei -44 bis -79. Der Angreifer ist dort also drei- bis fünfmal weniger erfolgreich.", {
    x: M, y: 4.5, w: W - 2 * M, h: 0.5,
    fontSize: 15, color: INK, fontFace: "Calibri", margin: 0,
  });
  s.addText("Die Schwierigkeit liegt damit nicht allein in der Topologie, sondern im Zusammenspiel aus Topologie und Angreiferherkunft. Für die Arbeit heißt das: Der Angreifer ist keine feste Umgebungseigenschaft, sondern eine zweite Variable.", {
    x: M, y: 5.1, w: W - 2 * M, h: 0.8,
    fontSize: 13, color: MUTED, fontFace: "Calibri", margin: 0,
  });
  s.addNotes("Diskussionspunkt: spricht fuer eine Auswertung, die nach Angreiferherkunft trennt.");
}

// =========================================================================
// 6 – Reward-Matrix mit Warnung
// =========================================================================
{
  const s = pres.addSlide();
  titelZeile(s, "Verteidiger-Reward — mit Vorsicht zu lesen",
    "Median der letzten 20 Episoden, über 5 Seeds gemittelt");

  const x0 = M + 1.75, y0 = 1.95, cw = 1.5, ch = 0.62;
  ATKS.forEach((a, j) => {
    s.addText(KURZ[a], {
      x: x0 + j * cw, y: y0 - 0.4, w: cw, h: 0.34,
      fontSize: 12, bold: true, color: MUTED, align: "center", fontFace: "Calibri", margin: 0,
    });
  });
  DEFS.forEach((t, i) => {
    const y = y0 + i * ch;
    s.addText(KURZ[t], {
      x: M, y: y, w: 1.65, h: ch,
      fontSize: 13, bold: true, color: INK, align: "right", valign: "middle",
      fontFace: "Calibri", margin: 0,
    });
    ATKS.forEach((a, j) => {
      const v = d.defender[t][a];
      const m = v ? Math.round(v.median) : null;
      s.addShape(pres.ShapeType.rect, {
        x: x0 + j * cw, y: y, w: cw - 0.06, h: ch - 0.06,
        fill: { color: m === null ? CARD : (m > 400 ? "E3EDF1" : "F7F8F9") },
        line: { color: "FFFFFF", width: 1.5 },
      });
      s.addText(m === null ? "–" : m.toLocaleString("de-DE"), {
        x: x0 + j * cw, y: y + 0.12, w: cw - 0.06, h: 0.36,
        fontSize: 14, bold: Math.abs(m || 0) > 400,
        color: m === null ? MUTED : (m < 0 ? ATK : INK),
        align: "center", fontFace: "Calibri", margin: 0,
      });
    });
  });

  s.addShape(pres.ShapeType.roundRect, {
    x: M, y: 4.75, w: W - 2 * M, h: 1.5, rectRadius: 0.1,
    fill: { color: "FBF3E4" }, line: { color: "EBD6AB", width: 1 },
  });
  s.addText("Diese Zahlen sind zwischen Topologien nicht vergleichbar", {
    x: M + 0.35, y: 4.95, w: W - 2 * M - 0.7, h: 0.35,
    fontSize: 15, bold: true, color: "8A6414", fontFace: "Calibri", margin: 0,
  });
  s.addText("Der Verteidiger-Reward ist an den des Angreifers gekoppelt, und wie viel dort überhaupt zu holen ist, unterscheidet sich je Topologie erheblich. Ein Wert nahe null kann heißen, dass gut verteidigt wurde, oder dass dort ohnehin wenig zu erreichen war. Vergleichbar wird es erst durch die Evaluation gegen ein ungeschütztes Netz.", {
    x: M + 0.35, y: 5.32, w: W - 2 * M - 0.7, h: 0.8,
    fontSize: 12, color: INK, fontFace: "Calibri", margin: 0,
  });
  s.addNotes("Alle Werte sind jetzt negativ und liegen zwischen -44 und -216. Vor dem Reward-Fix reichte die Spanne von -31889 bis +5484.");
}

// =========================================================================
// 7 / 8 – Reward-Tabellen beider Seiten
// =========================================================================
tabellenFolie(
  'defender_table.json',
  'Verteidiger-Reward: Beginn und Ende des Trainings',
  'Mittel der ersten 10 gegen die letzten 20 Episoden — konvergierte Seeds fortgeschrieben, am Schrittlimit beendete fallen heraus',
  false,
  'Blau = der Verteidiger verbessert sich im Lauf des Trainings. Rot = er verliert an Boden.',
  'Die DMZ-Zeile bleibt durchgehend nahe null: Der Verteidiger startet bei rund −730 und landet zwischen −40 und −100. Er lernt also, den Schaden auf fast nichts zu drücken. In Flat und Hub & Spoke laufen die Werte dagegen weit auseinander — von −3.846 auf −31.889 gegen den eigenen Angreifer, aber von −738 auf +4.649 gegen den Super-Angreifer.',
  'Zahlen aus prep_curves.py. Anfangswerte liegen ueberall bei etwa -600 bis -900, der Startpunkt ist also vergleichbar.'
);

tabellenFolie(
  'attacker_table.json',
  'Angreifer-Reward: Beginn und Ende des Trainings',
  'Dieselbe Rechnung für die Gegenseite — zeigt, ob der Verteidiger den Angreifer über die Zeit zurückdrängt',
  true,
  'Blau = der Angreifer verliert im Lauf des Trainings an Boden. Rot = er hält sein Niveau oder verbessert sich.',
  'Auffällig ist erneut die DMZ-Zeile: Dort bleibt der Angreifer-Reward über das gesamte Training nahezu unverändert. Der Verteidiger drängt ihn nicht zurück — er hält ihn von Anfang an klein. Die einzige Ausnahme ist der DMZ-Angreifer selbst, gegen den der Reward von 1.617 auf −2.406 kippt.',
  'Gegenstueck zur Verteidigerfolie. Beide Seiten sind ueber die Zerosum-Kopplung verbunden, aber nicht exakt spiegelbildlich.'
);

// =========================================================================
// 8 – Angreifer-Erfolg
// =========================================================================
{
  const s = pres.addSlide();
  titelZeile(s, "Wie weit kommt der Angreifer?",
    "Anteil der Episoden mit erreichtem Crown Jewel, je Matchup");

  const serien = ATKS.map((a) => ({
    name: KURZ[a],
    labels: DEFS.map((t) => KURZ[t]),
    values: DEFS.map((t) => (d.atkstats[t][a] ? d.atkstats[t][a].cj_pct : 0)),
  }));
  s.addChart(pres.ChartType.bar, serien, {
    x: M, y: 1.8, w: W - 2 * M, h: 4.0,
    barDir: "col", barGrouping: "clustered",
    chartColors: ["B9C0C8", "8FA3B3", "C2A05A", "7BA88F", "9C8AA5", ATK],
    showValue: false, showLegend: true, legendPos: "b",
    legendColor: INK, legendFontSize: 11, showTitle: false,
    valAxisMaxVal: 100, valAxisMinVal: 0,
    valAxisTitle: "Crown Jewel erreicht (%)", showValAxisTitle: true,
    valAxisTitleColor: MUTED, valAxisTitleFontSize: 11,
    catAxisLabelColor: INK, catAxisLabelFontSize: 12,
    valAxisLabelColor: MUTED, valAxisLabelFontSize: 10,
    valGridLine: { color: LINE, size: 1 },
    catGridLine: { style: "none" },
  });
  fussnote(s, "Der Crown Jewel beendet die Episode nicht — sie läuft bis zur Übernahme aller Knoten oder ins Schrittlimit.");
  s.addNotes("Ergaenzt die Konvergenz um die Frage, ob der Angreifer ueberhaupt vorankommt.");
}

// =========================================================================
// Wie viele Knoten nimmt der Angreifer?
// =========================================================================
{
  const s = pres.addSlide();
  titelZeile(s, "Wie viele Knoten hält der Angreifer?",
    "Mittel je Matchup, von zehn Knoten im Netz — Zeile = verteidigte Topologie, Spalte = Angreifer");

  const x0 = M + 1.75, y0 = 1.95, cw = 1.5, ch = 0.72;

  // Faerbung nach Anteil der zehn Knoten: je mehr der Angreifer haelt,
  // desto roter. Gleiche Leserichtung wie die Konvergenzfolie, nur
  // umgekehrtes Vorzeichen (dort ist dunkel gut, hier schlecht).
  function heatKnoten(v) {
    if (v === null || v === undefined) return CARD;
    const stufen = [
      [2.0, "F4F6F8"], [3.0, "FBEDEA"], [4.0, "F6D9D3"],
      [5.5, "EDB9AF"], [7.0, "E0968A"], [99, "D07C6E"],
    ];
    for (const [grenze, farbe] of stufen) if (v < grenze) return farbe;
    return "D07C6E";
  }

  ATKS.forEach((a, j) => {
    s.addText(KURZ[a], {
      x: x0 + j * cw, y: y0 - 0.42, w: cw, h: 0.36,
      fontSize: 12, bold: true, color: MUTED, align: "center", fontFace: "Calibri", margin: 0,
    });
  });
  s.addText("Angreifer", {
    x: x0, y: y0 - 0.78, w: cw * 6, h: 0.3,
    fontSize: 11, color: ATK, align: "center", fontFace: "Calibri", bold: true, margin: 0,
  });

  DEFS.forEach((t, i) => {
    const y = y0 + i * ch;
    s.addText(KURZ[t], {
      x: M, y: y, w: 1.65, h: ch,
      fontSize: 13, bold: true, color: INK, align: "right", valign: "middle",
      fontFace: "Calibri", margin: 0,
    });
    let summe = 0, n_zellen = 0;
    ATKS.forEach((a, j) => {
      const st = d.atkstats[t][a];
      const v = st ? st.max_owned : null;
      if (v !== null) { summe += v; n_zellen++; }
      s.addShape(pres.ShapeType.rect, {
        x: x0 + j * cw, y: y, w: cw - 0.06, h: ch - 0.06,
        fill: { color: heatKnoten(v) }, line: { color: "FFFFFF", width: 1.5 },
      });
      s.addText(v === null ? "–" : v.toFixed(1), {
        x: x0 + j * cw, y: y + 0.06, w: cw - 0.06, h: 0.34,
        fontSize: 15, bold: true, color: INK, align: "center", fontFace: "Calibri", margin: 0,
      });
      s.addText(st ? "CJ " + st.cj_pct.toFixed(0) + " %" : "", {
        x: x0 + j * cw, y: y + 0.38, w: cw - 0.06, h: 0.26,
        fontSize: 10, color: MUTED, align: "center", fontFace: "Calibri", margin: 0,
      });
    });
    s.addText(n_zellen ? "\u2300 " + (summe / n_zellen).toFixed(1) : "–", {
      x: x0 + 6 * cw + 0.12, y: y, w: 1.0, h: ch,
      fontSize: 15, bold: true, valign: "middle",
      color: INK, fontFace: "Cambria", margin: 0,
    });
  });

  s.addText("Der Angreifer hält fast überall ein bis drei der zehn Knoten. Nur auf der Diagonalen kommt er weiter: gegen den eigenen Angreifer bis 6,9 Knoten in der DMZ.", {
    x: M, y: 5.15, w: W - 2 * M, h: 0.4,
    fontSize: 14, bold: true, color: ATK, fontFace: "Calibri", margin: 0,
  });
  s.addText("Der Einstiegsknoten WebServer ist von Beginn an übernommen und zählt mit. Ein Wert von 1,1 heißt also, dass der Angreifer über den Einstieg praktisch nicht hinauskommt.", {
    x: M, y: 5.58, w: W - 2 * M, h: 0.5,
    fontSize: 12, color: MUTED, fontFace: "Calibri", margin: 0,
  });
  fussnote(s, "Mittel über alle Episoden aller fünf Seeds, gleiche Grundlage wie die Crown-Jewel-Quote der Vorfolie. Zweite Zeile je Feld: Anteil der Episoden mit erreichtem Crown Jewel.");
  s.addNotes("Ergaenzt die CJ-Folie: Die Krone wird oft erreicht, das Netz aber selten uebernommen. Der Angreifer kommt an das wertvolle System, breitet sich danach aber nicht aus.");
}


// =========================================================================
// 8–11 – Verlauf je verteidigter Topologie
// =========================================================================
DEFS.forEach((t) => {
  const bild = "verlauf_" + t + ".png";
  if (!fs.existsSync(bild)) return;
  const s = pres.addSlide();
  s.background = { color: DARK };
  s.addImage({ path: bild, x: 0.18, y: 0.16, w: W - 0.36, h: H - 0.32 });
  s.addNotes(
    "Je Angreifer ein Feld. Senkrechte Linien markieren, wann ein Seed endet: " +
    "gold gestrichelt = konvergiert und ausgestiegen, grau gepunktet = am Schrittlimit. " +
    "Blass gezeichnete Abschnitte beruhen nicht mehr auf allen fuenf Seeds. Konvergierte Seeds werden mit ihrem letzten Wert fortgeschrieben (das Kriterium sagt aus, dass er stabil ist); am Schrittlimit beendete Seeds fallen heraus, weil ihr Wert nicht stabil war."
  );
});

// =========================================================================
// Aktionsverteilung je verteidigter Topologie
// =========================================================================
{
  const s = pres.addSlide();
  titelZeile(s, 'Nichtstun als gelernte Strategie',
    'Anteil der Schritte je Aktionsart — die fünf Kategorien summieren sich auf die Episodenlänge');
  const karten = [
    ['≈ 66 %', 'ungültige Aktionen', 'Der Verteidiger arbeitet ohne Maske. Eine ungültige Aktion kostet ihn nichts — er überspringt den Zug. Sie ist damit sein günstigster Weg, nichts zu tun.'],
    ['88 % → 93 %', 'passive Züge gesamt', 'Ungültig plus Freigeben, also alles, was den Zustand nicht verändert. Dieser Anteil steigt in ALLEN 24 Matchups über das Training.'],
    ['6 % → 0 %', 'Dienst stoppen', 'Fällt in den ersten rund 15 Episoden fast vollständig weg. Das Stoppen sauberer Dienste kostet Strafpunkte, und genau das lernt der Agent zuerst ab.'],
  ];
  const kw = (W - 2 * M - 2 * 0.4) / 3;
  karten.forEach((k, i2) => {
    const x = M + i2 * (kw + 0.4);
    s.addShape(pres.ShapeType.roundRect, {
      x: x, y: 2.0, w: kw, h: 3.3, rectRadius: 0.1,
      fill: { color: CARD }, line: { color: LINE, width: 1 },
    });
    s.addText(k[0], {
      x: x + 0.3, y: 2.25, w: kw - 0.6, h: 0.6,
      fontSize: 30, bold: true, color: i2 === 2 ? GOLD : DEF, fontFace: 'Cambria', margin: 0,
    });
    s.addText(k[1], {
      x: x + 0.3, y: 2.9, w: kw - 0.6, h: 0.36,
      fontSize: 15, bold: true, color: INK, fontFace: 'Calibri', margin: 0,
    });
    s.addText(k[2], {
      x: x + 0.3, y: 3.35, w: kw - 0.6, h: 1.7,
      fontSize: 12, color: MUTED, fontFace: 'Calibri', margin: 0,
    });
  });
  s.addText('Der Anteil sinkt über das Training nicht, obwohl der Agent längst wissen müsste, was gültig ist. Der Grund steht im Code: die Strafe für eine ungültige Aktion ist auf 0 gesetzt, der Zug wird übersprungen. Jede echte Aktion birgt dagegen ein Risiko — ein sauberer Dienststopp kostet 10 Punkte, ein Reimage nimmt einen Knoten vom Netz. Passivität ist damit keine Schwäche, sondern gelernte Strategie.', {
    x: M, y: 5.5, w: W - 2 * M, h: 0.95, fontSize: 12, color: MUTED, fontFace: 'Calibri', margin: 0,
  });
  s.addNotes('Zahlen aus combined_episodes.csv, Mittel ueber alle 120 Laeufe. def_start_svc ist durchgehend 0 und deshalb nicht dargestellt.');
}

DEFS.forEach((t) => {
  const bild = 'aktionen_' + t + '.png';
  if (!fs.existsSync(bild)) return;
  const s = pres.addSlide();
  s.background = { color: DARK };
  s.addImage({ path: bild, x: 0.18, y: 0.16, w: W - 0.36, h: H - 0.32 });
  s.addNotes('Gestapelte Anteile je Episode, gemittelt nach denselben Seed-Regeln wie die Reward-Kurven. Die gestrichelte Linie markiert, ab wo nicht mehr alle fuenf Seeds beitragen.');
});

// =========================================================================
// SLA-Brueche
// =========================================================================
if (fs.existsSync('sla_matrix.png')) {
  const s = pres.addSlide();
  s.background = { color: DARK };
  s.addImage({ path: 'sla_matrix.png', x: 0.18, y: 0.16, w: W - 0.36, h: H - 0.32 });
  s.addNotes('SLA-Brueche treten in nur 4 von 24 Matchups ueberhaupt auf, und ausschliesslich dort, wo Verteidiger und Angreifer auf derselben Topologie beruhen bzw. gegen Hub & Spoke. Micro-Segmentation bricht die SLA nie.');
}

// =========================================================================
// Einzelne Seeds der beiden Selbst-Matchups
// =========================================================================
if (fs.existsSync("seeds_diagonale.png")) {
  const s = pres.addSlide();
  titelZeile(s, "Woher die Ausschläge kommen",
    "Verteidiger-Reward je Episode, jeder Seed einzeln — die beiden Matchups mit SLA-Brüchen");
  s.addImage({ path: "seeds_diagonale.png", x: 0.35, y: 1.5, w: W - 0.7, h: 4.15 });
  s.addText("Es ist kein einzelner Ausreißerlauf: In beiden Matchups brechen alle fünf Seeds das SLA. Dazwischen liegen sie stabil zwischen -100 und -300, und genau darauf greift das Konvergenzkriterium.", {
    x: M, y: 5.75, w: W - 2 * M, h: 0.5,
    fontSize: 14, bold: true, color: GOLD, fontFace: "Calibri", margin: 0,
  });
  fussnote(s, "Gestauchte Achse, sonst verschwindet der Arbeitsbereich neben den Einbrüchen. Ein SLA-Bruchschritt kostet -5000, die schlechteste Episode der Matrix liegt bei -185541.");
  s.addNotes("Antwort auf die Frage, wie 4 von 5 Seeds konvergieren koennen: Die Ausschlaege sind selten und das Kriterium arbeitet auf dem geglaetteten Verlauf.");
}


// =========================================================================
// 9 – Fazit
// =========================================================================
// =========================================================================
// Trenner: ab hier Evaluation
// =========================================================================
if (extra && extra.evaluation) {
  const s = pres.addSlide();
  s.background = { color: DARK };

  s.addText("Ab hier: Evaluation", {
    x: M, y: 0.85, w: W - 2 * M, h: 0.75,
    fontSize: 36, bold: true, color: "FFFFFF", fontFace: "Cambria", margin: 0,
  });
  s.addText("Die bisherigen Folien zeigen, wie schnell der Verteidiger stabil wird. Die folgenden zeigen, ob die gelernte Politik etwas nützt.", {
    x: M, y: 1.62, w: W - 2 * M, h: 0.5,
    fontSize: 15, color: "B8C0C9", fontFace: "Calibri", margin: 0,
  });

  const karten = [
    ["Beide Agenten eingefroren",
     "Es wird nichts mehr gelernt, nur noch gespielt. Gemessen wird die fertige Politik, nicht ihr Zustandekommen."],
    ["Drei Stufen je Lauf",
     "Kein Verteidiger als Obergrenze, ein Zufallsagent als Vergleich, das trainierte Modell. Der Angreifer ist in allen drei Stufen derselbe und stammt aus demselben Lauf-Ordner."],
    ["Umfang",
     "4 Topologien × 6 Angreifer × 5 Seeds × 3 Stufen = 360 Zellen, je 25 Episoden mit höchstens 2000 Schritten. Insgesamt 9000 Episoden."],
  ];
  const kw = (W - 2 * M - 2 * 0.4) / 3;
  karten.forEach((k, i) => {
    const x = M + i * (kw + 0.4);
    s.addShape(pres.ShapeType.roundRect, {
      x: x, y: 2.45, w: kw, h: 2.6, rectRadius: 0.1,
      fill: { color: "252A33" }, line: { color: "3A414C", width: 1 },
    });
    s.addText(k[0], {
      x: x + 0.3, y: 2.7, w: kw - 0.6, h: 0.45,
      fontSize: 16, bold: true, color: GOLD, fontFace: "Cambria", margin: 0,
    });
    s.addText(k[1], {
      x: x + 0.3, y: 3.2, w: kw - 0.6, h: 1.65,
      fontSize: 12, color: "B8C0C9", fontFace: "Calibri", margin: 0,
    });
  });

  s.addText("Warum das nötig ist: Konvergenz sagt nur, dass ein Verteidiger aufgehört hat, sich zu verändern. Sie sagt nichts darüber, ob der Zustand, in dem er stehen bleibt, gut ist.", {
    x: M, y: 5.3, w: W - 2 * M, h: 0.6,
    fontSize: 13, color: "8B94A0", fontFace: "Calibri", italic: true, margin: 0,
  });
  s.addNotes("Uebergangsfolie. Wichtig zu betonen: Der Zufallsagent ist die eigentliche Messlatte, nicht das ungeschuetzte Netz.");
}

// =========================================================================
// Was bringt der Verteidiger ueberhaupt?
// =========================================================================
if (extra && extra.evaluation && extra.evaluation.je_matchup_stufe) {
  const s = pres.addSlide();
  titelZeile(s, "Bringt der Verteidiger etwas? Angreifer-Reward",
    "Restanteil je Matchup: welchen Anteil seines Rewards der Angreifer gegen den Verteidiger noch erreicht, gemessen am ungeschützten Netz");

  const ms = extra.evaluation.je_matchup_stufe;
  const x0 = M + 1.75, y0 = 1.95, cw = 1.5, ch = 0.72;

  // Je niedriger der Restanteil, desto wirksamer der Verteidiger.
  function heatRest(v) {
    if (v === null || v === undefined) return CARD;
    const stufen = [
      [15, "CFE3EC"], [25, "DDEAF1"], [35, "EDF2F5"],
      [50, "FBEDEA"], [70, "F3D5CE"], [1e9, "E3A99C"],
    ];
    for (const [g, f] of stufen) if (v < g) return f;
    return "E3A99C";
  }

  ATKS.forEach((a, j) => {
    s.addText(KURZ[a], {
      x: x0 + j * cw, y: y0 - 0.42, w: cw, h: 0.36,
      fontSize: 12, bold: true, color: MUTED, align: "center", fontFace: "Calibri", margin: 0,
    });
  });
  s.addText("Angreifer", {
    x: x0, y: y0 - 0.78, w: cw * 6, h: 0.3,
    fontSize: 11, color: ATK, align: "center", fontFace: "Calibri", bold: true, margin: 0,
  });

  DEFS.forEach((t, i) => {
    const y = y0 + i * ch;
    s.addText(KURZ[t], {
      x: M, y: y, w: 1.65, h: ch,
      fontSize: 13, bold: true, color: INK, align: "right", valign: "middle",
      fontFace: "Calibri", margin: 0,
    });
    ATKS.forEach((a, j) => {
      const e = ms[t] ? ms[t][a] : null;
      let rt = null, rz = null;
      if (e && e.keiner) {
        if (e.trainiert !== null) rt = 100 * e.trainiert / e.keiner;
        if (e.zufaellig !== null) rz = 100 * e.zufaellig / e.keiner;
      }
      s.addShape(pres.ShapeType.rect, {
        x: x0 + j * cw, y: y, w: cw - 0.06, h: ch - 0.06,
        fill: { color: heatRest(rt) }, line: { color: "FFFFFF", width: 1.5 },
      });
      s.addText(rt === null ? "–" : rt.toFixed(0) + " %", {
        x: x0 + j * cw, y: y + 0.06, w: cw - 0.06, h: 0.34,
        fontSize: 15, bold: true, color: INK, align: "center", fontFace: "Calibri", margin: 0,
      });
      s.addText(rz === null ? "" : "Zufall " + rz.toFixed(0) + " %", {
        x: x0 + j * cw, y: y + 0.38, w: cw - 0.06, h: 0.26,
        fontSize: 10, color: MUTED, align: "center", fontFace: "Calibri", margin: 0,
      });
    });
  });

  s.addText("In fast jeder Zelle liegen trainiertes Modell und Zufallsagent dicht beieinander. Der Verteidiger wirkt, aber die gelernte Politik ist kaum besser als blindes Handeln.", {
    x: M, y: 5.05, w: W - 2 * M, h: 0.45,
    fontSize: 15, bold: true, color: ATK, fontFace: "Calibri", margin: 0,
  });
  s.addText("Bewusst ohne Zeilenmittel: Beide üblichen Arten zu aggregieren verzerren in verschiedene Richtungen. Das Verhältnis der Summen wird vom stärksten Angreifer bestimmt, das Mittel der Einzelverhältnisse vom schwächsten. Der Chain-Angreifer etwa erreicht in der Micro-Segmentation einen Restanteil von 67 Prozent, holt ungeschützt aber nur 36 Punkte.", {
    x: M, y: 5.5, w: W - 2 * M, h: 0.7,
    fontSize: 11.5, color: MUTED, fontFace: "Calibri", margin: 0,
  });
  fussnote(s, "Restanteil = Angreifer-Reward mit Verteidiger geteilt durch den ohne Verteidiger. Kleiner ist besser. 25 Episoden je Zelle, Median über Episoden und über alle " +
    (extra.evaluation.seeds || []).length + " Seeds. Beide Agenten sind eingefroren.");
  s.addNotes("Kernfolie fuer die Frage nach dem Nutzen. Auf die Zellen mit grossem Abstand zwischen trainiert und Zufall zeigen, das sind die Ausnahmen.");
}

// =========================================================================
// Gehaltene Knoten je Stufe
// =========================================================================
if (extra && extra.evaluation && extra.evaluation.je_matchup_knoten) {
  const s = pres.addSlide();
  titelZeile(s, "Bringt der Verteidiger etwas? Gehaltene Knoten",
    "Vom Angreifer gehaltene Knoten je Matchup, von zehn im Netz — große Zahl = trainiertes Modell");

  const mk = extra.evaluation.je_matchup_knoten;
  const x0 = M + 1.75, y0 = 1.95, cw = 1.5, ch = 0.78;

  function heatK(v) {
    if (v === null || v === undefined) return CARD;
    const st = [[1.5, "DCEAF1"], [2.5, "E9F1F5"], [4, "F4F6F8"],
                [6, "FBEDEA"], [8, "F2D3CC"], [1e9, "E0A092"]];
    for (const [g, f] of st) if (v < g) return f;
    return "E0A092";
  }

  ATKS.forEach((a, j) => {
    s.addText(KURZ[a], {
      x: x0 + j * cw, y: y0 - 0.42, w: cw, h: 0.36,
      fontSize: 12, bold: true, color: MUTED, align: "center", fontFace: "Calibri", margin: 0,
    });
  });
  s.addText("Angreifer", {
    x: x0, y: y0 - 0.78, w: cw * 6, h: 0.3,
    fontSize: 11, color: ATK, align: "center", fontFace: "Calibri", bold: true, margin: 0,
  });

  DEFS.forEach((t, i) => {
    const y = y0 + i * ch;
    s.addText(KURZ[t], {
      x: M, y: y, w: 1.65, h: ch,
      fontSize: 13, bold: true, color: INK, align: "right", valign: "middle",
      fontFace: "Calibri", margin: 0,
    });
    ATKS.forEach((a, j) => {
      const e = (mk[t] || {})[a] || {};
      s.addShape(pres.ShapeType.rect, {
        x: x0 + j * cw, y: y, w: cw - 0.06, h: ch - 0.06,
        fill: { color: heatK(e.trainiert) }, line: { color: "FFFFFF", width: 1.5 },
      });
      s.addText(e.trainiert === null || e.trainiert === undefined ? "–" : e.trainiert.toFixed(1), {
        x: x0 + j * cw, y: y + 0.06, w: cw - 0.06, h: 0.36,
        fontSize: 15, bold: true, color: INK, align: "center", fontFace: "Cambria", margin: 0,
      });
      const zeile2 = (e.keiner != null ? "ohne " + e.keiner.toFixed(1) : "") +
                     (e.zufaellig != null ? " · Zuf " + e.zufaellig.toFixed(1) : "");
      s.addText(zeile2, {
        x: x0 + j * cw, y: y + 0.42, w: cw - 0.06, h: 0.3,
        fontSize: 9, color: MUTED, align: "center", fontFace: "Calibri", margin: 0,
      });
    });
  });

  s.addText("In Hub & Spoke und DMZ hält der Angreifer gegen das trainierte Modell weniger Knoten als gegen den Zufallsagenten. In Flat und Micro-Segmentation macht das Training keinen Unterschied.", {
    x: M, y: 5.3, w: W - 2 * M, h: 0.5,
    fontSize: 14, bold: true, color: DEF, fontFace: "Calibri", margin: 0,
  });
  fussnote(s, "Median über 25 Episoden je Zelle und über alle fünf Seeds. Der Einstiegsknoten WebServer ist von Beginn an übernommen und zählt mit.");
  s.addNotes("Hier zeigt sich der Nutzen des Trainings deutlicher als am Reward, weil keine Strafterme dazwischenliegen.");
}

// =========================================================================
// Crown Jewel je Stufe
// =========================================================================
if (extra && extra.evaluation && extra.evaluation.je_matchup_cj) {
  const s = pres.addSlide();
  titelZeile(s, "Bringt der Verteidiger etwas? Crown Jewel",
    "Anteil der Episoden mit erreichtem Datenbankserver — große Zahl = trainiertes Modell");

  const mc = extra.evaluation.je_matchup_cj;
  const x0 = M + 1.75, y0 = 1.95, cw = 1.5, ch = 0.78;

  function heatC(v) {
    if (v === null || v === undefined) return CARD;
    const st = [[5, "DCEAF1"], [20, "E9F1F5"], [40, "F4F6F8"],
                [60, "FBEDEA"], [85, "F2D3CC"], [1e9, "E0A092"]];
    for (const [g, f] of st) if (v < g) return f;
    return "E0A092";
  }

  ATKS.forEach((a, j) => {
    s.addText(KURZ[a], {
      x: x0 + j * cw, y: y0 - 0.42, w: cw, h: 0.36,
      fontSize: 12, bold: true, color: MUTED, align: "center", fontFace: "Calibri", margin: 0,
    });
  });
  s.addText("Angreifer", {
    x: x0, y: y0 - 0.78, w: cw * 6, h: 0.3,
    fontSize: 11, color: ATK, align: "center", fontFace: "Calibri", bold: true, margin: 0,
  });

  DEFS.forEach((t, i) => {
    const y = y0 + i * ch;
    s.addText(KURZ[t], {
      x: M, y: y, w: 1.65, h: ch,
      fontSize: 13, bold: true, color: INK, align: "right", valign: "middle",
      fontFace: "Calibri", margin: 0,
    });
    ATKS.forEach((a, j) => {
      const e = (mc[t] || {})[a] || {};
      s.addShape(pres.ShapeType.rect, {
        x: x0 + j * cw, y: y, w: cw - 0.06, h: ch - 0.06,
        fill: { color: heatC(e.trainiert) }, line: { color: "FFFFFF", width: 1.5 },
      });
      s.addText(e.trainiert === null || e.trainiert === undefined ? "–" : e.trainiert.toFixed(0) + " %", {
        x: x0 + j * cw, y: y + 0.06, w: cw - 0.06, h: 0.36,
        fontSize: 15, bold: true, color: INK, align: "center", fontFace: "Cambria", margin: 0,
      });
      const zeile2 = (e.keiner != null ? "ohne " + e.keiner.toFixed(0) : "") +
                     (e.zufaellig != null ? " · Zuf " + e.zufaellig.toFixed(0) : "");
      s.addText(zeile2, {
        x: x0 + j * cw, y: y + 0.42, w: cw - 0.06, h: 0.3,
        fontSize: 9, color: MUTED, align: "center", fontFace: "Calibri", margin: 0,
      });
    });
  });

  s.addText("Der deutlichste Nutzen des Trainings: In der DMZ sinkt die Crown-Jewel-Quote gegenüber dem Zufallsagenten spürbar, in Hub & Spoke gegen den eigenen Angreifer in allen fünf Seeds.", {
    x: M, y: 5.3, w: W - 2 * M, h: 0.5,
    fontSize: 14, bold: true, color: DEF, fontFace: "Calibri", margin: 0,
  });
  fussnote(s, "Der Crown Jewel beendet die Episode nicht. Anteil über 25 Episoden je Zelle und alle fünf Seeds.");
  s.addNotes("Vorsicht bei dmz gegen dmz: Die Verbesserung von 97 auf 77 Prozent tragen nur zwei der fuenf Seeds.");
}

// =========================================================================
// Was die Verteidigung kostet
// =========================================================================
if (extra && extra.verteidiger) {
  const s = pres.addSlide();
  titelZeile(s, "Was die Verteidigung kostet",
    "Dieselben Episoden von der anderen Seite: große Zahl = trainiertes Modell, kleine = Zufallsagent");

  const v = extra.verteidiger;
  const spalten = [
    ["Reimages", "reimage", (x) => x.toFixed(1)],
    ["Dienststopps", "stop_svc", (x) => x.toFixed(0)],
    ["davon auf sauberem Knoten", "stop_svc_clean", (x) => x.toFixed(0)],
    ["Episoden mit SLA-Bruch", "sla_ep_pct", (x) => x.toFixed(1) + " %"],
    ["Verteidiger-Reward", "reward", (x) => x.toFixed(0)],
  ];

  const x0 = M + 1.75, y0 = 2.05, cw = 1.83, ch = 0.78;

  spalten.forEach((sp, j) => {
    s.addText(sp[0], {
      x: x0 + j * cw, y: y0 - 0.62, w: cw - 0.06, h: 0.56,
      fontSize: 11, bold: true, color: MUTED, align: "center", valign: "bottom",
      fontFace: "Calibri", margin: 0,
    });
  });

  DEFS.forEach((t, i) => {
    const y = y0 + i * ch;
    s.addText(KURZ[t], {
      x: M, y: y, w: 1.65, h: ch,
      fontSize: 13, bold: true, color: INK, align: "right", valign: "middle",
      fontFace: "Calibri", margin: 0,
    });
    spalten.forEach((sp, j) => {
      const e = v[t] || {};
      const tr = e.trainiert ? e.trainiert[sp[1]] : null;
      const zu = e.zufaellig ? e.zufaellig[sp[1]] : null;
      // Auffaellig einfaerben, wo sich beide Politiken stark unterscheiden
      let fuell = CARD;
      if (tr !== null && zu !== null && zu !== 0) {
        const faktor = Math.abs(zu) < 1e-9 ? 1 : Math.abs(tr / zu);
        if (faktor < 0.5 || faktor > 2) fuell = "E8F1F6";
      }
      s.addShape(pres.ShapeType.rect, {
        x: x0 + j * cw, y: y, w: cw - 0.06, h: ch - 0.06,
        fill: { color: fuell }, line: { color: "FFFFFF", width: 1.5 },
      });
      s.addText(tr === null ? "–" : sp[2](tr), {
        x: x0 + j * cw, y: y + 0.06, w: cw - 0.06, h: 0.38,
        fontSize: 16, bold: true, color: INK, align: "center",
        fontFace: "Cambria", margin: 0,
      });
      s.addText(zu === null ? "" : "Zufall " + sp[2](zu), {
        x: x0 + j * cw, y: y + 0.44, w: cw - 0.06, h: 0.26,
        fontSize: 10, color: MUTED, align: "center", fontFace: "Calibri", margin: 0,
      });
    });
  });

  s.addText("Beide setzen gleich oft Knoten neu auf. Daher stammt die Wirkung, und daher ist sie bei beiden gleich. Gelernt hat der Verteidiger etwas anderes: keine Dienste mehr grundlos zu stoppen. Das senkt seine eigenen Kosten um rund den Faktor zehn.", {
    x: M, y: 5.35, w: W - 2 * M, h: 0.55,
    fontSize: 14.5, bold: true, color: DEF, fontFace: "Calibri", margin: 0,
  });
  s.addText("Die SLA-Bruchrate ist dagegen in beiden Stufen nahezu identisch. Diese Brüche zu vermeiden hat der Verteidiger nicht gelernt.", {
    x: M, y: 5.9, w: W - 2 * M, h: 0.4,
    fontSize: 12, color: MUTED, fontFace: "Calibri", margin: 0,
  });
  fussnote(s, "Mediane über alle Episoden je Topologie, 25 Episoden je Zelle, alle fünf Seeds. Ein Dienststopp auf einem sauberen Knoten kostet -10.");
  s.addNotes("Antwort auf den Einwand, ein Zufallsagent sei gleichwertig: Auf der Angreiferseite ja, auf der eigenen Metrik keineswegs.");
}

{
  const s = pres.addSlide();
  s.background = { color: DARK };
  s.addText("Was die Matrix zeigt", {
    x: M, y: 0.75, w: W - 2 * M, h: 0.7,
    fontSize: 34, bold: true, color: "FFFFFF", fontFace: "Cambria", margin: 0,
  });

  const punkte = [
    ["Der Reward-Fehler hat die letzten Ergebnisse bestimmt",
      "Der Verteidiger konnte Reward farmen, indem er denselben Knoten wiederholt aufsetzte. Nach der Korrektur konvergieren 118 von 120 Läufen statt 65, und die Reward-Skala schrumpft von -31889 auf -216."],
    ["Die Konvergenz trennt die Topologien nicht mehr",
      "Nahezu jeder Lauf erreicht ein Plateau. Als Maß der Lerneffizienz taugt die Konvergenz damit nicht länger; der Unterschied muss aus dem Reward-Niveau und der Wirksamkeit kommen."],
    ["Die Angreiferherkunft zählt ebenso viel wie die Topologie",
      "Gegen den auf derselben Topologie trainierten Angreifer fällt der Reward auf -176 bis -216, gegen den neutralen Chain-Angreifer nur auf -44 bis -79."],
  ];
  punkte.forEach((p, i) => {
    const y = 1.75 + i * 1.45;
    s.addShape(pres.ShapeType.ellipse, {
      x: M, y: y + 0.04, w: 0.42, h: 0.42,
      fill: { color: GOLD }, line: { color: GOLD, width: 1 },
    });
    s.addText(String(i + 1), {
      x: M, y: y + 0.04, w: 0.42, h: 0.42,
      fontSize: 15, bold: true, color: DARK, align: "center", valign: "middle",
      fontFace: "Calibri", margin: 0,
    });
    s.addText(p[0], {
      x: M + 0.7, y: y, w: W - 2 * M - 0.7, h: 0.4,
      fontSize: 18, bold: true, color: "FFFFFF", fontFace: "Cambria", margin: 0,
    });
    s.addText(p[1], {
      x: M + 0.7, y: y + 0.42, w: W - 2 * M - 0.7, h: 0.75,
      fontSize: 13, color: "B8C0C9", fontFace: "Calibri", margin: 0,
    });
  });
  s.addText("Offen: Evaluation der Seeds 3 und 4 nachziehen · Wirksamkeit gegen Zufallsverteidiger auswerten · Kapitel 4 und 5 schreiben · Angreifer-Logs erfassen nur die letzten 100 Episoden", {
    x: M, y: H - 0.85, w: W - 2 * M, h: 0.4,
    fontSize: 11, color: MUTED, fontFace: "Calibri", italic: true, margin: 0,
  });
}

pres.writeFile({ fileName: OUT }).then(() => console.log("geschrieben: " + OUT));
