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

### Pas 7 — Pantalla de distribució per idioma (fase 2)
**Què fa:** permet triar a mà, en cada distribució, quins PDF d'idioma s'envien.

**Com es fa servir:**
- **Distribuir:**
  - la casella de cada destí és el PDF principal (`30150.pdf`), com fins ara;
  - a la dreta hi ha "Idiomes: CA ES EN PT" amb els idiomes marcats o que
    tenen traducció;
  - per defecte no n'hi ha cap de marcat;
  - els idiomes sense revisar surten desactivats;
  - un ✓ vol dir que aquell fitxer ja és al destí.
- **Historial:** columna nova "Fitxer" (Principal o CA/ES/EN/PT). **Comprovar** i
  **Retirar** de cada fila actuen només sobre aquell fitxer. El modal de retirar
  ho indica ("S'esborrarà el PDF en CA… Els altres fitxers no es toquen").
- **Comprovar destins:** una fila per fitxer, amb una etiqueta d'idioma.

**Fitxers:**
- `frontend/src/pages/DetallFitxa.jsx`:
  - `DistribuirPanel`: selecció d'idiomes;
  - `esJaDistribuit` i `esUltimaOkPerDesti` comparen pel mateix idioma;
  - les comprovacions de l'historial es guarden per destí i idioma.
- `frontend/src/components/RetirarDestiModal.jsx`: prop `idioma`.
- `frontend/src/components/ComprovarDestinsPanel.jsx`: etiqueta d'idioma i
  Retirar per idioma.
- `frontend/src/api/client.js`: `distribuirDesti`, `retirarDesti` i
  `comprovarDesti` accepten `idioma`.
- `frontend/src/app.css`: `.idioma-tag` i `.desti-idiomes`.

**Correcció d'un error que ja hi era:** el panell donava per "Distribuït" un
destí encara que el servidor hagués respost amb `estat: 'error'` (HTTP 200). Ara
es mira l'estat que retorna el servidor.

**Provat al navegador** amb un destí "xarxa" temporal:
- només s'ha marcat el PDF principal + CA, als altres destins no s'hi ha enviat
  res;
- s'han creat `30150.pdf` i `30150_CA.pdf`;
- a l'historial surten dues files;
- el ✓ del CA apareix correctament;
- el modal de retirar indica que es retira el CA;
- la comprovació marca només la fila del CA.

Les dades de prova s'han esborrat després.

**Tornar enrere:** `git revert <commit del pas 7>` i tornar a compilar el
frontend.

### Pas 8 — Correu amb PDFs d'idioma (fase 2)
**Què fa:** el modal "Enviar per correu" té un apartat **"Què s'adjunta"**:
- "PDF principal", marcat per defecte;
- una casella per a cada idioma que tingui revisat almenys una de les fitxes
  seleccionades.

La llista d'adjunts mostra exactament quins PDF sortiran de cada fitxa. D'un
idioma només s'adjunta la traducció revisada. Si una fitxa es quedaria sense cap
adjunt, el modal ho avisa i no deixa enviar.

**API** (`POST /api/enviaments`):
- Camps nous opcionals:
  - `incloure_principal`, per defecte `true`;
  - `idiomes`, per exemple `["ca","en"]`.
- Sense aquests camps funciona com abans (només el principal).
- `/api/enviaments/preparar` retorna `idiomes_revisats` per a cada fitxa.
- El límit `EMAIL_MAX_ADJUNTS` ara compta els PDF, no les fitxes.

**Historial:** cada PDF d'idioma és un `EnviamentEmailItem` amb `idioma` i
`nom_fitxer` (`30150_CA.pdf`). A la pestanya "Correus" del detall surt l'etiqueta
de l'idioma al costat de la revisió.

**Fitxers:**
- `backend/app/routes/enviaments.py`
- `frontend/src/components/EnviarCorreuModal.jsx`
- `frontend/src/pages/DetallFitxa.jsx`: historial de correus
- `frontend/src/app.css`: `.correu-idiomes`

**Provat en local** sense enviar cap correu (la funció d'enviament es va
substituir per una que només anotava els adjunts):
- es rebutja un idioma no revisat i també un enviament sense res a adjuntar;
- amb principal + CA s'adjunten `30150.pdf` i `30150_CA.pdf`, generats
  correctament;
- sense els camps nous s'adjunta només el principal, com abans;
- el modal funciona al navegador.

Les dades de prova s'han esborrat després.

