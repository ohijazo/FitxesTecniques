# Fitxes Tecniques - Guia de Desplegament a Produccio

**Instruccions per a l'equip de sistemes**

| Camp | Valor |
|------|-------|
| Versio | 1.0 |
| Data | Abril 2026 |
| Entorn | Ubuntu Server 24.04 + Apache + Gunicorn + PostgreSQL |
| Repositori | https://github.com/ohijazo/FitxesTecniques |
| Port backend | 50002 |
| Destinatari | Equip de Sistemes |

---

## Contingut

1. Requisits de la maquina virtual
2. Arquitectura
3. Instal-lacio de paquets
4. Configurar PostgreSQL
5. Descarregar i configurar l'aplicacio
6. Compilar el frontend
7. Backend com a servei (systemd)
8. Configurar Apache
9. Configuracio de xarxa
10. Verificacio final
11. Backups i manteniment
12. Resolucio de problemes

---

## 1. Requisits de la Maquina Virtual

L'aplicacio es lleugera. Es desplegara a la mateixa maquina Ubuntu on ja hi ha les altres aplicacions (Lab FC, Comandes de Venda).

### Recursos addicionals necessaris

| Recurs | Consum estimat |
|--------|---------------|
| RAM | ~200 MB (Gunicorn 2 workers) |
| Disc | ~500 MB (codi + uploads PDFs) |
| CPU | Minim (compartit) |

### Programari (ja instal-lat si hi ha Lab FC)

| Component | Versio | Funcio |
|-----------|--------|--------|
| Ubuntu Server | 24.04 LTS | Sistema operatiu |
| Python 3.12+ | Ja instal-lat | Runtime backend |
| PostgreSQL 16 | Ja instal-lat | Base de dades |
| Apache 2.4 | Ja instal-lat | Proxy invers |
| Node.js 20 | Ja instal-lat | Compilar frontend (un sol cop) |
| Git | Ja instal-lat | Descarregar codi |

### Connectivitat de xarxa

- Port 80 (HTTP via Apache) - ja obert
- Port 50002 (backend intern, nomes localhost)
- Acces FTP a `ftp.grupagrienergia.com` (port 21, TLS) per distribucio
- Acces SMB a carpetes de xarxa corporatives (opcional)

---

## 2. Arquitectura

```
Navegador dels usuaris (Chrome/Edge)
        |
        v
  Apache (port 80)
  |-- /fitxes/*      --> /var/www/fitxes-tecniques/frontend/dist/
  |                       (HTML, JS, CSS)
  |-- /fitxes/api/*  --> Reverse proxy a localhost:50002
        |
        v
  Gunicorn + Flask (port 50002)
        |
        v
  PostgreSQL (port 5432, BD: fitxes_tecniques)
        |
        v
  [FTP] [Carpeta xarxa] [SAP - futur]
```

### Fitxers de l'aplicacio

| Directori | Funcio |
|-----------|--------|
| `backend/app/` | Codi Flask (rutes, models, serveis) |
| `backend/app/templates/` | Plantilla HTML per generar PDFs |
| `backend/app/static/img/` | Logo corporatiu |
| `backend/uploads/` | PDFs generats i imatges (NO al git) |
| `backend/migrations/` | Migracions de base de dades |
| `frontend/src/` | Codi font React |
| `frontend/dist/` | Frontend compilat (servit per Apache) |

---

## 3. Instal-lacio de Paquets

**NOTA:** Si la maquina ja te Lab FC instal-lat, tots els paquets ja estan disponibles. Nomes cal verificar:

```bash
python3 --version   # 3.12+
node --version      # 20+
psql --version      # 16+
apache2 -v          # 2.4+
```

Si falta algun paquet:

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-pip python3-venv postgresql postgresql-contrib apache2 git

# Node.js (si no esta instal-lat)
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
```

### Paquet addicional: pdfplumber

L'aplicacio necessita `pdfplumber` per parsejar PDFs, que requereix algunes dependencies del sistema:

```bash
sudo apt install -y libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0
```

---

## 4. Configurar PostgreSQL

### Pas 4.1 - Crear la base de dades i l'usuari

```bash
sudo -u postgres psql
```

```sql
CREATE DATABASE fitxes_tecniques;
CREATE USER fitxes_user WITH PASSWORD 'CONTRASENYA_SEGURA';
GRANT ALL PRIVILEGES ON DATABASE fitxes_tecniques TO fitxes_user;

\c fitxes_tecniques
GRANT ALL ON SCHEMA public TO fitxes_user;

