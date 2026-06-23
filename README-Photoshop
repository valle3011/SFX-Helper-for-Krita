# SFX Helper for Photoshop 2019 (CEP)

A CEP version of the SFX Helper panel for **Photoshop 2019 (v20)** and older
(down to ~CC 2015). It does the same thing as the UXP plugin — type a manga SFX,
get language-aware font suggestions, and insert it as an **editable type layer**
with a **Stroke** (outline) and optional **Drop Shadow** layer effect.

## Why a separate plugin?

Photoshop's modern plugin system (**UXP**) only exists from **PS 2021/2022**
onward; **PS 2019 cannot load UXP plugins at all**. PS 2019 uses the older
**CEP** system (an HTML panel via CEF + an ExtendScript `.jsx` backend). A single
plugin can't span both runtimes, so:

| Plugin | Folder | Photoshop |
|--------|--------|-----------|
| UXP    | `photoshop-sfx-helper/`     | **2022+** |
| CEP    | `photoshop-sfx-helper-cep/` | **2019+** (also runs in newer PS) |

Both share the exact same brain — see below.

## One shared core (no duplicated logic)

The pure logic lives **once** in `sfx-core/` (`rules.js`, `match.js`, `i18n.js`,
`store_core.js`) and is consumed by both plugins. A tiny build copies it in:

```
python sync-core.py        # sfx-core/ -> photoshop-sfx-helper/ and -cep/core/
```

Run it after editing anything in `sfx-core/`. Only the platform-specific parts
differ per plugin:

| Concern | UXP | CEP |
|---------|-----|-----|
| Insert / layer styles | `insert.js` (batchPlay) | `host.jsx` (Action Manager, ES3) |
| Font listing | `app.fonts` (UXP) | `app.fonts` via `host.jsx` |
| Persistence | UXP localFileSystem (`store.js`) | Node `fs` (`store_cep.js`) |
| Panel | UXP DOM (`ui.js`) | CEF DOM (`main.js`) |

The panel (`main.js`) runs in CEF with Node enabled, so it `require()`s the same
core modules. The `.jsx` is ES3 (no `let`/`const`/arrow/`JSON`) and contains
**only** Photoshop actions.

## Install (development)

1. Enable unsigned extensions (PlayerDebugMode) for the matching CSXS version
   (PS 2019 = CSXS 9). In the registry under
   `HKEY_CURRENT_USER\Software\Adobe\CSXS.9` add a string value
   `PlayerDebugMode = 1` (repeat for `CSXS.10`/`CSXS.11` for newer PS).
2. Copy this `photoshop-sfx-helper-cep/` folder into the user extensions dir:
   `%APPDATA%\Adobe\CEP\extensions\`.
3. Restart Photoshop → **Window ▸ Extensions ▸ SFX Helper**.
4. Run `python sync-core.py` first so `core/` is populated.

To distribute, sign the folder as a **`.zxp`** with `ZXPSignCmd` and install it
with a CEP/ZXP installer (e.g. Anastasiy's Extension Manager / ZXP Installer).

### Update / Uninstall

Helper scripts (double-click the `.cmd`, no admin needed):

| Action | File | What it does |
|--------|------|--------------|
| Install | `install_win.cmd` | enables PlayerDebugMode (HKCU) + copies the panel into the CEP extensions folder |
| **Update** | `update_win.cmd` | refreshes the shared core (if `sfx-core/` is present) and reinstalls cleanly — **your presets/rules/learned fonts are kept** (they live in `%APPDATA%\SFXHelperCEP`, outside the extension) |
| **Uninstall** | `uninstall_win.cmd` | removes the panel; asks whether to also delete your saved data; leaves PlayerDebugMode alone |

So updating is just: replace this folder with the new version and run
`update_win.cmd` (or `install_win.cmd` — both do a clean copy). Restart
Photoshop afterwards.

## Requirements

- Photoshop **2019 (v20)** or newer.
- The fonts referenced by the rules must be **installed** to render. Missing
  fonts simply won't appear; pick any installed one.

## Look, View settings & rules

Matches the UXP version and follows **Photoshop's theme**: `main.js` reads the
host's real panel color (`appSkinInfo`) and switches light/dark automatically.

Every section header (▾/▸) collapses/expands (remembered). A **View** section
sets the **UI scale** and **which sections are shown**. **Manage rules** lists
the active rules and lets you **edit (✎) and delete (✕) both your own and the
built-in rules** (deleting/editing a built-in just overrides/hides it; **Restore
built-in rules** brings them back). **Add rule** opens a form (group,
comma-separated keywords/fonts); only the active **Rule language** (plus `*`) is
shown/active.

## Rule packs (import)

Same format as the UXP plugin: **Import** a JSON containing only `font_rules`
and it is merged into your rules (deduped by group + language) without touching
presets/settings. The ready-made `sfx-rules-cyl.json` (repo root) works here too.

## Testing

The shared logic is tested with Node (from `sfx-core/`):

```
node test/logic.test.js
```

These tests cover both plugins (identical core). The Photoshop side
(`host.jsx`, font listing, persistence, the panel) must be verified inside
Photoshop 2019 **and** 2022+.

## Not done / needs verification

- The `host.jsx` Action-Manager descriptors (Stroke = `frameFX` outset, hard
  Drop Shadow, RGB via `Grn`/`Bl`) follow Photoshop's action model and should be
  checked against PS 2019 — some effect keys can differ between versions.
- Type size is applied in **points** (1 pt = 1 px at 72 ppi).
- `CSInterface.js` here is a slimmed-down shim (just `evalScript`,
  `getSystemPath`); replace with Adobe's official `CSInterface.js` if you need
  the full API.
- Color inputs are hex text fields (CEF has no reliable native color picker in
  all PS versions); same choice as the UXP panel.
- `window.cep.fs` dialog signatures vary slightly across CEP versions; verify
  Import/Export on your target.
