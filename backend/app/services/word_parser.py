"""Extreu les dades d'un fitxer .docx de fitxa tècnica.

El document segueix l'estructura estàndard de Farinera Coromina:
- Capçalera: Rev, Data revisió, Data comprovació
- Paràgrafs amb etiqueta + valor
- Taules de paràmetres (fisicoquímiques, reològiques, etc.)
"""
import os
from docx import Document
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph
from docx.table import Table


def _extract_images(doc):
    """Extreu totes les imatges incrustades al document.

    Retorna llista de dicts: {'filename': 'image1.png', 'content_type': 'image/png', 'blob': bytes}
    """
    imatges = []
    seen = set()
    for rel_id, rel in doc.part.rels.items():
        if 'image' not in rel.reltype:
            continue
        try:
            part = rel.target_part
        except Exception:
            continue
        blob = part.blob
        if not blob:
            continue
        # Dedup per contingut (mateixa imatge referenciada més d'un cop)
        sig = (len(blob), blob[:32])
        if sig in seen:
            continue
        seen.add(sig)

        partname = getattr(part, 'partname', '') or ''
        original = os.path.basename(str(partname)) or f'image_{len(imatges) + 1}'
        content_type = getattr(part, 'content_type', '') or 'image/png'
        ext = os.path.splitext(original)[1]
        if not ext:
            mime_to_ext = {
                'image/png': '.png',
                'image/jpeg': '.jpg',
                'image/gif': '.gif',
                'image/webp': '.webp',
                'image/bmp': '.bmp',
                'image/svg+xml': '.svg',
            }
            ext = mime_to_ext.get(content_type, '.png')
            original = f'{original}{ext}'

        imatges.append({
            'filename': original,
            'content_type': content_type,
            'blob': blob,
        })
    return imatges


def _clean(text):
    """Neteja text: treure espais duplicats i salts innecessaris."""
    if not text:
        return ''
    return ' '.join(text.strip().split())


def _extract_bilingual(text):
    """Retorna el text complet (bilingüe). Per identificar etiquetes,
    retorna la part castellana per fer match."""
    return text.strip()


def _extract_bilingual_for_match(text):
    """Extreu la part castellana per fer match amb etiquetes."""
    if ' / ' in text:
        return text.split(' / ')[0].strip()
    return text.strip()


def _parse_header(doc):
    """Extreu rev, data_revisio, data_comprovacio de la capçalera.
    Busca tant al header de Word com a les taules del body."""
    info = {'rev': '', 'data_revisio': '', 'data_comprovacio': ''}

    def _check_cell(text):
        # Rev.: número — excloent "Fecha/Data Rev: dd/mm/aaaa" que també conté "Rev:"
        if ('Rev.:' in text or 'Rev:' in text) and 'Fecha' not in text and 'Data' not in text:
            import re
            m = re.search(r'Rev\.?:\s*(\d+)', text)
            if m:
                info['rev'] = m.group(1)
        if ('Fecha' in text or 'Data' in text) and ('rev' in text.lower() or 'Rev' in text) and 'comprov' not in text.lower():
            parts = text.split(':')
            if len(parts) >= 2:
                val = parts[-1].strip()
                if val and len(val) >= 6:
                    info['data_revisio'] = val
        if 'comprov' in text.lower() or 'Comprov' in text:
            parts = text.split(':')
            if len(parts) >= 2:
                val = parts[-1].strip()
                if val and len(val) >= 6:
                    info['data_comprovacio'] = val

    # Buscar al header de Word
    for section in doc.sections:
        header = section.header
        if not header or not header.tables:
            continue
        for table in header.tables:
            for row in table.rows:
                for cell in row.cells:
                    _check_cell(cell.text.strip())
        break

    # Si no s'ha trobat, buscar a les primeres taules del body
    if not info['rev']:
        for table in doc.tables[:3]:
            for row in table.rows:
                for cell in row.cells:
                    _check_cell(cell.text.strip())
            if info['rev']:
                break

    return info


