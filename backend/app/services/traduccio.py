"""Traduccions de les fitxes tècniques.

- separar_bilingue(): proposa la part castellana o catalana d'un contingut
  bilingüe ("castellà / català").
- traduir_ia(): proposa una traducció a l'anglès o al portuguès amb Claude.
- combinar(): munta el contingut d'una versió amb la traducció a sobre, per
  generar el PDF de l'idioma.

Totes les funcions retornen PROPOSTES: mai no escriuen res a la BD. Qualitat les
revisa a l'editor de traduccions abans de desar-les.
"""
import copy
import json
import os
import re

# Camps de text que es tradueixen. La resta (codi, EAN, denominació comercial,
# certificació, fabricat per, imatges) surt igual en tots els idiomes.
CAMPS_TEXT = (
    'denominacio_juridica', 'descripcio', 'origen', 'ingredients', 'alergens',
    'ogm', 'irradiacio', 'caract_organoleptiques', 'pesticidas',
    'presentacio_envase', 'us_previst', 'condicions_emmagatzematge',
    'condicions_transport', 'vida_util', 'legislacio_aplicable',
    'vigencia_document',
)

# Taules de paràmetres: es tradueix la columna 'parametre' i, si cal, el 'valor'
CAMPS_TAULA = (
    'fisicoquimiques', 'reologiques', 'microbiologiques', 'micotoxines',
    'alcaloides', 'metalls_pesants', 'valors_nutricionals',
)

# Peus de taula
CAMPS_NOTA = tuple(f'{t}_note' for t in CAMPS_TAULA)

CAMPS_TRADUIBLES = CAMPS_TEXT + CAMPS_NOTA + CAMPS_TAULA

# Separador bilingüe: una barra amb espai almenys a un costat.
# No talla '1999/2/CE', 'ufc/g', dates, '</span>' ni '<br />'.
_SEP_RE = re.compile(r'\s+/(?!>)\s*|(?<![<\s])/\s+')
_TAG_RE = re.compile(r'<[^>]+>')
_LLETRA_RE = re.compile(r'[A-Za-zÀ-ÿ]')
_DATA_RE = re.compile(r'^\d{1,2}/\d{1,2}/\d{2,4}$')


def _a_text_pla(text):
    """Passa <p> i <br> a salts de línia; la resta de marques es manté."""
    p_matches = re.findall(r'<p[^>]*>(.*?)</p>', text, re.DOTALL | re.IGNORECASE)
    if p_matches:
        text = '\n'.join(p_matches)
    return re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE).strip()


def _punt_de_tall(tros):
    """On s'acaba el català d'una parella i comença el castellà de la següent.

    Retorna l'índex o None si no es pot decidir.
    """
    millor = None
    for m in re.finditer(r'\n\s*', tros):
        seguent = tros[m.end():m.end() + 1]
        if not seguent or not (seguent.isupper() or seguent == '<'):
            continue
        anterior = tros[:m.start()].rstrip()[-1:]
        if anterior in '.):;' and anterior:
            millor = m.start()          # salt de frase clar: el darrer guanya
        elif millor is None:
            millor = m.start()
    if millor is not None:
        return millor
    # Sense salt de línia: darrer ". " seguit de majúscula
    for m in reversed(list(re.finditer(r'[.)]\s+(?=[A-ZÀ-Ý])', tros))):
        return m.start() + 1
    return None


def _netejar(part):
    """Uneix les línies tallades a mitja frase (herència del Word/PDF)."""
    part = part.strip()
    # Uneix si la línia anterior no acaba frase o la següent comença en minúscula/xifra
    part = re.sub(r'(?<=[^.:;!?\n])\n\s*', ' ', part)
    part = re.sub(r'\n\s*(?=[a-zà-ÿ0-9])', ' ', part)
    return part


def _tags_desquadrats(text):
    return text.count('<span') != text.count('</span') \
        or text.count('<strong') != text.count('</strong') \
        or text.count('<em') != text.count('</em')