**Tornar enrere:** `git revert <commit del pas 8>` i tornar a compilar el
frontend.

### Pas 9 — Pestanya Contingut en l'idioma triat
**Què fa:** la pestanya "Contingut" del detall té un selector "Veure en":
**Original** (el contingut de la versió, bilingüe) i un botó per a cada idioma que
tingui traducció.
- **Per defecte:** es mostra el **català** si la versió activa en té traducció; si
  no, l'original, com fins ara.
- Les traduccions pendents de revisar també es poden veure. Porten un `*` al botó
  i un avís a sobre del document.
- Només és visualització: no canvia dades ni el PDF principal.

**Fitxers:**
- `frontend/src/pages/DetallFitxa.jsx`: component `ContingutIdioma`.
- `frontend/src/components/IdiomesPanel.jsx`: `combinarTraduccio()`, la mateixa
  regla que `combinar()` del backend.
- `frontend/src/app.css`: `.contingut-idiomes`.

**Limitació:** en anglès i portuguès el contingut surt traduït, però els títols de
la vista web continuen bilingües (el diccionari de títols només és al backend). El
PDF de l'idioma sí que surt amb els títols traduïts.

**Desplegament:** `git pull`, `npm run build`. No cal migració ni reiniciar el
backend.

**Tornar enrere:** `git revert <commit del pas 9>` i tornar a compilar el
frontend.

## Fase 3 — Historial de traduccions i actualització automàtica

**Decisions de l'usuari:**
- Quan es modifica l'original (versió nova), les traduccions dels idiomes marcats
  **s'actualitzen soles** en desar:
  - els camps que no han canviat es copien;
  - els camps canviats es tornen a proposar, amb IA en el cas de l'anglès i el
    portuguès;
  - la traducció queda "Pendent de revisar".
- Cada traducció té un **historial complet**. A cada distribució i correu queda
  guardada la còpia exacta que es va enviar.

### Pas 10 — Model i migració de l'historial
**Què fa:**
- Taula nova `traduccio_historial`, on només s'afegeixen registres. Cada registre
  és una còpia completa de la traducció: `traduccio_id`, `versio_id`, `idioma`,
  `contingut`, `estat`, `origen`, `accio` (`desada` | `revisada` | `automatica`),
  `camps_canviats`, `created_at` i `created_by`.
- Columna `traduccio_historial_id` (opcional) a `distribucio` i a
  `enviament_email_item`.

No té claus foranes a propòsit: l'historial ha de sobreviure encara que
s'esborri una versió, com ja passa amb els correus.

**Fitxers:**
- `backend/app/models.py`: `TraduccioHistorial`, i les columnes noves també a
  `to_dict()`.
- `backend/migrations/versions/e5c1a7b3d924_historial_de_traduccions.py` (nova,
  va després de `d4b9e6f8a013`).

**Impacte:** additiva i retrocompatible. Els registres anteriors queden sense
còpia associada.

**Desplegament:** `flask db upgrade`.

**Tornar enrere:**
1. `flask db downgrade d4b9e6f8a013`. **Esborra l'historial de traduccions**: si ja
   s'ha fet servir, cal fer-ne abans una còpia amb
   `pg_dump -t traduccio_historial`.
2. `git revert <commit del pas 10>`.

Provat en local: `upgrade` → `downgrade` → `upgrade`.

### Pas 11 — Historial de traduccions al backend
**Què fa:**
- **Cada vegada que es desa o es revisa una traducció**, se'n guarda una còpia
  completa a `traduccio_historial` (accions `desada` i `revisada`). Les còpies
  no es modifiquen ni s'esborren mai des de l'aplicació.
- **Cada distribució d'un PDF d'idioma i cada adjunt d'idioma d'un correu**
  guarden en `traduccio_historial_id` la còpia exacta que es va enviar. Així
  es pot saber què deia el PDF en anglès que es va enviar al client el dia X.
- **Traduccions anteriors a l'historial:** quan s'envien, es crea abans una
  còpia `inicial`, perquè el que s'envia quedi sempre registrat.

**Rutes noves** (només lectura; hi té accés qualsevol usuari amb sessió):
| Ruta | Descripció |
| ---- | ---------- |
| `GET /api/fitxes/:id/traduccions/:idioma/historial` | Totes les còpies d'aquell idioma, de totes les versions, amb on s'ha enviat cada còpia (distribucions i correus que van acabar bé) |
| `GET /api/fitxes/:id/traduccions/historial/:hid` | Contingut d'una còpia |
| `GET /api/fitxes/:id/traduccions/historial/:hid/pdf` | PDF tal com era aquella còpia, amb la Rev. i les dates de la seva versió |

