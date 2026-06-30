# Guia d'actualització a producció — Juny 2026

**Servidor:** `ae01farwebsrv` (192.168.x.244) — `fitxesfc.agrienergia.local`
**App:** Fitxes Tècniques (qualitat, Farinera Coromina)
**Stack:** Ubuntu + Apache + Gunicorn:50002 + PostgreSQL
**Data prevista:** setmana del 8-12 de juny 2026

---

## 0. Resum del que canvia

Aquesta actualització recull totes les millores fetes des de la versió en producció actual. Els canvis més importants:

### Funcionalitats noves
- **Autosave d'esborranys** al formulari de fitxa (recuperació si es perd la connexió).
- **Cerca global** amb `Ctrl+K` / `Cmd+K`.
- **Diff lliure** entre versions no consecutives.
- **Exportació a Excel** del llistat de fitxes.
- **Cancel·lació de jobs** massius en curs.
- **Reintentar només els items en error** d'un job (sense reprocessar els ok).
- **Notificacions** del navegador quan acaba un job llarg.
- **Banner offline** quan cau la xarxa.
- **Audit log** de canvis de configuració (destins, estats).
- **Health endpoint** `/api/health` per monitorització.
- **Selecció de tots els filtrats** al llistat (per a operacions massives).
- **Última distribució visible** al llistat.

