"""Crea les seccions i camps per defecte de la fitxa tecnica."""
import sys
sys.path.insert(0, '.')

from app import create_app, db
from app.models import SeccioFitxa, CampFitxa

app = create_app()
with app.app_context():
    if SeccioFitxa.query.count() > 0:
        print('Ja hi ha seccions, saltant.')
        sys.exit(0)

    seccions = [
        {
            'titol': 'Identificacio del producte',
            'ordre': 1,
            'camps': [
                {'nom': 'denominacio_comercial', 'label': 'Denominacion comercial del Producto', 'tipus': 'text', 'obligatori': True, 'ordre': 1},
                {'nom': 'denominacio_juridica', 'label': 'Denominacion juridica del producto', 'tipus': 'text', 'obligatori': True, 'ordre': 2},
                {'nom': 'codi_ean', 'label': 'Codigo EAN', 'tipus': 'text', 'ordre': 3},
                {'nom': 'descripcio', 'label': 'Descripcion del producto', 'tipus': 'textarea', 'obligatori': True, 'ordre': 4,
                 'valor_defecte': 'Producto que se obtiene de la molienda del grano de trigo entero, maduro y sano.'},
                {'nom': 'origen', 'label': 'Origen del Producto y Procedencia del cereal', 'tipus': 'textarea', 'ordre': 5,
                 'valor_defecte': 'Producto elaborado en Espana, con cereal procedente de la UE.'},
                {'nom': 'ingredients', 'label': 'Ingredientes', 'tipus': 'textarea', 'obligatori': True, 'ordre': 6},
                {'nom': 'alergens', 'label': 'Alergenos', 'tipus': 'textarea', 'obligatori': True, 'ordre': 7},
                {'nom': 'ogm', 'label': 'OGM', 'tipus': 'textarea', 'ordre': 8,
                 'valor_defecte': 'Este producto no ha estado elaborado a partir de OGM ni con OGM. Conforme a los Reglamentos (CE) Num. 1829/2003 y 1830/2003.'},
                {'nom': 'irradiacio', 'label': 'Irradiacion - Ionizacion', 'tipus': 'textarea', 'ordre': 9,
                 'valor_defecte': 'Este producto no ha estado tratado con irradiacion ionizante y no contiene ingredientes irradiados. Segun Directiva 1999/2/CE'},
            ],
        },
        {
            'titol': 'Caracteristiques',
            'ordre': 2,
            'camps': [
                {'nom': 'caract_organoleptiques', 'label': 'Caracteristicas organolepticas', 'tipus': 'textarea', 'ordre': 1},
                {'nom': 'fisicoquimiques', 'label': 'Caracteristicas fisico-quimicas', 'tipus': 'taula', 'ordre': 2,
                 'opcions': {'columnes': ['Parametro', 'Valor']}},
                {'nom': 'reologiques', 'label': 'Caracteristicas reologicas', 'tipus': 'taula', 'ordre': 3,
                 'opcions': {'columnes': ['Parametro', 'Valor']}},
                {'nom': 'microbiologiques', 'label': 'Caracteristicas Microbiologicas', 'tipus': 'taula', 'ordre': 4,
                 'opcions': {'columnes': ['Parametro', 'Valor']}},
            ],
        },
        {
            'titol': 'Contaminants',
            'ordre': 3,
            'camps': [
                {'nom': 'micotoxines', 'label': 'Micotoxinas', 'tipus': 'taula', 'ordre': 1,
                 'opcions': {'columnes': ['Parametro', 'Valor']}},
                {'nom': 'alcaloides', 'label': 'Alcaloides del cornezuelo', 'tipus': 'taula', 'ordre': 2,
                 'opcions': {'columnes': ['Parametro', 'Valor']}},
                {'nom': 'metalls_pesants', 'label': 'Metales pesados', 'tipus': 'taula', 'ordre': 3,
                 'opcions': {'columnes': ['Parametro', 'Valor']}},
                {'nom': 'pesticidas', 'label': 'Pesticidas', 'tipus': 'textarea', 'ordre': 4,
                 'valor_defecte': 'De acuerdo con el Reglamento (CE) 396/2005 de 23 de febrero, relativo a los limites maximos de residuos de plaguicidas en alimentos y Piensos de origen vegetal y animal; y posteriores modificaciones.'},
            ],
        },
        {
            'titol': 'Valors nutricionals',
            'ordre': 4,
            'camps': [
                {'nom': 'valors_nutricionals', 'label': 'Valores nutricionales (por 100g)', 'tipus': 'taula', 'ordre': 1,
                 'opcions': {'columnes': ['Parametro', 'Valor']}},
            ],
        },
        {
            'titol': 'Informacio comercial i legal',
            'ordre': 5,
            'camps': [
                {'nom': 'presentacio_envase', 'label': 'Presentacion - envase', 'tipus': 'textarea', 'ordre': 1},
                {'nom': 'us_previst', 'label': 'Uso previsto', 'tipus': 'textarea', 'ordre': 2},
                {'nom': 'condicions_emmagatzematge', 'label': 'Condiciones de almacenaje', 'tipus': 'textarea', 'ordre': 3},
                {'nom': 'condicions_transport', 'label': 'Condiciones de transporte', 'tipus': 'textarea', 'ordre': 4},
                {'nom': 'vida_util', 'label': 'Vida util del producto', 'tipus': 'textarea', 'ordre': 5},
                {'nom': 'legislacio_aplicable', 'label': 'Otra legislacion aplicable', 'tipus': 'textarea', 'ordre': 6},
                {'nom': 'fabricat_per', 'label': 'Producto fabricado para (Razon social)', 'tipus': 'text', 'ordre': 7},
                {'nom': 'vigencia_document', 'label': 'Vigencia del documento', 'tipus': 'textarea', 'ordre': 8,
                 'valor_defecte': 'Esta ficha tecnica tiene una validez de 2 anos a partir de la fecha de comprobacion que aparece en la cabecera del documento.'},
            ],
        },
    ]

    for s_data in seccions:
        seccio = SeccioFitxa(titol=s_data['titol'], ordre=s_data['ordre'])
        db.session.add(seccio)
        db.session.flush()
        for c_data in s_data['camps']:
            camp = CampFitxa(
                seccio_id=seccio.id,
                nom=c_data['nom'],
                label=c_data['label'],
                tipus=c_data.get('tipus', 'text'),
                obligatori=c_data.get('obligatori', False),
                ordre=c_data.get('ordre', 0),
                opcions=c_data.get('opcions'),
                valor_defecte=c_data.get('valor_defecte', ''),
            )
            db.session.add(camp)

    db.session.commit()
    print('Seccions i camps creats correctament.')
