"""Operacions massives sobre fitxes (edició de camps en bloc).

L'edició massiva és síncrona — el cost real és DB-only i ràpid (~100ms per fitxa).
Per a 200 fitxes són uns 20s, dins del marge de timeout HTTP.

Cada fitxa rep una nova VersioFitxa amb activa=True i estat_versio='publicada',
sense passar pel circuit d'aprovació (rol admin requerit).
"""

import glob
import os
import uuid
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify

from app import db
from app.models import FitxaTecnica, VersioFitxa, Usuari
from app.auth import rol_requerit

bulk_bp = Blueprint('bulk', __name__)


# Camps que NO es poden modificar massivament (immutables o sense sentit semàntic):
# - art_codi / codi_referencia: identificador, no pot canviar (CLAUDE.md)
CAMPS_PROHIBITS = {'art_codi', 'codi_referencia'}

# Camps tipus 'table' també exclosos. El frontend filtra però validem aquí també.
# La llista la mantenim sincronitzada amb DEFAULT_SECTIONS del FitxaForm.jsx.
CAMPS_TIPUS_TABLE = {
    'fisicoquimiques', 'reologiques', 'microbiologiques',
    'micotoxines', 'alcaloides', 'metalls_pesants', 'contaminants_altres',
    'valors_nutricionals',
}

# Estats de fitxa que no es poden modificar bulk
ESTATS_BLOQUEJATS = {'inactiva', 'obsoleta'}

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', 'uploads')


def _invalidar_cache_pdf(art_codi):
    """Esborra els PDFs generats en cache per aquesta fitxa."""
    pattern = os.path.join(UPLOAD_DIR, art_codi, 'v*', '*_generat.pdf')
    for path in glob.glob(pattern):
        try:
            os.remove(path)
        except OSError:
            pass


@bulk_bp.route('/fitxes/bulk-edit', methods=['POST'])
@rol_requerit('admin')
def bulk_edit_fitxes():
    """Edita varis camps a varies fitxes alhora, creant una nova versió per cadascuna."""
    data = request.get_json() or {}
    fitxa_ids = data.get('fitxa_ids') or []
    canvis = data.get('canvis') or {}
    descripcio_canvi = (data.get('descripcio_canvi') or '').strip()
    password = data.get('password', '')

    # Validacions
    if not isinstance(fitxa_ids, list) or not fitxa_ids:
        return jsonify({'error': "Cal indicar fitxa_ids (llista no buida)"}), 400
    if not isinstance(canvis, dict) or not canvis:
        return jsonify({'error': "Cal indicar com a mínim un canvi"}), 400
    if len(descripcio_canvi) < 10:
        return jsonify({'error': "La descripció del canvi ha de tenir com a mínim 10 caràcters"}), 400
    if not password:
        return jsonify({'error': "Cal confirmar amb la teva contrasenya"}), 400

    # Camps prohibits
    camps_invalids = []
    for camp in canvis.keys():
        if camp in CAMPS_PROHIBITS:
            camps_invalids.append(camp)
        elif camp in CAMPS_TIPUS_TABLE:
            camps_invalids.append(camp)
    if camps_invalids:
        return jsonify({'error': f"Camps no editables massivament: {', '.join(camps_invalids)}"}), 400

    # Verificar contrasenya
    usuari = Usuari.query.filter_by(email=request.usuari.get('email')).first()
    if not usuari or not usuari.check_password(password):
        return jsonify({'error': "Contrasenya incorrecta"}), 403

    fitxa_ids = list(dict.fromkeys(int(x) for x in fitxa_ids))
    lot_uuid = uuid.uuid4().hex[:8]
    descripcio_complerta = f"[BULK {lot_uuid}] {descripcio_canvi}"

    ok_ids = []
    errors = []

    for fid in fitxa_ids:
        try:
            fitxa = FitxaTecnica.query.get(fid)
            if not fitxa:
                errors.append({'fitxa_id': fid, 'error': 'Fitxa no trobada'})
                continue
            if fitxa.estat in ESTATS_BLOQUEJATS:
                errors.append({'fitxa_id': fid, 'error': f"Estat '{fitxa.estat}' no editable"})
                continue

            versio_activa = VersioFitxa.query.filter_by(fitxa_id=fid, activa=True).first()
            if not versio_activa:
                errors.append({'fitxa_id': fid, 'error': 'Sense versió activa'})
                continue

            # Copiar contingut existent i aplicar canvis
            contingut_nou = dict(versio_activa.contingut) if versio_activa.contingut else {}
            for camp, valor in canvis.items():
                contingut_nou[camp] = valor

            # Calcular nou num_versio
            ultima = VersioFitxa.query.filter_by(fitxa_id=fid).order_by(
                VersioFitxa.num_versio.desc()
            ).first()
            nou_num = (ultima.num_versio if ultima else 0) + 1

            # Crear nova versió (sense fitxer_pdf perquè es regeneri amb el contingut nou)
            nova_versio = VersioFitxa(
                fitxa_id=fid,
                num_versio=nou_num,
                descripcio_canvi=descripcio_complerta,
                contingut=contingut_nou,
                fitxer_pdf=None,
                created_by=request.usuari.get('email', ''),
                activa=True,
                estat_versio='publicada',
            )

            # Desactivar versió anterior
            versio_activa.activa = False

            # Actualitzar fitxa: estat publicada i updated_at explícit
            if fitxa.estat == 'esborrany':
                fitxa.estat = 'publicada'
            fitxa.updated_at = datetime.now(timezone.utc)

            db.session.add(nova_versio)
            db.session.commit()

            # Invalidar cache PDF (post-commit)
            _invalidar_cache_pdf(fitxa.art_codi)

            ok_ids.append(fid)
        except Exception as e:
            db.session.rollback()
            errors.append({'fitxa_id': fid, 'error': str(e)})

    return jsonify({
        'lot_uuid': lot_uuid,
        'total': len(fitxa_ids),
        'ok': ok_ids,
        'errors': errors,
    }), 200