**Fitxers:**
- `backend/app/models.py`: `TraduccioVersio.desar_historial()` i `ultima_copia()`.
- `backend/app/routes/traduccions.py`:
  - desar i revisar registren una còpia;
  - rutes d'historial;
  - `_generar_pdf_traduccio()`, compartit pel PDF actual i pel de les còpies.
- `backend/app/routes/distribucions.py` i `backend/app/routes/enviaments.py`:
  guarden `traduccio_historial_id`.

**Provat en local** amb la fitxa 60360 i dades temporals:
- desar → revisar → corregir → revisar genera 4 còpies;
- la distribució i el correu apunten a l'última revisada;
- la còpia antiga conserva el text anterior i en genera el PDF;
- una còpia d'una altra fitxa retorna 404.

Les dades de prova s'han esborrat després.

**Tornar enrere:** `git revert <commit del pas 11>`. Les còpies que ja s'hagin
desat es queden a la taula.

### Pas 12 — Proveïdors de traducció (Microsoft o Claude)
**Per què:** a l'empresa es fa servir Copilot (Microsoft). Microsoft 365 Copilot
**no té una clau d'API** per fer-lo servir des d'una aplicació:
- La seva Chat API només funciona en nom d'un usuari amb llicència de Copilot
  que hagi iniciat sessió, i no la pot cridar un servidor pel seu compte.
- Demana permisos de lectura de correu, Teams i SharePoint.
- Està en *preview*.

La via de Microsoft amb clau és **Azure**: els mateixos models a **Azure OpenAI**,
o el servei **Azure AI Translator**. Sistemes ha de decidir què pot donar; per
això el codi admet tots dos, i també Claude, i es tria per configuració.

**Configuració** (`backend/.env`):
```
TRADUCCIO_PROVEIDOR=azure_openai        # o azure_translator, o anthropic

# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://<recurs>.openai.azure.com
AZURE_OPENAI_KEY=...
AZURE_OPENAI_DEPLOYMENT=<nom del deployment del model>
AZURE_OPENAI_API_VERSION=2024-10-21     # opcional

# Azure AI Translator
AZURE_TRANSLATOR_KEY=...
AZURE_TRANSLATOR_REGION=westeurope      # la regió del recurs
AZURE_TRANSLATOR_ENDPOINT=...           # opcional (per defecte, el global)

# Claude (opcional, desactivat per defecte)
ANTHROPIC_API_KEY=...
TRADUCCIO_MODEL=claude-opus-5-5         # opcional
```
- Sense cap proveïdor complet, la traducció automàtica no està disponible i es
  tradueix a mà.
- Per compatibilitat, si no hi ha `TRADUCCIO_PROVEIDOR` però sí `ANTHROPIC_API_KEY`,
  es fa servir Claude.

**Què ha canviat:**
- **Idioma d'origen.** Abans sempre era el castellà. Ara depèn de com està escrit
  l'original (`_idioma` de la versió):
  - **bilingüe:** el català i el castellà es **separen**; l'anglès i el
    portuguès es tradueixen del castellà;
  - **només castellà:** el castellà **es copia**; la resta es tradueix del
    castellà;
  - **només català** (cas de la 30150): el català **es copia**; el castellà,
    l'anglès i el portuguès es tradueixen del català.

  Si existeix la traducció de l'idioma d'origen, es fa servir com a font.
- **Azure OpenAI:** rep les mateixes instruccions que Claude (reglaments,
  al·lèrgens en majúscules, HTML) i fa servir sortida estructurada.
- **Azure AI Translator:** tradueix literal, sense instruccions. Manté l'HTML, i
  els salts de línia es conserven passant-los a `<br>`. Per al portuguès fa
  servir `pt-pt` (de Portugal).
- **Errors:** sempre retornen un missatge clar (clau no vàlida, servei saturat,
  temps esgotat, filtre de contingut…), amb un sol reintent per als errors
  temporals. Cada intent té un temps màxim de 50 s, perquè Gunicorn talla als
  120 s.
- `traduir_ia(..., camps=[...])` permet traduir només uns camps concrets. Ho farà
  servir l'actualització automàtica.