def _parse_param_table(table):
    """Extreu files parametre/valor d'una taula estàndard.
    Manté el text complet bilingüe dels paràmetres i notes."""
    rows = []
    for row in table.rows:
        cells = [cell.text.strip() for cell in row.cells]
        # Dedup merged cells
        deduped = []
        prev = None
        for c in cells:
            if c != prev:
                deduped.append(c)
            prev = c

        if len(deduped) < 2:
            continue

        param = deduped[0]
        valor = deduped[1]

        # Saltar capçaleres de taula
        param_lower = param.lower().strip()
        skip = ['parámetro', 'parámetro / paràmetre', 'valor', 'valor límite']
        if param_lower in skip:
            continue
        if not param or param == valor:
            continue

        # Mantenir text complet (bilingüe + notes com Según RD...)
        # Netejar espais excessius però conservar salts de línia significatius
        param_clean = '\n'.join(line.strip() for line in param.split('\n') if line.strip())

        rows.append({'parametre': param_clean, 'valor': valor})

    return rows


# Mapeig d'etiquetes de paràgrafs a camps del contingut
FIELD_MAP = {
    'código de referencia': 'codi_referencia',
    'codi de referència': 'codi_referencia',
    'certificación': 'certificacio',
    'certificació': 'certificacio',
    'denominación comercial del producto': 'denominacio_comercial',
    'denominació comercial del producte': 'denominacio_comercial',
    'denominación jurídica del producto': 'denominacio_juridica',
    'denominació jurídica del producte': 'denominacio_juridica',
    'código ean': 'codi_ean',
    'codi ean': 'codi_ean',
    'descripción del producto': 'descripcio',
    'descripció del producte': 'descripcio',
    'origen del producto y procedencia del cereal': 'origen',
    'origen del producte i procedència del cereal': 'origen',
    'ingredientes': 'ingredients',
    'ingredients': 'ingredients',
    'alérgenos': 'alergens',
    'al·lèrgens': 'alergens',
    'ogm': 'ogm',
    'irradiación – ionización': 'irradiacio',
    'irradiación': 'irradiacio',
    'irradiació': 'irradiacio',
    'características organolépticas': 'caract_organoleptiques',
    'característiques organolèptiques': 'caract_organoleptiques',
    'presentación – envase': 'presentacio_envase',
    'presentació': 'presentacio_envase',
    'uso previsto': 'us_previst',
    'ús previst': 'us_previst',
    'condiciones de almacenaje': 'condicions_emmagatzematge',
    "condicions d'emmagatzematge": 'condicions_emmagatzematge',
    'condiciones de transporte': 'condicions_transport',
    'condicions de transport': 'condicions_transport',
    'vida útil del producto': 'vida_util',
    'vida útil del producte': 'vida_util',
    'otra legislación aplicable': 'legislacio_aplicable',
    'altra legislació aplicable': 'legislacio_aplicable',
    'producto fabricado para (razón social)': 'fabricat_per',
    'producto fabricado para': 'fabricat_per',
    'producte fabricat per a': 'fabricat_per',
    'vigencia del documento': 'vigencia_document',
    'vigència del document': 'vigencia_document',
    'pesticidas': 'pesticidas',
    'pesticides': 'pesticidas',
}

# Títols de seccions a ignorar (no són camps de text)
SECTION_TITLES = {
    'características físico – químicas',
    'características físico-químicas',
    'características reológicas',
    'características microbiológicas',
    'parámetros de contaminantes',
    'valores nutricionales',
    'pesticidas',
}

# Títols de taules i el camp JSON corresponent
TABLE_MAP = {
    'humedad': 'fisicoquimiques',
    'proteína': 'fisicoquimiques',
    'w': 'reologiques',
    'p/l': 'reologiques',
    'aerobios': 'microbiologiques',
    'parámetros microbiológicos': 'microbiologiques',
    'micotoxinas': 'micotoxines',
    'aflatoxina': 'micotoxines',
    'alcaloides': 'alcaloides',
    'metales pesados': 'metalls_pesants',
    'cadmio': 'metalls_pesants',
    'pesticidas': 'pesticidas_taula',
    'valores nutricionales': 'valors_nutricionals',
    'valor energético': 'valors_nutricionals',
}


def _identify_table(table):
    """Identifica a quina secció pertany una taula pel seu contingut."""
    for row in table.rows:
        for cell in row.cells:
            text = cell.text.strip().lower()
            text_clean = _extract_bilingual_for_match(text).lower()
            for key, field in TABLE_MAP.items():
                if key in text_clean or key in text:
                    return field
    return None