\q
```

> **IMPORTANT:** Canviar `CONTRASENYA_SEGURA` per una contrasenya real. Anotar-la per al fitxer `.env`.

---

## 5. Descarregar i Configurar l'Aplicacio

### Pas 5.1 - Clonar el repositori

```bash
cd /var/www
sudo git clone https://github.com/ohijazo/FitxesTecniques.git fitxes-tecniques
sudo chown -R www-data:www-data /var/www/fitxes-tecniques
```

### Pas 5.2 - Crear l'entorn virtual Python

```bash
cd /var/www/fitxes-tecniques/backend
sudo -u www-data python3 -m venv venv
sudo -u www-data venv/bin/pip install --upgrade pip
sudo -u www-data venv/bin/pip install -r requirements.txt
sudo -u www-data venv/bin/pip install gunicorn pdfplumber
```

### Pas 5.3 - Crear el fitxer `.env`

```bash
cd /var/www/fitxes-tecniques/backend
sudo cp .env.example .env
sudo nano .env
```

Contingut del fitxer `.env`:

```env
DATABASE_URL=postgresql://fitxes_user:CONTRASENYA_SEGURA@localhost:5432/fitxes_tecniques
SECRET_KEY=clau-aleatoria-de-minim-32-caracters
FLASK_ENV=production
CORS_ORIGINS=http://fitxes.agrienergia.local
```

| Variable | Descripcio |
|----------|-----------|
| `DATABASE_URL` | Connexio PostgreSQL |
| `SECRET_KEY` | Clau secreta per JWT. Generar amb: `python3 -c "import secrets; print(secrets.token_hex(32))"` |
| `FLASK_ENV` | Posar sempre `production` |
| `CORS_ORIGINS` | URL exacta d'acces dels usuaris |

```bash
# Protegir el fitxer .env
sudo chmod 600 /var/www/fitxes-tecniques/backend/.env
sudo chown www-data:www-data /var/www/fitxes-tecniques/backend/.env
```

### Pas 5.4 - Inicialitzar la base de dades

```bash
cd /var/www/fitxes-tecniques/backend
sudo -u www-data venv/bin/flask db upgrade
```

### Pas 5.5 - Crear l'usuari administrador inicial

```bash
cd /var/www/fitxes-tecniques/backend
sudo -u www-data venv/bin/flask crear-admin admin@agrienergia.com "Administrador" "ContraSenyaAdmin"
```

### Pas 5.6 - Crear carpeta d'uploads

```bash
sudo mkdir -p /var/www/fitxes-tecniques/backend/uploads
sudo chown -R www-data:www-data /var/www/fitxes-tecniques/backend/uploads
```

### Pas 5.7 - Verificar el backend manualment

```bash
cd /var/www/fitxes-tecniques/backend
sudo -u www-data venv/bin/gunicorn -w 2 -b 0.0.0.0:50002 'app:create_app()'

# Des d'un altre terminal:
curl http://localhost:50002/api/fitxes
# Hauria de retornar JSON: {"fitxes": [], "total": 0, ...}

