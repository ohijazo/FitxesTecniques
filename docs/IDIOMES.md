# Fitxes tècniques en diversos idiomes

Document de treball de la funcionalitat d'idiomes (ca, es, en, pt).
Cada pas es desa en un commit propi a la branca `idiomes`, perquè es pugui
desfer per separat.

## Objectiu
- Poder deixar el PDF principal d'una fitxa (`{art_codi}.pdf`) **només en català**
  (cas de la fitxa 30150), a més de bilingüe o només en castellà.
- Que Qualitat pugui marcar, per a cada fitxa, en quins idiomes ha d'estar
  disponible (català, castellà, anglès, portuguès). Cada idioma marcat genera
  un PDF propi: `30150_CA.pdf`, `30150_EN.pdf`…
- Fer les traduccions de manera àgil:
  - català i castellà: es proposen separant el text bilingüe actual
    ("castellà / català");
  - anglès i portuguès: es proposen amb IA a partir del castellà;
  - en tots els casos Qualitat ho revisa abans que quedi disponible.

## Decisions
| Tema | Decisió |
| ---- | ------- |
| Idiomes | ca, es, en, pt |
| PDF principal `{art_codi}.pdf` | Es manté com ara: bilingüe per defecte; selector "Idioma del document" per deixar-lo només en castellà o només en català |
| PDFs per idioma | Un per idioma marcat, `{art_codi}_{IDIOMA}.pdf` |
| Traduir crea revisió nova? | **No.** La traducció va lligada a la versió i té estat propi (`pendent` / `revisada`) |
| Títols en/pt | Diccionari a `backend/app/services/etiquetes_idioma.py` (cal validació de Qualitat) |

## Fases
- **Fase 0** — opció "Només català" al PDF principal. Sense migració.
- **Fase 1** — idiomes per fitxa, traduccions per versió, editor de traduccions i
  descàrrega del PDF per idioma. Migració additiva.
- **Fase 2** — distribució als destins i enviament per correu dels PDFs per
  idioma (pendent; es farà quan la fase 1 estigui validada).

---

## Registre de passos

### Pas 0 — Opció "Només català" (fase 0)
**Què fa:** el selector "Idioma del document" del formulari té una tercera opció,
"Només català". Amb aquesta opció tots els títols de la fitxa (formulari i PDF)
surten només en català, incloent-hi la capçalera ("FITXA TÈCNICA", "Data Rev.",
"Data Comprov.").

**Fitxers:**
- `backend/app/services/etiquetes_idioma.py` (nou): `titol_idioma(text, idioma)` i
  diccionari de títols. Substitueix el filtre `bil` que hi havia dins de
  `pdf_generator.py`.
- `backend/app/services/pdf_generator.py`: el filtre `bil` crida `titol_idioma`.
- `backend/app/templates/fitxa_tecnica.html`: la capçalera, "OGM" i "Valor"
  també passen pel filtre `bil`.
- `frontend/src/components/FitxaForm.jsx`: `bil()`, `PdfPageHeader` i
  `IdiomaSelector` amb l'opció `ca`.
- `backend/tests/test_etiquetes_idioma.py` (nou).

**Dades:** cap canvi. El valor es desa a `contingut._idioma` (ja existent) en
desar la fitxa, i això crea una versió nova com qualsevol altra edició.

**Com aplicar-ho a la fitxa 30150:** editar la fitxa → "Idioma del document" →
"Només català" → Desar (nova versió) → publicar i distribuir com sempre.

**Desplegament:** `git pull`, build del frontend i restart del servei. Sense migració.

**Tornar enrere:** `git revert <commit del pas 0>`. Les fitxes que s'hagin desat
amb "Només català" tornarien a sortir bilingües (el codi antic tracta qualsevol
valor diferent de `es` com a bilingüe); no es perd cap dada.

### Pas 1 — Model i migració (fase 1)
**Què fa:** prepara la base de dades per als idiomes. Encara no hi ha cap canvi
visible per a l'usuari.

**Fitxers:**
- `backend/app/models.py`:
  - `FitxaTecnica.idiomes` (JSON, per defecte `[]`), que també surt a `to_dict()`;
  - model nou `TraduccioVersio`.
- `backend/migrations/versions/c3a8d5e7f912_idiomes_i_traduccions.py` (nova).

**Taula `traduccio_versio`:**
| Camp | Descripció |
| ---- | ---------- |
| `versio_id` | Versió traduïda (FK amb `ON DELETE CASCADE`) |
| `idioma` | `ca`, `es`, `en` o `pt` (una sola traducció per versió i idioma) |
| `contingut` | Només els camps traduïbles; la resta surt de la versió |
| `estat` | `pendent` o `revisada` |
| `origen` | `separat`, `ia`, `manual` o `copiada` |
| `camps_canviats` | Camps on el text font ha canviat respecte la versió anterior |
| `created_*`, `updated_*`, `revisat_*` | Traçabilitat de qui ha fet què |

**Impacte en dades:** additiva i retrocompatible. Les fitxes existents tenen
`idiomes = []` (com fins ara: només PDF principal). Les versions continuen sent
immutables: la traducció mai no modifica `versio_fitxa.contingut`.

`ON DELETE CASCADE` fa que els esborrats de fitxes i versions que ja existien
continuïn funcionant sense canvis (s'emporten les seves traduccions).

**Desplegament:** `flask db upgrade` (abans del restart).

**Tornar enrere:**
1. `flask db downgrade` (torna a `b7e3f1a9c2d4`). **Esborra les traduccions desades i
   les marques d'idioma**: si ja s'han fet servir, cal fer-ne abans una còpia
   (`pg_dump -t traduccio_versio`).
2. `git revert <commit del pas 1>`.

Provat en local: `upgrade` → `downgrade` → `upgrade` sense errors.
