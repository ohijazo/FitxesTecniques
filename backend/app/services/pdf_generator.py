import os
import io
import re
import base64
from flask import current_app
from jinja2 import Environment, FileSystemLoader
from markupsafe import Markup
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


# Detecta línies que arriben embolcallades com a text secundari (marcades pel
# parser Word al importar via character style EnfasisSutil/cursiva-gris).
_ALREADY_SECONDARY_RE = re.compile(
    r'^\s*<span[^>]*color\s*:\s*#595959[^>]*>[\s\S]*</span>\s*$',
    re.IGNORECASE,
)


def _already_secondary(line):
    return bool(line and _ALREADY_SECONDARY_RE.match(line))


# Prefixos regulatoris: quan un paràgraf sencer editat manualment comença amb
# un d'aquests tokens, es marca automàticament com a text secundari (cursiva
# gris petita). No s'aplica a fragments embedded al mig d'un paràgraf per
# evitar falsos positius quan un text normal casualment conté "Se recomienda".
SECONDARY_PREFIXES = (
    'según', 'segons', 'se recomienda', 'es recomana', 'de acuerdo',
    'd\'acord', 'conforme a', 'conforme els',
)


def _starts_with_secondary_prefix(line):
    if not line:
        return False
    stripped = re.sub(r'<[^>]+>', '', line).strip().lower()
    return stripped.startswith(SECONDARY_PREFIXES)


_LIST_OPEN_RE = re.compile(r'<(ul|ol)\b[^>]*>', re.IGNORECASE)
_LIST_TAG_RE = re.compile(r'</?(?:ul|ol)\b[^>]*>', re.IGNORECASE)
_IS_LIST_BLOCK_RE = re.compile(r'^<(?:ul|ol)\b', re.IGNORECASE)


def _extract_list_blocks(text):
    """Talla el text en trossos (es_llista, contingut).

    Es fa amb un escaneig amb comptador de profunditat i no amb un regex simple
    per tancar be les llistes niuades (<ul> dins d'un <li>).
    """
    chunks = []
    pos = 0
    while True:
        m = _LIST_OPEN_RE.search(text, pos)
        if not m:
            break
        depth = 0
        end = None
        for t in _LIST_TAG_RE.finditer(text, m.start()):
            if t.group(0).startswith('</'):
                depth -= 1
                if depth <= 0:
                    end = t.end()
                    break
            else:
                depth += 1
        if end is None:
            break  # llista sense tancar: es tracta com a text normal
        if m.start() > pos:
            chunks.append((False, text[pos:m.start()]))
        chunks.append((True, text[m.start():end]))
        pos = end
    if pos < len(text):
        chunks.append((False, text[pos:]))
    return chunks


def _split_plain(text):
    """Separa text sense llistes en linies, gestionant <p>, <br> i \n."""
    text = text.strip()
    if not text:
        return []
    # HTML amb <p>: concatenar contingut de cada <p> amb \n
    p_matches = re.findall(r'<p[^>]*>(.*?)</p>', text, re.DOTALL | re.IGNORECASE)
    if p_matches:
        text = '\n'.join(p_matches)
    # Normalitzar <br> a \n perque el split final ho tracti tot igual
    text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
    lines = [line.strip() for line in text.split('\n')]
    return [line for line in lines if line and line != '&nbsp;']


def _split_paragraphs(text):
    """Separa un text en blocs: linies de text i blocs de llista <ul>/<ol>.

    Els blocs de llista es retornen sencers i sense tocar (els renderitza
    param_html); la resta segueix el tractament de sempre (<p>, <br> i \n).
    """
    text = str(text or '').strip()
    if not text:
        return []
    blocks = []
    for is_list, chunk in _extract_list_blocks(text):
        if is_list:
            blocks.append(chunk.strip())
        else:
            blocks.extend(_split_plain(chunk))
    return blocks