def _iter_body_items(doc):
    """Itera els elements del body en ordre de document: (kind, obj)
    on kind és 'p' (paràgraf) o 't' (taula)."""
    body = doc.element.body
    for child in body.iterchildren():
        tag = child.tag
        if tag == qn('w:p'):
            yield ('p', Paragraph(child, doc))
        elif tag == qn('w:tbl'):
            yield ('t', Table(child, doc))


def _match_field_label(text):
    """Retorna el nom del camp si el text coincideix amb una etiqueta, o None."""
    text_for_match = _extract_bilingual_for_match(text).lower().rstrip('.')
    for label, field_name in FIELD_MAP.items():
        if text_for_match.startswith(label) or label.startswith(text_for_match):
            return field_name
    return None


def _is_section_title(text):
    text_for_match = _extract_bilingual_for_match(text).lower().rstrip('.')
    return text_for_match in SECTION_TITLES


def parse_docx(file_path):
    """Parseja un fitxer .docx de fitxa tècnica i retorna un dict amb les dades.

    Returns:
        dict amb:
            - 'contingut': dict amb tots els camps
            - 'rev': número de revisió
            - 'data_revisio': data de revisió
            - 'data_comprovacio': data de comprovació
            - 'art_codi': codi de referència (per identificar la fitxa)
            - 'imatges': llista de dicts {'filename', 'content_type', 'blob'} extretes del docx
    """
    doc = Document(file_path)

    # 1. Capçalera
    header_info = _parse_header(doc)

    # 2. Iterar en ordre de document: paràgrafs + taules barrejats
    contingut = {}
    tables_data = {
        'fisicoquimiques': [],
        'reologiques': [],
        'microbiologiques': [],
        'micotoxines': [],
        'alcaloides': [],
        'metalls_pesants': [],
        'valors_nutricionals': [],
    }
    current_field = None       # camp de text actiu (per paràgrafs següents)
    last_table_key = None      # última taula processada (per capturar el peu)

    for kind, item in _iter_body_items(doc):
        if kind == 'p':
            text = item.text.strip()
            if not text:
                continue  # línia en blanc: NO resetejar current_field

            # Nova etiqueta → canvi de camp
            field = _match_field_label(text)
            if field is not None:
                current_field = field
                last_table_key = None
                continue

            # Títol de secció → reset (però mantenir last_table_key per notes)
            if _is_section_title(text):
                current_field = None
                continue

            # Text lliure: prioritzar peu de taula si acabem de processar una taula
            if last_table_key and current_field is None:
                note_key = f'{last_table_key}_note'
                existing = contingut.get(note_key, '')
                contingut[note_key] = (existing + '\n' + text) if existing else text
                continue

            # Assignar al camp de text actiu
            if current_field:
                existing = contingut.get(current_field, '')
                contingut[current_field] = (existing + '\n' + text) if existing else text

        elif kind == 't':
            table_type = _identify_table(item)
            current_field = None  # una taula tanca el camp de text actiu

            if table_type == 'pesticidas_taula':
                # Taula amb estructura títol + text (fila 0 = "Pesticidas / Pesticides",
                # files següents = contingut bilingüe). No és paràmetre/valor.
                text_parts = []
                for row in item.rows[1:]:
                    for cell in row.cells:
                        t = cell.text.strip()
                        if t and t not in text_parts:
                            text_parts.append(t)
                if text_parts and not contingut.get('pesticidas'):
                    contingut['pesticidas'] = '\n'.join(text_parts)
                last_table_key = None
                continue

            if table_type and table_type in tables_data:
                rows = _parse_param_table(item)
                tables_data[table_type].extend(rows)
                last_table_key = table_type
            else:
                last_table_key = None

    contingut.update(tables_data)

    # Extreure art_codi
    art_codi = contingut.get('codi_referencia', '').strip()

    # Extreure imatges incrustades
    imatges = _extract_images(doc)

    return {
        'contingut': contingut,
        'rev': header_info['rev'],
        'data_revisio': header_info['data_revisio'],
        'data_comprovacio': header_info['data_comprovacio'],
        'art_codi': art_codi,
        'imatges': imatges,
    }
