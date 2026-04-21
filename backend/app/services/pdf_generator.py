import os
import io
import base64
from flask import current_app
from jinja2 import Environment, FileSystemLoader
from xhtml2pdf import pisa


def generar_pdf(contingut, rev, data_revisio, data_comprovacio):
    """Genera un PDF a partir del contingut JSONB d'una versió de fitxa tècnica.

    Returns:
        bytes del PDF generat
    """
    template_dir = os.path.join(current_app.root_path, 'templates')
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template('fitxa_tecnica.html')

    # Convertir logo a base64 per embedir-lo al HTML
    logo_path = os.path.join(current_app.root_path, 'static', 'img', 'logo.png')
    with open(logo_path, 'rb') as f:
        logo_b64 = base64.b64encode(f.read()).decode('utf-8')
    logo_uri = f'data:image/png;base64,{logo_b64}'

    defaults = {
        'ogm': (
            'Este producto no ha estado elaborado a partir de OGM ni con OGM. '
            'Conforme a los Reglamentos (CE) Núm. 1829/2003 y 1830/2003.'
        ),
        'irradiacio': (
            'Este producto no ha estado tratado con irradiación ionizante '
            'y no contiene ingredientes irradiados. '
            'Según Directiva 1999/2/CE'
        ),
        'pesticidas': (
            'De acuerdo con el Reglamento (CE) 396/2005 de 23 de febrero, '
            'relativo a los límites máximos de residuos de plaguicidas en alimentos '
            'y Piensos de origen vegetal y animal; y posteriores modificaciones.'
        ),
        'vigencia_document': (
            'Esta ficha técnica tiene una validez de 2 años a partir de la fecha '
            'de comprobación que aparece en la cabecera del documento.'
        ),
    }

    default_nutricionals = [
        {'parametre': 'Valor energético', 'valor': '--', 'sub': False},
        {'parametre': 'Grasas', 'valor': '--', 'sub': False},
        {'parametre': 'De las cuales saturadas', 'valor': '--', 'sub': True},
        {'parametre': 'Hidratos de Carbono', 'valor': '--', 'sub': False},
        {'parametre': 'De los cuales azúcares', 'valor': '--', 'sub': True},
        {'parametre': 'Proteína', 'valor': '--', 'sub': False},
        {'parametre': 'Fibra alimentaria', 'valor': '--', 'sub': False},
        {'parametre': 'Sal', 'valor': '--', 'sub': False},
    ]

    ctx = {
        'logo_path': logo_uri,
        'rev': rev,
        'data_revisio': data_revisio or '',
        'data_comprovacio': data_comprovacio or '',
        'codi_referencia': contingut.get('codi_referencia', ''),
        'denominacio_comercial': contingut.get('denominacio_comercial', ''),
        'denominacio_juridica': contingut.get('denominacio_juridica', ''),
        'codi_ean': contingut.get('codi_ean', ''),
        'descripcio': contingut.get('descripcio', ''),
        'origen': contingut.get('origen', ''),
        'ingredients': contingut.get('ingredients', ''),
        'alergens': contingut.get('alergens', ''),
        'ogm': contingut.get('ogm', defaults['ogm']),
        'irradiacio': contingut.get('irradiacio', defaults['irradiacio']),
        'caract_organoleptiques': contingut.get('caract_organoleptiques', ''),
        'fisicoquimiques': contingut.get('fisicoquimiques', []),
        'reologiques': contingut.get('reologiques', []),
        'microbiologiques': contingut.get('microbiologiques', []),
        'micotoxines': contingut.get('micotoxines', []),
        'alcaloides': contingut.get('alcaloides', []),
        'metalls_pesants': contingut.get('metalls_pesants', []),
        'pesticidas': contingut.get('pesticidas', defaults['pesticidas']),
        'valors_nutricionals': contingut.get('valors_nutricionals', default_nutricionals),
        'presentacio_envase': contingut.get('presentacio_envase', ''),
        'us_previst': contingut.get('us_previst', ''),
        'condicions_emmagatzematge': contingut.get('condicions_emmagatzematge', ''),
        'condicions_transport': contingut.get('condicions_transport', ''),
        'vida_util': contingut.get('vida_util', ''),
        'legislacio_aplicable': contingut.get('legislacio_aplicable', ''),
        'fabricat_per': contingut.get('fabricat_per', ''),
        'vigencia_document': contingut.get('vigencia_document', defaults['vigencia_document']),
    }

    html_content = template.render(**ctx)

    result = io.BytesIO()
    pdf = pisa.pisaDocument(io.StringIO(html_content), result, encoding='utf-8')

    if pdf.err:
        raise RuntimeError(f"Error generant PDF: {pdf.err}")

    return result.getvalue()