def generar_pdf(contingut, rev, data_revisio, data_comprovacio):
    """Genera un PDF a partir del contingut JSONB d'una versió de fitxa tècnica.

    Returns:
        bytes del PDF generat
    """
    template_dir = os.path.join(current_app.root_path, 'templates')
    env = Environment(loader=FileSystemLoader(template_dir))

    # Idioma del document: les fitxes de client són només en castellà i no han
    # de portar els títols duplicats "castellà / català". Per compatibilitat,
    # si la fitxa no ho té definit es manté el comportament bilingüe de sempre.
    idioma = contingut.get('_idioma') or 'bilingue'

    def bil(text):
        """Deixa només la part castellana d'un títol bilingüe.
        NOMÉS per a títols: els valors també poden contenir ' / '
        (p.ex. 'No detectado / 25g') i no s'han de tallar mai."""
        if idioma == 'es' and text and ' / ' in text:
            return text.split(' / ')[0].strip()
        return text
    env.filters['bil'] = bil

    # Filtre per renderitzar text preservant els paràgrafs (\n → <br>) i
    # normalitzant la mida dels spans de text secundari que ja venen marcats
    # pel parser Word (character style EnfasisSutil / cursiva-gris).
    def param_html(text):
        if not text:
            return Markup('')
        paragraphs = _split_paragraphs(text)
        if not paragraphs:
            return Markup('')

        secondary_style = 'font-size: 0.75em; color: #595959; font-style: italic;'

        def _render(p):
            if _already_secondary(p):
                # Normalitzar l'estil per uniformar mida amb la resta (les fitxes
                # importades amb versions anteriors poden portar mides diferents).
                return re.sub(r'<span[^>]*>', f'<span style="{secondary_style}">', p, count=1)
            if _starts_with_secondary_prefix(p):
                return f'<span style="{secondary_style}">{p}</span>'
            return p

        def _render_list(block):
            """Converteix un <ul>/<ol> en divs amb sagnat frances.

            No es fa servir <li> real perque xhtml2pdf sempre hi pinta un punt
            rodo (no hi ha cap list-style-type que doni el guio de l'original) i
            el seu suport de marges a <ul> es nomes parcial.
            """
            ordered = block.lstrip().lower().startswith('<ol')
            items = re.findall(r'<li[^>]*>(.*?)</li>', block, re.DOTALL | re.IGNORECASE)
            out = []
            for i, item in enumerate(items, 1):
                # Els <p> interns que hi posa l'editor no son salts de bloc aqui
                inner = re.sub(r'</p>\s*<p[^>]*>', '<br>', item, flags=re.IGNORECASE)
                inner = re.sub(r'</?p[^>]*>', '', inner, flags=re.IGNORECASE).strip()
                if not inner:
                    continue
                marca = f'{i}.' if ordered else '-'
                out.append(
                    '<tr>'
                    f'<td class="list-marker">{marca}</td>'
                    f'<td class="list-text">{_render(inner)}</td>'
                    '</tr>')
            if not out:
                return ''
            return '<table class="list-table">' + ''.join(out) + '</table>'

        def _render_block(block):
            if _IS_LIST_BLOCK_RE.match(block):
                return _render_list(block)
            return _render(block)

        parts = []
        for i, p in enumerate(paragraphs):
            block = _render_block(p)
            # Les llistes ja son blocs: no hi va <br> ni abans ni despres
            if i > 0 and not _IS_LIST_BLOCK_RE.match(p) \
                    and not _IS_LIST_BLOCK_RE.match(paragraphs[i - 1]):
                parts.append('<br>')
            parts.append(block)
        return Markup(''.join(parts))
    env.filters['param_html'] = param_html

    template = env.get_template('fitxa_tecnica.html')

    # Convertir logo a base64 per embedir-lo al HTML
    logo_path = os.path.join(current_app.root_path, 'static', 'img', 'logo.png')
    with open(logo_path, 'rb') as f:
        logo_b64 = base64.b64encode(f.read()).decode('utf-8')
    logo_uri = f'data:image/png;base64,{logo_b64}'

    ctx = {
        'logo_path': logo_uri,
        'idioma': idioma,
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
        'ogm': contingut.get('ogm', ''),
        'irradiacio': contingut.get('irradiacio', ''),
        'caract_organoleptiques': contingut.get('caract_organoleptiques', ''),
        'fisicoquimiques': contingut.get('fisicoquimiques', []),
        'reologiques': contingut.get('reologiques', []),
        'microbiologiques': contingut.get('microbiologiques', []),
        'micotoxines': contingut.get('micotoxines', []),
        'alcaloides': contingut.get('alcaloides', []),
        'metalls_pesants': contingut.get('metalls_pesants', []),
        'pesticidas': contingut.get('pesticidas', ''),
        'valors_nutricionals': contingut.get('valors_nutricionals', []),
        'presentacio_envase': contingut.get('presentacio_envase', ''),
        'us_previst': contingut.get('us_previst', ''),
        'condicions_emmagatzematge': contingut.get('condicions_emmagatzematge', ''),
        'condicions_transport': contingut.get('condicions_transport', ''),
        'vida_util': contingut.get('vida_util', ''),
        'legislacio_aplicable': contingut.get('legislacio_aplicable', ''),
        'fabricat_per': contingut.get('fabricat_per', ''),
        'vigencia_document': contingut.get('vigencia_document', ''),
    }

    # Peus de taula: només si estan explícitament guardats
    for key in ('fisicoquimiques', 'reologiques', 'microbiologiques',
                'micotoxines', 'alcaloides', 'metalls_pesants',
                'valors_nutricionals'):
        ctx[f'{key}_note'] = contingut.get(f'{key}_note') or ''

    # Convertir superíndex/subíndex Unicode a HTML <sup>/<sub>
    for key in ctx:
        if key not in ('logo_path', 'idioma'):
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

    # Configuracio de certificacio (posicio i mida)
    cert_config = contingut.get('_cert_config', {'align': 'right', 'size': 60})
    ctx['cert_align'] = cert_config.get('align', 'right')
    # Convertir px a pt per xhtml2pdf (1px ≈ 0.75pt)
    ctx['cert_height_pt'] = int(cert_config.get('size', 60) * 0.75)

    html_content = template.render(**ctx)

    result = io.BytesIO()
    pdf = pisa.pisaDocument(io.StringIO(html_content), result, encoding='utf-8')

    if pdf.err:
        raise RuntimeError(f"Error generant PDF: {pdf.err}")

    return result.getvalue()
