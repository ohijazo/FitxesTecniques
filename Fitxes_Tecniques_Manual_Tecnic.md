# Manual tècnic — Fitxes Tècniques

**Última revisió:** 2026-06-19
**Responsable:** Oscar Hijazo (ohijazo@agrienergia.com)
**Repositori:** GitHub intern (`FitxesTecniques`)
**Servidor:** `ae01farwebsrv.agrienergia.local` (192.168.11.244) — `/var/www/fitxes-tecniques` (Ubuntu 24.04)
**URL:** http://fitxesfc.agrienergia.local

---

## 1. Descripció funcional

**Fitxes Tècniques** és una aplicació web del departament de **qualitat** per centralitzar la gestió de fitxes tècniques de productes: creació, control de versions, publicació i **distribució automàtica** a destins múltiples (carpeta de xarxa SMB, FTP del proveïdor, futurament SharePoint). Substitueix processos manuals (FTP a mà, Excel, carpetes desordenades).

**Procés que cobreix:**

1. **Editor** crea una fitxa tècnica nova o n'edita una d'existent (estat: esborrany).
2. Defineix tipus de fitxa, seccions i camps dinàmics (multiidioma si cal).
3. Quan està OK, publica una **versió** (immutable). Cada versió genera el PDF i opcionalment Word.
4. Distribueix la versió activa a **destins** configurats:
   - **FTP del proveïdor** (puja `{art_codi}.pdf` amb reintents i backoff).
   - **Carpeta xarxa SMB corporativa**.
   - **SharePoint** (futur via M365).
5. Un **worker background** processa les distribucions; estat visible en temps real.
6. **Audit trail** complet: qui ha fet quin canvi i quan.

**Usuaris finals:** Departament de qualitat (crear/editar) i altres departaments (consultar).

**Rols:** `admin` (configuració + CRUD + usuaris), `editor` (CRUD fitxes + distribuir), `distribuidor` (gestió destins + distribució + jobs), `visualitzador` (només consulta).

**Pantalles clau:**

- `/` — Dashboard amb llista de fitxes + cercador (Ctrl+K).
- `/fitxes/nova` — Crear fitxa.
- `/fitxes/:id` — Detall + historial de versions + estat de distribucions.
- `/admin/destins` — Gestió de destins (FTP, SMB, SharePoint).
- `/admin/audit-log` — Registre de canvis del sistema.
- Pantalla de detall de job — Seguiment en temps real de distribucions massives.

---

## 2. Arquitectura tècnica

**Stack:**

- **Backend:** Python 3.10+ amb Flask 3.1 + SQLAlchemy (ORM).
- **Frontend:** React 19 amb React Router v7 + Vite 8.
- **BD:** PostgreSQL (obligatori; no funciona amb SQLite).
- **Generació PDF:** `xhtml2pdf` (template HTML/Jinja2 → PDF).
- **Distribuïdors:** FTP (`ftplib`), SMB (`smb_distributor.py`), SharePoint (futur via `msal`).
- **Auth:** JWT tokens (local) + MSAL opcional per M365.
- **CSS:** PicoCSS via CDN + estils custom.
- **Servidor web (prod):** Backend `fitxes-tecniques.service` (systemd) rere Apache.

**Diagrama (flux principal):**

```
Usuari (qualitat) navegador
    |
    v
Apache  ->  React (frontend estatic)  +  Backend Flask (API)
                                            |
                                            +-> PostgreSQL local
                                            |     fitxes, versions, distribucions,
                                            |     jobs, destins, audit
                                            |
                                            +-> Worker background
                                            |     genera PDF + distribueix
                                            |
                                            +-> FTP proveidor
                                            +-> SMB carpeta xarxa
                                            +-> SharePoint (futur, via MSAL)
```

**Dependències Python principals:**

| Paquet | Per a què |
|---|---|
| `Flask==3.1.x` | Framework web |
| `SQLAlchemy` | ORM PostgreSQL |
| `Alembic` | Migracions BD |
| `xhtml2pdf==0.2.17` | Generació PDF des de HTML |
| `python-docx` | Lectura/escriptura Word |
| `ftplib` (stdlib) | Distribució FTP |
| `cryptography` (Fernet) | Xifratge credencials FTP/SharePoint |
| `msal` | Autenticació M365 (SharePoint futur) |

**Estructura del repo:**

