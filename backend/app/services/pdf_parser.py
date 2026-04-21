"""Extreu les dades d'un PDF de fitxa tècnica usant pdfplumber.

L'estructura dels PDFs de Farinera Coromina és:
- Pàgina 1: Capçalera + camps de text (identificació, ingredients, al·lèrgens...)
- Pàgina 2: Taules (fisicoquímiques, reològiques, microbiològiques)
- Pàgina 3: Contaminants (micotoxines, alcaloides, metalls pesants)
- Pàgina 4-5: Nutricionals, presentació, ús previst, emmagatzematge, transport...

El text és bilingüe castellà/català separat per " / ".
"""
import re
import pdfplumber


def _split_bilingual(text):
    """Separa text bilingüe castellà/català. Retorna només la part castellana.
    El separador és ' / ' però cal evitar separar valors numèrics com '0,5 / 0,8'."""
    if not text:
        return ''

    lines = text.split('\n')
    result_lines = []
    skip_next = False

    for i, line in enumerate(lines):
        if skip_next:
            skip_next = False
            continue

        line_s = line.strip()

        # Si la línia següent és la traducció catalana, saltar-la
        # La traducció sol començar amb article català o verb català
        if i + 1 < len(lines):
            next_line = lines[i + 1].strip().lower()
            # Si la línia actual conté " / " amb text significatiu als dos costats
            if ' / ' in line_s:
                parts = line_s.split(' / ')
                # Si la primera part és text significatiu (no numèric)
                if len(parts[0]) > 5 and not re.match(r'^[\d,.\s\-–≤≥<>%]+$', parts[0]):
                    result_lines.append(parts[0].strip())
                    continue

        # Línia sense separador bilingüe dins
        if ' / ' in line_s:
            parts = line_s.split(' / ')
            if len(parts[0]) > 5 and not re.match(r'^[\d,.\s\-–≤≥<>%]+$', parts[0]):
                result_lines.append(parts[0].strip())
                continue

        result_lines.append(line_s)

    # Post-procés: eliminar línies que són clarament traducció catalana
    # (comencen amb articles/preposicions catalans comuns i la línia anterior té sentit)
    final = []
    catalan_starts = [
        'producte ', 'producte.', "s'obté", 'segons ', 'conforme els',
        'aquest producte', 'farina ', 'conté ', 'contenir ', 'pot contenir',
        'no ha estat', 'ingredients irradiats', 'no detectat',
        'espanya,', "d'acord ", 'conservar en un lloc', 'es recomana',
        'no es requereix', 'consumir preferentment', 'aquesta fitxa',
        'des de la data', 'en sac de paper', 'tots els materials',
        'com a sistema preventiu', 'productes de fleca',
        'la farina crua', 'no apte per', 'i no exposat',
        'emmagatzemar els palets', 'ambient i en èpoques',
        'paret.', 'recomana complir', 'correcta rotació',
        'reclamacions relacionades',
    ]
    for line in result_lines:
        line_lower = line.lower().strip()
        is_catalan = False
        for prefix in catalan_starts:
            if line_lower.startswith(prefix):
                is_catalan = True
                break
        if not is_catalan:
            final.append(line)

    return '\n'.join(final).strip()


def _clean_param_name(text):
    """Neteja el nom d'un paràmetre de taula: treu part catalana i notes."""
    if not text:
        return ''
    # Treure notes regulatòries (Según RD... / Segons RD...)
    text = re.split(r'\nSegún ', text)[0]
    text = re.split(r'\nSegons ', text)[0]
    return text.strip()


def _parse_header(pages):
    """Extreu rev, data_revisio, data_comprovacio de la capçalera."""
    info = {'rev': '', 'data_revisio': '', 'data_comprovacio': ''}

    for page in pages:
        tables = page.extract_tables()
        for table in tables:
            for row in table:
                for cell in row:
                    if not cell:
                        continue
                    if 'Rev.:' in cell:
                        m = re.search(r'Rev\.:\s*(\d+)', cell)
                        if m:
                            info['rev'] = m.group(1)
                    if 'Fecha' in cell and 'Rev' in cell and 'Comprov' not in cell:
                        m = re.search(r'(\d{1,2}/\d{1,2}/\d{4})', cell)
                        if m:
                            info['data_revisio'] = m.group(1)
                    if 'Comprov' in cell:
                        m = re.search(r'(\d{1,2}/\d{1,2}/\d{4})', cell)
                        if m:
                            info['data_comprovacio'] = m.group(1)
        break

    return info


