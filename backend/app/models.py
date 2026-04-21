from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from app import db


class Usuari(db.Model):
    __tablename__ = 'usuari'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(200), unique=True, nullable=False)
    nom = db.Column(db.String(200), nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    rol = db.Column(db.String(20), nullable=False, default='visualitzador')
    actiu = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'nom': self.nom,
            'rol': self.rol,
            'actiu': self.actiu,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class DestiDistribucio(db.Model):
    __tablename__ = 'desti_distribucio'

    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    tipus = db.Column(db.String(20), nullable=False)  # 'ftp' | 'xarxa' | 'sap'
    configuracio = db.Column(db.JSON, nullable=False, default={})
    patro_nom_fitxer = db.Column(db.String(200), nullable=False, default='{art_codi}.pdf')
    actiu = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    created_by = db.Column(db.String(100))

    def to_dict(self, include_config=False):
        data = {
            'id': self.id,
            'nom': self.nom,
            'tipus': self.tipus,
            'patro_nom_fitxer': self.patro_nom_fitxer,
            'actiu': self.actiu,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'created_by': self.created_by,
        }
        if include_config:
            # No exposar passwords al frontend
            config = dict(self.configuracio) if self.configuracio else {}
            if 'password' in config:
                config['password'] = '********'
            data['configuracio'] = config
        return data


class TipusFitxa(db.Model):
    __tablename__ = 'tipus_fitxa'

    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False)
    descripcio = db.Column(db.Text, default='')
    actiu = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    seccions = db.relationship('SeccioFitxa', backref='tipus',
                               lazy='dynamic', order_by='SeccioFitxa.ordre',
                               cascade='all, delete-orphan')

    def to_dict(self, include_seccions=False):
        data = {
            'id': self.id,
            'nom': self.nom,
            'slug': self.slug,
            'descripcio': self.descripcio,
            'actiu': self.actiu,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'num_seccions': self.seccions.count(),
        }
        if include_seccions:
            data['seccions'] = [s.to_dict(include_camps=True) for s in self.seccions]
        return data


class FitxaTecnica(db.Model):
    __tablename__ = 'fitxa_tecnica'

    id = db.Column(db.Integer, primary_key=True)
    tipus_id = db.Column(db.Integer, db.ForeignKey('tipus_fitxa.id'), nullable=True)
    art_codi = db.Column(db.String(50), unique=True, nullable=False)
    nom_producte = db.Column(db.String(200), nullable=False)
    categoria = db.Column(db.String(100))
    estat = db.Column(db.String(20), default='esborrany')
    es_client = db.Column(db.Boolean, default=False)
    observacions = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))
    created_by = db.Column(db.String(100))

    tipus_rel = db.relationship('TipusFitxa', backref='fitxes')
    versions = db.relationship('VersioFitxa', backref='fitxa',
                               lazy='dynamic', order_by='VersioFitxa.num_versio.desc()')

    def to_dict(self, include_versions=False):
        data = {
            'id': self.id,
            'tipus_id': self.tipus_id,
            'tipus_nom': self.tipus_rel.nom if self.tipus_rel else None,
            'art_codi': self.art_codi,
            'nom_producte': self.nom_producte,
            'categoria': self.categoria,
            'estat': self.estat,
            'es_client': self.es_client,
            'observacions': self.observacions or '',
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'created_by': self.created_by,
        }
        if include_versions:
            data['versions'] = [v.to_dict() for v in self.versions]
        return data


