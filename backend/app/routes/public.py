"""Endpoint public de nomes lectura: denominacio juridica per codi d'article.

El fa servir l'aplicacio del DeCA (Document de Control Administratiu de
transport), que ha d'imprimir la naturalesa de la mercaderia a cada albara.
L'article 6.d de l'Ordre FOM/2861/2012 demana precisament aixo, i la dada ja
existeix aqui validada per Qualitat.

Per que un endpoint a part i no un usuari de servei
---------------------------------------------------
Un usuari de servei donaria al DeCA un token valid per a TOTA l'API: podria
llegir composicions, vides utils, valors reologics i historials, que son dades
comercials que el DeCA no necessita per a res.

Aquest endpoint nomes torna codi d'article i denominacio juridica. Es el
minim que cal per fer la feina, i prou.

Seguretat
---------
- Clau fixa a la capcalera `X-API-Key`, comparada amb `compare_digest` per no
  filtrar informacio pel temps de resposta.
- Va a la capcalera i no a la URL a proposit: els parametres de consulta
  queden als registres d'Apache i a l'historial del navegador.
- Si `API_DENOMINACIONS_KEY` no esta configurada, l'endpoint respon 503. Ve
  desactivat de serie: no es pot obrir sense voler.
- Nomes lectura. No hi ha cap POST, PUT ni DELETE en aquest fitxer.
"""
import re
import secrets

from flask import Blueprint, current_app, jsonify, request

from app import db
from app.models import FitxaTecnica, VersioFitxa

public_bp = Blueprint('public', __name__)

ESTAT_PUBLICADA = 'publicada'

# Per que una fitxa que existeix no dona denominacio. Es important distingir-ho:
# "no publicada" la resol qui la publiqui, "sense denominacio" la resol Qualitat.
MOTIU_NO_PUBLICADA = 'fitxa no publicada'
MOTIU_SENSE_VERSIO = 'sense versio activa'
MOTIU_SENSE_DENOMINACIO = 'sense denominacio juridica'
# Un producte comercialitzat no el fabriquem: la fitxa es el PDF del
# proveidor, i alli la denominacio no esta en cap camp que puguem llegir.
# Es un cas diferent del d'una fitxa nostra a qui falta omplir-la: aquesta
# no s'omplira mai sola i algu l'ha d'anotar a ma.
MOTIU_COMERCIALITZAT = 'article comercialitzat: la fitxa es el PDF del proveidor'


def _clau_valida():
    """La clau de la peticio coincideix amb la configurada?"""
    esperada = current_app.config.get('API_DENOMINACIONS_KEY', '')
    if not esperada:
        return None                      # endpoint desactivat
    rebuda = request.headers.get('X-API-Key', '')
    return secrets.compare_digest(rebuda, esperada)


def _sense_html(text):
    """Les denominacions poden portar etiquetes de l'editor enriquit."""
    if not text:
        return ''
    return re.sub(r'<[^>]+>', '', str(text)).strip()


def _consultar():
    """Totes les fitxes, amb la seva versio activa si en tenen.

    Es porten totes i no nomes les publicades perque qui consumeix aixo pugui
    saber PER QUE li falta una denominacio. No es el mateix que un article no
    tingui fitxa que que la tingui sense publicar: la primera la resol
    Qualitat creant-la, la segona nomes cal publicar-la.
    """
    return (
        FitxaTecnica.query
        .outerjoin(VersioFitxa, db.and_(VersioFitxa.fitxa_id == FitxaTecnica.id,
                                        VersioFitxa.activa.is_(True)))
        .with_entities(FitxaTecnica.art_codi, FitxaTecnica.estat,
                       FitxaTecnica.tipus_producte,
                       VersioFitxa.contingut, VersioFitxa.num_versio,
                       VersioFitxa.data_revisio)
        .all()
    )


@public_bp.route('/public/denominacions', methods=['GET'])
def denominacions():
    """Denominacio juridica de cada article amb fitxa publicada."""
    valida = _clau_valida()
    if valida is None:
        return jsonify({'error': "Endpoint desactivat: falta API_DENOMINACIONS_KEY"}), 503
    if not valida:
        return jsonify({'error': "Clau invalida"}), 401

    llista, omesos = [], []
    for art_codi, estat, tipus_producte, contingut, num_versio, data_revisio in _consultar():
        codi = (art_codi or '').strip()
        if not codi:
            continue
        if estat != ESTAT_PUBLICADA:
            omesos.append({'art_codi': codi, 'motiu': MOTIU_NO_PUBLICADA})
            continue
        if num_versio is None:
            omesos.append({'art_codi': codi, 'motiu': MOTIU_SENSE_VERSIO})
            continue
        text = _sense_html((contingut or {}).get('denominacio_juridica'))
        if not text:
            comercialitzat = (tipus_producte or 'elaborat') == 'comercialitzat'
            omesos.append({'art_codi': codi,
                           'motiu': MOTIU_COMERCIALITZAT if comercialitzat
                                    else MOTIU_SENSE_DENOMINACIO})
            continue
        llista.append({
            'art_codi': codi,
            'denominacio_juridica': text,
            'revisio': num_versio,
            'data_revisio': data_revisio.isoformat() if data_revisio else None,
        })

    llista.sort(key=lambda d: d['art_codi'])
    omesos.sort(key=lambda d: d['art_codi'])
    return jsonify({
        'denominacions': llista,
        'total': len(llista),
        # Fitxes que existeixen pero no donen denominacio, i per que. Nomes el
        # codi i el motiu: cap altra dada de la fitxa.
        'omesos': omesos,
    })
