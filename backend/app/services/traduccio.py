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
# Traducció automàtica (IA)
#
# El proveïdor es tria amb TRADUCCIO_PROVEIDOR al .env:
#   azure_openai     -> Azure OpenAI (Microsoft). AZURE_OPENAI_ENDPOINT,
#                       AZURE_OPENAI_KEY, AZURE_OPENAI_DEPLOYMENT,
#                       AZURE_OPENAI_API_VERSION (opcional)
#   azure_translator -> Azure AI Translator (Microsoft). AZURE_TRANSLATOR_KEY,
#                       AZURE_TRANSLATOR_REGION, AZURE_TRANSLATOR_ENDPOINT (opcional)
#   anthropic        -> Claude. ANTHROPIC_API_KEY, TRADUCCIO_MODEL (opcional)
# Sense proveïdor configurat la traducció automàtica no està disponible i les
# traduccions es fan a mà.
# ------------------------------------------------------------------
import logging

LOG = logging.getLogger(__name__)

NOMS_IA = {
    'ca': 'Catalan', 'es': 'Spanish (Spain)',
    'en': 'English (British)', 'pt': 'European Portuguese',
}

# Codis d'idioma d'Azure AI Translator ('pt' és el del Brasil)
_CODIS_TRANSLATOR = {'ca': 'ca', 'es': 'es', 'en': 'en', 'pt': 'pt-pt'}

_SISTEMA_IA = (
    "You translate technical data sheets for wheat flour and other milled "
    "cereal products, written by the quality department of a Spanish flour "
    "mill, from {origen} into {desti}. The readers are industrial customers.\n"
    "You receive a JSON list of items {{id, text}}. Return every item with the "
    "same id and the translated text.\n"
    "- Keep any HTML tags exactly as they are; translate only the text inside.\n"
    "- Keep line breaks (\\n).\n"
    "- Do not change numbers, units, symbols, dates, product codes or "
    "regulation references (e.g. 'Reglamento (UE) Nº 1169/2011' becomes "
    "'Regulation (EU) No 1169/2011').\n"
    "- Keep allergens in CAPITAL LETTERS, as in the source.\n"
    "- Use the standard terminology of EU food law in the target language.\n"
    "- If a text is only numbers, units or symbols, return it unchanged.\n"
    "Answer ONLY with a JSON object {{\"items\": [{{\"id\": ..., \"text\": ...}}]}}, "
    "with no other text before or after it."
)

_ESQUEMA_IA = {
    'type': 'object',
    'properties': {
        'items': {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {'id': {'type': 'string'}, 'text': {'type': 'string'}},
                'required': ['id', 'text'],
                'additionalProperties': False,
            },
        },
    },
    'required': ['items'],
    'additionalProperties': False,
}

# Gunicorn talla les peticions als 120 s: 50 s per intent i 1 reintent com a màxim
_TIMEOUT = 50

# Els textos es tradueixen en trossos en paral·lel: una fitxa sencera (~45
# textos) passa de ~14 s a ~4 s. Mida mínima d'un tros i nombre màxim de trossos.
_MIDA_TROS = 8
_MAX_TROSSOS = 4

# Error que val la pena reintentar: la resposta no s'ha pogut llegir
ERROR_RESPOSTA = "La resposta del servei de traducció no és vàlida"


def proveidor_ia():
    """Proveïdor configurat, o None si no n'hi ha cap."""
    p = (os.environ.get('TRADUCCIO_PROVEIDOR') or '').strip().lower()
    if p == 'azure_openai':
        ok = all(os.environ.get(k) for k in ('AZURE_OPENAI_ENDPOINT', 'AZURE_OPENAI_KEY',
                                              'AZURE_OPENAI_DEPLOYMENT'))
        return p if ok else None
    if p == 'azure_translator':
        return p if os.environ.get('AZURE_TRANSLATOR_KEY') else None
    if p == 'anthropic' or (not p and os.environ.get('ANTHROPIC_API_KEY')):
        # Compatibilitat: abans n'hi havia prou amb ANTHROPIC_API_KEY
        return 'anthropic' if os.environ.get('ANTHROPIC_API_KEY') else None
    return None