```
FitxesTecniques/
├── backend/
│   ├── run.py                   # entrypoint (port 50002)
│   ├── config.py                # vars d'entorn
│   ├── requirements.txt
│   └── app/
│       ├── __init__.py          # factory Flask, logging
│       ├── models.py            # 13 models SQLAlchemy
│       ├── auth.py              # decorators @login_required, @rol_requerit
│       ├── routes/              # fitxes, versions, distribucions, admin, auth, jobs, bulk, health
│       └── services/            # pdf_generator, ftp_distributor, smb_distributor, job_worker, crypto, audit
├── frontend/
│   ├── package.json
│   ├── vite.config.js           # proxy /api -> http://localhost:50002
│   └── src/
│       ├── App.jsx
│       ├── pages/               # 26 components (LlistaFitxes, DetallFitxa, AdminDestins, ...)
│       ├── components/          # FitxaForm, DistribuirModal, RichEditor, Toast, BulkActionBar
│       └── api/client.js        # capa HTTP centralitzada
├── migrations/versions/         # 2 migracions Alembic
├── .env.example
├── CLAUDE.md                    # documentació interna
└── DEPLOY_ACTUALITZACIO_2026_06.md
```

---

## 3. Configuració i desplegament

### 3.1 Variables d'entorn (`.env`)

```ini
# BD
DATABASE_URL=postgresql://user:password@localhost:5432/fitxes_tecniques

# Flask
SECRET_KEY=cambiar-aquesta-clau
FLASK_ENV=production              # 'production' obliga SECRET_KEY definit

# FTP (proveidor)
FTP_HOST=farineracoromina.com
FTP_PORT=21
FTP_USER=usuari@farineracoromina.com
FTP_PASSWORD=...
FTP_PATH=/fitxestecniques

# SMB (carpeta xarxa corporativa)
NETWORK_SHARE_PATH=/mnt/qualitat/fitxes

# Logs
LOG_DIR=/var/log/fitxes-tecniques
LOG_LEVEL=INFO

# Xifrat credencials a BD (Fernet)
ENCRYPT_CONFIG_KEY=...            # opcional pero recomanat

# CORS
CORS_ORIGINS=https://fitxesfc.agrienergia.local
```

### 3.2 Desplegament inicial

```bash
# 1. Clonar
sudo -u www-data git clone <repo_url> /var/www/fitxes-tecniques
cd /var/www/fitxes-tecniques

# 2. Backend
sudo -u www-data python3 -m venv backend/venv
sudo -u www-data ./backend/venv/bin/pip install -r backend/requirements.txt

# 3. Frontend (compilar estatics)
sudo -u www-data npm --prefix frontend install
sudo -u www-data npm --prefix frontend run build

# 4. PostgreSQL
sudo -u postgres psql -c "CREATE DATABASE fitxes_tecniques;"
sudo -u postgres psql -c "CREATE USER fitxes_user WITH PASSWORD '...';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE fitxes_tecniques TO fitxes_user;"

# 5. Migracions
sudo -u www-data ./backend/venv/bin/alembic -c backend/alembic.ini upgrade head

# 6. .env amb valors reals (chmod 640)
sudo -u www-data nano /var/www/fitxes-tecniques/.env

# 7. Servei systemd
sudo systemctl enable fitxes-tecniques.service
sudo systemctl start fitxes-tecniques.service
```

Per al detall complet del primer desplegament vegeu `DEPLOY_ACTUALITZACIO_2026_06.md`.

### 3.3 Desplegament d'una actualització

```bash
sudo -u www-data git -C /var/www/fitxes-tecniques pull

# Si hi ha noves dependències Python
sudo -u www-data /var/www/fitxes-tecniques/backend/venv/bin/pip install \
    -r /var/www/fitxes-tecniques/backend/requirements.txt

# Si hi ha noves migracions
sudo -u www-data /var/www/fitxes-tecniques/backend/venv/bin/alembic \
    -c /var/www/fitxes-tecniques/backend/alembic.ini upgrade head

# Si hi ha canvis al frontend
sudo -u www-data npm --prefix /var/www/fitxes-tecniques/frontend run build

sudo systemctl restart fitxes-tecniques.service
sudo systemctl status fitxes-tecniques.service --no-pager
```

### 3.4 Entorns

| Entorn | URL | Servidor | Port | BD |
|---|---|---|---|---|
| Local (dev backend) | http://127.0.0.1:50002 | Portàtil | 50002 | PostgreSQL local |
| Local (dev frontend) | http://127.0.0.1:5173 | Portàtil | 5173 (Vite) | proxy a 50002 |
| Producció | http://fitxesfc.agrienergia.local | `ae01farwebsrv` (192.168.11.244) | Backend a 50002, Apache rere | PostgreSQL local |

---

## 4. Accessos i permisos