- A l'editor, el botó s'adapta a l'original: "Proposar des del bilingüe",
  "Copiar de l'original" o "Traduir amb IA".

**Fitxers:**
- `backend/app/services/traduccio.py`
- `backend/app/routes/traduccions.py`: `idioma_original()` i `font_traduccio()`
- `frontend/src/pages/TraduccioFitxa.jsx`
- `backend/tests/test_traduccio.py`: tests nous d'Azure OpenAI (petició i clau
  incorrecta), d'Azure AI Translator (salts de línia, `pt-pt`, regió), de la
  traducció de només uns camps i de la configuració incompleta. Totes les
  respostes són simulades.

**No provat amb els serveis reals:** encara no hi ha claus d'Azure. Quan
sistemes les doni, cal fer una prova real abans d'activar-ho a producció.

**Tornar enrere:** `git revert <commit del pas 12>`.

### Pas 13 — Actualització automàtica de les traduccions
**Què fa:** quan es desa una **versió nova** d'una fitxa amb idiomes marcats,
per a cada idioma que ja tenia traducció en una versió anterior es crea sol la
traducció de la versió nova:
- **Camps que no han canviat** a l'original: es copien de la traducció anterior.
- **Camps canviats:**
  - si l'original ja és en aquest idioma, es copien;
  - si l'original és bilingüe i l'idioma és el català o el castellà, se
    separen;
  - en la resta de casos, es tradueixen amb el proveïdor configurat (pas 12).
    Només s'envien a traduir els camps canviats.
- **Si no es poden traduir** (no hi ha proveïdor o el servei dona error), els
  camps conserven el text anterior i la traducció queda amb origen "de la
  versió anterior" (`copiada`). Al log del servidor s'escriu el motiu.
- La traducció queda **"Pendent de revisar"**, amb els camps canviats marcats
  en taronja a l'editor, i se'n desa una còpia a l'historial (acció
  `automatica`). No es pot distribuir fins que Qualitat la revisa.
- Els idiomes que mai no s'han traduït no es creen sols: es fan des de
  l'editor.
- Primer es fa l'idioma d'origen (el castellà, o el català si l'original és en
  català), perquè els altres en parteixin.

**Com s'engega:**
- La creació de versions **no es modifica**. Un escoltador de SQLAlchemy
  (`after_insert` de `VersioFitxa` + `after_commit`) detecta les versions noves
  vingui d'on vingui (editar, importar, editar en massa…). Quan la transacció
  ja està confirmada, llança un **fil de fons**, com fa l'enviament de correus,
  així que l'usuari no ha d'esperar.
- **Si l'usuari crea la traducció abans que el fil**, es respecta la seva
  (restricció única).
- **Si el fil falla**, la versió no se'n ressent. L'error queda al log i l'editor
  continua oferint la traducció anterior com a punt de partida.
- **Desactivable** amb `TRADUCCIO_AUTOMATICA=0` al `.env`.

**Fitxers:**
- `backend/app/services/traduccio_auto.py` (nou)
- `backend/app/__init__.py`: registre de l'escoltador; no s'activa en mode
  `TESTING`
- `backend/app/routes/traduccions.py`: nou origen `automatica`
- `frontend/src/pages/TraduccioFitxa.jsx`: text "actualitzada automàticament"
- `backend/tests/test_traduccio.py`

**Provat en local** amb la fitxa 60360, amb traduccions CA i EN revisades:
- **Versió nova canviant els ingredients, sense proveïdor:**
  - el CA s'ha actualitzat sol separant el bilingüe; la resta de camps s'ha
    copiat;
  - l'EN ha conservat el text anterior (`copiada`);
  - totes dues han quedat pendents, amb `ingredients` marcat.
- **Versió nova canviant l'origen, amb Azure Translator simulat:** només s'ha
  enviat a traduir el camp `origen`, del castellà a l'anglès.
- Tot s'ha restaurat al final: versió activa, estat de la fitxa i traduccions.

**Riscos:**
- Cada procés de Gunicorn té el seu escoltador. Si el servei es reinicia enmig
  d'una actualització, aquella traducció no es crea, però l'editor ofereix la
  base de la versió anterior com fins ara.
- Una edició en massa sobre moltes fitxes amb idiomes marcats fa una crida al
  proveïdor per fitxa i idioma, d'una en una.

**Tornar enrere:** `git revert <commit del pas 13>` i reiniciar el servei. També
es pot desactivar sense tocar codi amb `TRADUCCIO_AUTOMATICA=0`.

