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

from app.models import FitxaTecnica, VersioFitxa

public_bp = Blueprint('public', __name__)

ESTAT_PUBLICADA = 'publicada'


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
    """Fitxes publicades amb la seva versio activa.

    Nomes aquestes: la denominacio d'un esborrany no esta validada per
    Qualitat i no ha d'acabar impresa en un document legal.
    """
    return (
        FitxaTecnica.query
        .join(VersioFitxa, VersioFitxa.fitxa_id == FitxaTecnica.id)
        .filter(FitxaTecnica.estat == ESTAT_PUBLICADA, VersioFitxa.activa.is_(True))
        .with_entities(FitxaTecnica.art_codi, VersioFitxa.contingut,
                       VersioFitxa.num_versio, VersioFitxa.data_revisio)
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

    files = _consultar()
    denominacions_llista = []
    for art_codi, contingut, num_versio, data_revisio in files:
        text = _sense_html((contingut or {}).get('denominacio_juridica'))
        if not text:
            continue
        denominacions_llista.append({
            'art_codi': (art_codi or '').strip(),
            'denominacio_juridica': text,
            'revisio': num_versio,
            'data_revisio': data_revisio.isoformat() if data_revisio else None,
        })

    denominacions_llista.sort(key=lambda d: d['art_codi'])
    return jsonify({
        'denominacions': denominacions_llista,
        'total': len(denominacions_llista),
    })