def ia_disponible():
    return proveidor_ia() is not None


def extreure_camps(contingut):
    """Només els camps traduïbles d'un contingut (per a originals d'un sol idioma)."""
    contingut = contingut or {}
    res = {k: contingut[k] for k in CAMPS_TEXT + CAMPS_NOTA if contingut.get(k)}
    for camp in CAMPS_TAULA:
        files = contingut.get(camp)
        if isinstance(files, list) and files:
            res[camp] = [{'parametre': (f or {}).get('parametre', '')} for f in files]
    return res


def _items_per_traduir(font, camps=None):
    """Llista {id, text}. camps: si s'indica, només aquests camps."""
    items = []
    for camp in CAMPS_TEXT + CAMPS_NOTA:
        if (camps is None or camp in camps) and font.get(camp):
            items.append({'id': camp, 'text': font[camp]})
    for camp in CAMPS_TAULA:
        if camps is not None and camp not in camps:
            continue
        for i, fila in enumerate(font.get(camp) or []):
            fila = fila or {}
            if fila.get('parametre') and _LLETRA_RE.search(fila['parametre']):
                items.append({'id': f'{camp}.{i}.parametre', 'text': fila['parametre']})
            if fila.get('valor') and _LLETRA_RE.search(fila['valor']):
                items.append({'id': f'{camp}.{i}.valor', 'text': fila['valor']})
    return items


def _parse_items(text):
    """Llegeix {"items": [...]} tolerant: accepta el JSON dins de ```json ... ```
    o amb text al voltant."""
    text = (text or '').strip()
    inici, final = text.find('{'), text.rfind('}')
    if inici == -1 or final == -1:
        raise ValueError('sense JSON')
    return {it['id']: it['text'] for it in json.loads(text[inici:final + 1])['items']}


def _traduir_anthropic(items, origen, desti):
    try:
        import anthropic
    except ImportError:
        return None, "Falta instal·lar la llibreria 'anthropic' al servidor"
    # Sonnet 5.5: a la prova amb la 30150, mateixa qualitat que Opus 5.5 i el
    # doble de ràpid (decisió de l'usuari). Es pot canviar amb TRADUCCIO_MODEL.
    model = os.environ.get('TRADUCCIO_MODEL') or 'claude-sonnet-5-5'
    client = anthropic.Anthropic(timeout=float(_TIMEOUT), max_retries=1)
    try:
        # L'esquema garanteix que la resposta sigui un JSON vàlid (sense
        # esquema, els textos amb HTML de vegades el trencaven).
        resp = client.messages.create(
            model=model,
            max_tokens=16000,
            system=_SISTEMA_IA.format(origen=NOMS_IA[origen], desti=NOMS_IA[desti]),
            messages=[{'role': 'user', 'content': json.dumps(items, ensure_ascii=False)}],
            output_config={
                'effort': 'low',      # traduir no necessita raonament llarg; respon abans
                'format': {'type': 'json_schema', 'schema': _ESQUEMA_IA},
            },
        )
    except anthropic.AuthenticationError:
        return None, "La clau d'API de traducció no és vàlida"
    except anthropic.RateLimitError:
        return None, "El servei de traducció està saturat; torna-ho a provar d'aquí a un minut"
    except anthropic.APIStatusError as e:
        return None, f"Error del servei de traducció ({e.status_code}): {e.message}"
    except anthropic.APITimeoutError:
        return None, "El servei de traducció ha trigat massa; torna-ho a provar"
    except anthropic.APIConnectionError:
        return None, "No s'ha pogut connectar amb el servei de traducció"
    if resp.stop_reason == 'refusal':
        return None, "El servei de traducció ha refusat el text"
    if resp.stop_reason == 'max_tokens':
        return None, "El text és massa llarg per traduir-lo d'una vegada"
    text = next((b.text for b in resp.content if b.type == 'text'), '')
    try:
        return _parse_items(text), None
    except (ValueError, KeyError, TypeError):
        return None, ERROR_RESPOSTA