def separar_text(text, idioma):
    """Retorna (text_en_idioma, dubtos) per a un text bilingüe 'es / ca'."""
    if not text or not isinstance(text, str):
        return text, False
    if re.search(r'<(ul|ol)\b', text, re.IGNORECASE):
        return text, True       # llistes: massa arriscat, a mà
    pla = _a_text_pla(text)
    trossos = _SEP_RE.split(pla)
    if len(trossos) == 1:
        return pla, True        # no hi ha separador: potser ja és monolingüe

    dubtos = False
    es_parts = [trossos[0]]
    ca_parts = []
    for tros in trossos[1:-1]:
        tall = _punt_de_tall(tros)
        if tall is None:
            dubtos = True
            ca_parts.append(tros)
            es_parts.append('')
        else:
            ca_parts.append(tros[:tall])
            es_parts.append(tros[tall:])

    # Una data sola al final (data de la declaració) és comuna als dos idiomes
    linies = trossos[-1].split('\n')
    comunes = []
    while len(linies) > 1 and _DATA_RE.match(_TAG_RE.sub('', linies[-1]).strip()):
        comunes.insert(0, linies.pop().strip())
    ca_parts.append('\n'.join(linies))

    # Una data sola enmig del text sol ser una resta de la importació del Word
    for linia in '\n'.join(es_parts + ca_parts).split('\n'):
        if _DATA_RE.match(_TAG_RE.sub('', linia).strip()):
            dubtos = True

    parts = es_parts if idioma == 'es' else ca_parts
    resultat = '\n'.join(p for p in (_netejar(x) for x in parts) if p)
    if comunes:
        resultat = '\n'.join([resultat] + comunes)
    if _tags_desquadrats(resultat) or not resultat.strip():
        dubtos = True
    return resultat, dubtos


def _separar_parametre(text, idioma):
    """Paràmetre de taula: 'Humedad / Humitat'. Sense separador, igual en tots dos."""
    if not text or not isinstance(text, str) or ' / ' not in text:
        return text
    parts = text.split(' / ', 1)
    return parts[0 if idioma == 'es' else 1].strip()


def _separar_valor(valor, idioma):
    """Valor de taula en dues línies diferents ('No detectado / 25g' i
    'No detectat / 25g'): es queda la línia de l'idioma. Si no, None (no es toca)."""
    if not valor or not isinstance(valor, str):
        return None
    linies = [x.strip() for x in valor.split('\n') if x.strip()]
    if len(linies) == 2 and linies[0] != linies[1]:
        return linies[0] if idioma == 'es' else linies[1]
    return None


def separar_bilingue(contingut, idioma):
    """Proposta de traducció 'es' o 'ca' a partir del contingut bilingüe.

    Returns:
        (proposta, dubtosos): proposta amb només els camps traduïbles i llista
        de camps que cal mirar amb atenció.
    """
    if idioma not in ('es', 'ca'):
        raise ValueError("Només es pot separar en 'es' o 'ca'")
    contingut = contingut or {}
    proposta, dubtosos = {}, []

    for camp in CAMPS_TEXT + CAMPS_NOTA:
        valor = contingut.get(camp)
        if not valor:
            continue
        text, dubtos = separar_text(valor, idioma)
        proposta[camp] = text
        if dubtos:
            dubtosos.append(camp)

    for camp in CAMPS_TAULA:
        files = contingut.get(camp)
        if not isinstance(files, list) or not files:
            continue
        noves = []
        for fila in files:
            fila = fila if isinstance(fila, dict) else {}
            nova = {'parametre': _separar_parametre(fila.get('parametre', ''), idioma)}
            valor = _separar_valor(fila.get('valor'), idioma)
            if valor is not None:
                nova['valor'] = valor
                if camp not in dubtosos:
                    dubtosos.append(camp)
            noves.append(nova)
        proposta[camp] = noves

    return proposta, dubtosos


