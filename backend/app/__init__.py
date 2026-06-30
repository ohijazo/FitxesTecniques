import logging
import os
from logging.handlers import RotatingFileHandler

import click
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_migrate import Migrate

db = SQLAlchemy()
migrate = Migrate()


def _configurar_logging():
    """Configura logging arrel. Si LOG_DIR està definit i és escriptible,
    afegeix un RotatingFileHandler; en cas contrari, queda només stderr.

    Variables d'entorn:
      LOG_LEVEL: nivell global (default INFO)
      LOG_DIR:   directori per a app.log (default cap = stderr)
    """
    level = os.environ.get('LOG_LEVEL', 'INFO').upper()
    fmt = '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    root = logging.getLogger()
    root.setLevel(level)
    # Evitar duplicar handlers si create_app es crida més d'un cop (tests)
    if any(getattr(h, '_fitxes_handler', False) for h in root.handlers):
        return

    log_dir = os.environ.get('LOG_DIR', '').strip()
    if log_dir:
        try:
            os.makedirs(log_dir, exist_ok=True)
            fh = RotatingFileHandler(
                os.path.join(log_dir, 'app.log'),
                maxBytes=10 * 1024 * 1024, backupCount=5, encoding='utf-8',
            )
            fh.setFormatter(logging.Formatter(fmt))
            fh._fitxes_handler = True
            root.addHandler(fh)
        except OSError as e:
            logging.getLogger(__name__).warning(
                'No s\'ha pogut crear el RotatingFileHandler a %s: %s', log_dir, e
            )


def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')

    if app.config.get('FLASK_ENV') == 'production':
        secret = app.config.get('SECRET_KEY')
        if not secret or secret == 'dev-secret-key':
            raise RuntimeError(
                "SECRET_KEY no definida (o usa el valor per defecte 'dev-secret-key') "
                "amb FLASK_ENV=production. Definiu un valor real a .env abans d'arrencar."
            )

    _configurar_logging()

    db.init_app(app)
    migrate.init_app(app, db)

    # CORS restringit: només el frontend en desenvolupament i producció
    allowed_origins = app.config.get('CORS_ORIGINS', ['http://localhost:5173', 'http://localhost:5174'])
    CORS(app, resources={r'/api/*': {'origins': allowed_origins}})

    from app.routes.fitxes import fitxes_bp
    from app.routes.versions import versions_bp
    from app.routes.distribucions import distribucions_bp
    from app.routes.admin import admin_bp
    from app.routes.auth import auth_bp
    from app.routes.jobs import jobs_bp
    from app.routes.bulk import bulk_bp
    from app.routes.health import health_bp

    app.register_blueprint(auth_bp, url_prefix='/api')
    app.register_blueprint(fitxes_bp, url_prefix='/api')
    app.register_blueprint(versions_bp, url_prefix='/api')
    app.register_blueprint(distribucions_bp, url_prefix='/api')
    app.register_blueprint(admin_bp, url_prefix='/api')
    app.register_blueprint(jobs_bp, url_prefix='/api')
    app.register_blueprint(bulk_bp, url_prefix='/api')
    app.register_blueprint(health_bp, url_prefix='/api')

    # Worker resident per processar JobBulk en background
    # Es llança un cop per procés (idempotent). Desactivable amb ENABLE_JOB_WORKER=0.
    if not app.config.get('TESTING'):
        from app.services.job_worker import iniciar_worker
        iniciar_worker(app)

    # Comanda per crear l'admin inicial
    @app.cli.command('crear-admin')
    @click.argument('email')
    @click.argument('nom')
    @click.argument('password')
    def crear_admin(email, nom, password):
        from app.models import Usuari
        if Usuari.query.filter_by(email=email).first():
            click.echo(f"L'usuari {email} ja existeix.")
            return
        usuari = Usuari(email=email, nom=nom, rol='admin')
        usuari.set_password(password)
        db.session.add(usuari)
        db.session.commit()
        click.echo(f"Admin creat: {email}")

    return app