### Pas 14 — Pantalla de l'historial
**Què fa:** a l'editor de traduccions, a sota de tot, hi ha l'apartat
desplegable **"Historial de la traducció"**. Mostra totes les còpies d'aquell
idioma, de totes les versions de la fitxa, amb aquestes columnes:
- data;
- Rev.;
- acció ("Desada", "Revisada", "Actualitzada automàticament" o "Còpia
  inicial"), amb el nombre de camps que havien canviat a l'original;
- usuari;
- on s'ha enviat (destins i correus);
- un botó **Veure PDF**, que genera el PDF tal com era aquella còpia.

**Fitxers:**
- `frontend/src/pages/TraduccioFitxa.jsx`: component `HistorialTraduccio`.
- `frontend/src/components/IdiomesPanel.jsx`: `obrirPdf(url)` reutilitzable.
- `frontend/src/api/client.js`: `historialTraduccio`.
- `frontend/src/app.css`: `.trad-historial`.

**Provat al navegador** amb una traducció temporal de la 60360 (desada +
revisada): l'historial mostra les dues còpies i el PDF de la còpia antiga es
genera i s'obre. Les dades temporals s'han esborrat després.

**Tornar enrere:** `git revert <commit del pas 14>` i tornar a compilar el
frontend.

### Pas 15 — Vista prèvia del PDF en l'idioma triat
**Què fa:**
- **"Vista prèvia PDF"** obre el PDF en el mateix idioma que la pestanya
  Contingut: per defecte el català si la versió activa en té traducció, i si
  no, l'original bilingüe.
- **A dalt de la vista prèvia** hi ha els botons "Veure en: Original / Català /
  …" per canviar d'idioma sense sortir-ne.
- **L'idioma és compartit:** si es canvia a la vista prèvia, la pestanya
  Contingut també el fa servir, i al revés.
- **Sense canvis:**
  - La vista prèvia de versions antigues (pestanya Versions) sempre mostra
    l'original.
  - "Descarregar PDF" continua descarregant el PDF principal.

**Fitxers:**
- `frontend/src/pages/DetallFitxa.jsx`:
  - component `SelectorIdioma`, compartit;
  - `idiomaVista` i `idiomesTrad` passen a la pàgina;
  - `vistaPrevia(versioId, idioma)` crida `/pdf/:idioma` quan no és l'original.

**Provat al navegador** amb la 30150:
- la vista prèvia s'obre en català (`/pdf/ca`);
- en canviar a "Original" carrega el bilingüe (`/pdf`);
- en tancar, la pestanya Contingut es queda en "Original";
- no hi ha errors a la consola.

**Desplegament:** `git pull` i `npm run build`. No cal migració ni reiniciar.

**Tornar enrere:** `git revert <commit del pas 15>` i tornar a compilar el
frontend.

---

## Estat i pendents
- [x] Pas 0: "Només català" al PDF principal
- [x] Pas 1: model i migració
- [x] Pas 2: servei de traducció
- [x] Pas 3: API
- [x] Pas 4: pantalles
- [ ] Validació de Qualitat dels títols en anglès i portuguès
  (`backend/app/services/etiquetes_idioma.py`)
- [ ] Sistemes: decidir proveïdor (Azure OpenAI o Azure AI Translator) i donar-ne la clau
- [x] Pas 5: migració de la fase 2
- [x] Pas 6: distribució per idioma al backend
- [x] Pas 7: pantalla de distribució per idioma
- [x] Pas 8: correu amb PDFs d'idioma
- [x] Pas 9: pestanya Contingut en l'idioma triat (català per defecte)
- [x] Pas 10: model i migració de l'historial
- [x] Pas 11: historial de traduccions al backend
- [x] Pas 12: proveïdors de traducció (Azure OpenAI, Azure AI Translator, Claude)
- [x] Pas 13: actualització automàtica en crear una versió
- [x] Pas 14: pantalla de l'historial
- [x] Pas 15: vista prèvia del PDF en l'idioma triat

## Desplegament de la fase 0 + 1 (servidor Ubuntu)
```bash
cd /var/www/fitxes-tecniques
sudo -u www-data git pull
sudo -u www-data backend/venv/bin/pip install -r backend/requirements.txt   # anthropic
cd backend
sudo -u www-data venv/bin/flask db upgrade                                  # fins a e5c1a7b3d924
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
