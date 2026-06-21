# -*- coding: utf-8 -*-
"""
Speichern/Laden der selbst angelegten Presets.

Persistiert wird über Kritas eigene Einstellungen (landen in der
kritarc-Datei). So bleiben die im Docker erstellten Presets über
Neustarts hinweg erhalten – ganz ohne eigenes Datei-Handling.
"""
import json
from krita import Krita

_GROUP = "MangaSFX"
_KEY = "user_presets"
_KEY_RULES = "font_rules"
_KEY_SETTINGS = "last_settings"
_KEY_LANG = "language"
_KEY_VIEW = "view"
_KEY_USAGE = "usage"
_KEY_RULE_LANG = "rule_lang"


def load_user_presets():
    """Liste der eigenen Presets (leere Liste, wenn noch keine da sind)."""
    raw = Krita.instance().readSetting(_GROUP, _KEY, "")
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return []
    if not isinstance(data, list):
        return []

    presets = []
    for p in data:
        if isinstance(p, dict) and "name" in p:
            p["user"] = True            # Laufzeit-Markierung: eigenes Preset
            p.setdefault("keywords", [])
            presets.append(p)
    return presets


def save_user_presets(presets):
    """Schreibt die eigenen Presets in die Krita-Einstellungen."""
    Krita.instance().writeSetting(
        _GROUP, _KEY, json.dumps(presets, ensure_ascii=False))


def load_font_rules():
    """
    Font-Vorschlagsregeln: Liste von {"keywords": [...], "fonts": [...]}.
    Bedeutung: kommt eines der Stichwörter im SFX-Text vor, werden die
    zugehörigen Fonts vorgeschlagen.
    """
    raw = Krita.instance().readSetting(_GROUP, _KEY_RULES, "")
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return []
    if not isinstance(data, list):
        return []

    rules = []
    for r in data:
        if not isinstance(r, dict):
            continue
        kws = r.get("keywords", [])
        fonts = r.get("fonts", [])
        if isinstance(kws, list) and isinstance(fonts, list):
            # "lang": Regelsprache; fehlt sie (alte Daten) -> "*" = immer aktiv,
            # damit alte Regeln nicht verschwinden.
            rules.append({
                "group": str(r.get("group", "")),
                "keywords": [str(k) for k in kws],
                "fonts": [str(f) for f in fonts],
                "lang": str(r.get("lang", "*")) or "*",
            })
    return rules


def save_font_rules(rules):
    """Schreibt die Font-Vorschlagsregeln in die Krita-Einstellungen."""
    Krita.instance().writeSetting(
        _GROUP, _KEY_RULES, json.dumps(rules, ensure_ascii=False))


def load_rule_lang(default="en"):
    """Aktive Regelsprache (welche SFX-Regeln gelten). 'default' wenn nichts
    gespeichert ist."""
    val = Krita.instance().readSetting(_GROUP, _KEY_RULE_LANG, "")
    return val if val else default


def save_rule_lang(lang):
    """Speichert die aktive Regelsprache."""
    Krita.instance().writeSetting(_GROUP, _KEY_RULE_LANG, str(lang))


def load_language(default="en"):
    """Liest die gespeicherte Sprache ('en'/'de'); sonst 'default'."""
    val = Krita.instance().readSetting(_GROUP, _KEY_LANG, "")
    return val if val in ("en", "de") else default


def save_language(lang):
    """Speichert die gewählte Sprache."""
    Krita.instance().writeSetting(_GROUP, _KEY_LANG, lang)


def load_settings():
    """Zuletzt genutzter Stil (Font/Größe/Farben/Outline/...). Dict, ggf. leer."""
    raw = Krita.instance().readSetting(_GROUP, _KEY_SETTINGS, "")
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return {}
    return data if isinstance(data, dict) else {}


def save_settings(settings):
    """Speichert den zuletzt genutzten Stil."""
    Krita.instance().writeSetting(
        _GROUP, _KEY_SETTINGS, json.dumps(settings, ensure_ascii=False))


def load_view():
    """Layout-/Anzeige-Einstellungen des Dockers (Größen + ein-/ausblenden).
    Dict, ggf. leer – der Docker füllt fehlende Werte mit Standards auf."""
    raw = Krita.instance().readSetting(_GROUP, _KEY_VIEW, "")
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return {}
    return data if isinstance(data, dict) else {}


def save_view(view):
    """Speichert die Layout-/Anzeige-Einstellungen des Dockers."""
    Krita.instance().writeSetting(
        _GROUP, _KEY_VIEW, json.dumps(view, ensure_ascii=False))


def load_usage():
    """Lern-Statistik: welche Schrift wurde für welches (normalisierte) SFX-Wort
    wie oft gewählt. Form: { wort: { fontname: anzahl } }. Leeres Dict, wenn
    noch nichts gelernt wurde."""
    raw = Krita.instance().readSetting(_GROUP, _KEY_USAGE, "")
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return {}
    if not isinstance(data, dict):
        return {}
    out = {}
    for word, fonts in data.items():
        if isinstance(fonts, dict):
            clean = {}
            for f, c in fonts.items():
                try:
                    clean[str(f)] = int(c)
                except (TypeError, ValueError):
                    continue
            if clean:
                out[str(word)] = clean
    return out


def save_usage(usage):
    """Speichert die Lern-Statistik."""
    Krita.instance().writeSetting(
        _GROUP, _KEY_USAGE, json.dumps(usage, ensure_ascii=False))
