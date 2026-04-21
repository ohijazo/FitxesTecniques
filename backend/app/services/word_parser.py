"""Extreu les dades d'un fitxer .docx de fitxa tècnica.

El document segueix l'estructura estàndard de Farinera Coromina:
- Capçalera: Rev, Data revisió, Data comprovació
- Paràgrafs amb etiqueta + valor
- Taules de paràmetres (fisicoquímiques, reològiques, etc.)
"""
from docx import Document


def _clean(text):
    """Neteja text: treure espais duplicats i salts innecessaris."""
    if not text:
        return ''
    return ' '.join(text.strip().split())


def _extract_bilingual(text):
    """Extreu la part castellana d'un text bilingüe 'castellà / català'.
    Si no té separador, retorna el text complet."""
    if ' / ' in text:
        return text.split(' / ')[0].strip()
    return text.strip()


def _parse_header(doc):
    """Extreu rev, data_revisio, data_comprovacio de la capçalera."""
    info = {'rev': '', 'data_revisio': '', 'data_comprovacio': ''}

    for section in doc.sections:
        header = section.header
        if not header or not header.tables:
            continue

        for table in header.tables:
            for row in table.rows:
                for cell in row.cells:
                    text = cell.text.strip()
                    if text.startswith('Rev.:'):
                        info['rev'] = text.replace('Rev.:', '').strip()
                    elif 'Fecha' in text and 'rev' in text.lower() and 'comprov' not in text.lower():
                        parts = text.split(':')
                        if len(parts) >= 2:
                            info['data_revisio'] = parts[-1].strip()
                    elif 'comprov' in text.lower():
                        parts = text.split(':')
                        if len(parts) >= 2:
                            info['data_comprovacio'] = parts[-1].strip()
        break  # Només mirem la primera secció

    return info


def _parse_param_table(table):
    """Extreu files parametre/valor d'una taula estàndard."""
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

        # Saltar capçaleres
        if param.lower() in ('parámetro', 'parámetro / paràmetre', 'valor'):
            continue
        if not param or param == valor:
            continue

        # Netejar bilingüe del paràmetre
        param = _extract_bilingual(param)
        # Netejar salts de línia dins el paràmetre
        param = ' '.join(param.split('\n')[0:1])  # Primera línia del paràmetre

        rows.append({'parametre': param, 'valor': valor})

    return rows


# Mapeig d'etiquetes de paràgrafs a camps del contingut
FIELD_MAP = {
    'código de referencia': 'codi_referencia',
    'denominación comercial del producto': 'denominacio_comercial',
    'denominación jurídica del producto': 'denominacio_juridica',
    'código ean': 'codi_ean',
    'descripción del producto': 'descripcio',
    'origen del producto y procedencia del cereal': 'origen',
    'ingredientes': 'ingredients',
    'alérgenos': 'alergens',
    'ogm': 'ogm',
    'irradiación – ionización': 'irradiacio',
    'características organolépticas': 'caract_organoleptiques',
    'presentación – envase': 'presentacio_envase',
    'uso previsto': 'us_previst',
    'condiciones de almacenaje': 'condicions_emmagatzematge',
    'condiciones de transporte': 'condicions_transport',
    'vida útil del producto': 'vida_util',
    'otra legislación aplicable': 'legislacio_aplicable',
    'producto fabricado para (razón social)': 'fabricat_per',
    'vigencia del documento': 'vigencia_document',
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
            text_clean = _extract_bilingual(text).lower()
            for key, field in TABLE_MAP.items():
                if key in text_clean:
                    return field
    return None


def parse_docx(file_path):
    """Parseja un fitxer .docx de fitxa tècnica i retorna un dict amb les dades.

    Returns:
        dict amb:
            - 'contingut': dict amb tots els camps
            - 'rev': número de revisió
            - 'data_revisio': data de revisió
            - 'data_comprovacio': data de comprovació
            - 'art_codi': codi de referència (per identificar la fitxa)
    """
    doc = Document(file_path)

    # 1. Capçalera
    header_info = _parse_header(doc)

    # 2. Paràgrafs (camps de text)
    contingut = {}
    current_field = None

    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            current_field = None
            continue

        # Comprovar si és una etiqueta
        text_lower = _extract_bilingual(text).lower().rstrip('.')
        matched = False
        for label, field_name in FIELD_MAP.items():
            if text_lower.startswith(label) or label.startswith(text_lower):
                current_field = field_name
                matched = True
                break

        if matched:
            continue

        # Comprovar si és un títol de secció a ignorar
        if text_lower in SECTION_TITLES:
            current_field = None
            continue

        # Si tenim un camp actiu, assignar el valor
        if current_field:
            existing = contingut.get(current_field, '')
            if existing:
                contingut[current_field] = existing + '\n' + text
            else:
                contingut[current_field] = text

    # 3. Taules
    tables_data = {
        'fisicoquimiques': [],
        'reologiques': [],
        'microbiologiques': [],
        'micotoxines': [],
        'alcaloides': [],
        'metalls_pesants': [],
        'valors_nutricionals': [],
    }

    for table in doc.tables:
        table_type = _identify_table(table)
        if table_type and table_type in tables_data:
            rows = _parse_param_table(table)
            tables_data[table_type].extend(rows)

    contingut.update(tables_data)

    # Extreure art_codi
    art_codi = contingut.get('codi_referencia', '').strip()

    return {
        'contingut': contingut,
        'rev': header_info['rev'],
        'data_revisio': header_info['data_revisio'],
        'data_comprovacio': header_info['data_comprovacio'],
        'art_codi': art_codi,
    }