### 4.1 Usuari del sistema operatiu

L'app corre com a `www-data`. Tots els fitxers `chown www-data:www-data`. `.env` `chmod 640`.

### 4.2 Rols d'aplicació

| Rol | Pot fer | NO pot fer |
|---|---|---|
| `admin` | Tot (CRUD fitxes, gestió destins, audit, usuaris, estats) | — |
| `editor` | CRUD fitxes, publicar versions, distribuir fitxes | Gestionar destins, usuaris, estats |
| `distribuidor` | Gestionar destins de distribució (`/admin/destins` CRUD), distribuir fitxes (individual o massiu), gestionar jobs (crear, reprendre, cancel·lar, retry-errors, arxivar) | CRUD de fitxes, usuaris, estats |
| `visualitzador` | Consultar fitxes publicades | Editar o distribuir |

### 4.3 Autenticació

JWT amb cookie HttpOnly. Si està habilitat MSAL, opcional login amb compte M365.

### 4.4 Xifratge de credencials a BD

Les credencials de destins (FTP password, SharePoint tokens) es xifren amb **Fernet** (clau definida a `ENCRYPT_CONFIG_KEY`). Si la clau es perd, els destins existents s'han de tornar a configurar.

### 4.5 Accessos a BD

- **PostgreSQL `fitxes_user`** — usuari de l'app, ALL PRIVILEGES sobre la BD pròpia.
- **PostgreSQL `postgres`** (superuser) — només per a migracions inicials i debug.

---

## 5. Base de dades

### 5.1 PostgreSQL (BD pròpia)

Motor: PostgreSQL 14+. Pool: `pool_pre_ping=True, pool_recycle=3600` (re-detecta connexions caigudes en jobs llargs).

**Models principals (13):**

| Model | Propòsit | Camps clau |
|---|---|---|
| `FitxaTecnica` | Fitxa base | `art_codi` (PK), `nom`, `categoria`, `estat` (esborrany/publicada) |
| `VersioFitxa` | Versió immutable | `num_versio`, `fitxer_pdf`, `fitxer_docx`, `activa` |
| `Distribucio` | Registre de cada distribució | `versio_id`, `desti`, `estat` (pendent/ok/error) |
| `JobBulk` | Treball massiu | `estat`, `num_items` |
| `JobItem` | Ítem dins d'un job | `fitxa_id`, `desti_id`, `estat`, `locked_at` |
| `SeccioFitxa`, `CampFitxa` | Definició dinàmica de camps per tipus | — |
| `DestiDistribucio` | Configuració dels destins | `tipus`, `configuracio` (JSON, xifrable) |
| `AuditLog` | Auditoria | `usuari`, `accio`, `target`, `quan` |
| `EstatFitxa`, `RegistreEliminacio` | Estats i registre d'eliminacions | — |

### 5.2 Migracions

Ubicació: `migrations/versions/`. Aplicació amb `alembic upgrade head`.

### 5.3 Versionat de fitxes

Les versions són **immutables**: en lloc d'actualitzar-les, sempre se'n crea una de nova i s'activa. Manté un historial complet.

---

## 6. Integracions externes

### 6.1 FTP del proveïdor

`ftp_distributor.py` puja `{art_codi}.pdf` al directori configurat amb reintents i backoff exponencial. Credencials viuen a la BD xifrades.

### 6.2 SMB (carpeta de xarxa corporativa)

`smb_distributor.py` copia la fitxa a la carpeta muntada (definida per `NETWORK_SHARE_PATH`). Útil per als departaments interns que la consulten via Windows Explorer.

### 6.3 SharePoint (futur)

Pendent d'implementar. Es preveu autenticació via MSAL (OAuth2) i pujada via Microsoft Graph.

### 6.4 SAP Business One (futur)

Pendent. Integració via Service Layer per pujar metadades.

---

## 7. Errors habituals i resolució

| Símptoma | Causa probable | Diagnòstic | Resolució |
|---|---|---|---|
| FTP falla amb "530 Login authentication failed" | Credencials canviades pel proveïdor | Logs del job + `ftp_distributor` | Actualitzar credencials a `/admin/destins` |
| SMB no es publica | Carpeta no muntada al servidor | `mount | grep <ruta>` | Remuntar SMB i reiniciar servei |
| PDF d'una fitxa surt mal renderitzat | Template HTML modificat, classes CSS no suportades per xhtml2pdf | Mirar log del job | Limitar CSS a subset suportat per xhtml2pdf |
| Migració Alembic falla amb "permission denied" | Usuari `fitxes_user` no és propietari | Provar amb `postgres` | Aplicar com a superuser |
| Worker es queda penjat sense processar jobs | Lock orfe per error previ | Mirar `JobItem.locked_at` antic | Restart del servei (`systemctl restart fitxes-tecniques`) |
| Frontend amb 404 a `/api/...` en dev | Vite proxy no apunta al port correcte | `vite.config.js` ha de proxy a `localhost:50002` | Revisar config |
| Audit log buit | `AuditLog` no s'està escrivint | Mirar errors a `app.log` (PG caigut?) | Comprovar BD |

