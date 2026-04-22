import os
import io
import re
import base64
from flask import current_app
from jinja2 import Environment, FileSystemLoader
from xhtml2pdf import pisa


# Mapa de caràcters Unicode superíndex/subíndex a digits normals
SUPERSCRIPT_MAP = str.maketrans('⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ⁿ', '0123456789+-=()n')
SUBSCRIPT_MAP = str.maketrans('₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎', '0123456789+-=()')


def _fix_unicode_scripts(text):
    """Converteix caràcters Unicode superíndex/subíndex a tags HTML <sup>/<sub>."""
    if not text or not isinstance(text, str):
        return text

    # Superíndex: agrupar caràcters consecutius
    def replace_sup(m):
        digits = m.group(0).translate(SUPERSCRIPT_MAP)
        return f'<sup>{digits}</sup>'

    def replace_sub(m):
        digits = m.group(0).translate(SUBSCRIPT_MAP)
        return f'<sub>{digits}</sub>'

    text = re.sub(r'[⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ⁿ]+', replace_sup, text)
    text = re.sub(r'[₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎]+', replace_sub, text)
    return text


def _process_value(value):
    """Processa un valor (string o llista de dicts) per convertir superíndex."""
    if isinstance(value, str):
        return _fix_unicode_scripts(value)
    if isinstance(value, list):
        result = []
        for item in value:
            if isinstance(item, dict):
                result.append({
                    k: _fix_unicode_scripts(v) if isinstance(v, str) else v
                    for k, v in item.items()
                })
            else:
                result.append(item)
        return result
    return value


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
        'certificacio': contingut.get('certificacio', ''),
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

    # Convertir superíndex/subíndex Unicode a HTML <sup>/<sub>
    for key in ctx:
        if key != 'logo_path':
            ctx[key] = _process_value(ctx[key])

    # Recollir imatges del contingut (camps amb URLs /api/fitxes/...)
    imatges = []
    upload_base = os.path.join(current_app.root_path, '..', 'uploads')
    for key, val in contingut.items():
        if isinstance(val, str) and val.startswith('/api/fitxes/') and '/imatges/' in val:
            # Extreure path local de la imatge
            parts = val.split('/imatges/')
            if len(parts) == 2:
                filename = parts[1]
                art_codi = contingut.get('codi_referencia', '')
                img_path = os.path.join(upload_base, art_codi, 'img', filename)
                if os.path.exists(img_path):
                    with open(img_path, 'rb') as imgf:
                        img_b64 = base64.b64encode(imgf.read()).decode('utf-8')
                    ext = os.path.splitext(filename)[1].lower().lstrip('.')
                    if ext == 'svg':
                        mime = 'image/svg+xml'
                    else:
                        mime = f'image/{ext}' if ext in ('png', 'gif', 'webp') else 'image/jpeg'
                    imatges.append({
                        'key': key,
                        'data_uri': f'data:{mime};base64,{img_b64}',
                    })
    ctx['imatges'] = imatges

    html_content = template.render(**ctx)

    result = io.BytesIO()
    pdf = pisa.pisaDocument(io.StringIO(html_content), result, encoding='utf-8')

    if pdf.err:
        raise RuntimeError(f"Error generant PDF: {pdf.err}")

    return result.getvalue()