def combinar(contingut_versio, contingut_traduccio, idioma):
    """Contingut de la versió amb la traducció a sobre (per generar el PDF).

    Les taules es combinen fila a fila per posició: de la traducció només
    s'agafen 'parametre' i, si hi és, 'valor'.
    """
    resultat = copy.deepcopy(contingut_versio or {})
    trad = contingut_traduccio or {}
    for camp in CAMPS_TEXT + CAMPS_NOTA:
        if trad.get(camp):
            resultat[camp] = trad[camp]
    for camp in CAMPS_TAULA:
        files_trad = trad.get(camp)
        files = resultat.get(camp)
        if not isinstance(files_trad, list) or not isinstance(files, list):
            continue
        for i, fila in enumerate(files):
            if i >= len(files_trad) or not isinstance(fila, dict):
                continue
            ft = files_trad[i] or {}
            if ft.get('parametre'):
                fila['parametre'] = ft['parametre']
            if ft.get('valor'):
                fila['valor'] = ft['valor']
    resultat['_idioma'] = idioma
    return resultat


def camps_canviats(contingut_abans, contingut_ara):
    """Camps traduïbles on el text font ha canviat entre dues versions."""
    abans = contingut_abans or {}
    ara = contingut_ara or {}
    canviats = []
    for camp in CAMPS_TEXT + CAMPS_NOTA:
        if (abans.get(camp) or '') != (ara.get(camp) or ''):
            canviats.append(camp)
    for camp in CAMPS_TAULA:
        def _clau(files):
            return [((f or {}).get('parametre'), (f or {}).get('valor'))
                    for f in (files or []) if isinstance(f, dict)]
        if _clau(abans.get(camp)) != _clau(ara.get(camp)):
            canviats.append(camp)
    return canviats


# ------------------------------------------------------------------
# Traducció amb IA (anglès i portuguès)
# ------------------------------------------------------------------
NOMS_IA = {'en': 'English (British)', 'pt': 'European Portuguese'}

_SISTEMA_IA = (
    "You translate technical data sheets for wheat flour and other milled "
    "cereal products, written by the quality department of a Spanish flour "
    "mill, from Spanish into {lang}. The readers are industrial customers.\n"
    "You receive a JSON list of items {{id, text}}. Return every item with the "
    "same id and the translated text.\n"
    "- Keep any HTML tags exactly as they are; translate only the text inside.\n"
    "- Keep line breaks (\\n).\n"
    "- Do not change numbers, units, symbols, dates, product codes or "
    "regulation references (e.g. 'Reglamento (UE) Nº 1169/2011' becomes "
    "'Regulation (EU) No 1169/2011').\n"
    "- Keep allergens in CAPITAL LETTERS, as in the source.\n"
    "- Use the standard terminology of EU food law in the target language.\n"
    "- If a text is only numbers, units or symbols, return it unchanged."
)


def ia_disponible():
    return bool(os.environ.get('ANTHROPIC_API_KEY'))


def _items_per_traduir(contingut_es):
    items = []
    for camp in CAMPS_TEXT + CAMPS_NOTA:
        if contingut_es.get(camp):
            items.append({'id': camp, 'text': contingut_es[camp]})
    for camp in CAMPS_TAULA:
        for i, fila in enumerate(contingut_es.get(camp) or []):
            fila = fila or {}
            if fila.get('parametre') and _LLETRA_RE.search(fila['parametre']):
                items.append({'id': f'{camp}.{i}.parametre', 'text': fila['parametre']})
            if fila.get('valor') and _LLETRA_RE.search(fila['valor']):
                items.append({'id': f'{camp}.{i}.valor', 'text': fila['valor']})
    return items


