# SFX Helper – Krita docker

A dockable panel for Krita 5.x that quickly drops styled manga **SFX** (sound
effects) with an outline onto a **vector layer** – without setting the font,
color and outline by hand every time.

> The plugin's folder, library id (`mangasfx`) and saved settings group stay
> unchanged for compatibility; only the **display name** is "SFX Helper".

> A German version of this README is available in
> [`README.de.md`](README.de.md). The plugin's UI is bilingual
> (**English = default**, German), switchable at the top of the docker.

## Features
- Text field for the SFX word
- Font dropdown with every installed font (searchable) + a favorites list
- Inputs for font size, fill color, outline color and outline width
- **Optional drop shadow** (new): color + X/Y offset
- **WYSIWYG live preview** (new): shows the text with the actual **outline and
  shadow** (not just fill), fitted to the preview area
- Preset buttons (font + color + outline + shadow in one click)
- **Insert SFX** -> builds SVG text and adds it to the active vector layer via
  `addShapesFromSvg` (creating the layer automatically if needed). The text is
  now placed **centered** – in the middle of the active **selection** if there
  is one, otherwise the middle of the image (no more top-left corner).
- **Built-in smart font suggestions** (new): out of the box, typing an SFX word
  suggests matching fonts grouped by mood (see *Built-in SFX rules* below). You
  can still add your own rules on top.
- Font suggestions: define in the docker which font(s) suit which SFX word –
  optionally in groups (e.g. Shout / Scared / Normal / Soft); as you type, the
  matching suggestions appear grouped and clickable
- **Adjustable layout** (new): resize or hide parts of the docker (see
  *Layout & sizes* below)
- Language switch: **English = default**, German – at the top of the docker
- Convenience: live font preview, UPPERCASE / bold / italic toggles, and the
  docker remembers the last used style across restarts
- **Reset** button: style back to defaults – optionally also delete all your own
  presets + font rules
- Import / Export: save your presets + font rules (with groups) as `.json`,
  share them and read them back (merge or replace)

---

## Built-in SFX rules (smart suggestions)

The plugin ships with a **large set of built-in font rules** — **29 groups**
covering **400+ SFX words** (English *and* romanized Japanese). As soon as you
type an SFX word, it suggests fitting fonts, grouped by what kind of sound it is:

| Group | Example words | First suggested font |
| --- | --- | --- |
| Boom / Explosion | boom, kaboom, blast, *don*, *dokan* | BadaBoom Pro BB |
| Hit / Punch | pow, smack, thud, knock, *doga* | BeatDown BB |
| Crash / Break | crash, smash, crack, *gasha*, *bakin* | Autodestruct BB |
| Slash / Cut / Tear | slash, slice, stab, snap, rip, *zan* | Brushzerker BB |
| Gunfire | shot, gun, ratatat, ping | Bulletproof BB |
| Metal / Clang / Click | clang, click, clack, *gatan*, *gakin* | Armor Piercing BB |
| Whoosh / Dash | whoosh, swoosh, dash, rush, *suu* | Blowhole BB |
| Jump / Fall / Slide | hop, jump, bounce, fall, slide | ActionFigure BB |
| Friction / Creak | creak, screech, grind, scrape | AtlandSketches BB |
| Rumble / Shake | rumble, rattle, quake, *gogo*, *goro* | Autodestruct BB |
| Engine / Electronic | beep, buzz, vroom, ring, *brrring* | Android Nation BB |
| Electric / Spark | zap, spark, flash, *biri*, *pachi* | BlackHole BB |
| Sparkle / Shine / Magic | sparkle, *kira*, *pika*, twinkle | Arcanum BB |
| Water / Liquid | splash, drip, gush, *basha*, *poro* | Blowhole BB |
| Eating / Mouth | munch, chomp, slurp, gulp, *zuru* | Blambot Casual |
| Cry / Sob | sob, waaah, wail, cry, sniff | Blambot Casual |
| Breath / Sleep | gasp, pant, snore, sleep, *zzz* | Blambot Casual |
| Whisper / Silence | whisper, hush, psst, *koso*, *shiin* | Anime Ace 2.0 BB |
| Laugh / Smile | haha, giggle, *fufu*, *niko*, *niyari* | Blambot Casual |
| Roar / Growl | roar, growl, grr, snarl, *gao* | Always Angry BB |
| Scream / Shout | scream, yell, *gyaa*, *kyaa*, *uwaa* | Always Angry BB |
| Reaction | eek, ack, ugh, ow, *gaan* | ActionFigure BB |
| Heartbeat / Tension / Stare | *doki*, *kyun*, *zawa*, stare, *jii* | Astounder Squared BB |
| Touch / Grab / Soft | grab, hug, pet, *peta*, *fuwa*, *mofu* | Astounder Round LC BB |
| Pop / Bounce | pop, poof, boing, *pon*, *pyon* | Astounder Round BB |
| Flutter / Flap | flutter, rustle, flap, *basa*, *batan* | Astounder Round LC BB |
| Footsteps / Taps | tap, step, *tok*, patter, stomp | Blambot Casual |
| Clap / Cheer | clap, cheer, yay, hooray, ta-da | ActionFigure BB |
| Animal | meow, woof, *nyaa*, chirp, croak | Blambot Casual |