def precarregar():
    """Importa la llibreria del proveïdor en segon pla en arrencar l'aplicació.

    'import anthropic' carrega molts mòduls: en una unitat de xarxa pot trigar
    prop d'un minut i, si es fes en la primera traducció, l'usuari l'esperaria.
    """
    if proveidor_ia() == 'anthropic':
        import threading
        threading.Thread(target=lambda: __import__('anthropic'), daemon=True,
                         name='precarrega-traduccio').start()


def _post(url, **kwargs):
    """POST amb 1 reintent per a errors temporals (429 / 5xx / connexió)."""
    import requests
    for intent in range(2):
        try:
            r = requests.post(url, timeout=_TIMEOUT, **kwargs)
        except requests.Timeout:
            if intent:
                return None, "El servei de traducció ha trigat massa; torna-ho a provar"
            continue
        except requests.RequestException:
            if intent:
                return None, "No s'ha pogut connectar amb el servei de traducció"
            continue
        if (r.status_code == 429 or r.status_code >= 500) and not intent:
            continue
        return r, None
    return None, "El servei de traducció no respon"


def _error_http(r):
    if r.status_code in (401, 403):
        return "La clau del servei de traducció no és vàlida o no té permisos"
    if r.status_code == 429:
        return "El servei de traducció està saturat; torna-ho a provar d'aquí a un minut"
    try:
        detall = (r.json().get('error') or {}).get('message') or ''
    except ValueError:
        detall = ''
    return f"Error del servei de traducció ({r.status_code}){': ' + detall if detall else ''}"


def _traduir_azure_openai(items, origen, desti):
    endpoint = os.environ['AZURE_OPENAI_ENDPOINT'].rstrip('/')
    deployment = os.environ['AZURE_OPENAI_DEPLOYMENT']
    versio_api = os.environ.get('AZURE_OPENAI_API_VERSION') or '2024-10-21'
    url = f'{endpoint}/openai/deployments/{deployment}/chat/completions?api-version={versio_api}'
    cos = {
        'messages': [
            {'role': 'system', 'content': _SISTEMA_IA.format(origen=NOMS_IA[origen], desti=NOMS_IA[desti])},
            {'role': 'user', 'content': json.dumps(items, ensure_ascii=False)},
        ],
        'response_format': {
            'type': 'json_schema',
            'json_schema': {'name': 'traduccions', 'strict': True, 'schema': _ESQUEMA_IA},
        },
    }
    r, error = _post(url, json=cos, headers={'api-key': os.environ['AZURE_OPENAI_KEY']})
    if error:
        return None, error
    if r.status_code != 200:
        return None, _error_http(r)
    try:
        opcio = r.json()['choices'][0]
        if opcio.get('finish_reason') == 'content_filter':
            return None, "El filtre de contingut d'Azure ha bloquejat el text"
        if opcio.get('finish_reason') == 'length':
            return None, "El text és massa llarg per traduir-lo d'una vegada"
        return _parse_items(opcio['message']['content']), None
    except (ValueError, KeyError, TypeError, IndexError):
        return None, ERROR_RESPOSTA


def _traduir_azure_translator(items, origen, desti):
    """Azure AI Translator: traducció literal, sense instruccions.

    textType=html conserva les marques; els salts de línia es passen a <br>
    perquè en HTML no es perdin. Màxim 1000 textos i ~50.000 caràcters per
    petició: es fan lots.
    """
    endpoint = (os.environ.get('AZURE_TRANSLATOR_ENDPOINT')
                or 'https://api.cognitive.microsofttranslator.com').rstrip('/')
    url = (f'{endpoint}/translate?api-version=3.0&textType=html'
           f'&from={_CODIS_TRANSLATOR[origen]}&to={_CODIS_TRANSLATOR[desti]}')
    capcaleres = {'Ocp-Apim-Subscription-Key': os.environ['AZURE_TRANSLATOR_KEY']}
    if os.environ.get('AZURE_TRANSLATOR_REGION'):
        capcaleres['Ocp-Apim-Subscription-Region'] = os.environ['AZURE_TRANSLATOR_REGION']

    traduits = {}
    lot, mida = [], 0
    lots = []
    for it in items:
        text = it['text'].replace('\n', '<br>')
        if lot and (len(lot) >= 900 or mida + len(text) > 45000):
            lots.append(lot)
            lot, mida = [], 0
        lot.append((it['id'], text))
        mida += len(text)
    if lot:
        lots.append(lot)

    for lot in lots:
        r, error = _post(url, json=[{'Text': t} for _, t in lot], headers=capcaleres)
        if error:
            return None, error
        if r.status_code != 200:
            return None, _error_http(r)
        try:
            for (iid, _), res in zip(lot, r.json()):
                text = res['translations'][0]['text']
                traduits[iid] = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
        except (ValueError, KeyError, TypeError, IndexError):
            return None, ERROR_RESPOSTA
    return traduits, None


