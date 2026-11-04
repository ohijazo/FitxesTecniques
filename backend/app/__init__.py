import click
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_migrate import Migrate

db = SQLAlchemy()
migrate = Migrate()


def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')

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
    from app.routes.public import public_bp
    from app.routes.enviaments import enviaments_bp
    from app.routes.traduccions import traduccions_bp

    app.register_blueprint(auth_bp, url_prefix='/api')
    app.register_blueprint(fitxes_bp, url_prefix='/api')
    app.register_blueprint(versions_bp, url_prefix='/api')
    app.register_blueprint(distribucions_bp, url_prefix='/api')
    app.register_blueprint(admin_bp, url_prefix='/api')
    app.register_blueprint(jobs_bp, url_prefix='/api')
    app.register_blueprint(bulk_bp, url_prefix='/api')
    app.register_blueprint(enviaments_bp, url_prefix='/api')
    app.register_blueprint(traduccions_bp, url_prefix='/api')
    # Nomes lectura, protegit per clau fixa. El fa servir l'aplicacio del DeCA.
    app.register_blueprint(public_bp, url_prefix='/api')

    # Traduccions: en crear una versió nova s'actualitzen soles (fil de fons).
    # Desactivable amb TRADUCCIO_AUTOMATICA=0.
    if not app.config.get('TESTING'):
        from app.services.traduccio_auto import registrar
        registrar(app)
        from app.services.traduccio import precarregar
        precarregar()

    # Worker resident per processar JobBulk en background
    # Es llança un cop per procés (idempotent). Desactivable amb ENABLE_JOB_WORKER=0.
    if not app.config.get('TESTING'):
        from app.services.job_worker import iniciar_worker
        iniciar_worker(app)

    # Ordres de la traducció inicial (exportar / importar traduccions)
    from app.cli_traduccions import registrar as registrar_cli_traduccions
    registrar_cli_traduccions(app)
    from app.cli_superindexs import registrar as registrar_cli_superindexs
    registrar_cli_superindexs(app)

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