# Etiquetes de camp ordenades per ordre d'aparició al PDF.
# Cada tupla: (etiqueta per detectar a l'inici de línia, nom camp JSON)
FIELD_LABELS = [
    ('código de referencia', 'codi_referencia'),
    ('codi de referència', 'codi_referencia'),
    ('certificación', 'certificacio'),
    ('certificació', 'certificacio'),
    ('denominación comercial', 'denominacio_comercial'),
    ('denominació comercial', 'denominacio_comercial'),
    ('denominación jurídica', 'denominacio_juridica'),
    ('denominació jurídica', 'denominacio_juridica'),
    ('código ean', 'codi_ean'),
    ('codi ean', 'codi_ean'),
    ('descripción del producto', 'descripcio'),
    ('descripció del producte', 'descripcio'),
    ('origen del producto', 'origen'),
    ('origen del producte', 'origen'),
    ('ingredientes', 'ingredients'),
    ('ingredients', 'ingredients'),
    ('alérgenos', 'alergens'),
    ('al·lèrgens', 'alergens'),
    ('ogm', 'ogm'),
    ('irradiación', 'irradiacio'),
    ('irradiació', 'irradiacio'),
    ('características organolépticas', 'caract_organoleptiques'),
    ('característiques organolèptiques', 'caract_organoleptiques'),
    ('presentación', 'presentacio_envase'),
    ('presentació', 'presentacio_envase'),
    ('uso previsto', 'us_previst'),
    ('ús previst', 'us_previst'),
    ('condiciones de almacenaje', 'condicions_emmagatzematge'),
    ("condicions d'emmagatzematge", 'condicions_emmagatzematge'),
    ('condiciones de transporte', 'condicions_transport'),
    ('condicions de transport', 'condicions_transport'),
    ('vida útil', 'vida_util'),
    ('otra legislación', 'legislacio_aplicable'),
    ('altra legislació', 'legislacio_aplicable'),
    ('producto fabricado para', 'fabricat_per'),
    ('producte fabricat per', 'fabricat_per'),
    ('vigencia del documento', 'vigencia_document'),
    ('vigència del document', 'vigencia_document'),
    ('pesticidas', 'pesticidas'),
    ('pesticides', 'pesticidas'),
    ('níquel', 'niquel'),
]

# Títols de secció que no són camps de text
SECTION_TITLES = [
    'características físico',
    'características reológicas',
    'características microbiológicas',
    'parámetros de contaminantes',
    'valores nutricionales',
    'parámetros microbiológicos',
]

# Subtítols explícits dins la taula (primera fila sol ser el subtítol)
# Aquestes classificacions tenen màxima prioritat
SUBTITLE_CLASSIFIERS = [
    ('micotoxines', ['micotoxinas']),
    ('alcaloides', ['alcaloides del cornezuelo', 'alcaloides de cornezuelo']),
    ('metalls_pesants', ['metales pesados']),
    ('microbiologiques', ['parámetros microbiológicos']),
    ('valors_nutricionals', ['valores nutricionales']),
    ('lipids', ['lípidos']),
]

# Classificació per contingut (quan no hi ha subtítol explícit)
# fisicoquimiques va primer perquè les taules mixtes solen ser sota aquest títol
CONTENT_CLASSIFIERS = [
    ('valors_nutricionals', ['valor energético', 'energía']),
    ('microbiologiques', ['aerobios', 'hongos', 'e. coli', 'salmonella']),
    ('reologiques', ['p/l', 'índice de caída']),
    ('fisicoquimiques', ['humedad', 'proteína', 'cenizas', 'gluten']),
    ('lipids', ['ácidos grasos', 'colesterol']),
]

