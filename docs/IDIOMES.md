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

### Pas 2 — Servei de traducció (fase 1)
**Què fa:** prepara les propostes de traducció. Encara no és visible per a l'usuari
(no hi ha rutes ni pantalla). **No escriu res a la base de dades.**

**Fitxers:**
- `backend/app/services/traduccio.py` (nou)
- `backend/tests/test_traduccio.py` (nou, 14 tests amb textos reals de les fitxes
  30150 i 01921)
- `backend/requirements.txt`: `anthropic>=2.4,<3`

**Camps traduïbles** (constant `CAMPS_TRADUIBLES`):
- textos: denominació jurídica, descripció, origen, ingredients, al·lèrgens, OGM,
  irradiació, organolèptiques, pesticides, presentació, ús previst,
  emmagatzematge, transport, vida útil, legislació, vigència;
- peus de taula (`*_note`);
- taules: la columna `parametre` i, només si cal, el `valor`.

Codi, EAN, denominació comercial, certificació, "fabricat per a" i imatges no es
tradueixen.

**Funcions:**
| Funció | Què fa |
| ------ | ------ |
| `separar_bilingue(contingut, 'ca'\|'es')` | Proposa la part catalana o castellana. Retorna també els camps **dubtosos** |
| `traduir_ia(contingut_es, 'en'\|'pt')` | Proposa la traducció amb Claude a partir del castellà. Retorna `(proposta, error)` i no llança mai excepcions |
| `combinar(contingut_versio, traduccio, idioma)` | Contingut per generar el PDF d'un idioma (no modifica la versió) |
| `camps_canviats(abans, ara)` | Camps traduïbles que han canviat entre dues versions |

**Com separa el bilingüe:** busca la barra amb espai (`" / "`, `"trigo/ Farina"`,
`"sano /⏎Producte"`), però no talla `1999/2/CE`, `ufc/g`, dates ni etiquetes HTML.
Quan hi ha diverses parelles, troba on acaba el català d'una i comença el castellà
de la següent (salt de línia després de punt i seguit de majúscula). Uneix les
línies tallades a mitja frase. Una data sola al final es manté en els dos idiomes.

**Camps marcats com a dubtosos** (cal revisar-los amb atenció):
- no tenen separador (potser ja són monolingües, p.ex. "RD 677/2016…");
- no s'ha trobat on tallar;
- hi ha una data enmig del text (resta d'una importació del Word, p.ex. la 30150
  a "Condicions d'emmagatzematge");
- tenen llistes HTML;
- les marques HTML queden desquadrades;
- un valor de taula està escrit en dues línies (p.ex. Salmonella "No detectado / 25g"
  i "No detectat / 25g").

**IA (anglès i portuguès):**
- Variables d'entorn:
  - `ANTHROPIC_API_KEY` (obligatòria; sense aquesta variable la IA no està disponible);
  - `TRADUCCIO_MODEL` (opcional, per defecte `claude-opus-5-5`).
- La petició fa servir sortida estructurada (JSON schema), així la resposta
  sempre té el format esperat.
- Instruccions al model: no tocar números, unitats, dates ni referències de
  reglaments, mantenir l'HTML i els salts de línia, i al·lèrgens en majúscules.
- **S'envia el text de la fitxa a un servei extern (Anthropic).** Cal el
  vist-i-plau de l'empresa abans d'activar la clau a producció.

**Dependència nova `anthropic`:** és l'SDK oficial. Gestiona reintents i errors
tipificats. L'alternativa sense dependència seria `requests` contra l'API REST,
però caldria reimplementar els reintents i el tractament d'errors. A Ubuntu cal
`pip install -r requirements.txt` dins del venv.

**Tornar enrere:** `git revert <commit del pas 2>`. No hi ha dades afectades.