# Ctrl+C per aturar
```

---

## 6. Compilar el Frontend

```bash
cd /var/www/fitxes-tecniques/frontend
sudo -u www-data npm install
sudo -u www-data npm run build
```

Aixo genera `frontend/dist/` amb els fitxers estatics.

> **NOTA:** El frontend fa les crides API a `/api/*`. Apache les redirigira al backend via proxy. Cal configurar el `vite.config.js` o el build perque les URLs siguin relatives.

---

## 7. Backend com a Servei (systemd)

### Pas 7.1 - Crear el fitxer de servei

```bash
sudo nano /etc/systemd/system/fitxes-tecniques.service
```

Contingut:

```ini
[Unit]
Description=Fitxes Tecniques - Backend API
After=network.target postgresql.service

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/fitxes-tecniques/backend
EnvironmentFile=/var/www/fitxes-tecniques/backend/.env
ExecStart=/var/www/fitxes-tecniques/backend/venv/bin/gunicorn \
    -w 2 \
    -b 127.0.0.1:50002 \
    --timeout 120 \
    --access-logfile /var/log/fitxes-tecniques/access.log \
    --error-logfile /var/log/fitxes-tecniques/error.log \
    'app:create_app()'
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### Pas 7.2 - Preparar permisos i logs

```bash
sudo mkdir -p /var/log/fitxes-tecniques
sudo chown www-data:www-data /var/log/fitxes-tecniques
```

### Pas 7.3 - Activar i arrencar el servei

```bash
sudo systemctl daemon-reload
sudo systemctl enable fitxes-tecniques
sudo systemctl start fitxes-tecniques
sudo systemctl status fitxes-tecniques
# Hauria de dir: active (running)
```

### Comandes de gestio del servei

| Comanda | Accio |
|---------|-------|
| `sudo systemctl start fitxes-tecniques` | Arrencar |
| `sudo systemctl stop fitxes-tecniques` | Aturar |
| `sudo systemctl restart fitxes-tecniques` | Reiniciar |
| `sudo systemctl status fitxes-tecniques` | Veure estat |
| `sudo journalctl -u fitxes-tecniques -f` | Logs en temps real |

---

## 8. Configurar Apache

### Pas 8.1 - Activar moduls (si no estan activats)

```bash
sudo a2enmod proxy proxy_http rewrite
sudo systemctl restart apache2
```

### Pas 8.2 - Crear el VirtualHost

```bash
sudo nano /etc/apache2/sites-available/fitxes-tecniques.conf
```

Contingut:

```apache
<VirtualHost *:80>
    ServerName fitxes.agrienergia.local

    # Frontend: fitxers estatics compilats
    DocumentRoot /var/www/fitxes-tecniques/frontend/dist

    <Directory /var/www/fitxes-tecniques/frontend/dist>
        Options -Indexes +FollowSymLinks
        AllowOverride All
        Require all granted

        # SPA: redirigir totes les rutes a index.html
        RewriteEngine On
        RewriteBase /
        RewriteCond %{REQUEST_FILENAME} !-f
        RewriteCond %{REQUEST_FILENAME} !-d
        RewriteCond %{REQUEST_URI} !^/api/
        RewriteRule ^ /index.html [L]
    </Directory>

    # Proxy API -> backend Gunicorn
    ProxyPreserveHost On
    ProxyPass /api/ http://127.0.0.1:50002/api/
    ProxyPassReverse /api/ http://127.0.0.1:50002/api/

    # Logs
    ErrorLog ${APACHE_LOG_DIR}/fitxes-tecniques-error.log
    CustomLog ${APACHE_LOG_DIR}/fitxes-tecniques-access.log combined
</VirtualHost>
```

### Pas 8.3 - Activar el site

```bash
sudo a2ensite fitxes-tecniques.conf
sudo apache2ctl configtest
# Hauria de dir: Syntax OK
sudo systemctl restart apache2
```

---

## 9. Configuracio de Xarxa

### Firewall (UFW)

Si el firewall ja esta configurat per Lab FC, no cal fer res mes (port 80 ja obert).

```bash
sudo ufw status
# Verificar que 80/tcp esta ALLOW
```

### DNS intern

Crear una entrada DNS al servidor DNS de l'empresa:

| Tipus | Nom | Valor |
|-------|-----|-------|
| A | fitxes.agrienergia.local | IP-DE-LA-MAQUINA |

Si no es configura DNS, els usuaris accediran per IP directament.

### Acces FTP (distribucio)

L'aplicacio necessita connectar al servidor FTP per distribuir fitxes:

| Parametre | Valor |
|-----------|-------|
| Host | ftp.grupagrienergia.com |
| Port | 21 |
| Protocol | FTP amb TLS explicit |

Verificar que el servidor Ubuntu pot connectar:

```bash
# Instal-lar client FTP si cal
sudo apt install -y ftp

# Provar connexio
curl -v --ftp-ssl ftp://ftp.grupagrienergia.com/ --user "usuari:password"
```

### Acces carpeta de xarxa (distribucio)

Si es configura un desti de carpeta de xarxa (SMB):

```bash
# Instal-lar client SMB
sudo apt install -y cifs-utils smbclient

# Provar connexio
smbclient //servidor/compartit -U domini/usuari
```

---

## 10. Verificacio Final

### Checklist de verificacio

| # | Verificacio | Comanda | Resultat esperat |
|---|------------|---------|-----------------|
| 1 | PostgreSQL actiu | `sudo systemctl status postgresql` | active (running) |
| 2 | Backend actiu | `sudo systemctl status fitxes-tecniques` | active (running) |
| 3 | Apache actiu | `sudo systemctl status apache2` | active (running) |
| 4 | API respon | `curl http://localhost:50002/api/fitxes` | JSON amb fitxes |
| 5 | Frontend accessible | Obrir `http://fitxes.agrienergia.local` | Pantalla login |
| 6 | Login admin | Entrar amb credencials admin | Dashboard |
| 7 | Acces des d'altre PC | Obrir `http://IP-MAQUINA` des d'un PC | Pantalla login |
| 8 | Auto-start | `sudo reboot` i verificar | Tot actiu |

### Prova completa

Des d'un PC de la xarxa local, obrir el navegador i anar a:

```
http://fitxes.agrienergia.local
```

Entrar amb les credencials d'admin configurades al pas 5.5.

---

## 11. Backups i Manteniment

### Backup de la base de dades

```bash
# Backup manual
sudo -u postgres pg_dump -F c fitxes_tecniques > /backups/fitxes_$(date +%Y%m%d).dump

# Restaurar
sudo -u postgres pg_restore -d fitxes_tecniques /backups/fitxes_20260423.dump
```

### Backup automatic amb cron

```bash
sudo nano /usr/local/bin/backup-fitxes.sh
```

Contingut:

```bash
#!/bin/bash
BACKUP_DIR=/backups
DATE=$(date +%Y%m%d)

# Backup BD
pg_dump -U postgres -F c fitxes_tecniques > $BACKUP_DIR/fitxes_$DATE.dump

# Backup uploads (imatges i PDFs)
tar czf $BACKUP_DIR/fitxes_uploads_$DATE.tar.gz -C /var/www/fitxes-tecniques/backend uploads/

# Eliminar backups de mes de 30 dies
find $BACKUP_DIR -name 'fitxes_*' -mtime +30 -delete
```

```bash
sudo chmod +x /usr/local/bin/backup-fitxes.sh

# Programar backup diari a les 3:00 AM
sudo crontab -e
# Afegir:
# 0 3 * * * /usr/local/bin/backup-fitxes.sh
```

### Actualitzar l'aplicacio

Quan es lliuri una nova versio:

```bash
# 1. Descarregar nova versio
cd /var/www/fitxes-tecniques
sudo git pull

# 2. Actualitzar dependencies backend
cd backend
sudo -u www-data venv/bin/pip install -r requirements.txt
sudo -u www-data venv/bin/flask db upgrade

# 3. Recompilar frontend
cd ../frontend
sudo -u www-data npm install
sudo -u www-data npm run build

# 4. Restaurar permisos
sudo chown -R www-data:www-data /var/www/fitxes-tecniques

# 5. Reiniciar backend
sudo systemctl restart fitxes-tecniques
```

### Rotacio de logs

```bash
sudo nano /etc/logrotate.d/fitxes-tecniques
```

Contingut:

```
/var/log/fitxes-tecniques/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    copytruncate
}
```

---

## 12. Resolucio de Problemes

| Problema | Causa probable | Solucio |
|----------|---------------|---------|
| Servei no arrenca | Error config o dependencies | `journalctl -u fitxes-tecniques -n 50` |
| Error 502 | Gunicorn no respon | `sudo systemctl restart fitxes-tecniques` |
| Login no funciona | BD no inicialitzada | Executar pas 5.4 i 5.5 |
| PDFs no es generen | Falten dependencies | `sudo apt install libpango-1.0-0 libpangocairo-1.0-0` |
| FTP falla | Firewall o credencials | Verificar connexio FTP des del servidor |
| Carpeta xarxa falla | SMB no instal-lat | `sudo apt install cifs-utils` |
| Frontend en blanc | No compilat | Executar pas 6 |
| API retorna 404 | Proxy Apache mal configurat | Revisar VirtualHost pas 8.2 |
| Imatges no es mostren | Permisos uploads | `sudo chown -R www-data:www-data uploads/` |

### Logs de l'aplicacio

| Log | Ubicacio |
|-----|---------|
| Backend acces | `/var/log/fitxes-tecniques/access.log` |
| Backend errors | `/var/log/fitxes-tecniques/error.log` |
| Apache acces | `/var/log/apache2/fitxes-tecniques-access.log` |
| Apache errors | `/var/log/apache2/fitxes-tecniques-error.log` |
| Servei systemd | `sudo journalctl -u fitxes-tecniques` |
| PostgreSQL | `/var/log/postgresql/` |

---

## Resum

### Resum de passos

| Pas | Accio | Temps estimat |
|-----|-------|--------------|
| 1 | Verificar paquets (ja instal-lats) | 2 min |
| 2 | Crear BD i usuari PostgreSQL | 5 min |
| 3 | Clonar repositori i configurar backend | 10 min |
| 4 | Compilar frontend | 5 min |
| 5 | Crear servei systemd | 5 min |
| 6 | Configurar Apache (VirtualHost) | 10 min |
| 7 | Configurar DNS | 5 min |
| 8 | Verificacio final | 5 min |
| | **Temps total estimat** | **~47 minuts** |

### Ports utilitzats

| Port | Servei | Acces |
|------|--------|-------|
| 80 | Apache (HTTP) | Extern (usuaris) |
| 50002 | Gunicorn (backend) | Intern (localhost) |
| 5432 | PostgreSQL | Intern (localhost) |
| 21 | FTP (distribucio) | Sortida al FTP extern |

### Dades de configuracio

| Parametre | Valor |
|-----------|-------|
| Directori aplicacio | `/var/www/fitxes-tecniques` |
| Servei systemd | `fitxes-tecniques` |
| Base de dades | `fitxes_tecniques` |
| Usuari BD | `fitxes_user` |
| URL acces | `http://fitxes.agrienergia.local` |
| Repositori | `https://github.com/ohijazo/FitxesTecniques` |