# Classificació per fila individual (paràmetre → categoria)
# S'usa per taules mixtes on una sola taula conté files de categories diferents
ROW_CLASSIFIERS = {
    'fisicoquimiques': [
        'humedad', 'proteína', 'proteïna', 'gluten', 'cenizas', 'cendres',
        '% harina extraña', '% farina estranya', 'gluten índex', 'gluten seco',
        'lípidos totales',
    ],
    'reologiques': ['índice de caída'],
    'microbiologiques': [
        'aerobios', 'hongos', 'mohos', 'e. coli', 'escherichia',
        'salmonella', 'enterobact',
    ],
    'micotoxines': [
        'aflatoxina', 'ocratoxina', 'desoxinivalenol', 'deoxinivalenol',
        'zearalenona', 'ht-2', 't-2', 'toxinas t2',
    ],
    'alcaloides': ['alcaloides', 'atropina', 'escopolanina'],
    'metalls_pesants': ['cadmio', 'plomo', 'melamina', 'níquel', 'niquel'],
    'contaminants_altres': ['ác.cianhídrico', 'residuos plaguicid',
                            'mijo pelado', 'amapola', 'pipa girasol', 'lino'],
}


def _classify_row(param_text):
    """Classifica una fila individual pel nom del paràmetre."""
    param_lower = param_text.lower().strip()
    for category, keywords in ROW_CLASSIFIERS.items():
        for kw in keywords:
            if param_lower.startswith(kw) or kw in param_lower:
                return category
    return None


def _classify_table(table):
    """Classifica una taula pel seu contingut.

    Returns:
        tuple (category, is_subtitle_match)
        - category: nom de la categoria o None
        - is_subtitle_match: True si la taula té un subtítol explícit
    """
    all_text = ' '.join(
        (cell or '').lower()
        for row in table
        for cell in row
    )

    if 'ficha técnica' in all_text and 'rev.:' in all_text:
        return None, False

    if 'pesticidas' in all_text and 'reglamento' in all_text:
        return None, False

    # 1. Buscar subtítol explícit (primera fila de la taula)
    #    Ex: "Micotoxinas / Micotoxines" com a cel·la de subtítol
    first_rows_text = ' '.join(
        (cell or '').lower()
        for row in table[:2]
        for cell in row
    )
    for category, keywords in SUBTITLE_CLASSIFIERS:
        for kw in keywords:
            if kw in first_rows_text:
                return category, True

    # 2. Classificació per contingut (sense subtítol → pot ser taula mixta)
    for category, keywords in CONTENT_CLASSIFIERS:
        for kw in keywords:
            if kw in all_text:
                return category, False

    return None, False


def _extract_table_rows(table):
    """Extreu files parametre/valor d'una taula (sense classificar)."""
    rows = []
    for row in table:
        raw_cells = [(c or '').strip() for c in row]
        non_empty = [(i, c) for i, c in enumerate(raw_cells) if c]
        if len(non_empty) < 2:
            continue

        param = non_empty[0][1]
        valor = non_empty[-1][1]
        if param == valor and len(non_empty) > 1:
            valor = non_empty[1][1]

        # Saltar capçaleres i subtítols
        param_lower = param.lower()
        skip_exact = ['parámetro', 'valor', 'valor límite',
                      'parámetro / paràmetre']
        skip_starts = [
            'micotoxinas', 'alcaloides del',
            'metales pesados', 'valores nutricionales',
            'parámetros microbiológicos', 'minerales',
            'vitaminas', 'lípidos',
        ]
        if param_lower in skip_exact or \
           any(param_lower.startswith(s) for s in skip_starts):
            continue
        if not param or param == valor:
            continue

        param_clean = _clean_param_name(param)
        if not param_clean:
            continue

        # Per params multi-línia: separar sub-ítems (De las cuales saturades)
        # Però ignorar notes regulatòries (Según RD...)
        if '\n' in param:
            lines = param.split('\n')
            main_param = _clean_param_name(lines[0])
            sub_entries = [{'parametre': main_param, 'valor': valor, 'sub': False}]
            for subline in lines[1:]:
                subline_lower = subline.strip().lower()
                # Ignorar notes regulatòries i traduccions
                if subline_lower.startswith('según ') or subline_lower.startswith('segons ') or \
                   subline_lower.startswith('conforme ') or not subline.strip():
                    continue
                sub_clean = _clean_param_name(subline)
                if sub_clean:
                    sub_entries.append({'parametre': sub_clean, 'valor': valor, 'sub': True})
            rows.extend(sub_entries)
            continue

        rows.append({'parametre': param_clean, 'valor': valor.strip()})

    return rows


