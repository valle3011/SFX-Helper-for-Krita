# -*- coding: utf-8 -*-
"""
SFX Helper – die eigentliche Docker-Klasse (UI + Logik).

Sprache: Standard Englisch, umschaltbar auf Deutsch (oben im Docker).
Komfort: Live-Vorschau, GROSSBUCHSTABEN-Schalter, merkt sich den zuletzt
genutzten Stil über Neustarts.
"""
import json
import re

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit,
    QComboBox, QPushButton, QSpinBox, QSlider, QColorDialog, QScrollArea,
    QCompleter, QInputDialog, QMessageBox, QMenu, QCheckBox,
    QDialog, QDialogButtonBox, QFileDialog, QSizePolicy,
)
from PyQt5.QtGui import (
    QColor, QFontDatabase, QFont, QFontMetricsF, QPainter, QPainterPath,
    QBrush, QPen,
)
from PyQt5.QtCore import Qt

from krita import Krita, DockWidget

from .config import (
    SFX_FONTS, SFX_PRESETS, SFX_RULES, DEFAULTS, SHOW_ALL_SYSTEM_FONTS,
)
from .svg_builder import build_sfx_svg
from .presets_store import (
    load_user_presets, save_user_presets, load_font_rules, save_font_rules,
    load_language, save_language, load_settings, save_settings,
    load_view, save_view, load_usage, save_usage,
    load_rule_lang, save_rule_lang,
)

# Sprachen, für die SFX-Regeln gewählt werden können (Endonyme fürs Dropdown).
RULE_LANGS = ("en", "de", "es", "fr", "pt", "it")
RULE_LANG_NAMES = {
    "en": "English", "de": "Deutsch", "es": "Español",
    "fr": "Français", "pt": "Português", "it": "Italiano",
}
from .i18n import tr, LANGUAGES


# Gedehnte SFX-Schreibweisen normalisieren, damit "BOOOOM", "BOOM" und
# "GASHAAAN" alle gleich behandelt werden.
_RUN_RE = re.compile(r"(.)\1+")          # jede Wiederholung eines Zeichens


def normalize_sfx(text):
    """Vereinheitlicht ein SFX-Wort fürs Stichwort-Matching:
    klein schreiben, jeden Lauf gleicher Zeichen auf EIN Zeichen stauchen
    ("booooom"->"bom", "gashaaan"->"gashan"), und alles außer Buchstaben/
    Ziffern entfernen ("ka-boom!"->"kabom"). Stichwort und Text werden gleich
    behandelt, daher matchen unterschiedlich gedehnte Schreibweisen sicher.

    Ausnahme: Ein Wort aus nur EINEM wiederholten Zeichen (z. B. "zzz") würde
    sonst auf ein einziges Zeichen schrumpfen und ignoriert werden; daher
    behalten wir dort zwei Zeichen ("zzz"/"zzzz" -> "zz")."""
    raw = re.sub(r"[^a-z0-9]+", "", (text or "").lower())
    s = _RUN_RE.sub(r"\1", raw)
    if len(s) == 1 and len(raw) >= 2:
        s = s * 2
    return s


def keyword_matches(keyword, text_norm):
    """True, wenn das gestauchte Stichwort zum gestauchten Text passt.

    - 1 Zeichen Rest  -> ignorieren (zu breit).
    - 2 Zeichen Rest  -> EXAKT (so matchen "ow"/"gr"/"ah" nur als ganzes Wort,
      nicht versteckt in "pow"/"grab"/"haha").
    - 3+ Zeichen      -> Teilstring (so matchen auch verdoppelte/gedehnte
      Formen wie "boom-boom" -> "bombom" über "boom" -> "bom")."""
    kw = normalize_sfx(keyword)
    if len(kw) < 2:
        return False
    if len(kw) == 2:
        return text_norm == kw
    return kw in text_norm


# ---------------------------------------------------------------------------
# Lautmuster-Heuristik
#
# Ordnet ein UNBEKANNTES SFX (für das keine Regel direkt matcht) anhand seines
# Klangbilds einer der vorhandenen Gruppen zu. Bewusst grob – nur als Fallback,
# damit auch erfundene SFX ("DKKBAM", "fwooosh") einen Vorschlag bekommen.
# ---------------------------------------------------------------------------

_SFX_HARD = set("bdgkpqt")          # harte Plosive  -> Aufprall/Knall
_SFX_SIB = set("fsz")               # Zischlaute     -> Wisch/Energie
_SFX_NASAL = set("mn")
_SFX_LIQUID = set("lr")
_END_VOWEL_RE = re.compile(r"([aeiouy])\1{2,}$")   # 3+ gleiche End-Vokale


def classify_sfx(word, available=None):
    """Grobe Stimmungs-Schätzung für ein unbekanntes SFX anhand von Lautmustern.

    Gibt bis zu zwei Gruppennamen zurück (nur solche, die in `available`
    enthalten sind, falls angegeben). Greift im Docker nur, wenn keine echte
    Regel matcht."""
    raw = (word or "").strip()
    letters = [c for c in raw.lower() if c.isalpha()]
    if len(letters) < 2:
        return []
    s = "".join(letters)
    n = len(s)
    hard = sum(1 for c in s if c in _SFX_HARD)
    sib = sum(1 for c in s if c in _SFX_SIB) + s.count("sh") + s.count("wh")
    nasal = sum(1 for c in s if c in _SFX_NASAL)
    liquid = sum(1 for c in s if c in _SFX_LIQUID)
    z = s.count("z")
    g = s.count("g")
    r = s.count("r")
    caps = raw.isupper() and n >= 2
    bang = "!" in raw
    only_z = set(s) <= {"z"}
    end_vowel_run = bool(_END_VOWEL_RE.search(s))

    score = {}

    def add(group, pts):
        if pts > 0:
            score[group] = score.get(group, 0) + pts

    if only_z:                                  # "zzz" -> Schlaf
        add("Breath / Sleep", 5)
    elif z:                                     # sonst Strom/Energie
        add("Electric / Spark", 2 + z)
    if hard >= 2:
        add("Boom / Explosion", hard + (1 if caps else 0) + (1 if bang else 0))
    if hard >= 1 and n <= 5:
        add("Hit / Punch", hard + (1 if caps else 0))
    if sib >= 1 and ("w" in s or "f" in s or s.count("sh")):
        add("Whoosh / Dash", sib + 1)
    if end_vowel_run:
        add("Scream / Shout", 3 + (1 if caps else 0) + (1 if bang else 0))
    if g >= 1 and r >= 1:
        add("Roar / Growl", g + r + 1)
    if (s.count("sp") or s.count("dr") or s.count("pl") or s.count("bl")
            or s.count("gl")):
        add("Water / Liquid", 2)
    if (nasal + liquid) >= 2 and hard == 0 and not caps and not bang:
        add("Whisper / Silence", nasal + liquid)
    if bang and not score:
        add("Scream / Shout", 2)

    if not score:
        return []
    ordered = sorted(score.items(), key=lambda kv: kv[1], reverse=True)
    if available is not None:
        ordered = [(grp, pts) for grp, pts in ordered if grp in available]
    if not ordered:
        return []
    top = ordered[0][1]
    return [grp for grp, pts in ordered if pts >= max(2, top * 0.6)][:2]