### Millores de seguretat i robustesa
- `SECRET_KEY` obligatòria en producció (l'app no arrencarà si és la del default).
- Credencials FTP/SharePoint **xifrades a BD** (opcional, recomanat).
- Validació de mida i tipus dels uploads (Word 20MB, imatges 5MB).
- Validació endurida del codi d'article (`art_codi`).
- Logging estructurat als distribuïdors (FTP/SMB/SharePoint).
- Reintents amb backoff a FTP per errors transitoris.
- Logs rotatius a fitxer (opcional, recomanat).
- Backoff i recuperació millor del worker.

### Millores de rendiment
- Llistat de fitxes: ~60+ queries reduïdes a 4 (N+1 eliminat).
- Generació de PDF refactoritzada: una versió genera el PDF un cop, reutilitzat per a totes les distribucions consecutives.

---

## 1. Pre-deploy (fer durant la setmana, abans del dia D)

### 1.1 Verificar que el codi local funciona

A la teva màquina Windows:

```powershell
cd P:\FitxesTecniques\backend
.\venv\Scripts\activate
python run.py
```

I en una altra terminal:

```powershell
cd P:\FitxesTecniques\frontend
npm run dev
```

Obre `http://localhost:5173`, fes login, prova:
- Crear una fitxa.
- Editar i veure el banner d'autosave.
- Cercar amb `Ctrl+K`.
- Veure el llistat (data d'última distribució a la columna).
- Anar a *Configuració → Audit log*.

Si tot va bé, estàs llest per al deploy.

### 1.2 Decidir si activaràs l'**encriptació de credencials**

És **opcional** però recomanat. Si l'actives:

```powershell
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Et donarà una clau com `aBcDeF1234...XyZ=`. **Apunta-la a un gestor de secrets fiable** (KeePass, gestor corporatiu, etc.). Si la perds, les credencials xifrades a la BD no es podran recuperar mai més.

Si **NO** l'actives ara: cap problema, el codi continua funcionant com abans amb els secrets en clar. La podràs activar més endavant.

### 1.3 Verificar `SECRET_KEY` actual del servidor

> ⚠️ **Important.** A partir d'aquesta versió, si `FLASK_ENV=production` i `SECRET_KEY` no està definida (o val `'dev-secret-key'`), **l'app no arrencarà**.

SSH al servidor i comprova:

```bash
ssh sysadmin@ae01farwebsrv
sudo grep SECRET_KEY /var/www/fitxes-tecniques/backend/.env
```

- Si veus `SECRET_KEY=<algun_valor_real_llarg>` → tot OK.
- Si **no veus la línia** o val `dev-secret-key` → generar-la abans del deploy:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(64))"
```

I afegir-la a `.env` (veure pas 3.4).

### 1.4 Programar la finestra de manteniment

- Idealment dilluns o dimarts al matí (no divendres a la tarda).
- Avisa qualitat de **finestra de ~10 minuts** sense disponibilitat.
- Estima total: ~20-30 min incloent verificacions.

---

## 2. Backup abans del deploy (dia D, primer pas)

> Cap pas de l'actualització és destructiu, però **sempre backup primer**.

### 2.1 Backup BD

```bash
ssh sysadmin@ae01farwebsrv
sudo -u postgres pg_dump -Fc fitxes_tecniques > /backups/fitxes_pre_deploy_$(date +%Y%m%d_%H%M).dump
ls -lh /backups/fitxes_pre_deploy_*.dump  # comprovar que té mida raonable (>1MB)
```

### 2.2 Backup d'uploads (PDFs i imatges)

```bash
sudo tar czf /backups/fitxes_uploads_$(date +%Y%m%d_%H%M).tar.gz -C /var/www/fitxes-tecniques/backend uploads/
ls -lh /backups/fitxes_uploads_*.tar.gz
```

### 2.3 Apuntar la versió actual

```bash
cd /var/www/fitxes-tecniques
sudo -u www-data git log -1 --oneline
# Apunta aquest hash en algun lloc — el necessitaràs per al rollback
```

---

## 3. Deploy (dia D, finestra de manteniment)

### 3.1 Avisar usuaris

Si tens cap canal d'avís (mail, Teams) — "Manteniment Fitxes Tècniques, 10 min, tornem aviat".

### 3.2 Aturar el servei

```bash
sudo systemctl stop fitxes-tecniques
sudo systemctl status fitxes-tecniques  # ha de dir 'inactive (dead)'
```

### 3.3 Actualitzar el codi

```bash
cd /var/www/fitxes-tecniques
sudo -u www-data git fetch origin
sudo -u www-data git pull origin master
# Apunta el nou hash:
sudo -u www-data git log -1 --oneline
```

### 3.4 Actualitzar variables d'entorn

Edita `.env`:

```bash
sudo -u www-data nano /var/www/fitxes-tecniques/backend/.env
```

**Obligatori verificar:**
- `SECRET_KEY=...` ha d'existir i tenir un valor real (no `dev-secret-key`).

**Afegir (recomanat):**

```ini
# Logs persistents a fitxer (opcional, recomanat)
LOG_LEVEL=INFO
LOG_DIR=/var/log/fitxes-tecniques

# Heartbeat del worker per a /api/health (opcional)
HEARTBEAT_DIR=/var/run/fitxes-tecniques

# Sostre uploads (opcional, default 30MB)
# MAX_CONTENT_LENGTH=31457280
```

**Si actives l'encriptació de credencials (vegeu 1.2):**

```ini
# ⚠️ FER BACKUP D'AQUESTA CLAU FORA DEL SERVIDOR. Sense ella, els
# secrets xifrats a BD no es poden recuperar.
ENCRYPTION_KEY=<la_clau_generada_al_pas_1.2>
```

Crear els directoris si fas servir `LOG_DIR` i `HEARTBEAT_DIR`:

```bash
sudo mkdir -p /var/log/fitxes-tecniques /var/run/fitxes-tecniques
sudo chown www-data:www-data /var/log/fitxes-tecniques /var/run/fitxes-tecniques
```

### 3.5 Instal·lar la dependència nova del backend

```bash
cd /var/www/fitxes-tecniques/backend
sudo -u www-data ./venv/bin/pip install -r requirements.txt
```

Hauràs de veure que instal·la **`cryptography`** (és la única dep nova).

### 3.6 Aplicar les migracions de BD

Hi ha **2 migracions noves**:
- `e4f1a2b3c5d6` — afegeix la taula `audit_log`
- `f5g2b3c4d6e7` — xifra les credencials existents dels destins (només si `ENCRYPTION_KEY` està definida; en cas contrari deixa els valors en clar amb un avís al log)

```bash
cd /var/www/fitxes-tecniques/backend
sudo -u www-data ./venv/bin/flask db current  # estat actual
sudo -u www-data ./venv/bin/flask db upgrade  # aplicar les pendents
sudo -u www-data ./venv/bin/flask db current  # ha de dir 'f5g2b3c4d6e7 (head)'
```

Si `flask db upgrade` falla → **no continuïs**. Vés directament a la **secció 5 (rollback)**.

### 3.7 Compilar el frontend

```bash
cd /var/www/fitxes-tecniques/frontend
sudo -u www-data npm ci  # només si package-lock.json ha canviat
sudo -u www-data npm run build
```

> Si veus warnings de Vite sobre mida del bundle, ignora'ls — no afecten l'arrencada.

### 3.8 Arrencar el servei

```bash
sudo systemctl start fitxes-tecniques
sudo systemctl status fitxes-tecniques  # ha de dir 'active (running)'
```

Si arrenca, salta a la secció 4. Si no:

```bash
sudo journalctl -u fitxes-tecniques --since "5 minutes ago" --no-pager
```

Errors típics:
- `SECRET_KEY no definida` → pas 3.4 mal fet.
- `ImportError: No module named cryptography` → pas 3.5 mal fet.
- `alembic ... already exists` → la migració s'ha aplicat parcialment, comprova `flask db current`.

---

## 4. Verificacions post-deploy

### 4.1 Health endpoint

```bash
curl -s http://localhost:50002/api/health | python3 -m json.tool
```

Hauries de veure:
```json
{
  "ok": true,
  "db": "ok",
  "worker": {"ok": true, "estat": "ok", "workers": [...]}
}
```

Si `worker.estat` és `"unknown"`: espera 60s i torna a provar — el worker triga uns segons a tocar el primer heartbeat.

Si `worker.estat` és `"stale"` després de 2 min → revisa que `HEARTBEAT_DIR` existeix i `www-data` hi pot escriure.

### 4.2 Frontend funcional

Des del navegador:
1. `https://fitxesfc.agrienergia.local` → ha de carregar el login.
2. Fer login.
3. Veure el llistat de fitxes — comprovar que la columna *Distribuït* mostra ara la **data relativa** ("fa 3 dies", etc.) sota el badge.
4. `Ctrl+K` → s'ha d'obrir la cerca global.
5. Obrir una fitxa, anar a *Editar* — el formulari ha de funcionar com abans.
6. Configuració → **Audit log** (entrada nova) — la pàgina ha de carregar.
7. Configuració → Destins — verifica que els destins existents continuen al lloc (només per confirmar que la migració no els ha trencat).

### 4.3 Distribució de prova

> Important: comprovar que les credencials xifrades funcionen.

- Tria una fitxa qualsevol en estat publicada.
- Distribueix-la a un destí FTP o SharePoint (cap nou — els existents).
- Ha d'anar OK. Si dóna error d'autenticació → vés a la secció 5.

### 4.4 Audit log

Crear un destí nou (de prova), editar-lo i esborrar-lo. Anar a `/admin/audit-log` i comprovar que les 3 accions hi apareixen amb `abans/després`.

### 4.5 Comprovar logs

```bash
ls -lh /var/log/fitxes-tecniques/
sudo tail -50 /var/log/fitxes-tecniques/app.log
```

Hauries de veure-hi les peticions i events del worker amb el format `2026-06-XX [INFO] ...`.

---

## 5. Rollback (si alguna cosa va malament)

> Important: el rollback és segur perquè totes les migracions tenen `downgrade`.

### 5.1 Aturar el servei

```bash
sudo systemctl stop fitxes-tecniques
```

### 5.2 Revertir migracions

```bash
cd /var/www/fitxes-tecniques/backend
sudo -u www-data ./venv/bin/flask db downgrade c2d8e5a3b1f0
# Això reverteix les 2 migracions noves:
#   f5g2b3c4d6e7 (downgrade desxifra els destins)
#   e4f1a2b3c5d6 (downgrade elimina taula audit_log)
```

Si vols fer-ho pas a pas:
```bash
sudo -u www-data ./venv/bin/flask db downgrade -1  # reverteix una
```

### 5.3 Revertir codi

```bash
cd /var/www/fitxes-tecniques
sudo -u www-data git reset --hard <HASH_ANTIC>  # el que vas apuntar al 2.3
```

### 5.4 Reconstruir frontend antic

```bash
cd /var/www/fitxes-tecniques/frontend
sudo -u www-data npm run build
```

### 5.5 Reinstal·lar requirements antics

```bash
cd /var/www/fitxes-tecniques/backend
sudo -u www-data ./venv/bin/pip install -r requirements.txt
```

### 5.6 Arrencar

```bash
sudo systemctl start fitxes-tecniques
curl -s http://localhost:50002/api/  # o el que sigui que funcionava abans
```

### 5.7 (Si fos imprescindible) Restaurar BD

Només si la BD ha quedat en un estat estrany. **Aquest pas perd tots els canvis fets des del backup.**

```bash
sudo systemctl stop fitxes-tecniques
sudo -u postgres dropdb fitxes_tecniques
sudo -u postgres createdb -O fitxes fitxes_tecniques
sudo -u postgres pg_restore -d fitxes_tecniques /backups/fitxes_pre_deploy_<data>.dump
sudo systemctl start fitxes-tecniques
```

---

## 6. Notes a llarg termini

### 6.1 Logs

Si activat `LOG_DIR=/var/log/fitxes-tecniques`, els logs es roten automàticament (10MB × 5 fitxers per `app.log`).
Si vols afegir rotació pel sistema, considera `logrotate`:

```bash
sudo tee /etc/logrotate.d/fitxes-tecniques > /dev/null <<EOF
/var/log/fitxes-tecniques/*.log {
    weekly
    rotate 4
    compress
    missingok
    notifempty
    copytruncate
}
EOF
```

### 6.2 Monitorització del health endpoint

Considera un cron que comprovi cada 5 min:

```bash
*/5 * * * * curl -s -o /dev/null -w "%{http_code}" http://localhost:50002/api/health | grep -qv 200 && echo "ALERTA: health degradat" | mail -s "Fitxes Tècniques" tu@agrienergia.com
```

(O fes-ho amb Uptime Kuma / Zabbix si en teniu.)

### 6.3 Backup periòdic

Si encara no tens un cron de backup setmanal de la BD, és bon moment per afegir-lo:

```bash
# /etc/cron.d/fitxes-backup
0 2 * * 0 postgres pg_dump -Fc fitxes_tecniques > /backups/fitxes_weekly_$(date +\%Y\%m\%d).dump
```

### 6.4 Activar ENCRYPTION_KEY més endavant

Si avui no l'has activat i la vols activar la setmana següent:

1. Generar la clau (vegeu 1.2) i posar-la a `.env`.
2. Aplicar de nou la migració de xifrat:
   ```bash
   cd /var/www/fitxes-tecniques/backend
   sudo -u www-data ./venv/bin/flask db downgrade e4f1a2b3c5d6
   sudo -u www-data ./venv/bin/flask db upgrade
   ```
   (Això re-aplica `f5g2b3c4d6e7` que ara sí xifrarà perquè té la clau.)
3. Reiniciar.

---

## 7. Resum dels canvis a `.env` (referència ràpida)

| Variable | Obligatori | Valor recomanat | Comentari |
|----------|------------|-----------------|-----------|
| `SECRET_KEY` | **Sí** (ja hi és) | string llarg aleatori | L'app no arrenca sense |
| `DATABASE_URL` | Sí (ja hi és) | — | — |
| `FTP_*`, `SHAREPOINT_*`, etc. | Sí (ja hi són) | — | — |
| `LOG_LEVEL` | No | `INFO` | DEBUG molt verbós, WARNING massa silenciós |
| `LOG_DIR` | No | `/var/log/fitxes-tecniques` | Sense, logs van a stderr de Gunicorn |
| `HEARTBEAT_DIR` | No | `/var/run/fitxes-tecniques` | Default `/tmp` (es buida al reiniciar) |
| `MAX_CONTENT_LENGTH` | No | (default 30MB) | Sostre absolut d'uploads |
| `ENCRYPTION_KEY` | No (recomanat) | Fernet 32 bytes b64 | Si la perds, secrets a BD inrecuperables |
| `ENABLE_JOB_WORKER` | No | (default `1`) | Posar `0` només per debugging |

---

## 8. Contactes en cas de problema

- Desenvolupament: Oscar Hijazo
- Si el deploy bloqueja l'app i el rollback no recupera: restaurar BD del backup (5.7) i tornar al commit del 2.3.

---

**Bona sort amb el deploy!** Si tens dubtes durant el procés, abans de fer accions destructives sempre val la pena aturar-se i comprovar.
