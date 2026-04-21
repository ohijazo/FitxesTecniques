# CLAUDE.md — Gestió de Fitxes Tècniques (Quality Docs)

## 1. Projecte

Aplicació web per centralitzar la creació, control de versions i distribució de fitxes tècniques de productes del departament de qualitat.

Substitueix el procés manual actual (carpeta de xarxa, FTP via FileZilla, Excel de versions) per un sistema únic amb control de versions integrat i distribució semiautomàtica als destins configurats.

---

## 2. Problema actual

El departament de qualitat, quan crea o actualitza una fitxa tècnica, ha de:

1. Guardar l'original `.docx` a una carpeta de xarxa
2. Generar un PDF i guardar-lo a la mateixa carpeta
3. Pujar el PDF al FTP via FileZilla, renombrant-lo amb el codi d'article (que conté la mateixa fitxa)
4. Actualitzar manualment un Excel de control de versions
5. (Pendent) Actualitzar SAP Business One quan estigui en producció

Problemes derivats:
- Inconsistències de noms entre destins
- Versions desincronitzades
- Procés manual repetitiu i propens a errors
- Sense historial centralitzat

---

## 3. Objectiu

Sistema web únic on el departament de qualitat:

- Crea i edita fitxes tècniques
- Gestiona versions amb historial de canvis
- Distribueix als destins configurats (carpeta de xarxa, FTP, SAP B1) de forma semiautomàtica o automàtica
- Consulta l'estat de cada distribució

---

## 4. Entorn tècnic

- Servidor aplicació: Ubuntu Server (producció)
- Desenvolupament: Windows 11 + PowerShell
- Autenticació: Microsoft 365 (Azure AD / Entra ID) — SSO corporatiu
- Xarxa corporativa: carpeta de xarxa accessible des del servidor (muntatge SMB)