class VersioFitxa(db.Model):
    __tablename__ = 'versio_fitxa'

    id = db.Column(db.Integer, primary_key=True)
    fitxa_id = db.Column(db.Integer, db.ForeignKey('fitxa_tecnica.id'), nullable=False)
    num_versio = db.Column(db.Integer, nullable=False)
    descripcio_canvi = db.Column(db.Text, nullable=False)
    contingut = db.Column(db.JSON)
    fitxer_docx = db.Column(db.String(500))
    fitxer_pdf = db.Column(db.String(500))
    data_comprovacio = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    created_by = db.Column(db.String(100))
    activa = db.Column(db.Boolean, default=False)
    estat_versio = db.Column(db.String(20), default='esborrany')  # esborrany|en_revisio|aprovada|publicada
    aprovat_per = db.Column(db.String(100))
    aprovat_at = db.Column(db.DateTime, nullable=True)

    distribucions = db.relationship('Distribucio', backref='versio', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id,
            'fitxa_id': self.fitxa_id,
            'num_versio': self.num_versio,
            'descripcio_canvi': self.descripcio_canvi,
            'contingut': self.contingut,
            'fitxer_docx': self.fitxer_docx,
            'fitxer_pdf': self.fitxer_pdf,
            'data_comprovacio': self.data_comprovacio.isoformat() if self.data_comprovacio else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'created_by': self.created_by,
            'activa': self.activa,
            'estat_versio': self.estat_versio or 'esborrany',
            'aprovat_per': self.aprovat_per,
            'aprovat_at': self.aprovat_at.isoformat() if self.aprovat_at else None,
        }


class Distribucio(db.Model):
    __tablename__ = 'distribucio'

    id = db.Column(db.Integer, primary_key=True)
    versio_id = db.Column(db.Integer, db.ForeignKey('versio_fitxa.id'), nullable=False)
    desti_id = db.Column(db.Integer, db.ForeignKey('desti_distribucio.id'), nullable=True)
    desti = db.Column(db.String(20), nullable=False)
    estat = db.Column(db.String(20), default='pendent')
    intents = db.Column(db.Integer, default=0)
    missatge_error = db.Column(db.Text)
    executat_at = db.Column(db.DateTime)
    executat_by = db.Column(db.String(100))

    def to_dict(self):
        return {
            'id': self.id,
            'versio_id': self.versio_id,
            'desti_id': self.desti_id,
            'desti': self.desti,
            'estat': self.estat,
            'intents': self.intents,
            'missatge_error': self.missatge_error,
            'executat_at': self.executat_at.isoformat() if self.executat_at else None,
            'executat_by': self.executat_by,
        }


class SeccioFitxa(db.Model):
    __tablename__ = 'seccio_fitxa'

    id = db.Column(db.Integer, primary_key=True)
    tipus_id = db.Column(db.Integer, db.ForeignKey('tipus_fitxa.id'), nullable=True)
    titol = db.Column(db.String(200), nullable=False)
    ordre = db.Column(db.Integer, default=0)

    camps = db.relationship('CampFitxa', backref='seccio',
                            lazy='dynamic', order_by='CampFitxa.ordre',
                            cascade='all, delete-orphan')

    def to_dict(self, include_camps=True):
        data = {
            'id': self.id,
            'tipus_id': self.tipus_id,
            'titol': self.titol,
            'ordre': self.ordre,
        }
        if include_camps:
            data['camps'] = [c.to_dict() for c in self.camps]
        return data


class CampFitxa(db.Model):
    __tablename__ = 'camp_fitxa'

    id = db.Column(db.Integer, primary_key=True)
    seccio_id = db.Column(db.Integer, db.ForeignKey('seccio_fitxa.id'), nullable=True)
    categoria = db.Column(db.String(100))
    nom = db.Column(db.String(100), nullable=False)
    label = db.Column(db.String(100), nullable=False)
    tipus = db.Column(db.String(20), default='text')  # text|textarea|number|date|select|taula
    obligatori = db.Column(db.Boolean, default=False)
    ordre = db.Column(db.Integer, default=0)
    opcions = db.Column(db.JSON)  # per select: llista opcions; per taula: columnes
    valor_defecte = db.Column(db.Text)

    def to_dict(self):
        return {
            'id': self.id,
            'seccio_id': self.seccio_id,
            'categoria': self.categoria,
            'nom': self.nom,
            'label': self.label,
            'tipus': self.tipus,
            'obligatori': self.obligatori,
            'ordre': self.ordre,
            'opcions': self.opcions,
            'valor_defecte': self.valor_defecte,
        }