---

## 8. Logs i monitorització

### 8.1 Logs de l'aplicació

| Tipus | Ubicació | Comanda |
|---|---|---|
| Log de l'app (rotat 5×10MB) | `/var/log/fitxes-tecniques/app.log` | `tail -f /var/log/fitxes-tecniques/app.log` |
| Log del servei | systemd journal | `journalctl -u fitxes-tecniques.service -f` |
| Errors | També al journal | `journalctl -u fitxes-tecniques -p err -n 100` |
| Audit log (BD) | Taula `AuditLog` | Consulta SQL amb filtre per `quan` |

**Configuració de logs:**
- Format: `%(asctime)s [%(levelname)s] %(name)s: %(message)s`
- Rotació: `RotatingFileHandler`, 10 MB per fitxer, 5 backups, UTF-8.
- Nivell per defecte: `INFO` (configurable amb `LOG_LEVEL`).

### 8.2 Què mirar primer en cas d'incidència

1. `systemctl status fitxes-tecniques.service`
2. `journalctl -u fitxes-tecniques -n 100`
3. `tail -100 /var/log/fitxes-tecniques/app.log`
4. Estat dels destins: `/admin/destins` (sortida d'errors en background).

### 8.3 Health endpoint

Si existeix `/api/health`, retorna estat de BD + workers actius.

---

## 9. Pla de contingència

### 9.1 Backup de PostgreSQL

```bash
# Cron www-data, cada nit a les 02:30
30 2 * * * pg_dump -h localhost -U postgres -F c -d fitxes_tecniques \
              -f /var/backups/pg/fitxes_tecniques_$(date +\%Y\%m\%d).dump
```

Retenció recomanada: 30 dies.

### 9.2 Backup dels PDFs generats

Els PDFs viuen a la BD (`VersioFitxa.fitxer_pdf` com a `BYTEA`) — entren al `pg_dump` per defecte. Si en alguna versió es decideix moure'ls a disc, s'haurà d'afegir un backup específic d'aquella carpeta.

### 9.3 Restauració

```bash
sudo systemctl stop fitxes-tecniques.service
pg_restore -h localhost -U postgres -d fitxes_tecniques_restored -c \
    /var/backups/pg/fitxes_tecniques_20260619.dump
sudo systemctl start fitxes-tecniques.service
```

### 9.4 Rollback de codi

```bash
sudo -u www-data git -C /var/www/fitxes-tecniques log --oneline -10
sudo -u www-data git -C /var/www/fitxes-tecniques checkout <commit_estable>
# Si cal rebuild de frontend:
sudo -u www-data npm --prefix /var/www/fitxes-tecniques/frontend run build
sudo systemctl restart fitxes-tecniques.service
```

### 9.5 Què fer si el FTP del proveïdor no és accessible

Les distribucions queden en `pendent` o `error` — l'app no es bloqueja. Es poden reintentar manualment des de la UI un cop restablerta la connectivitat. La fitxa queda accessible internament.

---

## 10. Contactes i dependències externes

### 10.1 Contactes interns

| Rol | Nom | Contacte |
|---|---|---|
| Responsable tècnic | Oscar Hijazo | ohijazo@agrienergia.com |
| Responsable funcional (qualitat) | Oscar Hijazo | ohijazo@agrienergia.com |
| IT (servidor `ae01farwebsrv`) | Jordi Coma | jcoma@agrienergia.com |

### 10.2 Dependències externes

| Servei | Proveïdor | Contacte |
|---|---|---|
| FTP del proveïdor (`farineracoromina.com`) | Farinera Coromina | — |
| SharePoint / M365 (futur) | Microsoft | Admin Entra ID intern |
| Hosting (servidor intern) | `ae01farwebsrv.agrienergia.local` (192.168.11.244) | Jordi Coma (jcoma@agrienergia.com) |

### 10.3 Recursos addicionals

- `CLAUDE.md` — Especificacions internes.
- `DEPLOY_ACTUALITZACIO_2026_06.md` — Guia detallada del primer desplegament.