def traduir_ia(contingut_es, idioma, valors_originals=None):
    """Proposta de traducció a 'en' o 'pt' a partir de la versió castellana.

    Args:
        contingut_es: camps traduïbles en castellà (p.ex. de separar_bilingue).
        idioma: 'en' o 'pt'.
        valors_originals: contingut de la versió, per incloure al text a traduir
            els valors de taula que no tenen versió castellana pròpia.

    Returns:
        (proposta, None) o (None, missatge_error). Mai no llança excepcions.
    """
    if idioma not in NOMS_IA:
        return None, "La traducció amb IA només és per a l'anglès i el portuguès"
    if not ia_disponible():
        return None, "La traducció amb IA no està configurada (falta ANTHROPIC_API_KEY)"

    contingut_es = copy.deepcopy(contingut_es or {})
    # Valors de taula: si la proposta castellana no en té, s'agafen de la versió
    for camp in CAMPS_TAULA:
        originals = (valors_originals or {}).get(camp) or []
        for i, fila in enumerate(contingut_es.get(camp) or []):
            if not fila.get('valor') and i < len(originals) and isinstance(originals[i], dict):
                fila['valor'] = originals[i].get('valor') or ''

    items = _items_per_traduir(contingut_es)
    if not items:
        return {}, None

    try:
        import anthropic
    except ImportError:
        return None, "Falta instal·lar la llibreria 'anthropic' al servidor"

    model = os.environ.get('TRADUCCIO_MODEL') or 'claude-opus-5-5'
    client = anthropic.Anthropic(timeout=120.0)
    try:
        resp = client.messages.create(
            model=model,
            max_tokens=16000,
            system=_SISTEMA_IA.format(lang=NOMS_IA[idioma]),
            messages=[{'role': 'user', 'content': json.dumps(items, ensure_ascii=False)}],
            output_config={
                'effort': 'medium',
                'format': {
                    'type': 'json_schema',
                    'schema': {
                        'type': 'object',
                        'properties': {
                            'items': {
                                'type': 'array',
                                'items': {
                                    'type': 'object',
                                    'properties': {
                                        'id': {'type': 'string'},
                                        'text': {'type': 'string'},
                                    },
                                    'required': ['id', 'text'],
                                    'additionalProperties': False,
                                },
                            },
                        },
                        'required': ['items'],
                        'additionalProperties': False,
                    },
                },
            },
        )
    except anthropic.AuthenticationError:
        return None, "La clau d'API de traducció no és vàlida"
    except anthropic.RateLimitError:
        return None, "El servei de traducció està saturat; torna-ho a provar d'aquí a un minut"
    except anthropic.APIStatusError as e:
        return None, f"Error del servei de traducció ({e.status_code}): {e.message}"
    except anthropic.APIConnectionError:
        return None, "No s'ha pogut connectar amb el servei de traducció"

    if resp.stop_reason == 'refusal':
        return None, "El servei de traducció ha refusat el text"
    if resp.stop_reason == 'max_tokens':
        return None, "El text és massa llarg per traduir-lo d'una vegada"
    text = next((b.text for b in resp.content if b.type == 'text'), '')
    try:
        traduits = {it['id']: it['text'] for it in json.loads(text)['items']}
    except (ValueError, KeyError, TypeError):
        return None, "La resposta del servei de traducció no és vàlida"

    proposta = {}
    for camp in CAMPS_TEXT + CAMPS_NOTA:
        if camp in traduits:
            proposta[camp] = traduits[camp]
    for camp in CAMPS_TAULA:
        files = contingut_es.get(camp)
        if not files:
            continue
        noves = []
        for i, fila in enumerate(files):
            fila = fila or {}
            nova = {'parametre': traduits.get(f'{camp}.{i}.parametre', fila.get('parametre', ''))}
            valor = traduits.get(f'{camp}.{i}.valor')
            if valor and valor != fila.get('valor'):
                nova['valor'] = valor
            noves.append(nova)
        proposta[camp] = noves
    return proposta, None
