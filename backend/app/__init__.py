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

    app.register_blueprint(auth_bp, url_prefix='/api')
    app.register_blueprint(fitxes_bp, url_prefix='/api')
    app.register_blueprint(versions_bp, url_prefix='/api')
    app.register_blueprint(distribucions_bp, url_prefix='/api')
    app.register_blueprint(admin_bp, url_prefix='/api')

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
