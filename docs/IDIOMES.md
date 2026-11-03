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

### Pas 3 — API de traduccions (fase 1)
**Què fa:** exposa les traduccions a l'API. Encara no hi ha pantalla.

**Fitxers:**
- `backend/app/routes/traduccions.py` (nou blueprint)
- `backend/app/__init__.py`: registre del blueprint

**Rutes** (les d'escriptura són per als rols `admin` i `editor`, com la resta
d'edicions de fitxes):
| Mètode | Ruta | Descripció |
| ------ | ---- | ---------- |
| GET | `/api/fitxes/:id/traduccions` | Estat per idioma de la versió activa, idiomes marcats i si la IA està disponible |
| PUT | `/api/fitxes/:id/idiomes` | Marcar idiomes `{"idiomes": ["ca","en"]}` |
| GET | `/api/fitxes/:id/versions/:vid/traduccions/:idioma` | Original, traducció desada i, si no n'hi ha, la base de la versió anterior |
| PUT | `/api/fitxes/:id/versions/:vid/traduccions/:idioma` | Desar `{contingut, origen, camps_canviats}`. Torna l'estat a `pendent` |
| POST | `…/traduccions/:idioma/revisar` | Marcar com a revisada (usuari i data) |
| POST | `…/traduccions/:idioma/proposta` | `{"metode": "separar"\|"ia"}`. Retorna una proposta **sense desar-la** |
| GET | `/api/fitxes/:id/pdf/:idioma[?versio_id=]` | PDF de l'idioma (`30150_CA.pdf`) |

**Estats d'un idioma:**
| Estat | Significat |
| ----- | ---------- |
| `falta` | No hi ha cap traducció |
| `desactualitzada` | Hi ha la traducció d'una versió anterior, però no de la versió activa |
| `pendent` | Desada, falta revisar-la |
| `revisada` | Revisada per Qualitat |

**Canvi respecte al pla inicial:** no es copien les traduccions en crear una
versió nova. Hi ha 6 llocs que creen versions (editar, importar, massiu…) i
tocar-los tots era massa invasiu. En lloc d'això, quan s'obre la traducció d'una
versió que no en té, l'API retorna com a `base` la traducció de la versió
anterior, amb la llista de camps on el text original ha canviat. L'usuari la
revisa i la desa. Així **no es modifica cap codi de versions**.

**PDF per idioma:**
- Es genera amb `combinar()`, que posa la traducció sobre el contingut de la
  versió.
- Té el mateix número de revisió i les mateixes dates que el PDF principal.
- Memòria cau: `uploads/{art_codi}/v{n}/{art_codi}_{IDIOMA}_generat.pdf`. Segueix
  el patró `*_generat.pdf`, així les invalidacions que ja existien també
  l'esborren. També s'esborra en desar o revisar la traducció.

**Altres:**
- Les fitxes de producte comercialitzat no es poden traduir: el seu PDF és un
  fitxer pujat.
- Errors de la IA: es retornen com a 502 amb el missatge clar, no com un 500
  genèric.

**Provat en local** amb la fitxa 30150 (marcar idiomes, proposta, desar, PDF,
revisar, resum) i amb una fitxa amb 2 versions (base de la versió anterior). Les
dades de prova s'han esborrat després.

**Tornar enrere:** `git revert <commit del pas 3>`. No toca dades: les traduccions
ja desades es queden a la taula fins que es faci el downgrade del pas 1.

### Pas 4 — Pantalles (fase 1)
**Què fa:** Qualitat ja pot marcar idiomes, traduir, revisar i veure el PDF de cada
idioma des de l'aplicació.

**Fitxers:**
- `frontend/src/components/IdiomesPanel.jsx` (nou): pestanya "Idiomes" del detall.
- `frontend/src/pages/TraduccioFitxa.jsx` (nou): editor de traduccions, ruta
  `/fitxes/:id/traduccio/:idioma` (rols `admin` i `editor`).
- `frontend/src/pages/DetallFitxa.jsx`: pestanya "Idiomes".
- `frontend/src/App.jsx`: ruta nova.
- `frontend/src/api/client.js`:
  - funcions de traduccions;
  - `request()` accepta `timeoutMs`, perquè la IA pot trigar més de 60 s.
- `frontend/src/app.css`: estils `.trad-*` i `.idiomes-panel`.
- `backend/app/services/traduccio.py`: temps màxims de la IA ajustats al límit de
  120 s de Gunicorn (50 s per intent, 1 reintent, `effort: low`).

**Com es fa servir:**
1. Detall de la fitxa → pestanya **Idiomes** → marcar els idiomes en què ha d'estar
   disponible.
2. **Traduir** (o **Editar traducció**) obre l'editor. L'original queda a
   l'esquerra i la traducció a la dreta.
3. Per obtenir una proposta:
   - català i castellà: **Proposar des del bilingüe**;
   - anglès i portuguès: **Traduir amb IA**.

   La proposta no es desa sola. En el cas del bilingüe, els camps dubtosos
   surten marcats en groc.
4. Revisar i corregir → **Desar**. La traducció queda "Pendent de revisar".
5. **Marcar com a revisada**: queda registrat qui ho ha fet i quan.
6. **Veure PDF** obre `{codi}_{IDIOMA}.pdf`.
7. Quan es crea una versió nova de la fitxa, l'idioma passa a "De la versió
   anterior". En obrir l'editor es carrega la traducció anterior, amb els camps
   canviats a l'original marcats en taronja.

A les taules, la columna "Valor" buida vol dir que es fa servir el valor original.

**Provat al navegador** amb la fitxa 30150 i l'usuari de proves: marcar el
català, proposta (2 camps dubtosos), desar, revisar, panell actualitzat, sense
errors a la consola. Les dades de prova s'han esborrat després.

**Tornar enrere:** `git revert <commit del pas 4>` i tornar a compilar el
frontend. Les dades no es veuen afectades.

### Pas 5 — Migració de la fase 2
**Decisió de l'usuari:** en distribuir, els idiomes **es trien a mà**. Per
defecte només surt marcat el PDF principal.

**Què fa:** afegeix la columna `idioma` (opcional) a `distribucio` i a
`enviament_email_item`. El valor `NULL` vol dir PDF principal (`{art_codi}.pdf`),
així que tot l'historial existent continua sent vàlid sense tocar-lo.

**Fitxers:**
- `backend/app/models.py`: `Distribucio.idioma` i `EnviamentEmailItem.idioma`,
  també a `to_dict()`.
- `backend/migrations/versions/d4b9e6f8a013_idioma_a_distribucio_i_correu.py`
  (nova, va després de `c3a8d5e7f912`).

**Desplegament:** `flask db upgrade`.

**Tornar enrere:**
1. **Abans**, cal retirar dels destins els fitxers d'idioma que s'hagin
   distribuït. Si no es fa, després del downgrade aquests registres semblarien
   del PDF principal i podrien confondre Retirar i Comprovar.
2. `flask db downgrade c3a8d5e7f912`.
3. `git revert <commit del pas 5>`.

Provat en local: `upgrade` → `downgrade` → `upgrade`.

### Pas 6 — Distribució per idioma al backend (fase 2)
**Què fa:** permet distribuir, retirar i comprovar el PDF de cada idioma per
separat. Sense paràmetre `idioma`, totes les rutes funcionen exactament com
abans, així que el contracte de l'API no canvia.

**Rutes:**
| Ruta | Canvi |
| ---- | ----- |
| `POST /api/fitxes/:id/distribuir/:desti?idioma=en` | Puja `30150_EN.pdf`. Només si la traducció de la versió activa està **revisada**; si no, retorna 400 amb el motiu i no crea cap registre |
| `POST /api/fitxes/:id/retirar/:desti?idioma=en` | Retira només el fitxer d'aquell idioma |
| `POST /api/fitxes/:id/comprovar` | Comprova també els fitxers d'idioma que consten a l'historial. Cada resultat porta `idioma` |
| `POST /api/fitxes/:id/comprovar/:desti?idioma=en` | Comprova un fitxer d'idioma |

**Fitxers:**
- `backend/app/routes/distribucions.py`:
  - `_nom_amb_idioma`, `_filtre_idioma`, `_traduccio_distribuible` i
    `_assegurar_pdf_idioma` (noves);
  - `idioma` opcional a `_generar_nom_fitxer`, `_referencia_al_desti`,
    `_nom_fitxer_al_desti`, `_assegurar_pdf` i `_destins_amb_fitxa`;
  - `_executar_distribucio` fa servir `dist.idioma`.
- `backend/app/services/verificador.py`: `verificar_distribucio(..., idioma=None)`.
- `backend/app/routes/fitxes.py`: el resum de distribucions de la llista només
  compta el PDF principal.
- `backend/app/routes/jobs.py`: els jobs massius només treballen amb el PDF
  principal.
- `backend/app/services/pdf_parser.py`: la capçalera es llegeix també en català,
  anglès i portuguès ("Data Rev.", "Rev. date", "Check date", "Data verif.").
  Sense això, Comprovar no veuria les dates dels PDF en un sol idioma, inclòs el
  principal amb l'opció "Només català" (pas 0).
- `backend/tests/test_distribucio_idiomes.py` (nou, 19 tests).

**Nom al destí:** el del patró del destí, amb `_{IDIOMA}` abans de l'extensió
(`{art_codi}.pdf` → `30150_EN.pdf`).

**PDF d'idioma:**
- Es genera de nou a cada distribució (la traducció es pot haver corregit), a
  `uploads/{art_codi}/v{n}/{art_codi}_{IDIOMA}.pdf`.
- No es desa a `versio.fitxer_pdf`, que continua sent només el principal.

**Regla clau:** totes les consultes de "l'última distribució d'un destí" filtren
per idioma (`_filtre_idioma`; `NULL` = principal). Així, en retirar o comprovar el
principal mai no s'agafa un fitxer d'idioma, ni al revés. Hi ha tests que
vigilen que cap d'aquestes consultes perdi el filtre.

**Sense canvis:**
- "Distribuir a tots", la distribució massiva i la verificació massiva continuen
  treballant només amb el PDF principal.
- En eliminar una fitxa o la seva última versió, s'esborren dels destins tots els
  fitxers que consten com a `ok`, també els d'idioma. Aquest codi no s'ha tocat,
  perquè ja funcionava així.

**Provat en local** amb un destí "xarxa" temporal apuntant a una carpeta local:
- un idioma sense traducció o amb la traducció pendent es rebutja;
- es pugen `30150.pdf` i `30150_CA.pdf`;
- Comprovar distingeix els dos fitxers;
- en retirar el CA, el principal es queda.

Les dades de prova (destí, registres i traducció) s'han esborrat després.

**Tornar enrere:** `git revert <commit del pas 6>`. Abans, cal retirar els fitxers
d'idioma que s'hagin distribuït (vegeu el pas 5).

---

## Estat i pendents
- [x] Pas 0: "Només català" al PDF principal
- [x] Pas 1: model i migració
- [x] Pas 2: servei de traducció
- [x] Pas 3: API
- [x] Pas 4: pantalles
- [ ] Validació de Qualitat dels títols en anglès i portuguès
  (`backend/app/services/etiquetes_idioma.py`)
- [ ] Vist-i-plau de l'empresa per enviar text a Anthropic i clau `ANTHROPIC_API_KEY`
- [x] Pas 5: migració de la fase 2
- [x] Pas 6: distribució per idioma al backend
- [ ] Fase 2: pantalla de distribució (pas 7) i correu (pas 8)

## Desplegament de la fase 0 + 1 (servidor Ubuntu)
```bash
cd /var/www/fitxes-tecniques
sudo -u www-data git pull
sudo -u www-data backend/venv/bin/pip install -r backend/requirements.txt   # anthropic
cd backend
sudo -u www-data venv/bin/flask db upgrade                                  # fins a d4b9e6f8a013
cd ../frontend
sudo -u www-data npm run build
sudo systemctl restart fitxes-tecniques
```
Opcional (IA): afegir `ANTHROPIC_API_KEY=...` (i, si es vol, `TRADUCCIO_MODEL=...`) a
`backend/.env` i reiniciar.

## Tornar enrere tot el desenvolupament
Els commits estan a la branca `idiomes`, un per pas (vegeu `git log`).
1. Abans del `git pull`/merge a `master`: n'hi ha prou amb no fusionar la branca.
2. Ja desplegat:
   - si hi ha traduccions que es vulguin conservar, fer-ne abans una còpia:
     `pg_dump -t traduccio_versio`;
   - `flask db downgrade b7e3f1a9c2d4`;
   - `git revert` dels commits en ordre invers;
   - build del frontend i restart.