### FTP
- Host: [PENDENT — configurar]
- Port: [PENDENT]
- Credencials: [PENDENT — variables d'entorn]
- Ruta destí: [PENDENT]
- Nom fitxer: `{art_codi}.pdf` (codi d'article extret de la fitxa)

### SAP Business One
- Versió: [PENDENT — en implementació]
- Integració: [PENDENT — via Service Layer o DI API]
- Estat: futur / opcional en fase inicial

---

## 5. Stack

| Capa          | Tecnologia                        |
| ------------- | --------------------------------- |
| Backend       | Python + Flask + Flask-SQLAlchemy |
| Base de dades | PostgreSQL                        |
| Frontend      | React + React Router + Vite       |
| CSS           | PicoCSS (CDN) + custom CSS        |
| CORS          | Flask-CORS                        |
| Autenticació  | MSAL (Microsoft Authentication Library) |
| Generació PDF | WeasyPrint o LibreOffice headless |
| FTP           | ftplib (Python stdlib) o ftputil  |

---

## 6. Arquitectura

### Desenvolupament

```
frontend (localhost:5173)
    ↓ (Vite proxy /api/*)
backend (localhost:5000)
    ↓
PostgreSQL
```

### Producció

```
Usuaris empresa (navegador)
    ↓
Servidor Ubuntu
    ↓
Frontend React compilat
    ↓
Backend Flask
    ↓
PostgreSQL
    ↓
[Carpeta de xarxa SMB] [FTP] [SAP B1 — futur]
```

---

## 7. Conceptes clau del domini

### Fitxa Tècnica
Document que descriu les característiques tècniques d'un producte. Té:
- **Codi d'article** (`art_codi`): identificador únic, s'utilitza com a nom de fitxer al FTP
- **Nom de producte**
- **Versió**: numèrica (1, 2, 3...) o semàntica (1.0, 1.1...)
- **Contingut**: camps estructurats (a definir per producte/categoria)
- **Estat**: `esborrany` | `publicada` | `obsoleta`

### Versió
Cada canvi significatiu genera una nova versió. S'ha de registrar:
- Número de versió
- Data
- Usuari que l'ha fet
- Descripció del canvi (obligatòria)
- Fitxer PDF generat

### Distribució
Registre de cada enviament a cada destí:
- Destí: `xarxa` | `ftp` | `sap`
- Estat: `pendent` | `ok` | `error`
- Data i hora
- Missatge d'error si n'hi ha

---

## 8. Model de dades

```sql
fitxa_tecnica
  id                SERIAL PK
  art_codi          VARCHAR(50) UNIQUE NOT NULL   -- codi article (nom fitxer FTP)
  nom_producte      VARCHAR(200) NOT NULL
  categoria         VARCHAR(100)
  estat             VARCHAR(20) DEFAULT 'esborrany'
  created_at        TIMESTAMP
  updated_at        TIMESTAMP
  created_by        VARCHAR(100)                  -- usuari M365
```

```sql
versio_fitxa
  id                SERIAL PK
  fitxa_id          FK -> fitxa_tecnica.id
  num_versio        INTEGER NOT NULL
  descripcio_canvi  TEXT NOT NULL
  contingut         JSONB                         -- camps de la fitxa en aquesta versió
  fitxer_docx       VARCHAR(500)                  -- ruta fitxer .docx
  fitxer_pdf        VARCHAR(500)                  -- ruta fitxer .pdf generat
  created_at        TIMESTAMP
  created_by        VARCHAR(100)
  activa            BOOLEAN DEFAULT FALSE          -- és la versió publicada actual
```

```sql
distribucio
  id                SERIAL PK
  versio_id         FK -> versio_fitxa.id
  desti             VARCHAR(20) NOT NULL           -- 'xarxa' | 'ftp' | 'sap'
  estat             VARCHAR(20) DEFAULT 'pendent'  -- 'pendent' | 'ok' | 'error'
  intents           INTEGER DEFAULT 0
  missatge_error    TEXT
  executat_at       TIMESTAMP
  executat_by       VARCHAR(100)
```

```sql
camp_fitxa
  id                SERIAL PK
  categoria         VARCHAR(100)
  nom               VARCHAR(100) NOT NULL
  label             VARCHAR(100) NOT NULL
  tipus             VARCHAR(20) DEFAULT 'text'     -- text | textarea | number | date | select
  obligatori        BOOLEAN DEFAULT FALSE
  ordre             INTEGER
  opcions           JSONB                          -- per tipus 'select'
```

---

## 9. API

### Fitxes

| Mètode | Ruta                              | Descripció                    |
| ------ | --------------------------------- | ----------------------------- |
| GET    | `/api/fitxes`                     | Llistar (paginat + cerca)     |
| GET    | `/api/fitxes/:id`                 | Detall fitxa + versions       |
| POST   | `/api/fitxes`                     | Crear fitxa (v1 esborrany)    |
| PUT    | `/api/fitxes/:id`                 | Editar fitxa (nova versió)    |
| DELETE | `/api/fitxes/:id`                 | Eliminar (si no distribuïda)  |

### Versions

| Mètode | Ruta                                      | Descripció                  |
| ------ | ----------------------------------------- | --------------------------- |
| GET    | `/api/fitxes/:id/versions`                | Historial de versions       |
| GET    | `/api/fitxes/:id/versions/:vid`           | Detall versió               |
| POST   | `/api/fitxes/:id/versions/:vid/publicar`  | Publicar versió             |

### Distribució

| Mètode | Ruta                                         | Descripció                        |
| ------ | -------------------------------------------- | --------------------------------- |
| POST   | `/api/fitxes/:id/distribuir`                 | Distribuir versió activa (tots)   |
| POST   | `/api/fitxes/:id/distribuir/:desti`          | Distribuir a un destí concret     |
| GET    | `/api/fitxes/:id/distribucions`              | Historial distribucions           |

### Fitxers

| Mètode | Ruta                                         | Descripció                  |
| ------ | -------------------------------------------- | --------------------------- |
| GET    | `/api/fitxes/:id/pdf`                        | Descarregar PDF versió activa |
| GET    | `/api/fitxes/:id/docx`                       | Descarregar DOCX original   |

### Admin (camps)

| Mètode         | Ruta                     | Descripció               |
| -------------- | ------------------------ | ------------------------ |
| GET/POST       | `/api/admin/camps`       | Llistar / Crear camps    |
| PUT/DELETE     | `/api/admin/camps/:id`   | Editar / Eliminar camp   |

---

## 10. Rutes frontend

| Ruta                          | Pàgina                         |
| ----------------------------- | ------------------------------ |
| `/`                           | Dashboard / Llista fitxes      |
| `/fitxes/nova`                | Crear fitxa                    |
| `/fitxes/:id`                 | Detall fitxa + historial       |
| `/fitxes/:id/editar`          | Editar / nova versió           |
| `/fitxes/:id/distribuir`      | Panell distribució             |
| `/admin/camps`                | Gestió camps per categoria     |

---

## 11. Flux principal

1. Usuari crea fitxa → s'assigna `art_codi` + v1 en esborrany
2. Emplena contingut (camps dinàmics per categoria)
3. Puja fitxer `.docx` original (opcional)
4. Genera PDF (des de l'app)
5. Publica la versió → estat `publicada`
6. Distribueix: l'app copia a carpeta de xarxa + puja al FTP com `{art_codi}.pdf`
7. Registra resultat de cada distribució
8. Si cal actualitzar: edita → nova versió → repeteix des de pas 3

---

## 12. Generació de PDF

Dues opcions (a decidir):

**Opció A — LibreOffice headless** (si es puja `.docx`)
```bash
libreoffice --headless --convert-to pdf fitxa.docx
```

**Opció B — WeasyPrint** (si es genera des de plantilla HTML/Jinja2)
```python
from weasyprint import HTML
HTML(string=html_content).write_pdf('fitxa.pdf')
```

👉 Decisió pendent. Ambdues funcionen en Ubuntu.

---

## 13. Distribució FTP

```python
import ftplib

def pujar_ftp(pdf_path, art_codi, config):
    with ftplib.FTP(config.host) as ftp:
        ftp.login(config.user, config.password)
        ftp.cwd(config.ruta_desti)
        with open(pdf_path, 'rb') as f:
            ftp.storbinary(f'STOR {art_codi}.pdf', f)
```

El nom del fitxer al FTP és sempre `{art_codi}.pdf`.

---

## 14. Integració SAP B1

**Estat: PENDENT — futur**

Quan s'implementi, caldrà definir:
- Endpoint Service Layer o DI API
- Camp on s'adjunta o referencia la fitxa
- Trigger: automàtic en publicar o manual

No implementar fins que SAP B1 estigui en producció i els requisits siguin clars.

---

## 15. Autenticació M365

- Login via MSAL (Microsoft Authentication Library)
- SSO corporatiu — sense gestió de contrasenyes pròpies
- L'usuari autenticat es registra als camps `created_by` / `executat_by`
- Rols inicials: `qualitat` (CRUD complet) | `consulta` (només lectura)

---

## 16. Estat actual del projecte

- [ ] Definició de requisits (en curs)
- [ ] Model de dades
- [ ] Backend Flask (CRUD fitxes + versions)
- [ ] Generació PDF
- [ ] Distribució FTP
- [ ] Distribució carpeta xarxa
- [ ] Frontend React
- [ ] Autenticació MSAL
- [ ] Deploy Ubuntu
- [ ] Integració SAP B1 (futur)

---

## 17. Estructura de la fitxa tècnica

Basada en la fitxa real del producte (ex: `60360.pdf`). El PDF té **4 pàgines** amb capçalera corporativa a totes.

### Capçalera (totes les pàgines)
| Camp             | Descripció                         |
| ---------------- | ---------------------------------- |
| `rev`            | Número de revisió (ex: `0`, `1`…)  |
| `data_revisio`   | Data de revisió                    |
| `data_comprovacio` | Data de comprovació              |

### Secció 1 — Identificació del producte
| Camp                        | Tipus     | Exemple                                      |
| --------------------------- | --------- | -------------------------------------------- |
| `codi_referencia`           | text      | `60360`  ← és l'`art_codi`, clau del sistema |
| `denominacio_comercial`     | text      | `PBUK PUNJABI ATTA 10 KG`                    |
| `denominacio_juridica`      | text      | `Harina morena de trigo`                     |
| `descripcio`                | textarea  | Descripció lliure del producte               |
| `origen`                    | textarea  | Origen del producte i procedència del cereal |
| `ingredients`               | textarea  | Llistat d'ingredients                        |
| `alergents`                 | textarea  | Alérgenos i traces                           |
| `ogm`                       | textarea  | Declaració OGM (text fix / editable)         |
| `irradiacio`                | textarea  | Declaració irradiació (text fix / editable)  |

### Secció 2 — Característiques
| Camp                         | Tipus     | Observacions                              |
| ---------------------------- | --------- | ----------------------------------------- |
| `caract_organoleptiques`     | textarea  | Color, olor, sabor                        |
| `caract_fisicoquimiques`     | taula     | Paràmetre → Valor (ex: Humedad ≤ 15%)     |
| `caract_reologiques`         | taula     | W, P/L, Índex de caiguda…                 |
| `caract_microbiologiques`    | taula     | Aerobis, fongs, E. coli, Salmonella…      |
| `micotoxines`                | taula     | Aflatoxina B1, OTA, DON, ZEA, HT-2…      |
| `alcaloides_cornezuelo`      | taula     | Alcaloides de cornezuelo µg/kg            |
| `metalls_pesants`            | taula     | Cadmi, Plom mg/kg                         |
| `pesticides`                 | textarea  | Referència reglament (text fix/editable)  |

> Les **taules** tenen estructura dinàmica: llista de files `{parametre, valor, nota?}`.  
> Cada tipus de producte pot tenir diferents paràmetres.

### Secció 3 — Valors nutricionals
Taula estàndard per 100g:
- Valor energètic
- Grasses / De les quals saturades
- Hidrats de carboni / Dels quals sucres
- Proteïna
- Fibra alimentària
- Sal

### Secció 4 — Informació comercial i legal
| Camp                   | Tipus    | Exemple                                    |
| ---------------------- | -------- | ------------------------------------------ |
| `presentacio_envase`   | textarea | Sac de paper 2 capes, 10kg…               |
| `us_previst`           | textarea | Ús industrial, no consumidor final…        |
| `condicions_emmagatzematge` | textarea | Lloc sec, fresc…                      |
| `condicions_transport` | textarea | No requereix Tª regulada                   |
| `vida_util`            | textarea | Consumir preferentment abans de…           |
| `legislacio_aplicable` | textarea | RD 677/2016…                               |
| `fabricat_per`         | text     | Raó social del client (ex: PBUK BALSICAS S.L.) |
| `vigencia_document`    | textarea | Validesa 2 anys a partir de…               |

---

### Notes importants de disseny

- El `codi_referencia` és immutable un cop creat — és l'`art_codi` que s'usa com a nom de fitxer al FTP (`60360.pdf`)
- Les taules de paràmetres (fisicoquímiques, microbiològiques, etc.) han de ser **editables dinàmicament**: afegir/eliminar files
- Alguns camps de text (OGM, irradiació, pesticidas) solen ser **text fix** que rarament canvia — considerar plantilles per defecte editables
- La capçalera del PDF (logo + dades empresa) és sempre la mateixa — no és un camp de la fitxa
- `rev` i les dates de capçalera es gestionen automàticament pel sistema de versions

---

## 18. Pendents crítics a definir

- Plantilla visual del PDF (disseny exacte, logo, colors, maquetació)
- Configuració FTP (host, port, ruta, credencials)
- Ruta carpeta de xarxa (muntatge SMB al servidor Ubuntu)
- Naming convention del `.docx` a la carpeta de xarxa
- Rols i permisos M365 (quins grups/usuaris accedeixen)
- Hi ha altres **categories de producte** amb seccions diferents? (ex: premescles, additius…)

---

## 18. Execució en desenvolupament

### Backend

```powershell
cd backend
venv\Scripts\activate
python run.py
```

### Frontend

```powershell
cd frontend
npm run dev
```

---

## 19. Entorns

### Local
- Windows 11
- PowerShell
- PostgreSQL local

### Producció
- Ubuntu Server
- Flask
- PostgreSQL
- Accés empresa via xarxa corporativa

---

## 20. Preferències

- Idioma: català (UI) / castellà o català (comentaris codi)
- Windows + PowerShell (desenvolupament)
- Deploy Ubuntu (producció)

⚠️ No usar `&&` en comandes

---

# NORMES PER CLAUDE CODE

## Abans de fer canvis

- Analitza el codi existent
- Explica el pla si el canvi és complex
- Fes canvis mínims
- No refactoritzar innecessàriament

---

## Regla principal

👉 NO TRENCAR EL FLUX DE VERSIONS NI EL REGISTRE DE DISTRIBUCIONS

Qualsevol canvi ha de preservar:
- la integritat del historial de versions
- el registre de distribucions (audit trail)
- la traçabilitat de qui ha fet cada acció

---

## Backend

- Respectar Flask actual
- No afegir dependències noves sense justificació
- Evitar migracions destructives
- Les distribucions FTP/xarxa han d'anar en workers/tasques separades, no bloquejar la resposta HTTP

---

## Base de dades

- PostgreSQL obligatori
- No assumir SQLite
- Pensar en producció (Ubuntu)
- Preservar historial: mai eliminar versions ni distribucions, marcar com a `obsoleta` o `error`

---

## Frontend

- Components reutilitzables
- No hardcodejar destins de distribució
- UI en català
- Mostrar sempre l'estat de cada distribució

---

## API

- No trencar contractes existents
- Compatibilitat frontend garantida
- Els errors de distribució (FTP, xarxa) no han de retornar 500 genèric: retornar estat `error` amb missatge

---

## Producció

- Pensar en Ubuntu
- Multiusuari (departament de qualitat + consulta)
- Variables d'entorn per a FTP, rutes, credencials
- Mai hardcodejar credencials

---

## Estil de treball

Sempre indicar:

1. Fitxers afectats
2. Canvis concrets
3. Impacte
4. Riscos

---

## Flux obligatori de treball

Quan es demani qualsevol canvi:

1. NO escriure codi directament
2. Primer fer:
   - resum del problema
   - pla curt (passos)
   - fitxers afectats
   - riscos

3. Esperar confirmació si el canvi és gran. Es considera canvi gran si afecta:
   - models / base de dades
   - lògica de versions
   - lògica de distribució (FTP, xarxa, SAP)
   - autenticació
   - desplegament
   - més de 3 fitxers

4. Implementar només després de confirmació

5. Després d'implementar confirmar:
   - compatibilitat PostgreSQL mantinguda
   - historial de versions intacte
   - distribucions registrades correctament
   - si requereix migració
   - si afecta el desplegament a Ubuntu

⚠️ Si no es segueix aquest flux, la resposta no és vàlida

---

## Anti-errors crítics

Claude ha d'evitar explícitament:

- Sobreescriure versions anteriors (les versions són immutables)
- Eliminar registres de distribució de la BD
- Hardcodejar credencials FTP o rutes de xarxa
- Bloquejar el thread principal amb operacions FTP/SMB lentes
- Fer el codi FTP o de xarxa acoblat al codi de negoci (separar en mòduls)
- Assumir que el codi d'article (`art_codi`) pot canviar (és immutable un cop creat)

---

## Mode revisió

Per qualsevol canvi validar:

- integritat del historial de versions
- registre correcte de distribucions
- compatibilitat PostgreSQL
- compatibilitat frontend
- impacte en producció (Ubuntu)
- simplicitat de la solució
- credencials sempre en variables d'entorn

---

## Regla de mínima intervenció

Sempre prioritzar:

1. Reutilitzar codi existent
2. Modificar el mínim possible
3. Evitar crear nous patrons si ja n'hi ha

❌ No crear noves estructures si ja hi ha una forma establerta

---

## Quan hi ha dubtes

Si falta informació:

- No inventar
- Fer la mínima assumpció possible
- Indicar explícitament què falta (especialment: configuració FTP, rutes SMB, estructura SAP B1)

---

## Dependències

- No afegir noves llibreries sense justificació clara
- Si es proposa una nova dependència:
  - explicar per què és necessària
  - indicar alternatives sense dependència
  - indicar impacte en producció Ubuntu

---

## Anti-sobreenginyeria

Evitar:

- Cues de missatges complexes si no són necessàries
- Microserveis per a operacions simples
- Abstraccions excessives al voltant de FTP/SMB
- Optimitzacions prematures

👉 Preferir sempre la solució més simple que funcioni

---

## Canvis a base de dades

Qualsevol canvi que impliqui:

- noves columnes
- modificació de camps
- migracions

ha de:

1. Explicar impacte en dades existents
2. Indicar si és retrocompatible
3. Evitar pèrdua de dades

⚠️ No aplicar canvis destructius sense avisar explícitament

---

## Validació final obligatòria

Abans de donar un canvi per vàlid, Claude ha de verificar mentalment:

- que el codi compilaria / funcionaria
- que no introdueix errors evidents
- que segueix l'estructura existent del projecte
- que no ha oblidat imports, dependències o connexions
- que les credencials van per variables d'entorn

---

## Filosofia

Sistema centralitzat, traçable i robust per a la gestió documental de qualitat.

👉 Prioritzar integritat de dades, traçabilitat i simplicitat operativa