Both English and **romanized Japanese onomatopoeia** (*italic* above) are
recognized, and the matching is **elongation-aware**: `BOOM`, `BOOOOM`,
`ka-boom!` and `boom-boom` all match the same rule (repeated letters,
punctuation and the hyphen in doubled SFX are normalized away). Short
exclamations like `ow`, `eh` or `grr` match only as the whole word, so they
don't fire inside `pow`, `the` or `grab`.

**Guess for unknown SFX (new).** If a word matches no rule at all, the docker
falls back to a **sound-pattern heuristic** and still proposes a fitting group
(e.g. invented words: `DKKBAM` → Boom, `fwooosh` → Whoosh, `iiiieee` → Scream,
`zzzz` → Sleep). The header then reads *"Best guess for this word"*.

**Learns from you (new).** Whenever you insert an SFX, the docker remembers
which font you picked for that word. Next time you type the same word, that font
is offered first under *"Used before"*. This is stored in Krita's settings and
survives restarts (at most 8 fonts per word).

> These rules reference the **Blambot comic SFX fonts** (BadaBoom, Blambot
> FXPro, Astounder, Brushzerker, …). For Krita to actually render them, the
> fonts must be **installed in your system**. If one isn't installed, the
> suggestion still appears but Krita will fall back to a default font – just
> install the font (or point the rule at one you have).

The built-in rules are shown in the **Font suggestions** section (with a
*built-in* tooltip; click one to apply its font). They cannot be deleted, but
you can add your own rules next to them, and your rules can extend a built-in
group. To change the rule set itself, edit `SFX_RULES` in
[`mangasfx/config.py`](mangasfx/config.py).

### Rules are per language (new)

Every rule belongs to **one language**. A **Rule language** dropdown (in the
Font suggestions section) decides which rules are shown *and* active: only rules
of the selected language take effect when you type. So German rules
(`BUMM`, `KRACH`, `PENG` …) only fire when German is selected, Spanish rules
(`PUM`, `PAF` …) only under Spanish, etc. The default rule language follows the
interface language but can be changed independently. New rules you add are
tagged with the current rule language; your old rules (made before this change)
stay visible in every language.

**Romanized Japanese onomatopoeia** (`doki`, `gashan`, `zan` …) are tagged
`"*"` (universal) so they keep working in **every** language. Built-in rule sets
ship for **English, German and Spanish**; more can be added in `SFX_RULES` by
giving each rule a `"lang"`.

The interface itself is available in **English, German, Spanish, French,
Portuguese and Italian**; languages beyond EN/DE are core-translated and fall
back to English for the rest.

---

## Layout & sizes (customizing the docker)

Click the **⚙ Layout & sizes** button near the top of the docker to open a
small panel where you can:

- **Preview** – show/hide it and set its height in pixels (e.g. if you find it
  too tall or don't need it),
- **Suggestions**, **Presets** and **Font rules** – show or hide each section.

**Reset layout** restores the defaults. Your choices are remembered across
restarts. The docker is in a scroll area, so hiding or resizing parts never
clips anything.

The docker also **adapts to the dock width** (like TypeR): drag the dock
narrower or wider and the controls follow. The font dropdown and the rule /
suggestion buttons no longer force a fixed wide minimum — long rule labels are
shortened (the full text stays in the tooltip), so a narrow dock stays usable.

---

## Installation (Windows, Krita 5.x)

1. **Open the resource folder**
   Krita -> *Settings ▸ Manage Resources… ▸ Open Resource Folder*.
   Or directly in Explorer: `C:\Users\<YOU>\AppData\Roaming\krita\`

2. Go into the **`pykrita`** folder (create it if it does not exist).

3. **Copy in** exactly these two things:
   ```
   pykrita\
     ├─ mangasfx.desktop      <- the file
     └─ mangasfx\             <- the whole folder with all .py files
          ├─ __init__.py
          ├─ config.py
          ├─ i18n.py
          ├─ presets_store.py
          ├─ svg_builder.py
          └─ sfx_docker.py
   ```
   Important: `mangasfx.desktop` sits **next to** the `mangasfx\` folder, not
   inside it.

   On Linux/macOS the resource folder is
   `~/.local/share/krita/` or `~/Library/Application Support/krita/`.

4. **Restart Krita.**

5. **Enable the plugin**
   *Settings ▸ Configure Krita… ▸ Python Plugin Manager* -> tick
   **"SFX Helper"** -> OK -> **restart Krita again**.

6. **Show the docker**
   *Settings ▸ Dockers ▸ SFX Helper*.

> Note: this needs a Python-enabled build of Krita (the regular Windows build
> from krita.org is, by default).

---

## Usage
1. Have a document open and type the SFX word.
2. Choose font / size / colors / shadow **or** click a preset. The **live
   preview** shows exactly how it will look (with outline + shadow).
3. **Insert SFX** (or press Enter in the text field).
   If no vector layer is active, a layer named "SFX" is created automatically.
   The text is placed **centered** (in the active selection if there is one,
   otherwise in the middle of the image) – move/transform it freely afterwards.

---

## Customizing – everything in `config.py`

**Fonts:** the dropdown automatically contains ALL installed system fonts (just
type to search). `SFX_FONTS` is only your favorites list for quick access at the
top of the dropdown – the first entry is the default. To hide all system fonts
and show only favorites: `SHOW_ALL_SYSTEM_FONTS = False`.
```python
SFX_FONTS = [
    "CC Wild Words",        # default
    "My favorite SFX",      # <- new favorite
]
```

**Create presets right in the docker (recommended):**
1. Set font, size, colors and outline.
2. Click **"＋ Save current as preset"** and give it a name.
3. Optionally add keywords (comma-separated) – type such a word into the SFX
   text later and the docker suggests this preset.

Your preset shows up as a button immediately. **Right-click one of your own
presets** for a menu: *Rename*, *Edit keywords*, *Overwrite with current slider
values* or *Delete*. To edit a preset: click the button (loads its values) ->
adjust the controls -> right-click -> *Overwrite with current slider values*.
It is stored in Krita's settings, so it persists across restarts.

**Built-in presets** are edited in the `SFX_PRESETS` block (`config.py`);
`keywords` is optional and drives the mood suggestion:
```python
{
    "name": "Loud",
    "font": "CC Shout Out",
    "size": 160,
    "fill": "#000000",
    "outline": "#ffffff",
    "outline_px": 8,
    "keywords": ["boom", "crash", "bang", "explo"],   # optional
},
```

**Font suggestions (which font[s] suit which SFX word):**
*Font suggestions* section in the docker → **"＋ Add font rule"**:
1. Choose or type a **group** (e.g. `Shout`, `Scared`, `Normal`, `Soft`) – this
   lets you keep several mood variants for the same word. Leave empty = no group.
2. Enter keywords (comma-separated, e.g. `ah, aah`).
3. Choose font(s): a **searchable font dropdown** + "Add" (so you can look names
   up comfortably); the list stays freely editable, so **multiple fonts** via
   commas are possible too.

Example: create four rules for the word `ah` – group *Shout* → a loud font,
*Scared* → a shaky font, *Normal* → the default font, *Soft* → a thin font. Type
`ah` at the top and the suggestions appear **grouped** (a click sets the font).
**Left-click** a rule to edit it, **right-click** for *Edit/Delete*. Stored
permanently.

**Back up / share presets & rules:** at the bottom of the docker, **Export…**
writes your own presets + font rules (incl. groups) to a `.json` file;
**Import…** reads them back – either *Merge* (add to what exists; a preset with
the same name is replaced, exact duplicate rules are skipped) or *Replace*
(overwrite all of your own with the file). Handy for backups or moving between
machines. Built-in presets from `config.py` are not affected.

After editing `config.py`, a **Krita restart** is enough.

---

## What you still do by hand
The plugin sets the text cleanly – the artistic placement stays your job:
- **Position / scale / rotate:** the *Edit Shape* or *Transform* tool (Ctrl+T).
- **Warp / perspective** (fit the SFX to motion/panel): Transform ->
  *Warp*, *Cage* or *Perspective*. Tip: for a strong warp, first right-click the
  SFX layer and *Convert to Paint Layer* (rasterize); it then distorts more
  reliably.
- **Polish:** gradient/glow on the fill or a double outline – as additional
  layer effects. (A basic **drop shadow** is now built in.)

> Performance note: the list of system fonts is read **once and cached**, so the
> docker stays responsive even with very large font collections.

---

## Project layout

| File | Purpose |
| --- | --- |
| `mangasfx/sfx_docker.py` | Docker UI and SFX insertion |
| `mangasfx/svg_builder.py` | Builds the outlined SVG text |
| `mangasfx/presets_store.py` | Loads/saves user presets + font rules |
| `mangasfx/config.py` | Favorite fonts, built-in presets, defaults |
| `mangasfx/i18n.py` | UI translations (English / German) |
| `mangasfx/__init__.py` | Registers the docker with Krita |
| `mangasfx.desktop` | Krita plugin descriptor |