_PROVEIDORS = {
    'azure_openai': _traduir_azure_openai,
    'azure_translator': _traduir_azure_translator,
    'anthropic': _traduir_anthropic,
}


def _traduir_tros(proveidor, tros, origen, desti):
    """Tradueix un tros; si la resposta no porta tots els textos, ho torna a provar un cop."""
    error = None
    for _ in range(2):
        try:
            traduits, error = _PROVEIDORS[proveidor](tros, origen, desti)
        except Exception as e:  # cap error del proveïdor ha de tombar la petició
            LOG.exception('Traducció automàtica (%s)', proveidor)
            return None, f"Error inesperat del servei de traducció: {e}"
        if error == ERROR_RESPOSTA:
            continue                  # resposta il·legible: es torna a demanar
        if error:
            return None, error
        if all(it['id'] in traduits for it in tros):
            return traduits, None
        error = "La resposta del servei de traducció no és completa"
    return None, error


def _traduir_en_trossos(proveidor, items, origen, desti):
    """Parteix els textos en trossos i els tradueix en paral·lel."""
    from concurrent.futures import ThreadPoolExecutor
    n = max(1, min(_MAX_TROSSOS, -(-len(items) // _MIDA_TROS)))
    trossos = [items[i::n] for i in range(n)]
    if n == 1:
        return _traduir_tros(proveidor, trossos[0], origen, desti)
    with ThreadPoolExecutor(max_workers=n) as ex:
        resultats = list(ex.map(lambda t: _traduir_tros(proveidor, t, origen, desti), trossos))
    traduits = {}
    for parcial, error in resultats:
        if error:
            return None, error
        traduits.update(parcial)
    return traduits, None


def traduir_ia(font, idioma, valors_originals=None, idioma_origen='es', camps=None):
    """Proposta de traducció a `idioma` a partir de `font` (idioma_origen).

    Args:
        font: camps traduïbles en l'idioma d'origen (p.ex. de separar_bilingue).
        idioma: idioma de destí ('ca'|'es'|'en'|'pt').
        valors_originals: contingut de la versió, per incloure els valors de
            taula que la font no porta.
        idioma_origen: 'es' (per defecte) o 'ca' si l'original és en català.
        camps: si s'indica, només es tradueixen aquests camps.

    Returns:
        (proposta, None) o (None, missatge_error). Mai no llança excepcions.
    """
    if idioma not in NOMS_IA or idioma_origen not in NOMS_IA:
        return None, f"Idioma no vàlid: {idioma}"
    if idioma == idioma_origen:
        return None, "L'idioma de destí és el mateix que el de l'original"
    proveidor = proveidor_ia()
    if not proveidor:
        return None, "La traducció automàtica no està configurada al servidor"

    font = copy.deepcopy(font or {})
    # Valors de taula: si la font no en té, s'agafen de la versió
    for camp in CAMPS_TAULA:
        originals = (valors_originals or {}).get(camp) or []
        for i, fila in enumerate(font.get(camp) or []):
            if not fila.get('valor') and i < len(originals) and isinstance(originals[i], dict):
                fila['valor'] = originals[i].get('valor') or ''

    items = _items_per_traduir(font, camps)
    if not items:
        return {}, None

    traduits, error = _traduir_en_trossos(proveidor, items, idioma_origen, idioma)
    if error:
        return None, error

    proposta = {}
    for camp in CAMPS_TEXT + CAMPS_NOTA:
        if camp in traduits:
            proposta[camp] = traduits[camp]
    for camp in CAMPS_TAULA:
        files = font.get(camp)
        if not files or (camps is not None and camp not in camps):
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
