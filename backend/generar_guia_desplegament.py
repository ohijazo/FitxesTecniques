"""
Genera el PDF de la Guia de Desplegament de Fitxes T&egrave;cniques.
"""
import io
from xhtml2pdf import pisa
from markupsafe import Markup


def cmd(text):
    """Format comanda: fons gris clar, text petit."""
    return f'<div class="cmd">{text}</div>'


def note(text):
    return f'<div class="note">{text}</div>'


def warn(text):
    return f'<div class="warning">{text}</div>'


HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  @page {
    size: A4;
    margin: 18mm 16mm 22mm 16mm;
    @frame footer {
      -pdf-frame-content: page-footer;
      bottom: 0mm;
      margin-left: 16mm;
      margin-right: 16mm;
      height: 10mm;
    }
  }
  body {
    font-family: Helvetica, Arial, sans-serif;
    font-size: 9.5pt;
    color: #1f2937;
    line-height: 1.45;
  }
  h1 { color: #2F5496; font-size: 20pt; margin: 0 0 4px 0; border-bottom: 2px solid #2F5496; padding-bottom: 6px; }
  h2 { color: #2F5496; font-size: 13pt; margin: 16px 0 6px 0; border-bottom: 1px solid #2F5496; padding-bottom: 2px; }
  h3 { color: #2F5496; font-size: 10.5pt; margin: 10px 0 3px 0; }
  p { margin: 3px 0 5px 0; }
  .cmd {
    background: #f3f4f6;
    border: 1px solid #d1d5db;
    padding: 6px 10px;
    font-family: Courier, monospace;
    font-size: 8pt;
    line-height: 1.35;
    margin: 4px 0 8px 0;
    word-wrap: break-word;
  }
  .conf {
    background: #f9fafb;
    border: 1px solid #e5e7eb;
    padding: 6px 10px;
    font-family: Courier, monospace;
    font-size: 8pt;
    line-height: 1.35;
    margin: 4px 0 8px 0;
    word-wrap: break-word;
  }
  table { width: 100%; border-collapse: collapse; margin: 4px 0 8px 0; font-size: 9pt; }
  th { background: #2F5496; color: white; text-align: left; padding: 4px 6px; border: 1px solid #2F5496; }
  td { padding: 3px 6px; border: 1px solid #d1d5db; }
  .note { background: #eff6ff; border-left: 3px solid #2F5496; padding: 6px 10px; font-size: 8.5pt; margin: 6px 0; color: #1e40af; }
  .warning { background: #fef3c7; border-left: 3px solid #d97706; padding: 6px 10px; font-size: 8.5pt; margin: 6px 0; color: #92400e; }
  .subtitle { color: #6b7280; font-size: 10pt; }
  ul, ol { margin: 3px 0 6px 0; padding-left: 18px; }
  li { margin: 1px 0; }
  code { font-family: Courier, monospace; font-size: 8.5pt; background: #f3f4f6; padding: 0 3px; }
  .page-break { page-break-before: always; }
  .meta td { border: none; padding: 2px 6px; font-size: 9pt; }
  .meta td:first-child { font-weight: bold; color: #2F5496; width: 110px; }
</style>
</head>
<body>

<div id="page-footer" style="text-align: center; font-size: 6.5pt; color: #9ca3af; border-top: 1px solid #d1d5db; padding-top: 2px;">
  Fitxes T&egrave;cniques &mdash; Guia de Desplegament v1.0 &mdash; <pdf:pagenumber> / <pdf:pagecount>
</div>

<!-- ============ PORTADA + CONTINGUT (mateixa p&agrave;gina) ============ -->
<h1 style="border: none; font-size: 22pt; text-align: center; margin-top: 30px;">Fitxes T&egrave;cniques</h1>
<p style="font-size: 14pt; color: #2F5496; text-align: center; margin: 5px 0 15px 0;">Guia de Desplegament a Producci&oacute;</p>
<p style="text-align: center; color: #6b7280; font-size: 9.5pt;">Instruccions per a l'equip de sistemes &mdash; Ubuntu Server + Apache + Gunicorn + PostgreSQL</p>
<p style="text-align: center; font-size: 8.5pt; color: #2F5496; margin-top: 10px;">
  <b>Versi&oacute;:</b> 1.0 &nbsp;&nbsp;|&nbsp;&nbsp;
  <b>Data:</b> Abril 2026 &nbsp;&nbsp;|&nbsp;&nbsp;
  <b>Port:</b> 50002 &nbsp;&nbsp;|&nbsp;&nbsp;
  <b>DNS:</b> fitxesfc.agrienergia.local
</p>
<p style="text-align: center; font-size: 8.5pt; color: #2F5496;">
  <b>Repositori:</b> github.com/ohijazo/FitxesTecniques
</p>
<h2>Contingut</h2>
<ol>
  <li>Requisits de la m&agrave;quina</li>
  <li>Arquitectura</li>
  <li>Instal&middot;lacio de paquets</li>
  <li>Configurar PostgreSQL</li>
  <li>Descarregar i configurar l'aplicaci&oacute;</li>
  <li>Compilar el frontend</li>
  <li>Backend com a servei (systemd)</li>
  <li>Configurar Apache</li>
  <li>Configuraci&oacute; de xarxa</li>
  <li>Verificaci&oacute; final</li>
  <li>Migrar dades de desenvolupament</li>
  <li>Backups i manteniment</li>
  <li>Resoluci&oacute; de problemes</li>
</ol>

<!-- ============ 1. REQUISITS ============ -->
<h2>1. Requisits de la Maquina</h2>
<p>L'aplicacio es desplegara a la mateixa m&agrave;quina Ubuntu on ja hi ha Lab FC i Comandes de Venda.</p>

<h3>Recursos addicionals</h3>
<table>
  <tr><th>Recurs</th><th>Consum estimat</th></tr>
  <tr><td>RAM</td><td>~200 MB (Gunicorn 2 workers)</td></tr>
  <tr><td>Disc</td><td>~500 MB (codi + PDFs pujats)</td></tr>
  <tr><td>CPU</td><td>M&iacute;nim (compartit)</td></tr>
</table>

<h3>Programari (ja instal&middot;lat)</h3>
<table>
  <tr><th>Component</th><th>Versi&oacute;</th><th>Funci&oacute;</th></tr>
  <tr><td>Ubuntu Server</td><td>24.04 LTS</td><td>Sistema operatiu</td></tr>
  <tr><td>Python</td><td>3.12+</td><td>Backend</td></tr>
  <tr><td>PostgreSQL</td><td>16</td><td>Base de dades</td></tr>
  <tr><td>Apache</td><td>2.4</td><td>Proxy invers</td></tr>
  <tr><td>Node.js</td><td>20 LTS</td><td>Compilar frontend</td></tr>
  <tr><td>Git</td><td>2.40+</td><td>Codi font</td></tr>
</table>

<h3>Connectivitat</h3>
<ul>
  <li>Port 80 (HTTP, ja obert)</li>
  <li>Port 50002 (backend, nom&eacute;s localhost)</li>
  <li>Sortida FTP a <code>ftp.grupagrienergia.com:21</code> (TLS)</li>
  <li>Sortida SMB a carpetes de xarxa corporatives (opcional)</li>
</ul>

<!-- ============ 2. ARQUITECTURA ============ -->
<h2>2. Arquitectura</h2>
<div class="conf">
Navegador (Chrome/Edge)<br/>
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;|<br/>
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;v<br/>
Apache (port 80)<br/>
|-- /*&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;-->&nbsp;/var/www/fitxes-tecniques/frontend/dist/<br/>
|-- /api/*&nbsp;&nbsp;-->&nbsp;Reverse proxy a localhost:50002<br/>
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;|<br/>
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;v<br/>
Gunicorn + Flask (port 50002)<br/>
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;|<br/>
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;v<br/>
PostgreSQL (BD: fitxes_tecniques)<br/>
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;|<br/>
[FTP]&nbsp;&nbsp;[Carpeta xarxa]&nbsp;&nbsp;[SAP - futur]
</div>

<h3>Estructura de fitxers</h3>
<table>
  <tr><th>Directori</th><th>Funci&oacute;</th></tr>
  <tr><td><code>backend/app/</code></td><td>Codi Flask (rutes, models, serveis)</td></tr>
  <tr><td><code>backend/uploads/</code></td><td>PDFs i imatges pujades</td></tr>
  <tr><td><code>backend/migrations/</code></td><td>Migracions BD (Alembic)</td></tr>
  <tr><td><code>frontend/dist/</code></td><td>Frontend compilat (Apache)</td></tr>
</table>

<!-- ============ 3. PAQUETS ============ -->
<h2>3. Instal&middot;lacio de Paquets</h2>
<div class="note">Si Lab FC ja esta instal&middot;lat, tots els paquets ja hi son. Nom&eacute;s cal verificar.</div>

<h3>Verificar</h3>
<div class="cmd">python3 --version&nbsp;&nbsp;&nbsp;# 3.12+<br/>node --version&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;# 20+<br/>psql --version&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;# 16+<br/>apache2 -v&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;# 2.4+</div>

<h3>Si falta algun paquet</h3>
<div class="cmd">sudo apt update && sudo apt upgrade -y<br/>sudo apt install -y python3 python3-pip python3-venv postgresql postgresql-contrib apache2 git</div>

<h3>Dependencies per generaci&oacute; PDF</h3>
<div class="cmd">sudo apt install -y libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0</div>

<!-- ============ 4. POSTGRESQL ============ -->
<h2>4. Configurar PostgreSQL</h2>
<div class="cmd">sudo -u postgres psql</div>
<div class="cmd">CREATE DATABASE fitxes_tecniques;<br/>CREATE USER fitxes_user WITH PASSWORD '<b>CONTRASENYA_SEGURA</b>';<br/>GRANT ALL PRIVILEGES ON DATABASE fitxes_tecniques TO fitxes_user;<br/><br/>\\c fitxes_tecniques<br/>GRANT ALL ON SCHEMA public TO fitxes_user;<br/>\\q</div>
<div class="warning">IMPORTANT: Canviar CONTRASENYA_SEGURA per una contrasenya real. Anotar-la per al fitxer .env.</div>

<!-- ============ 5. CONFIGURAR APP ============ -->
<h2>5. Descarregar i Configurar l'Aplicacio</h2>

<h3>5.1 Clonar el repositori</h3>
<div class="cmd">cd /var/www<br/>sudo git clone https://github.com/ohijazo/FitxesTecniques.git fitxes-tecniques<br/>sudo chown -R www-data:www-data /var/www/fitxes-tecniques</div>

<h3>5.2 Entorn virtual Python</h3>
<div class="cmd">cd /var/www/fitxes-tecniques/backend<br/>sudo -u www-data python3 -m venv venv<br/>sudo -u www-data venv/bin/pip install --upgrade pip<br/>sudo -u www-data venv/bin/pip install -r requirements.txt<br/>sudo -u www-data venv/bin/pip install gunicorn pdfplumber</div>

<h3>5.3 Fitxer .env</h3>
<div class="cmd">sudo cp .env.example .env<br/>sudo nano .env</div>
<p>Contingut:</p>
<div class="conf">DATABASE_URL=postgresql://fitxes_user:CONTRASENYA@localhost:5432/fitxes_tecniques<br/>SECRET_KEY=clau-aleatoria-minim-32-caracters<br/>FLASK_ENV=production<br/>CORS_ORIGINS=http://fitxesfc.agrienergia.local</div>

<table>
  <tr><th>Variable</th><th>Descripci&oacute;</th></tr>
  <tr><td><code>DATABASE_URL</code></td><td>Connexi&oacute; PostgreSQL</td></tr>
  <tr><td><code>SECRET_KEY</code></td><td>Generar: <code>python3 -c "import secrets; print(secrets.token_hex(32))"</code></td></tr>
  <tr><td><code>FLASK_ENV</code></td><td>Sempre <code>production</code></td></tr>
  <tr><td><code>CORS_ORIGINS</code></td><td>URL exacta d'acces</td></tr>
</table>

<div class="cmd">sudo chmod 600 .env<br/>sudo chown www-data:www-data .env</div>

<h3>5.4 Inicialitzar BD</h3>
<div class="cmd">sudo -u www-data venv/bin/flask db upgrade</div>

<h3>5.5 Crear admin</h3>
<div class="cmd">sudo -u www-data venv/bin/flask crear-admin admin@agrienergia.com "Administrador" "ContrAdmin"</div>

<h3>5.6 Carpeta uploads</h3>
<div class="cmd">sudo mkdir -p /var/www/fitxes-tecniques/backend/uploads<br/>sudo chown -R www-data:www-data /var/www/fitxes-tecniques/backend/uploads</div>

<h3>5.7 Verificar backend</h3>
<div class="cmd">sudo -u www-data venv/bin/gunicorn -w 2 -b 0.0.0.0:50002 'app:create_app()'<br/><br/># Des d'un altre terminal:<br/>curl http://localhost:50002/api/fitxes<br/># Ha de retornar JSON. Ctrl+C per aturar.</div>

<!-- ============ 6. FRONTEND ============ -->
<h2>6. Compilar el Frontend</h2>
<div class="cmd">cd /var/www/fitxes-tecniques/frontend<br/>sudo -u www-data npm install<br/>sudo -u www-data npm run build</div>
<div class="note">Genera frontend/dist/. Node.js nom&eacute;s cal durant la compilacio, no en execucio permanent.</div>

<!-- ============ 7. SYSTEMD ============ -->
<h2>7. Backend com a Servei (systemd)</h2>

<h3>7.1 Crear servei</h3>
<div class="cmd">sudo nano /etc/systemd/system/fitxes-tecniques.service</div>
<div class="conf">[Unit]<br/>Description=Fitxes T&egrave;cniques - Backend API<br/>After=network.target postgresql.service<br/><br/>[Service]<br/>User=www-data<br/>Group=www-data<br/>WorkingDirectory=/var/www/fitxes-tecniques/backend<br/>EnvironmentFile=/var/www/fitxes-tecniques/backend/.env<br/>ExecStart=/var/www/fitxes-tecniques/backend/venv/bin/gunicorn \\<br/>&nbsp;&nbsp;&nbsp;&nbsp;-w 2 \\<br/>&nbsp;&nbsp;&nbsp;&nbsp;-b 127.0.0.1:50002 \\<br/>&nbsp;&nbsp;&nbsp;&nbsp;--timeout 120 \\<br/>&nbsp;&nbsp;&nbsp;&nbsp;--access-logfile /var/log/fitxes-tecniques/access.log \\<br/>&nbsp;&nbsp;&nbsp;&nbsp;--error-logfile /var/log/fitxes-tecniques/error.log \\<br/>&nbsp;&nbsp;&nbsp;&nbsp;'app:create_app()'<br/>Restart=always<br/>RestartSec=5<br/><br/>[Install]<br/>WantedBy=multi-user.target</div>

<h3>7.2 Preparar logs</h3>
<div class="cmd">sudo mkdir -p /var/log/fitxes-tecniques<br/>sudo chown www-data:www-data /var/log/fitxes-tecniques</div>

<h3>7.3 Activar</h3>
<div class="cmd">sudo systemctl daemon-reload<br/>sudo systemctl enable fitxes-tecniques<br/>sudo systemctl start fitxes-tecniques<br/>sudo systemctl status fitxes-tecniques</div>

<h3>Comandes utils</h3>
<table>
  <tr><th>Comanda</th><th>Acci&oacute;</th></tr>
  <tr><td><code>sudo systemctl start fitxes-tecniques</code></td><td>Arrencar</td></tr>
  <tr><td><code>sudo systemctl stop fitxes-tecniques</code></td><td>Aturar</td></tr>
  <tr><td><code>sudo systemctl restart fitxes-tecniques</code></td><td>Reiniciar</td></tr>
  <tr><td><code>sudo systemctl status fitxes-tecniques</code></td><td>Estat</td></tr>
  <tr><td><code>sudo journalctl -u fitxes-tecniques -f</code></td><td>Logs temps real</td></tr>
</table>

<!-- ============ 8. APACHE ============ -->
<h2>8. Configurar Apache</h2>

<h3>8.1 Activar moduls</h3>
<div class="cmd">sudo a2enmod proxy proxy_http rewrite<br/>sudo systemctl restart apache2</div>

<h3>8.2 Crear VirtualHost</h3>
<div class="cmd">sudo nano /etc/apache2/sites-available/fitxes-tecniques.conf</div>
<div class="conf">&lt;VirtualHost *:80&gt;<br/>&nbsp;&nbsp;ServerName fitxesfc.agrienergia.local<br/><br/>&nbsp;&nbsp;DocumentRoot /var/www/fitxes-tecniques/frontend/dist<br/><br/>&nbsp;&nbsp;&lt;Directory /var/www/fitxes-tecniques/frontend/dist&gt;<br/>&nbsp;&nbsp;&nbsp;&nbsp;Options -Indexes +FollowSymLinks<br/>&nbsp;&nbsp;&nbsp;&nbsp;AllowOverride All<br/>&nbsp;&nbsp;&nbsp;&nbsp;Require all granted<br/>&nbsp;&nbsp;&nbsp;&nbsp;RewriteEngine On<br/>&nbsp;&nbsp;&nbsp;&nbsp;RewriteBase /<br/>&nbsp;&nbsp;&nbsp;&nbsp;RewriteCond %{REQUEST_FILENAME} !-f<br/>&nbsp;&nbsp;&nbsp;&nbsp;RewriteCond %{REQUEST_FILENAME} !-d<br/>&nbsp;&nbsp;&nbsp;&nbsp;RewriteCond %{REQUEST_URI} !^/api/<br/>&nbsp;&nbsp;&nbsp;&nbsp;RewriteRule ^ /index.html [L]<br/>&nbsp;&nbsp;&lt;/Directory&gt;<br/><br/>&nbsp;&nbsp;ProxyPreserveHost On<br/>&nbsp;&nbsp;ProxyPass /api/ http://127.0.0.1:50002/api/<br/>&nbsp;&nbsp;ProxyPassReverse /api/ http://127.0.0.1:50002/api/<br/><br/>&nbsp;&nbsp;ErrorLog ${APACHE_LOG_DIR}/fitxes-tecniques-error.log<br/>&nbsp;&nbsp;CustomLog ${APACHE_LOG_DIR}/fitxes-tecniques-access.log combined<br/>&lt;/VirtualHost&gt;</div>

<h3>8.3 Activar</h3>
<div class="cmd">sudo a2ensite fitxes-tecniques.conf<br/>sudo apache2ctl configtest<br/>sudo systemctl restart apache2</div>

<!-- ============ 9. XARXA ============ -->
<h2>9. Configuraci&oacute; de Xarxa</h2>

<h3>Firewall</h3>
<p>Port 80 ja obert si Lab FC funciona. Verificar:</p>
<div class="cmd">sudo ufw status</div>

<h3>DNS intern</h3>
<table>
  <tr><th>Tipus</th><th>Nom</th><th>Valor</th></tr>
  <tr><td>A</td><td>fitxesfc.agrienergia.local</td><td>IP de la m&agrave;quina</td></tr>
</table>

<h3>Acces FTP (distribuci&oacute;)</h3>
<div class="cmd">curl -v --ftp-ssl ftp://ftp.grupagrienergia.com/ --user "usuari:password"</div>

<h3>Acces carpeta xarxa (opcional)</h3>
<div class="cmd">sudo apt install -y cifs-utils smbclient</div>

<!-- ============ 10. VERIFICACIO ============ -->
<h2>10. Verificaci&oacute; Final</h2>
<table>
  <tr><th>#</th><th>Verificaci&oacute;</th><th>Comanda</th><th>Esperat</th></tr>
  <tr><td>1</td><td>PostgreSQL</td><td><code>systemctl status postgresql</code></td><td>active</td></tr>
  <tr><td>2</td><td>Backend</td><td><code>systemctl status fitxes-tecniques</code></td><td>active</td></tr>
  <tr><td>3</td><td>Apache</td><td><code>systemctl status apache2</code></td><td>active</td></tr>
  <tr><td>4</td><td>API</td><td><code>curl localhost:50002/api/fitxes</code></td><td>JSON</td></tr>
  <tr><td>5</td><td>Frontend</td><td>Navegador: fitxesfc.agrienergia.local</td><td>Login</td></tr>
  <tr><td>6</td><td>Login</td><td>Credencials admin</td><td>Dashboard</td></tr>
  <tr><td>7</td><td>Extern</td><td>Des d'un altre PC</td><td>Login</td></tr>
  <tr><td>8</td><td>Auto-start</td><td><code>sudo reboot</code></td><td>Tot actiu</td></tr>
</table>

<!-- ============ 11. MIGRAR DADES ============ -->
<h2>11. Migrar Dades de Desenvolupament</h2>
<p>Per pujar les dades locals (fitxes, versions, imatges) al servidor de produccio:</p>

<h3>11.1 Exportar BD local (des del PC Windows)</h3>
<div class="cmd"># Al PC de desenvolupament (Windows):<br/>cd P:\\fitxestecniques\\backend<br/>pg_dump -U postgres -F c fitxes_tecniques > fitxes_backup.dump</div>

<h3>11.2 Copiar fitxers al servidor</h3>
<div class="cmd"># Copiar backup BD i uploads al servidor via SCP:<br/>scp fitxes_backup.dump usuari@IP_SERVIDOR:/tmp/<br/>scp -r uploads/ usuari@IP_SERVIDOR:/tmp/fitxes_uploads/</div>

<h3>11.3 Restaurar al servidor</h3>
<div class="cmd"># Al servidor Ubuntu:<br/>sudo -u postgres pg_restore -c -d fitxes_tecniques /tmp/fitxes_backup.dump<br/><br/># Copiar uploads<br/>sudo cp -r /tmp/fitxes_uploads/* /var/www/fitxes-tecniques/backend/uploads/<br/>sudo chown -R www-data:www-data /var/www/fitxes-tecniques/backend/uploads/<br/><br/># Reiniciar<br/>sudo systemctl restart fitxes-tecniques</div>

<div class="note">Despr&eacute;s de restaurar, verificar que les fitxes apareixen al navegador i que les imatges de certificacio es mostren correctament.</div>

<!-- ============ 12. BACKUPS ============ -->
<h2>12. Backups i Manteniment</h2>

<h3>Backup automatic (cron)</h3>
<div class="cmd">sudo nano /usr/local/bin/backup-fitxes.sh</div>
<div class="conf">#!/bin/bash<br/>BACKUP_DIR=/backups<br/>DATE=$(date +%Y%m%d)<br/>pg_dump -U postgres -F c fitxes_tecniques > $BACKUP_DIR/fitxes_$DATE.dump<br/>tar czf $BACKUP_DIR/fitxes_uploads_$DATE.tar.gz \\<br/>&nbsp;&nbsp;-C /var/www/fitxes-tecniques/backend uploads/<br/>find $BACKUP_DIR -name 'fitxes_*' -mtime +30 -delete</div>
<div class="cmd">sudo chmod +x /usr/local/bin/backup-fitxes.sh<br/>sudo crontab -e<br/># Afegir: 0 3 * * * /usr/local/bin/backup-fitxes.sh</div>

<h3>Actualitzar l'aplicaci&oacute;</h3>
<div class="cmd">cd /var/www/fitxes-tecniques<br/>sudo git pull<br/>cd backend<br/>sudo -u www-data venv/bin/pip install -r requirements.txt<br/>sudo -u www-data venv/bin/flask db upgrade<br/>cd ../frontend<br/>sudo -u www-data npm install<br/>sudo -u www-data npm run build<br/>sudo chown -R www-data:www-data /var/www/fitxes-tecniques<br/>sudo systemctl restart fitxes-tecniques</div>

<h3>Rotaci&oacute; de logs</h3>
<div class="cmd">sudo nano /etc/logrotate.d/fitxes-tecniques</div>
<div class="conf">/var/log/fitxes-tecniques/*.log {<br/>&nbsp;&nbsp;daily<br/>&nbsp;&nbsp;missingok<br/>&nbsp;&nbsp;rotate 14<br/>&nbsp;&nbsp;compress<br/>&nbsp;&nbsp;delaycompress<br/>&nbsp;&nbsp;notifempty<br/>&nbsp;&nbsp;copytruncate<br/>}</div>

<!-- ============ 13. PROBLEMES ============ -->
<h2>13. Resoluci&oacute; de Problemes</h2>
<table>
  <tr><th>Problema</th><th>Causa</th><th>Soluci&oacute;</th></tr>
  <tr><td>Servei no arrenca</td><td>Error config</td><td><code>journalctl -u fitxes-tecniques -n 50</code></td></tr>
  <tr><td>Error 502</td><td>Backend caigut</td><td><code>systemctl restart fitxes-tecniques</code></td></tr>
  <tr><td>Login falla</td><td>BD buida</td><td>Executar pas 5.4 i 5.5</td></tr>
  <tr><td>PDFs no es generen</td><td>Falten libs</td><td><code>apt install libpango-1.0-0</code></td></tr>
  <tr><td>FTP falla</td><td>Firewall/creds</td><td>Verificar connexi&oacute; FTP</td></tr>
  <tr><td>Xarxa falla</td><td>SMB no instal&middot;lat</td><td><code>apt install cifs-utils</code></td></tr>
  <tr><td>Frontend en blanc</td><td>No compilat</td><td>Pas 6</td></tr>
  <tr><td>API 404</td><td>Apache config</td><td>Revisar VirtualHost</td></tr>
  <tr><td>Imatges no surten</td><td>Permisos</td><td><code>chown -R www-data uploads/</code></td></tr>
</table>

<h3>Logs</h3>
<table>
  <tr><th>Log</th><th>Ubicaci&oacute;</th></tr>
  <tr><td>Backend acces</td><td><code>/var/log/fitxes-tecniques/access.log</code></td></tr>
  <tr><td>Backend errors</td><td><code>/var/log/fitxes-tecniques/error.log</code></td></tr>
  <tr><td>Apache acces</td><td><code>/var/log/apache2/fitxes-tecniques-access.log</code></td></tr>
  <tr><td>Apache errors</td><td><code>/var/log/apache2/fitxes-tecniques-error.log</code></td></tr>
  <tr><td>Systemd</td><td><code>journalctl -u fitxes-tecniques</code></td></tr>
</table>

<!-- ============ RESUM ============ -->
<h2>Resum</h2>
<table>
  <tr><th>Pas</th><th>Acci&oacute;</th><th>Temps</th></tr>
  <tr><td>1</td><td>Verificar paquets</td><td>2 min</td></tr>
  <tr><td>2</td><td>Crear BD PostgreSQL</td><td>5 min</td></tr>
  <tr><td>3</td><td>Clonar i configurar backend</td><td>10 min</td></tr>
  <tr><td>4</td><td>Compilar frontend</td><td>5 min</td></tr>
  <tr><td>5</td><td>Servei systemd</td><td>5 min</td></tr>
  <tr><td>6</td><td>Apache VirtualHost</td><td>10 min</td></tr>
  <tr><td>7</td><td>DNS + xarxa</td><td>5 min</td></tr>
  <tr><td>8</td><td>Migrar dades</td><td>10 min</td></tr>
  <tr><td>9</td><td>Verificaci&oacute;</td><td>5 min</td></tr>
  <tr><td></td><td><b>Total estimat</b></td><td><b>~57 min</b></td></tr>
</table>

<h3>Dades clau</h3>
<table>
  <tr><th>Parametre</th><th>Valor</th></tr>
  <tr><td>Directori</td><td><code>/var/www/fitxes-tecniques</code></td></tr>
  <tr><td>Servei</td><td><code>fitxes-tecniques</code></td></tr>
  <tr><td>Base de dades</td><td><code>fitxes_tecniques</code></td></tr>
  <tr><td>Usuari BD</td><td><code>fitxes_user</code></td></tr>
  <tr><td>URL</td><td><code>http://fitxesfc.agrienergia.local</code></td></tr>
  <tr><td>Repositori</td><td><code>github.com/ohijazo/FitxesTecniques</code></td></tr>
  <tr><td>Port backend</td><td>50002</td></tr>
</table>

</body>
</html>
"""


def main():
    output_path = '../Fitxes_Tecniques_Guia_Desplegament.pdf'
    result = io.BytesIO()
    pdf = pisa.pisaDocument(io.StringIO(HTML), result, encoding='utf-8')

    if pdf.err:
        print(f'Error: {pdf.err}')
        return

    with open(output_path, 'wb') as f:
        f.write(result.getvalue())

    print(f'PDF generat: {output_path}')
    print(f'Mida: {len(result.getvalue()) / 1024:.0f} KB')


if __name__ == '__main__':
    main()