class SFXPreview(QWidget):
    """WYSIWYG-Vorschau des SFX-Texts.

    Zeichnet den Text per QPainterPath in der Reihenfolge
    Schatten -> Kontur -> Füllung (wie die eingefügte Ebene), eingepasst in die
    Vorschaufläche. Kontur- und Schattenstärke bleiben proportional zur
    eingestellten Größe, damit die Wirkung dem späteren Ergebnis entspricht."""

    _MARGIN = 8

    def __init__(self):
        super().__init__()
        self._opts = None
        self.setMinimumHeight(56)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def set_data(self, opts):
        """opts: dict mit text, family, size_ref, bold, italic, fill (QColor),
        outline (bool), outline_color (QColor), outline_px (float),
        shadow (bool), shadow_color (QColor), shadow_dx, shadow_dy."""
        self._opts = opts
        self.update()

    def _fit_size(self, o, text, avail_w, avail_h):
        """Größte ganzzahlige Pixelgröße, bei der der Text in die Fläche passt."""
        lo, hi, best = 6, 240, 6
        while lo <= hi:
            mid = (lo + hi) // 2
            fn = self._font(o, mid)
            fm = QFontMetricsF(fn)
            if fm.horizontalAdvance(text) <= avail_w and fm.height() <= avail_h:
                best = mid
                lo = mid + 1
            else:
                hi = mid - 1
        return best

    def _font(self, o, px):
        fn = QFont(o["family"]) if o["family"] else QFont()
        fn.setItalic(bool(o.get("italic")))
        fn.setBold(bool(o.get("bold")))
        fn.setPixelSize(max(1, int(px)))
        return fn

    def paintEvent(self, _ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setRenderHint(QPainter.TextAntialiasing, True)
        w, h = self.width(), self.height()
        self._paint_background(p, w, h)
        p.setPen(QPen(QColor(0, 0, 0, 60), 1))
        p.setBrush(Qt.NoBrush)
        p.drawRect(0, 0, w - 1, h - 1)

        o = self._opts
        text = (o or {}).get("text", "").strip() if o else ""
        if not o or not text:
            p.setPen(QColor(0, 0, 0, 110))
            f = QFont()
            f.setItalic(True)
            f.setPixelSize(13)
            p.setFont(f)
            p.drawText(self.rect(), Qt.AlignCenter, "Aa")
            p.end()
            return

        m = self._MARGIN
        avail_w = max(10, w - 2 * m)
        avail_h = max(10, h - 2 * m)
        fs = self._fit_size(o, text, avail_w, avail_h)
        fn = self._font(o, fs)
        fm = QFontMetricsF(fn)
        adv = fm.horizontalAdvance(text)
        # waagerecht + senkrecht zentrieren
        x = m + (avail_w - adv) / 2.0
        baseline = m + (avail_h - fm.height()) / 2.0 + fm.ascent()

        path = QPainterPath()
        path.addText(x, baseline, fn, text)

        size_ref = max(1, int(o.get("size_ref", fs)))
        scale = fs / float(size_ref)

        if o.get("shadow") and (o.get("shadow_dx") or o.get("shadow_dy")):
            sp = QPainterPath(path)
            sp.translate(o["shadow_dx"] * scale, o["shadow_dy"] * scale)
            p.fillPath(sp, QBrush(o["shadow_color"]))
        if o.get("outline") and o.get("outline_px", 0) > 0:
            pen = QPen(o["outline_color"])
            pen.setWidthF(max(0.5, 2.0 * o["outline_px"] * scale))
            pen.setJoinStyle(Qt.RoundJoin)
            pen.setCapStyle(Qt.RoundCap)
            p.strokePath(path, pen)
        p.fillPath(path, QBrush(o["fill"]))
        p.end()

    def _paint_background(self, p, w, h):
        """Hellgraues Schachbrett – zeigt helle wie dunkle Textfarben gut."""
        p.fillRect(0, 0, w, h, QColor(0x9A, 0x9A, 0x9A))
        tile = 8
        p.setPen(Qt.NoPen)
        c = QColor(0x88, 0x88, 0x88)
        y = 0
        row = 0
        while y < h:
            x = (row % 2) * tile
            while x < w:
                p.fillRect(x, y, tile, tile, c)
                x += 2 * tile
            y += tile
            row += 1


class MangaSFXDocker(DockWidget):
    """Dockbares Panel zum schnellen Setzen von Manga-SFX (Anzeigename: SFX Helper)."""

    # Standardwerte für das Layout-Panel (Größen + ein-/ausblenden)
    _VIEW_DEFAULTS = {
        "open": False,
        "preview_show": True, "preview_h": 56,
        "suggest_show": True,
        "presets_show": True,
        "rules_show": True,
    }

    def __init__(self):
        super().__init__()
        self._lang = load_language("en")          # Standard: Englisch
        self._user_presets = load_user_presets()  # eigene Presets (persistiert)
        self._font_rules = load_font_rules()      # Stichwort -> Font(s) (persistiert)
        self._pending_state = load_settings()     # zuletzt genutzter Stil
        self._view = self._load_view_merged()     # Layout-/Anzeige-Einstellungen
        self._families_cache = None               # System-Fonts nur einmal laden
        self._usage = load_usage()                # gelernte Wort->Font-Häufigkeit
        self._group_fonts_cache = None            # Gruppenname -> Fonts (gefiltert)
        self._rule_lang = self._load_rule_lang_merged()  # aktive Regelsprache
        self.setWindowTitle(self.t("window_title"))
        self._build_ui()

    def _load_rule_lang_merged(self):
        """Gespeicherte Regelsprache; sonst die UI-Sprache (falls Regeln dafür
        denkbar sind), sonst Englisch."""
        saved = load_rule_lang(default="")
        if saved in RULE_LANGS:
            return saved
        return self._lang if self._lang in RULE_LANGS else "en"

    def _families(self):
        """Liste aller System-Font-Familien – nur EINMAL ermitteln und cachen.
        (Bei zehntausenden Fonts wäre das wiederholte Laden sonst spürbar
        langsam – es passiert bei jedem Sprachwechsel und in jedem Regel-Dialog.)"""
        if self._families_cache is None:
            self._families_cache = list(QFontDatabase().families())
        return self._families_cache

    def _load_view_merged(self):
        """Gespeicherte View-Einstellungen mit den Standards auffüllen."""
        v = dict(self._VIEW_DEFAULTS)
        saved = load_view()
        if isinstance(saved, dict):
            v.update({k: saved[k] for k in saved if k in v})
        return v

    # ------------------------------------------------------------------
    # Pflicht-Override der DockWidget-API (wird hier nicht gebraucht)
    # ------------------------------------------------------------------
    def canvasChanged(self, canvas):
        pass

    # ------------------------------------------------------------------
    # Übersetzungs-Kurzform
    # ------------------------------------------------------------------
    def t(self, key, **kw):
        return tr(self._lang, key, **kw)

    # ==================================================================
    #  UI-Aufbau (wird bei Sprachwechsel komplett neu aufgebaut)
    # ==================================================================
    def _build_ui(self):
        root = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        root.setLayout(layout)

        # --- Sprachauswahl --------------------------------------------
        lang_row = QHBoxLayout()
        lang_row.addWidget(QLabel(self.t("lang_label") + ":"))
        self.lang_combo = QComboBox()
        for code, label in LANGUAGES:
            self.lang_combo.addItem(label, code)
        li = self.lang_combo.findData(self._lang)
        self.lang_combo.setCurrentIndex(li if li >= 0 else 0)
        # erst nach dem Setzen verbinden, sonst feuert es beim Aufbau
        self.lang_combo.currentIndexChanged.connect(self._on_lang_changed)
        lang_row.addWidget(self.lang_combo, 1)
        layout.addLayout(lang_row)

        # --- einklappbares "Layout & Größen"-Panel --------------------
        # Lässt den Nutzer Teile des Dockers vergrößern/verkleinern oder ganz
        # ausblenden; die Wahl wird über Neustarts gemerkt.
        self.view_toggle = QPushButton(self.t("view_toggle"))
        self.view_toggle.setCheckable(True)
        self.view_toggle.setChecked(bool(self._view["open"]))
        self.view_toggle.toggled.connect(self._on_view_toggle)
        layout.addWidget(self.view_toggle)

        self.view_box = QWidget()
        vlay = QVBoxLayout()
        vlay.setContentsMargins(6, 2, 6, 2)
        vlay.setSpacing(4)
        self.view_box.setLayout(vlay)
        hint = QLabel(self.t("view_hint"))
        hint.setWordWrap(True)
        hint.setStyleSheet("color: gray;")
        vlay.addWidget(hint)

        vgrid = QGridLayout()
        vgrid.setHorizontalSpacing(8)
        self.v_preview_chk = QCheckBox(self.t("view_preview"))
        self.v_preview_chk.setChecked(bool(self._view["preview_show"]))
        self.v_preview_h = QSpinBox()
        self.v_preview_h.setRange(28, 600)
        self.v_preview_h.setSingleStep(8)
        self.v_preview_h.setSuffix(" px")
        self.v_preview_h.setValue(int(self._view["preview_h"]))
        vgrid.addWidget(self.v_preview_chk, 0, 0)
        vgrid.addWidget(self.v_preview_h, 0, 1)
        self.v_suggest_chk = QCheckBox(self.t("view_suggest"))
        self.v_suggest_chk.setChecked(bool(self._view["suggest_show"]))
        vgrid.addWidget(self.v_suggest_chk, 1, 0)
        self.v_presets_chk = QCheckBox(self.t("view_presets"))
        self.v_presets_chk.setChecked(bool(self._view["presets_show"]))
        vgrid.addWidget(self.v_presets_chk, 2, 0)
        self.v_rules_chk = QCheckBox(self.t("view_rules"))
        self.v_rules_chk.setChecked(bool(self._view["rules_show"]))
        vgrid.addWidget(self.v_rules_chk, 3, 0)
        vgrid.setColumnStretch(0, 1)
        vlay.addLayout(vgrid)

        self.view_reset_btn = QPushButton(self.t("view_reset"))
        self.view_reset_btn.clicked.connect(self._on_view_reset)
        vlay.addWidget(self.view_reset_btn)
        layout.addWidget(self.view_box)
        self.view_box.setVisible(self.view_toggle.isChecked())

        # nach dem Setzen der Startwerte verbinden (sonst feuert es beim Aufbau)
        for _w in (self.v_preview_chk, self.v_suggest_chk,
                   self.v_presets_chk, self.v_rules_chk):
            _w.toggled.connect(self._on_view_changed)
        self.v_preview_h.valueChanged.connect(self._on_view_changed)

        # --- 1) Texteingabe -------------------------------------------
        layout.addWidget(self._heading(self.t("sfx_text")))
        self.text_input = QLineEdit()
        self.text_input.setPlaceholderText(self.t("sfx_placeholder"))
        self.text_input.returnPressed.connect(self._insert_sfx)  # Enter = einfügen
        layout.addWidget(self.text_input)

        # Schalter: GROSSBUCHSTABEN / Fett / Kursiv (2-spaltig, damit nichts
        # bei schmalem Docker abgeschnitten wird)
        opt_grid = QGridLayout()
        self.upper_chk = QCheckBox(self.t("uppercase"))
        self.upper_chk.setChecked(True)
        self.upper_chk.toggled.connect(self._on_upper_toggled)
        self.bold_chk = QCheckBox(self.t("bold"))
        self.bold_chk.toggled.connect(lambda _c: self._update_preview())
        self.italic_chk = QCheckBox(self.t("italic"))
        self.italic_chk.toggled.connect(lambda _c: self._update_preview())
        opt_grid.addWidget(self.upper_chk, 0, 0)
        opt_grid.addWidget(self.bold_chk, 0, 1)
        opt_grid.addWidget(self.italic_chk, 1, 0)
        opt_grid.setColumnStretch(2, 1)
        layout.addLayout(opt_grid)

        # --- Live-Vorschau (WYSIWYG, ein-/ausblendbar) ----------------
        self.sec_preview = QWidget()
        pv = QVBoxLayout()
        pv.setContentsMargins(0, 0, 0, 0)
        self.sec_preview.setLayout(pv)
        pv.addWidget(self._heading(self.t("preview")))
        self.preview = SFXPreview()
        pv.addWidget(self.preview)
        layout.addWidget(self.sec_preview)

        # --- Live-Vorschläge zum aktuellen SFX-Wort (ein-/ausblendbar) -
        self.sec_suggest = QWidget()
        sv = QVBoxLayout()
        sv.setContentsMargins(0, 0, 0, 0)
        self.sec_suggest.setLayout(sv)
        self.suggest_box = QVBoxLayout()
        self.suggest_box.setSpacing(3)
        sv.addLayout(self.suggest_box)
        layout.addWidget(self.sec_suggest)
        # textChanged erst jetzt verbinden – suggest_box/preview müssen existieren
        self.text_input.textChanged.connect(self._on_text_changed)

        # --- 2) Font (Favoriten + alle System-Fonts, durchsuchbar) ----
        layout.addWidget(self._heading(self.t("font")))
        self.font_combo = self._build_font_combo()
        self.font_combo.currentTextChanged.connect(lambda _t: self._update_preview())
        layout.addWidget(self.font_combo)

        # --- 3) Schriftgröße ------------------------------------------
        self.size_slider, self.size_spin = self._slider_spin_row(
            layout, self.t("font_size"), 10, 600, DEFAULTS["size"])
        self.size_spin.valueChanged.connect(lambda _v: self._update_preview())

        # --- Füllfarbe ------------------------------------------------
        layout.addWidget(self._heading(self.t("fill_color")))
        self.fill_btn = QPushButton()
        self.fill_btn.setFixedHeight(26)
        self._set_btn_color(self.fill_btn, QColor(DEFAULTS["fill"]))
        self.fill_btn.clicked.connect(lambda: self._pick_color(self.fill_btn))
        layout.addWidget(self.fill_btn)

        # --- Outline-Farbe --------------------------------------------
        layout.addWidget(self._heading(self.t("outline_color")))
        self.outline_btn = QPushButton()
        self.outline_btn.setFixedHeight(26)
        self._set_btn_color(self.outline_btn, QColor(DEFAULTS["outline"]))
        self.outline_btn.clicked.connect(lambda: self._pick_color(self.outline_btn))
        layout.addWidget(self.outline_btn)

        # --- Outline-Stärke -------------------------------------------
        self.out_slider, self.out_spin = self._slider_spin_row(
            layout, self.t("outline_width"), 0, 60, DEFAULTS["outline_px"])
        self.out_spin.valueChanged.connect(lambda _v: self._update_preview())

        # --- Schatten (optional) --------------------------------------
        self.shadow_chk = QCheckBox(self.t("shadow"))
        self.shadow_chk.setChecked(bool(DEFAULTS.get("shadow", False)))
        self.shadow_chk.toggled.connect(self._on_shadow_toggled)
        layout.addWidget(self.shadow_chk)
        self.shadow_btn = QPushButton(self.t("shadow_color"))
        self.shadow_btn.setFixedHeight(26)
        self._set_btn_color(self.shadow_btn,
                            QColor(DEFAULTS.get("shadow_color", "#000000")))
        self.shadow_btn.clicked.connect(lambda: self._pick_color(self.shadow_btn))
        layout.addWidget(self.shadow_btn)
        layout.addWidget(QLabel(self.t("shadow_offset")))
        sh_row = QHBoxLayout()
        self.shadow_dx = QSpinBox()
        self.shadow_dx.setRange(-100, 100)
        self.shadow_dx.setValue(int(DEFAULTS.get("shadow_dx", 6)))
        self.shadow_dx.valueChanged.connect(lambda _v: self._update_preview())
        self.shadow_dy = QSpinBox()
        self.shadow_dy.setRange(-100, 100)
        self.shadow_dy.setValue(int(DEFAULTS.get("shadow_dy", 6)))
        self.shadow_dy.valueChanged.connect(lambda _v: self._update_preview())
        sh_row.addWidget(self.shadow_dx)
        sh_row.addWidget(self.shadow_dy)
        sh_row.addStretch(1)
        layout.addLayout(sh_row)
        self._update_shadow_enabled()

        # --- 4) Presets (integriert + selbst angelegte; ein-/ausblendbar) -
        self.sec_presets = QWidget()
        prv = QVBoxLayout()
        prv.setContentsMargins(0, 0, 0, 0)
        self.sec_presets.setLayout(prv)
        prv.addWidget(self._heading(self.t("presets")))
        self.preset_box = QVBoxLayout()
        prv.addLayout(self.preset_box)
        self.save_preset_btn = QPushButton(self.t("save_preset_btn"))
        self.save_preset_btn.setToolTip(self.t("save_preset_tip"))
        self.save_preset_btn.clicked.connect(self._save_current_as_preset)
        prv.addWidget(self.save_preset_btn)
        layout.addWidget(self.sec_presets)
        self._rebuild_presets()

        # --- 4b) Font-Vorschläge verwalten (ein-/ausblendbar) ---------
        self.sec_rules = QWidget()
        rlv = QVBoxLayout()
        rlv.setContentsMargins(0, 0, 0, 0)
        self.sec_rules.setLayout(rlv)
        rlv.addWidget(self._heading(self.t("font_suggestions")))
        # Regelsprache: nur Regeln dieser Sprache (+ "*") werden gezeigt/aktiv.
        rl_row = QHBoxLayout()
        self.lbl_rule_lang = QLabel(self.t("rule_lang"))
        rl_row.addWidget(self.lbl_rule_lang)
        self.rule_lang_combo = QComboBox()
        for code in RULE_LANGS:
            self.rule_lang_combo.addItem(RULE_LANG_NAMES.get(code, code), code)
        ri = self.rule_lang_combo.findData(self._rule_lang)
        self.rule_lang_combo.setCurrentIndex(ri if ri >= 0 else 0)
        self.rule_lang_combo.currentIndexChanged.connect(self._on_rule_lang_changed)
        self._make_shrinkable(self.rule_lang_combo)
        rl_row.addWidget(self.rule_lang_combo, 1)
        rlv.addLayout(rl_row)
        rules_hint = QLabel(self.t("rules_hint"))
        rules_hint.setWordWrap(True)
        rlv.addWidget(rules_hint)
        self.rules_box = QVBoxLayout()
        self.rules_box.setSpacing(3)
        rlv.addLayout(self.rules_box)
        self.add_rule_btn = QPushButton(self.t("add_rule_btn"))
        self.add_rule_btn.setToolTip(self.t("add_rule_tip"))
        self.add_rule_btn.clicked.connect(self._add_font_rule)
        rlv.addWidget(self.add_rule_btn)
        layout.addWidget(self.sec_rules)
        self._rebuild_rules()

        # --- 5) Einfügen ----------------------------------------------
        self.insert_btn = QPushButton(self.t("insert_btn"))
        self.insert_btn.setMinimumHeight(34)
        self.insert_btn.clicked.connect(self._insert_sfx)
        layout.addWidget(self.insert_btn)

        # --- Status / Hinweise ----------------------------------------
        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        # --- Import / Export (eigene Presets + Font-Regeln) -----------
        io_row = QHBoxLayout()
        self.import_btn = QPushButton(self.t("import_btn"))
        self.import_btn.clicked.connect(self._import_data)
        self.export_btn = QPushButton(self.t("export_btn"))
        self.export_btn.clicked.connect(self._export_data)
        io_row.addWidget(self.import_btn)
        io_row.addWidget(self.export_btn)
        layout.addLayout(io_row)

        # --- Zurücksetzen ---------------------------------------------
        self.reset_btn = QPushButton(self.t("reset_btn"))
        self.reset_btn.setToolTip(self.t("reset_tip"))
        self.reset_btn.clicked.connect(self._reset)
        layout.addWidget(self.reset_btn)

        layout.addStretch(1)

        # In ScrollArea verpacken; alte (bei Sprachwechsel) sauber entsorgen
        old = self.widget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(root)
        self.setWidget(scroll)
        if old is not None:
            old.setParent(None)
            old.deleteLater()

        # zuletzt genutzten / vor dem Sprachwechsel gemerkten Stil anwenden
        self._apply_state(self._pending_state)
        self._apply_view()
        self._update_preview()

    # ==================================================================
    #  Layout / Anzeige (Größen + ein-/ausblenden)
    # ==================================================================
    def _apply_view(self):
        """Sichtbarkeit + Vorschauhöhe gemäß den View-Einstellungen setzen."""
        self.sec_preview.setVisible(self.v_preview_chk.isChecked())
        h = self.v_preview_h.value()
        self.preview.setMinimumHeight(h)
        self.preview.setMaximumHeight(h)
        self.v_preview_h.setEnabled(self.v_preview_chk.isChecked())
        self.sec_suggest.setVisible(self.v_suggest_chk.isChecked())
        self.sec_presets.setVisible(self.v_presets_chk.isChecked())
        self.sec_rules.setVisible(self.v_rules_chk.isChecked())

    def _capture_view(self):
        return {
            "open": self.view_toggle.isChecked(),
            "preview_show": self.v_preview_chk.isChecked(),
            "preview_h": self.v_preview_h.value(),
            "suggest_show": self.v_suggest_chk.isChecked(),
            "presets_show": self.v_presets_chk.isChecked(),
            "rules_show": self.v_rules_chk.isChecked(),
        }

    def _on_view_changed(self, *_a):
        self._view = self._capture_view()
        save_view(self._view)
        self._apply_view()

    def _on_view_toggle(self, checked):
        self.view_box.setVisible(checked)
        self._view = self._capture_view()
        save_view(self._view)

    def _on_view_reset(self):
        self._view = dict(self._VIEW_DEFAULTS)
        self._view["open"] = self.view_toggle.isChecked()  # Panel offen lassen
        save_view(self._view)
        widgets = (self.v_preview_chk, self.v_suggest_chk, self.v_presets_chk,
                   self.v_rules_chk, self.v_preview_h)
        for w in widgets:
            w.blockSignals(True)
        self.v_preview_chk.setChecked(self._view["preview_show"])
        self.v_preview_h.setValue(self._view["preview_h"])
        self.v_suggest_chk.setChecked(self._view["suggest_show"])
        self.v_presets_chk.setChecked(self._view["presets_show"])
        self.v_rules_chk.setChecked(self._view["rules_show"])
        for w in widgets:
            w.blockSignals(False)
        self._apply_view()

    # ==================================================================
    #  Sprache
    # ==================================================================
    def _on_lang_changed(self, _idx):
        code = self.lang_combo.currentData()
        if code and code != self._lang:
            self._set_language(code)

    def _set_language(self, lang):
        self._pending_state = self._capture_state()   # Eingaben nicht verlieren
        self._lang = lang
        save_language(lang)
        self.setWindowTitle(self.t("window_title"))
        self._build_ui()                               # komplett neu in neuer Sprache

    # ==================================================================
    #  kleine UI-Helfer
    # ==================================================================
    def _heading(self, text):
        lbl = QLabel(text)
        f = lbl.font()
        f.setBold(True)
        lbl.setFont(f)
        return lbl

    @staticmethod
    def _elide(text, limit=34):
        """Lange Texte für Buttons kürzen (voller Text bleibt im Tooltip)."""
        text = text or ""
        return text if len(text) <= limit else text[:limit - 1].rstrip() + "…"

    @staticmethod
    def _make_shrinkable(widget):
        """Damit sich der Docker schmal ziehen lässt: das Widget darf horizontal
        beliebig schrumpfen und erzwingt keine große Mindestbreite mehr."""
        sp = widget.sizePolicy()
        sp.setHorizontalPolicy(QSizePolicy.Ignored)
        widget.setSizePolicy(sp)
        widget.setMinimumWidth(0)
        return widget

    def _slider_spin_row(self, parent_layout, title, lo, hi, value):
        """Erzeugt 'Überschrift + Slider + SpinBox' und synchronisiert beide."""
        parent_layout.addWidget(self._heading(title))
        row = QHBoxLayout()
        slider = QSlider(Qt.Horizontal)
        slider.setRange(lo, hi)
        slider.setValue(value)
        spin = QSpinBox()
        spin.setRange(lo, hi)
        spin.setValue(value)
        slider.valueChanged.connect(spin.setValue)
        spin.valueChanged.connect(slider.setValue)
        row.addWidget(slider, 1)
        row.addWidget(spin, 0)
        parent_layout.addLayout(row)
        return slider, spin

    def _set_btn_color(self, btn, qcolor):
        """Färbt einen Button als Farb-Swatch und schreibt den Hexcode drauf."""
        btn._color = qcolor
        txt = "#000000" if qcolor.lightness() > 128 else "#ffffff"
        btn.setText(qcolor.name())
        btn.setStyleSheet(
            f"background-color: {qcolor.name()}; color: {txt};"
            f" border: 1px solid #555; padding: 3px;")

    def _pick_color(self, btn):
        c = QColorDialog.getColor(btn._color, self.widget(), self.t("choose_color"))
        if c.isValid():
            self._set_btn_color(btn, c)
            self._update_preview()

    # --- Vorschau / Großbuchstaben ------------------------------------
    def _effective_text(self):
        """Der Text, der wirklich eingefügt wird (ggf. in Großbuchstaben)."""
        txt = self.text_input.text().strip()
        if getattr(self, "upper_chk", None) and self.upper_chk.isChecked():
            txt = txt.upper()
        return txt

    def _on_upper_toggled(self, _checked):
        self._update_preview()

    def _on_shadow_toggled(self, _checked):
        self._update_shadow_enabled()
        self._update_preview()

    def _update_shadow_enabled(self):
        """Schattenfarbe + Versatz nur bei aktivem Schatten bedienbar."""
        on = self.shadow_chk.isChecked()
        self.shadow_btn.setEnabled(on)
        self.shadow_dx.setEnabled(on)
        self.shadow_dy.setEnabled(on)

    def _update_preview(self):
        """WYSIWYG-Vorschau mit Font/Größe/Farben/Outline/Schatten neu zeichnen."""
        needed = ("preview", "font_combo", "size_spin", "fill_btn",
                  "outline_btn", "out_spin", "shadow_chk", "shadow_btn",
                  "shadow_dx", "shadow_dy", "bold_chk", "italic_chk")
        if not all(hasattr(self, a) for a in needed):
            return
        self.preview.set_data({
            "text": self._effective_text(),
            "family": self.font_combo.currentText(),
            "size_ref": max(1, self.size_spin.value()),
            "bold": self.bold_chk.isChecked(),
            "italic": self.italic_chk.isChecked(),
            "fill": QColor(self.fill_btn._color),
            "outline": self.out_spin.value() > 0,
            "outline_color": QColor(self.outline_btn._color),
            "outline_px": float(self.out_spin.value()),
            "shadow": self.shadow_chk.isChecked(),
            "shadow_color": QColor(self.shadow_btn._color),
            "shadow_dx": float(self.shadow_dx.value()),
            "shadow_dy": float(self.shadow_dy.value()),
        })

    # --- Stand sichern / wiederherstellen -----------------------------
    def _capture_state(self):
        return {
            "text": self.text_input.text(),
            "font": self.font_combo.currentText(),
            "size": self.size_spin.value(),
            "fill": self.fill_btn._color.name(),
            "outline": self.outline_btn._color.name(),
            "outline_px": self.out_spin.value(),
            "uppercase": self.upper_chk.isChecked(),
            "bold": self.bold_chk.isChecked(),
            "italic": self.italic_chk.isChecked(),
            "shadow": self.shadow_chk.isChecked(),
            "shadow_color": self.shadow_btn._color.name(),
            "shadow_dx": self.shadow_dx.value(),
            "shadow_dy": self.shadow_dy.value(),
        }

    def _apply_state(self, st):
        if not st:
            return
        if st.get("text"):
            self.text_input.setText(st["text"])
        if st.get("font"):
            self._select_font(st["font"])
        for key, spin in (("size", self.size_spin), ("outline_px", self.out_spin),
                          ("shadow_dx", self.shadow_dx),
                          ("shadow_dy", self.shadow_dy)):
            if key in st:
                try:
                    spin.setValue(int(st[key]))
                except (TypeError, ValueError):
                    pass
        if st.get("fill"):
            self._set_btn_color(self.fill_btn, QColor(st["fill"]))
        if st.get("outline"):
            self._set_btn_color(self.outline_btn, QColor(st["outline"]))
        if st.get("shadow_color"):
            self._set_btn_color(self.shadow_btn, QColor(st["shadow_color"]))
        if "uppercase" in st:
            self.upper_chk.setChecked(bool(st["uppercase"]))
        if "bold" in st:
            self.bold_chk.setChecked(bool(st["bold"]))
        if "italic" in st:
            self.italic_chk.setChecked(bool(st["italic"]))
        if "shadow" in st:
            self.shadow_chk.setChecked(bool(st["shadow"]))
        self._update_shadow_enabled()

    def _preset_tooltip(self, p):
        lines = [
            self.t("tip_font", v=p["font"]),
            self.t("tip_size", v=p["size"]),
            self.t("tip_fill", v=p["fill"]),
            self.t("tip_outline", c=p["outline"], w=p["outline_px"]),
        ]
        kws = p.get("keywords") or []
        if kws:
            lines.append(self.t("tip_keywords", v=", ".join(kws)))
        lines.append(self.t("tip_user_preset") if p.get("user")
                     else self.t("tip_builtin"))
        return "\n".join(lines)

    # ==================================================================
    #  Presets
    # ==================================================================
    def _apply_preset(self, preset):
        self._select_font(preset["font"])
        self.size_spin.setValue(preset["size"])
        self.out_spin.setValue(preset["outline_px"])
        self._set_btn_color(self.fill_btn, QColor(preset["fill"]))
        self._set_btn_color(self.outline_btn, QColor(preset["outline"]))
        self.bold_chk.setChecked(bool(preset.get("bold", False)))
        self.italic_chk.setChecked(bool(preset.get("italic", False)))
        # Schatten (in alten Presets nicht vorhanden -> Standard aus)
        self.shadow_chk.setChecked(bool(preset.get("shadow", False)))
        if preset.get("shadow_color"):
            self._set_btn_color(self.shadow_btn, QColor(preset["shadow_color"]))
        self.shadow_dx.setValue(int(preset.get("shadow_dx",
                                               DEFAULTS.get("shadow_dx", 6))))
        self.shadow_dy.setValue(int(preset.get("shadow_dy",
                                               DEFAULTS.get("shadow_dy", 6))))
        self._update_shadow_enabled()
        self._update_preview()
        self.status_label.setText(self.t("st_preset_loaded", name=preset["name"]))

    def _all_presets(self):
        """Integrierte Presets (aus config.py) + eigene (persistiert)."""
        builtin = [dict(p, user=False) for p in SFX_PRESETS]
        return builtin + self._user_presets

    def _rebuild_presets(self):
        """Baut die Preset-Buttons neu auf (nach Anlegen/Löschen aufrufen)."""
        self._clear_layout(self.preset_box)
        grid = QGridLayout()
        grid.setSpacing(4)
        for i, preset in enumerate(self._all_presets()):
            btn = QPushButton(self._elide(preset["name"], 18))
            btn.setToolTip(self._preset_tooltip(preset))
            self._make_shrinkable(btn)
            btn.clicked.connect(lambda _c=False, p=preset: self._apply_preset(p))
            if preset.get("user"):
                btn.setContextMenuPolicy(Qt.CustomContextMenu)
                btn.customContextMenuRequested.connect(
                    lambda pos, p=preset, b=btn: self._show_preset_menu(p, b, pos))
            grid.addWidget(btn, i // 2, i % 2)
        self.preset_box.addLayout(grid)

    def _clear_layout(self, layout):
        """Entfernt alle Widgets/Unterlayouts aus einem Layout."""
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
            else:
                child = item.layout()
                if child is not None:
                    self._clear_layout(child)

    def _current_settings_as_preset(self, name, keywords):
        """Liest die aktuellen Regler aus und baut daraus ein Preset-Dict."""
        return {
            "name": name,
            "font": self.font_combo.currentText(),
            "size": self.size_spin.value(),
            "fill": self.fill_btn._color.name(),
            "outline": self.outline_btn._color.name(),
            "outline_px": self.out_spin.value(),
            "bold": self.bold_chk.isChecked(),
            "italic": self.italic_chk.isChecked(),
            "shadow": self.shadow_chk.isChecked(),
            "shadow_color": self.shadow_btn._color.name(),
            "shadow_dx": self.shadow_dx.value(),
            "shadow_dy": self.shadow_dy.value(),
            "keywords": keywords,
            "user": True,
        }

    def _save_current_as_preset(self):
        """Fragt Name (+ optionale Schlüsselwörter) ab und speichert das Preset."""
        name, ok = QInputDialog.getText(
            self.widget(), self.t("dlg_save_title"), self.t("dlg_save_name"))
        if not ok:
            return
        name = name.strip()
        if not name:
            self._warn(self.t("warn_no_name"))
            return

        kw_text, ok2 = QInputDialog.getText(
            self.widget(), self.t("dlg_kw_opt_title"), self.t("dlg_kw_opt_label"))
        keywords = []
        if ok2 and kw_text.strip():
            keywords = [k.strip().lower() for k in kw_text.split(",") if k.strip()]

        preset = self._current_settings_as_preset(name, keywords)
        self._user_presets = [p for p in self._user_presets
                              if p.get("name") != name]
        self._user_presets.append(preset)
        save_user_presets(self._user_presets)
        self._rebuild_presets()
        self.status_label.setText(self.t("st_preset_saved", name=name))

    def _show_preset_menu(self, preset, button, pos):
        """Kontextmenü für ein eigenes Preset (Rechtsklick)."""
        menu = QMenu(self.widget())
        act_rename = menu.addAction(self.t("menu_rename"))
        act_keywords = menu.addAction(self.t("menu_edit_keywords"))
        act_overwrite = menu.addAction(self.t("menu_overwrite"))
        menu.addSeparator()
        act_delete = menu.addAction(self.t("menu_delete"))

        chosen = menu.exec_(button.mapToGlobal(pos))
        if chosen is None:
            return
        if chosen == act_rename:
            self._rename_user_preset(preset)
        elif chosen == act_keywords:
            self._edit_keywords(preset)
        elif chosen == act_overwrite:
            self._overwrite_user_preset(preset)
        elif chosen == act_delete:
            self._delete_user_preset(preset)

    def _rename_user_preset(self, preset):
        old = preset.get("name", "")
        new, ok = QInputDialog.getText(
            self.widget(), self.t("dlg_rename_title"), self.t("dlg_rename_label"),
            text=old)
        if not ok:
            return
        new = new.strip()
        if not new:
            self._warn(self.t("warn_no_name"))
            return
        if new == old:
            return
        if any(p is not preset and p.get("name") == new for p in self._user_presets):
            self._warn(self.t("warn_name_exists", name=new))
            return
        preset["name"] = new
        save_user_presets(self._user_presets)
        self._rebuild_presets()
        self.status_label.setText(self.t("st_preset_renamed", name=new))

    def _edit_keywords(self, preset):
        current = ", ".join(preset.get("keywords", []))
        txt, ok = QInputDialog.getText(
            self.widget(), self.t("dlg_editkw_title"), self.t("dlg_editkw_label"),
            text=current)
        if not ok:
            return
        preset["keywords"] = [k.strip().lower() for k in txt.split(",") if k.strip()]
        save_user_presets(self._user_presets)
        self._rebuild_presets()
        self._on_text_changed(self.text_input.text())
        self.status_label.setText(self.t("st_keywords_updated", name=preset["name"]))

    def _overwrite_user_preset(self, preset):
        reply = QMessageBox.question(
            self.widget(), self.t("dlg_overwrite_title"),
            self.t("dlg_overwrite_q", name=preset["name"]),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        preset["font"] = self.font_combo.currentText()
        preset["size"] = self.size_spin.value()
        preset["fill"] = self.fill_btn._color.name()
        preset["outline"] = self.outline_btn._color.name()
        preset["outline_px"] = self.out_spin.value()
        preset["bold"] = self.bold_chk.isChecked()
        preset["italic"] = self.italic_chk.isChecked()
        preset["shadow"] = self.shadow_chk.isChecked()
        preset["shadow_color"] = self.shadow_btn._color.name()
        preset["shadow_dx"] = self.shadow_dx.value()
        preset["shadow_dy"] = self.shadow_dy.value()
        save_user_presets(self._user_presets)
        self._rebuild_presets()
        self.status_label.setText(self.t("st_preset_overwritten", name=preset["name"]))

    def _delete_user_preset(self, preset):
        name = preset.get("name", "")
        reply = QMessageBox.question(
            self.widget(), self.t("dlg_delpreset_title"),
            self.t("dlg_delpreset_q", name=name),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        self._user_presets = [p for p in self._user_presets if p is not preset]
        save_user_presets(self._user_presets)
        self._rebuild_presets()
        self.status_label.setText(self.t("st_preset_deleted", name=name))

    # ==================================================================
    #  Font-Dropdown
    # ==================================================================
    def _build_font_combo(self):
        """Dropdown mit Favoriten + allen System-Fonts, durchsuchbar."""
        combo = QComboBox()
        combo.setEditable(True)
        combo.setInsertPolicy(QComboBox.NoInsert)

        combo.addItems(SFX_FONTS)
        if SHOW_ALL_SYSTEM_FONTS:
            families = self._families()      # einmal ermittelt + gecacht
            if families:
                combo.insertSeparator(combo.count())
                combo.addItems(families)

        completer = combo.completer()
        if completer is not None:
            completer.setCompletionMode(QCompleter.PopupCompletion)
            completer.setCaseSensitivity(Qt.CaseInsensitive)
            completer.setFilterMode(Qt.MatchContains)

        # Breite an einer kurzen Mindestlänge ausrichten statt am längsten
        # Fontnamen – sonst zwingt das Dropdown den ganzen Docker breit.
        combo.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        combo.setMinimumContentsLength(6)
        self._make_shrinkable(combo)
        combo.setCurrentIndex(0)
        return combo

    def _select_font(self, font_name):
        """Wählt den Font im Dropdown; bei editierbarem Feld notfalls als Text."""
        idx = self.font_combo.findText(font_name)
        if idx >= 0:
            self.font_combo.setCurrentIndex(idx)
        else:
            self.font_combo.setCurrentText(font_name)

    # ==================================================================
    #  Live-Vorschläge
    # ==================================================================
    def _on_text_changed(self, txt):
        self._refresh_suggestions(txt)
        self._update_preview()

    def _add_suggestion_btn(self, fnt):
        """Ein anklickbarer Vorschlags-Button für eine Schrift (kurz + schrumpfbar)."""
        btn = QPushButton(self.t("sug_font", name=self._elide(fnt, 28)))
        btn.setToolTip(self.t("sug_font_tip", name=fnt))
        self._make_shrinkable(btn)
        btn.clicked.connect(lambda _c=False, ff=fnt: self._select_font(ff))
        self.suggest_box.addWidget(btn)

    def _refresh_suggestions(self, text):
        """Baut die Vorschlagszeile neu: vorher benutzte Schrift -> passende
        Fonts (echte Regel oder Heuristik-Schätzung) -> passendes Preset."""
        self._clear_layout(self.suggest_box)
        norm = normalize_sfx(text)
        learned = self._learned_fonts(norm)
        groups = self._suggested_groups(text)
        guessed = False
        if not groups:                       # keine echte Regel -> Heuristik
            groups = self._heuristic_groups(text)
            guessed = bool(groups)
        preset = self._find_matching_preset(text)
        if not learned and not groups and preset is None:
            return

        header = self.t("suggestions_guess") if (guessed and not learned) \
            else self.t("suggestions")
        info = QLabel(header)
        info.setWordWrap(True)
        self.suggest_box.addWidget(info)

        # Fonts gruppenübergreifend nur einmal zeigen, Gesamtzahl begrenzen.
        shown = set()
        remaining = 8
        # 1) vorher für genau dieses Wort benutzte Schriften zuerst
        if learned:
            self.suggest_box.addWidget(
                self._mini_heading(self.t("suggestions_learned")))
            for fnt in learned:
                if remaining <= 0:
                    break
                if fnt in shown:
                    continue
                shown.add(fnt)
                remaining -= 1
                self._add_suggestion_btn(fnt)
        # 2) Fonts aus Regeln/Heuristik
        for group, fonts in groups:
            if remaining <= 0:
                break
            new_fonts = [f for f in fonts if f not in shown][:remaining]
            if not new_fonts:
                continue
            if group:                       # Gruppen-Überschrift (z. B. "Shout")
                self.suggest_box.addWidget(self._mini_heading(group))
            for fnt in new_fonts:
                shown.add(fnt)
                self._add_suggestion_btn(fnt)
            remaining -= len(new_fonts)

        if preset is not None:
            btn = QPushButton(self.t("sug_preset", name=preset["name"],
                                     font=self._elide(preset["font"], 22)))
            btn.setToolTip(self.t("sug_preset_tip"))
            self._make_shrinkable(btn)
            btn.clicked.connect(lambda _c=False, p=preset: self._apply_preset(p))
            self.suggest_box.addWidget(btn)

    def _group_fonts(self):
        """Gruppenname -> Fonts (erste passende eingebaute Regel)."""
        if self._group_fonts_cache is None:
            cache = {}
            for r in SFX_RULES:
                cache.setdefault(r.get("group", ""), list(r.get("fonts", [])))
            self._group_fonts_cache = cache
        return self._group_fonts_cache

    def _heuristic_groups(self, text):
        """Fallback-Vorschläge per Lautmuster-Heuristik (nur ohne echten Treffer)."""
        gf = self._group_fonts()
        out = []
        for g in classify_sfx(text, available=set(gf.keys())):
            fonts = gf.get(g) or []
            if fonts:
                out.append((g, list(fonts)))
        return out

    def _learned_fonts(self, norm):
        """Für dieses (normalisierte) Wort früher gewählte Schriften, häufigste
        zuerst."""
        if not norm:
            return []
        d = self._usage.get(norm) or {}
        return [f for f, _c in sorted(d.items(),
                                      key=lambda kv: kv[1], reverse=True)]

    def _record_usage(self, text, font):
        """Merkt sich: für dieses Wort wurde diese Schrift gewählt (lernt dazu)."""
        norm = normalize_sfx(text)
        if not norm or not font:
            return
        d = self._usage.setdefault(norm, {})
        d[font] = d.get(font, 0) + 1
        if len(d) > 8:                       # pro Wort höchstens 8 Schriften
            self._usage[norm] = dict(
                sorted(d.items(), key=lambda kv: kv[1], reverse=True)[:8])
        try:
            save_usage(self._usage)
        except Exception:
            pass

    def _all_rules(self):
        """(rule, is_builtin) für eingebaute + eigene Regeln – aber NUR die der
        aktiven Regelsprache (plus die sprachübergreifenden "*"-Regeln).

        Für eigene Regeln wird das Original-Dict zurückgegeben, damit
        Bearbeiten/Löschen über die Identität weiter funktioniert."""
        active = self._rule_lang

        def ok(r):
            lang = r.get("lang", "*")
            return lang == "*" or lang == active

        rules = [(r, True) for r in SFX_RULES if ok(r)]
        rules += [(r, False) for r in self._font_rules if ok(r)]
        return rules

    def _on_rule_lang_changed(self, _idx):
        """Regelsprache gewechselt: speichern, Regel-Liste + Vorschläge neu."""
        code = self.rule_lang_combo.currentData()
        if not code or code == self._rule_lang:
            return
        self._rule_lang = code
        save_rule_lang(code)
        self._rebuild_rules()
        self._refresh_suggestions(self.text_input.text())

    def _suggested_groups(self, text):
        """[(group, [fonts]), ...] für Regeln, deren Stichwort im Text vorkommt.

        Nutzt normalisiertes Matching, sodass gedehnte SFX ("BOOOOM") und
        Schreibweisen mit Satzzeichen ("ka-boom!") sicher erkannt werden.
        Gruppen mit einem EXAKTEN Worttreffer (ganzes Wort) werden nach vorne
        sortiert, damit der treffendste Vorschlag zuerst kommt."""
        norm = normalize_sfx(text)
        if not norm:
            return []
        result = []                       # je Eintrag: [group, [fonts], exact]
        index = {}
        for rule, _builtin in self._all_rules():
            matched = [kw for kw in rule.get("keywords", [])
                       if keyword_matches(kw, norm)]
            if not matched:
                continue
            exact = any(normalize_sfx(kw) == norm for kw in matched)
            g = rule.get("group") or ""
            if g not in index:
                index[g] = len(result)
                result.append([g, [], exact])
            entry = result[index[g]]
            entry[2] = entry[2] or exact
            for f in rule.get("fonts", []):
                if f and f not in entry[1]:
                    entry[1].append(f)
        # stabile Sortierung: exakte Treffer zuerst, sonst Reihenfolge erhalten
        result.sort(key=lambda e: 0 if e[2] else 1)
        return [(g, fonts) for g, fonts, _ex in result]

    def _mini_heading(self, text):
        """Kleine, fette Zwischenüberschrift (für Gruppen)."""
        lbl = QLabel(text)
        f = lbl.font()
        f.setBold(True)
        lbl.setFont(f)
        return lbl

    def _find_matching_preset(self, text):
        """Erstes Preset, dessen Schlüsselwort im Text vorkommt (oder None).
        Gleiches normalisiertes Matching wie bei den Font-Regeln."""
        norm = normalize_sfx(text)
        if not norm:
            return None
        for preset in self._all_presets():
            for kw in preset.get("keywords", []):
                if keyword_matches(kw, norm):
                    return preset
        return None

    # ==================================================================
    #  Font-Vorschläge (Stichwort -> Font(s)), im Docker verwaltbar
    # ==================================================================
    def _rebuild_rules(self):
        """Baut die Regel-Buttons neu auf, nach Gruppen sortiert.

        Eingebaute Regeln (aus config.py) sind immer dabei und nur lesbar
        (Klick übernimmt ihren ersten Font). Eigene Regeln sind links-/rechts-
        klickbar zum Bearbeiten/Löschen."""
        self._clear_layout(self.rules_box)
        all_rules = self._all_rules()
        if not all_rules:
            hint = QLabel(self.t("no_rules"))
            hint.setWordWrap(True)
            self.rules_box.addWidget(hint)
            return
        for group in self._ordered_groups():
            self.rules_box.addWidget(
                self._mini_heading(group if group else self.t("group_none")))
            for rule, is_builtin in all_rules:
                if (rule.get("group") or "") != group:
                    continue
                kw = ", ".join(rule.get("keywords", []))
                fo = ", ".join(rule.get("fonts", []))
                full = f"{kw}  →  {fo}"
                btn = QPushButton(f"{self._elide(kw, 22)}  →  {self._elide(fo, 22)}")
                self._make_shrinkable(btn)
                if is_builtin:
                    btn.setToolTip(full + "\n" + self.t("rule_builtin_tip"))
                    fonts = rule.get("fonts") or []
                    if fonts:
                        first = fonts[0]
                        btn.clicked.connect(
                            lambda _c=False, f=first: self._select_font(f))
                else:
                    btn.setToolTip(full + "\n" + self.t("rule_tip"))
                    btn.clicked.connect(
                        lambda _c=False, r=rule: self._edit_font_rule(r))
                    btn.setContextMenuPolicy(Qt.CustomContextMenu)
                    btn.customContextMenuRequested.connect(
                        lambda pos, r=rule, b=btn: self._show_rule_menu(r, b, pos))
                self.rules_box.addWidget(btn)

    def _ordered_groups(self):
        """Gruppen in Reihenfolge des ersten Auftretens; 'ohne Gruppe' ans Ende.
        Berücksichtigt eingebaute UND eigene Regeln."""
        order = []
        has_empty = False
        for rule, _b in self._all_rules():
            g = rule.get("group") or ""
            if g == "":
                has_empty = True
            elif g not in order:
                order.append(g)
        if has_empty:
            order.append("")
        return order

    def _existing_groups(self):
        """Vorhandene (nicht-leere) Gruppennamen – für die Auswahl im Dialog.
        Eingebaute Gruppen sind dabei, damit eigene Regeln sie erweitern können."""
        seen = []
        for rule, _b in self._all_rules():
            g = (rule.get("group") or "").strip()
            if g and g not in seen:
                seen.append(g)
        return seen

    def _show_rule_menu(self, rule, button, pos):
        menu = QMenu(self.widget())
        act_edit = menu.addAction(self.t("menu_edit"))
        menu.addSeparator()
        act_del = menu.addAction(self.t("menu_delete"))
        chosen = menu.exec_(button.mapToGlobal(pos))
        if chosen == act_edit:
            self._edit_font_rule(rule)
        elif chosen == act_del:
            self._delete_font_rule(rule)

    def _ask_fonts(self, fonts_init):
        """
        Dialog zum Auswählen der Font(s) für eine Regel.

        Bietet ein durchsuchbares Dropdown ALLER Fonts (Namen nachschlagen!)
        + 'Hinzufügen'-Knopf, der den gewählten Font an die Liste anhängt.
        Die Liste bleibt frei editierbar, also auch mehrere Fonts per Hand
        möglich. Rückgabe: Komma-String oder None bei Abbruch.
        """
        dlg = QDialog(self.widget())
        dlg.setWindowTitle(self.t("dlg_rule_fonts_title"))
        lay = QVBoxLayout(dlg)
        lbl = QLabel(self.t("dlg_rule_fonts_label"))
        lbl.setWordWrap(True)
        lay.addWidget(lbl)

        # Durchsuchbares Dropdown aller Fonts + Hinzufügen-Knopf
        pick_row = QHBoxLayout()
        combo = self._build_font_combo()
        pick_row.addWidget(combo, 1)
        add_btn = QPushButton(self.t("add_font_btn"))
        pick_row.addWidget(add_btn, 0)
        lay.addLayout(pick_row)

        # frei editierbare, Komma-getrennte Liste (mehrere Fonts möglich)
        line = QLineEdit(fonts_init)
        lay.addWidget(line)

        def add_current():
            name = combo.currentText().strip()
            if not name:
                return
            existing = [f.strip() for f in line.text().split(",") if f.strip()]
            if name not in existing:
                existing.append(name)
            line.setText(", ".join(existing))

        add_btn.clicked.connect(add_current)

        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(dlg.accept)
        bb.rejected.connect(dlg.reject)
        lay.addWidget(bb)

        if dlg.exec_() != QDialog.Accepted:
            return None
        return line.text()

    def _prompt_font_rule(self, group_init, kw_init, fonts_init):
        """Fragt Gruppe + Stichwörter + Fonts ab; (group, keywords, fonts) oder None."""
        # Gruppe: vorhandene Gruppen zur Auswahl, editierbar (neue eintippbar)
        items = list(self._existing_groups())
        if group_init and group_init not in items:
            items.insert(0, group_init)
        if not items:
            items = [""]
        current = items.index(group_init) if group_init in items else 0
        group, ok = QInputDialog.getItem(
            self.widget(), self.t("dlg_rule_group_title"),
            self.t("dlg_rule_group_label"), items, current, True)
        if not ok:
            return None
        group = group.strip()

        kw_text, ok2 = QInputDialog.getText(
            self.widget(), self.t("dlg_rule_kw_title"), self.t("dlg_rule_kw_label"),
            text=kw_init)
        if not ok2:
            return None
        keywords = [k.strip().lower() for k in kw_text.split(",") if k.strip()]
        if not keywords:
            self._warn(self.t("warn_no_keyword"))
            return None

        fonts_text = self._ask_fonts(fonts_init)
        if fonts_text is None:
            return None
        fonts = [f.strip() for f in fonts_text.split(",") if f.strip()]
        if not fonts:
            self._warn(self.t("warn_no_font"))
            return None
        return group, keywords, fonts

    def _add_font_rule(self):
        res = self._prompt_font_rule("", "", self.font_combo.currentText())
        if res is None:
            return
        group, keywords, fonts = res
        # neue Regel gehört zur aktuell aktiven Regelsprache
        self._font_rules.append(
            {"group": group, "keywords": keywords, "fonts": fonts,
             "lang": self._rule_lang})
        save_font_rules(self._font_rules)
        self._rebuild_rules()
        self._refresh_suggestions(self.text_input.text())
        self.status_label.setText(self.t("st_rule_added"))

    def _edit_font_rule(self, rule):
        res = self._prompt_font_rule(
            rule.get("group", ""),
            ", ".join(rule.get("keywords", [])),
            ", ".join(rule.get("fonts", [])))
        if res is None:
            return
        rule["group"], rule["keywords"], rule["fonts"] = res
        save_font_rules(self._font_rules)
        self._rebuild_rules()
        self._refresh_suggestions(self.text_input.text())
        self.status_label.setText(self.t("st_rule_updated"))

    def _delete_font_rule(self, rule):
        reply = QMessageBox.question(
            self.widget(), self.t("dlg_delrule_title"), self.t("dlg_delrule_q"),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        self._font_rules = [r for r in self._font_rules if r is not rule]
        save_font_rules(self._font_rules)
        self._rebuild_rules()
        self._refresh_suggestions(self.text_input.text())
        self.status_label.setText(self.t("st_rule_deleted"))

    # ==================================================================
    #  Kern: SFX einfügen
    # ==================================================================
    def _insert_sfx(self):
        doc = Krita.instance().activeDocument()
        if doc is None:
            self._warn(self.t("st_no_doc"))
            return

        text = self._effective_text()
        if not text:
            self._warn(self.t("st_no_text"))
            return

        # Aktive Ebene prüfen – ist es keine Vektor-Ebene, neue anlegen.
        node = doc.activeNode()
        created = False
        if node is None or node.type() != "vectorlayer":
            node = doc.createVectorLayer("SFX")
            rootnode = doc.rootNode()
            children = rootnode.childNodes()
            above = children[-1] if children else None   # möglichst ganz oben
            rootnode.addChildNode(node, above)
            doc.setActiveNode(node)
            created = True

        # Zielmitte bestimmen: wenn eine Auswahl aktiv ist, deren Mitte,
        # sonst die Bildmitte (damit der SFX nicht mehr oben links klebt).
        img_w, img_h = doc.width(), doc.height()
        box_x, box_y, box_w, box_h = 0, 0, img_w, img_h
        sel = doc.selection()
        if sel is not None:
            try:
                if sel.width() > 0 and sel.height() > 0:
                    box_x, box_y = sel.x(), sel.y()
                    box_w, box_h = sel.width(), sel.height()
            except Exception:
                pass
        fsize = self.size_spin.value()
        tx = box_x + box_w / 2.0
        ty = box_y + box_h / 2.0 + fsize * 0.35   # grobe senkrechte Zentrierung

        svg = build_sfx_svg(
            text=text,
            font_family=self.font_combo.currentText(),
            font_size=fsize,
            fill=self.fill_btn._color.name(),
            outline=self.outline_btn._color.name(),
            outline_px=self.out_spin.value(),
            bold=self.bold_chk.isChecked(),
            italic=self.italic_chk.isChecked(),
            x=tx, y=ty, anchor="middle", img_w=img_w, img_h=img_h,
            shadow=self.shadow_chk.isChecked(),
            shadow_color=self.shadow_btn._color.name(),
            shadow_dx=self.shadow_dx.value(),
            shadow_dy=self.shadow_dy.value(),
        )

        try:
            ok = node.addShapesFromSvg(svg)
        except Exception as e:                      # noqa: BLE001
            self._warn(self.t("st_insert_fail", err=e))
            return
        doc.refreshProjection()

        if ok is False:
            self._warn(self.t("st_svg_fail"))
            return

        # zuletzt genutzten Stil merken (ohne den Text selbst)
        style = self._capture_state()
        style.pop("text", None)
        save_settings(style)

        # dazulernen: welche Schrift wurde für dieses Wort gewählt
        self._record_usage(text, self.font_combo.currentText())

        self.status_label.setText(
            self.t("st_layer_created") if created else self.t("st_inserted"))

    # ==================================================================
    #  Zurücksetzen
    # ==================================================================
    def _reset(self):
        """Zurücksetzen – wahlweise nur Stil oder alles (Presets + Regeln)."""
        box = QMessageBox(self.widget())
        box.setWindowTitle(self.t("reset_title"))
        box.setText(self.t("reset_q"))
        btn_style = box.addButton(self.t("reset_style"), QMessageBox.AcceptRole)
        btn_all = box.addButton(self.t("reset_all"), QMessageBox.DestructiveRole)
        box.addButton(self.t("cancel"), QMessageBox.RejectRole)
        box.setDefaultButton(btn_style)
        box.exec_()
        clicked = box.clickedButton()

        if clicked is btn_all:
            self._user_presets = []
            self._font_rules = []
            save_user_presets(self._user_presets)
            save_font_rules(self._font_rules)
            self._rebuild_presets()
            self._rebuild_rules()
            msg = self.t("st_reset_all")
        elif clicked is btn_style:
            msg = self.t("st_reset_style")
        else:
            return  # Abbrechen

        self._reset_style_to_defaults()
        save_settings({})                 # gemerkten Stil verwerfen
        self.status_label.setText(msg)

    def _reset_style_to_defaults(self):
        """Setzt Font/Größe/Farben/Outline/Großschreibung auf die Startwerte."""
        if SFX_FONTS:
            self._select_font(SFX_FONTS[0])
        else:
            self.font_combo.setCurrentIndex(0)
        self.size_spin.setValue(DEFAULTS["size"])
        self.out_spin.setValue(DEFAULTS["outline_px"])
        self._set_btn_color(self.fill_btn, QColor(DEFAULTS["fill"]))
        self._set_btn_color(self.outline_btn, QColor(DEFAULTS["outline"]))
        self.shadow_chk.setChecked(bool(DEFAULTS.get("shadow", False)))
        self._set_btn_color(self.shadow_btn,
                            QColor(DEFAULTS.get("shadow_color", "#000000")))
        self.shadow_dx.setValue(int(DEFAULTS.get("shadow_dx", 6)))
        self.shadow_dy.setValue(int(DEFAULTS.get("shadow_dy", 6)))
        self._update_shadow_enabled()
        self.upper_chk.setChecked(True)
        self.bold_chk.setChecked(False)
        self.italic_chk.setChecked(False)
        self.text_input.clear()
        self._update_preview()

    def _warn(self, msg):
        self.status_label.setText("⚠ " + msg)

    # ==================================================================
    #  Import / Export (eigene Presets + Font-Regeln)
    # ==================================================================
    def _export_data(self):
        """Schreibt eigene Presets + Font-Regeln in eine .json-Datei."""
        path, _flt = QFileDialog.getSaveFileName(
            self.widget(), self.t("export_title"),
            "manga_sfx_presets.json", "JSON (*.json)")
        if not path:
            return
        if not path.lower().endswith(".json"):
            path += ".json"
        data = {
            "manga_sfx": 1,
            "presets": self._user_presets,
            "font_rules": self._font_rules,
        }
        try:
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(data, fh, ensure_ascii=False, indent=2)
        except OSError as e:                        # noqa: BLE001
            self._warn(self.t("st_export_fail", err=e))
            return
        self.status_label.setText(self.t(
            "st_exported", p=len(self._user_presets), r=len(self._font_rules)))

    def _import_data(self):
        """Liest Presets + Regeln aus einer .json-Datei (Zusammenführen/Ersetzen)."""
        path, _flt = QFileDialog.getOpenFileName(
            self.widget(), self.t("import_title"), "", "JSON (*.json)")
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, ValueError) as e:          # noqa: BLE001
            self._warn(self.t("st_import_fail", err=e))
            return
        if not isinstance(data, dict):
            self._warn(self.t("st_import_bad"))
            return

        presets = self._sanitize_presets(data.get("presets", []))
        rules = self._sanitize_rules(data.get("font_rules", []))
        if not presets and not rules:
            self._warn(self.t("st_import_empty"))
            return

        # Zusammenführen oder ersetzen?
        box = QMessageBox(self.widget())
        box.setWindowTitle(self.t("import_title"))
        box.setText(self.t("import_q", p=len(presets), r=len(rules)))
        btn_merge = box.addButton(self.t("import_merge"), QMessageBox.AcceptRole)
        btn_replace = box.addButton(self.t("import_replace"),
                                    QMessageBox.DestructiveRole)
        box.addButton(self.t("cancel"), QMessageBox.RejectRole)
        box.setDefaultButton(btn_merge)
        box.exec_()
        clicked = box.clickedButton()

        if clicked is btn_replace:
            self._user_presets = presets
            self._font_rules = rules
        elif clicked is btn_merge:
            self._merge_presets(presets)
            self._merge_rules(rules)
        else:
            return  # Abbrechen

        save_user_presets(self._user_presets)
        save_font_rules(self._font_rules)
        self._rebuild_presets()
        self._rebuild_rules()
        self._refresh_suggestions(self.text_input.text())
        self.status_label.setText(self.t(
            "st_imported", p=len(presets), r=len(rules)))

    # --- Hilfen für den Import ----------------------------------------
    def _as_int(self, value, default):
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def _sanitize_presets(self, raw):
        """Macht importierte Presets robust (fehlende Felder auffüllen)."""
        out = []
        if not isinstance(raw, list):
            return out
        for p in raw:
            if not isinstance(p, dict) or not p.get("name"):
                continue
            kws = p.get("keywords", [])
            out.append({
                "name": str(p.get("name", "")).strip(),
                "font": str(p.get("font", "")),
                "size": self._as_int(p.get("size"), DEFAULTS["size"]),
                "fill": str(p.get("fill", DEFAULTS["fill"])),
                "outline": str(p.get("outline", DEFAULTS["outline"])),
                "outline_px": self._as_int(p.get("outline_px"),
                                           DEFAULTS["outline_px"]),
                "bold": bool(p.get("bold", False)),
                "italic": bool(p.get("italic", False)),
                "shadow": bool(p.get("shadow", False)),
                "shadow_color": str(p.get("shadow_color",
                                          DEFAULTS.get("shadow_color", "#000000"))),
                "shadow_dx": self._as_int(p.get("shadow_dx"),
                                          DEFAULTS.get("shadow_dx", 6)),
                "shadow_dy": self._as_int(p.get("shadow_dy"),
                                          DEFAULTS.get("shadow_dy", 6)),
                "keywords": ([str(k).strip().lower() for k in kws if str(k).strip()]
                             if isinstance(kws, list) else []),
                "user": True,
            })
        return out

    def _sanitize_rules(self, raw):
        """Macht importierte Font-Regeln robust; verwirft unvollständige."""
        out = []
        if not isinstance(raw, list):
            return out
        for r in raw:
            if not isinstance(r, dict):
                continue
            kws = r.get("keywords", [])
            fonts = r.get("fonts", [])
            if not isinstance(kws, list) or not isinstance(fonts, list):
                continue
            keywords = [str(k).strip().lower() for k in kws if str(k).strip()]
            fontlist = [str(f).strip() for f in fonts if str(f).strip()]
            if not keywords or not fontlist:
                continue
            lang = str(r.get("lang", "")).strip() or "*"   # alt -> "*" = immer
            out.append({
                "group": str(r.get("group", "")).strip(),
                "keywords": keywords,
                "fonts": fontlist,
                "lang": lang,
            })
        return out

    def _merge_presets(self, imported):
        """Fügt importierte Presets hinzu; gleicher Name ersetzt das alte."""
        names = {p["name"] for p in imported}
        self._user_presets = [p for p in self._user_presets
                              if p.get("name") not in names]
        self._user_presets.extend(imported)

    def _merge_rules(self, imported):
        """Fügt importierte Regeln hinzu, ohne exakte Duplikate."""
        def sig(r):
            return ((r.get("group") or ""),
                    tuple(r.get("keywords", [])),
                    tuple(r.get("fonts", [])))
        existing = {sig(r) for r in self._font_rules}
        for r in imported:
            if sig(r) not in existing:
                self._font_rules.append(r)
                existing.add(sig(r))