def _parse_text_fields(pages):
    """Parseja els camps de text de totes les pàgines."""
    contingut = {}
    current_field = None

    for page in pages:
        text = page.extract_text() or ''
        lines = text.split('\n')

        # Detectar si la pàgina comença amb capçalera repetida
        # Si és així, el camp actiu de la pàgina anterior ha de continuar
        page_has_header = any(
            'FICHA TÉCNICA' in (l or '') or 'FITXA TÈCNICA' in (l or '')
            for l in lines[:5]
        )

        for line in lines:
            line = line.strip()
            if not line:
                # No resetejar current_field si estem entre pàgines
                # (les línies buides entre capçalera i contingut no tallen el camp)
                continue

            # Ignorar peu de pàgina i números de pàgina (1-9)
            if line.startswith('AGRI-ENERGIA') or line.startswith('C/ Girona') or \
               line.startswith('www.farinera') or re.match(r'^[1-9]$', line):
                continue

            # Ignorar capçalera repetida
            if 'FICHA TÉCNICA' in line or 'FITXA TÈCNICA' in line or \
               line.startswith('Rev.:') or \
               line.startswith('Fecha') or 'Comprov' in line:
                continue

            line_lower = line.lower()

            # Cas especial: "00Código de referencia..." (el PDF fusiona dígits amb l'etiqueta)
            cleaned_lower = re.sub(r'^\d+', '', line_lower)

            # Comprovar si és una etiqueta de camp (NOMÉS startswith)
            # Per etiquetes bilingües "Condiciones de almacenaje / Condicions d'emmagatzematge"
            # comprovar també la part després del " / "
            matched_field = None
            check_texts = [line_lower, cleaned_lower]
            if ' / ' in line_lower:
                parts = line_lower.split(' / ')
                check_texts.extend([p.strip() for p in parts])
            for label, field_name in FIELD_LABELS:
                for check in check_texts:
                    if check.startswith(label):
                        matched_field = field_name
                        break
                if matched_field:
                    break

            if matched_field:
                current_field = matched_field
                continue

            # Comprovar si és títol de secció
            is_section = False
            for s in SECTION_TITLES:
                if line_lower.startswith(s):
                    is_section = True
                    current_field = None
                    break
            if is_section:
                continue

            # Ignorar notes establerts/según que no pertanyen a cap camp
            if line_lower.startswith('establecidos como') or \
               line_lower.startswith('establerts com'):
                continue

            # Si tenim un camp actiu, afegir el valor
            if current_field:
                existing = contingut.get(current_field, '')
                if existing:
                    contingut[current_field] = existing + '\n' + line
                else:
                    contingut[current_field] = line

    return contingut


def parse_pdf(file_path):
    """Parseja un PDF de fitxa tècnica i retorna un dict amb totes les dades.

    Returns:
        dict amb:
            - 'contingut': dict amb tots els camps
            - 'rev': número de revisió
            - 'data_revisio': data de revisió
            - 'data_comprovacio': data de comprovació
            - 'art_codi': codi de referència
    """
    with pdfplumber.open(file_path) as pdf:
        pages = pdf.pages

        # 1. Capçalera
        header_info = _parse_header(pages)

        # 2. Camps de text
        contingut = _parse_text_fields(pages)

        # 3. Taules
        tables_data = {
            'fisicoquimiques': [],
            'reologiques': [],
            'microbiologiques': [],
            'micotoxines': [],
            'alcaloides': [],
            'metalls_pesants': [],
            'valors_nutricionals': [],
            'contaminants_altres': [],
        }

        # Categories on la taula és fiable i no cal reclassificar files
        for page in pages:
            tables = page.extract_tables()
            for table in tables:
                table_category, has_subtitle = _classify_table(table)
                if table_category is None:
                    continue

                rows = _extract_table_rows(table)

                if has_subtitle:
                    # Taula amb subtítol explícit → confiar al 100%
                    for row_data in rows:
                        if table_category in tables_data:
                            tables_data[table_category].append(row_data)
                else:
                    # Taula sense subtítol → pot ser mixta, tots els valors
                    # queden sota la categoria detectada (ex: fisicoquimiques)
                    for row_data in rows:
                        if table_category in tables_data:
                            tables_data[table_category].append(row_data)

        # Fusionar lipids dins valors_nutricionals
        if 'lipids' in tables_data:
            tables_data['valors_nutricionals'].extend(tables_data.pop('lipids'))

        # Eliminar categories buides
        for key in list(tables_data.keys()):
            if not tables_data[key]:
                del tables_data[key]

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
