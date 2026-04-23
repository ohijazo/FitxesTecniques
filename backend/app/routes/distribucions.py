import os
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify
from app import db
from app.models import FitxaTecnica, VersioFitxa, Distribucio, DestiDistribucio
from app.auth import login_required, rol_requerit

distribucions_bp = Blueprint('distribucions', __name__)


def _executar_distribucio(dist, fitxa, versio, desti):
    """Executa la distribució segons el tipus de destí."""
    dist.intents += 1
    dist.executat_at = datetime.now(timezone.utc)
    dist.executat_by = request.usuari.get('email', '')

    if desti.tipus == 'ftp':
        from app.services.ftp_distributor import distribuir_ftp

        # Buscar el PDF: primer el generat, si no el descarregat
        pdf_path = versio.fitxer_pdf
        if not pdf_path or not os.path.exists(pdf_path):
            # Generar PDF des del contingut
            from app.services.pdf_generator import generar_pdf
            contingut = versio.contingut or {}
            if 'codi_referencia' not in contingut:
                contingut['codi_referencia'] = fitxa.art_codi
            if 'denominacio_comercial' not in contingut:
                contingut['denominacio_comercial'] = fitxa.nom_producte
            data_rev = versio.created_at.strftime('%d/%m/%Y') if versio.created_at else ''
            data_comp = versio.data_comprovacio.strftime('%d/%m/%Y') if versio.data_comprovacio else data_rev

            pdf_bytes = generar_pdf(contingut, versio.num_versio, data_rev, data_comp)

            # Guardar temporalment
            upload_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', 'uploads',
                                       fitxa.art_codi, f'v{versio.num_versio}')
            os.makedirs(upload_dir, exist_ok=True)
            pdf_path = os.path.join(upload_dir, f'{fitxa.art_codi}.pdf')
            with open(pdf_path, 'wb') as f:
                f.write(pdf_bytes)
            versio.fitxer_pdf = pdf_path

        config = desti.configuracio or {}
        result = distribuir_ftp(pdf_path, fitxa.art_codi, config)

        if result['ok']:
            dist.estat = 'ok'
            dist.missatge_error = result.get('url', '')
        else:
            dist.estat = 'error'
            dist.missatge_error = result['error']

    elif desti.tipus == 'xarxa':
        from app.services.smb_distributor import distribuir_xarxa

        pdf_path = versio.fitxer_pdf
        if not pdf_path or not os.path.exists(pdf_path):
            from app.services.pdf_generator import generar_pdf
            contingut = versio.contingut or {}
            if 'codi_referencia' not in contingut:
                contingut['codi_referencia'] = fitxa.art_codi
            if 'denominacio_comercial' not in contingut:
                contingut['denominacio_comercial'] = fitxa.nom_producte
            data_rev = versio.created_at.strftime('%d/%m/%Y') if versio.created_at else ''
            data_comp = versio.data_comprovacio.strftime('%d/%m/%Y') if versio.data_comprovacio else data_rev

            pdf_bytes = generar_pdf(contingut, versio.num_versio, data_rev, data_comp)

            upload_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', 'uploads',
                                       fitxa.art_codi, f'v{versio.num_versio}')
            os.makedirs(upload_dir, exist_ok=True)
            pdf_path = os.path.join(upload_dir, f'{fitxa.art_codi}.pdf')
            with open(pdf_path, 'wb') as f:
                f.write(pdf_bytes)
            versio.fitxer_pdf = pdf_path

        config = desti.configuracio or {}
        result = distribuir_xarxa(pdf_path, fitxa.art_codi, config)

        if result['ok']:
            dist.estat = 'ok'
            dist.missatge_error = result.get('path', '')
        else:
            dist.estat = 'error'
            dist.missatge_error = result['error']

    elif desti.tipus == 'sap':
        # TODO: Implementar integració SAP
        dist.estat = 'error'
        dist.missatge_error = 'Integració SAP no implementada'

    else:
        dist.estat = 'error'
        dist.missatge_error = f"Tipus de destí desconegut: {desti.tipus}"


@distribucions_bp.route('/fitxes/<int:fitxa_id>/distribucions', methods=['GET'])
@login_required
def llistar_distribucions(fitxa_id):
    db.get_or_404(FitxaTecnica, fitxa_id)
    distribucions = Distribucio.query.join(VersioFitxa).filter(
        VersioFitxa.fitxa_id == fitxa_id
    ).order_by(Distribucio.executat_at.desc()).all()
    return jsonify([d.to_dict() for d in distribucions])


@distribucions_bp.route('/fitxes/<int:fitxa_id>/distribuir', methods=['POST'])
@rol_requerit('admin', 'editor')
def distribuir_tots(fitxa_id):
    fitxa = db.get_or_404(FitxaTecnica, fitxa_id)
    versio_activa = VersioFitxa.query.filter_by(
        fitxa_id=fitxa_id, activa=True
    ).first()

    if not versio_activa:
        return jsonify({'error': "No hi ha cap versió publicada"}), 400

    destins = DestiDistribucio.query.filter_by(actiu=True).all()
    if not destins:
        return jsonify({'error': "No hi ha destins de distribució configurats"}), 400

    resultats = []
    for desti in destins:
        dist = Distribucio(
            versio_id=versio_activa.id,
            desti_id=desti.id,
            desti=desti.nom,
            estat='pendent',
        )
        db.session.add(dist)
        db.session.flush()

        try:
            _executar_distribucio(dist, fitxa, versio_activa, desti)
        except Exception as e:
            dist.estat = 'error'
            dist.missatge_error = str(e)

        resultats.append(dist)

    db.session.commit()
    return jsonify([d.to_dict() for d in resultats]), 200


@distribucions_bp.route('/fitxes/<int:fitxa_id>/distribuir/<int:desti_id>', methods=['POST'])
@rol_requerit('admin', 'editor')
def distribuir_desti(fitxa_id, desti_id):
    fitxa = db.get_or_404(FitxaTecnica, fitxa_id)
    desti = db.get_or_404(DestiDistribucio, desti_id)

    if not desti.actiu:
        return jsonify({'error': f"El destí '{desti.nom}' està desactivat"}), 400

    versio_activa = VersioFitxa.query.filter_by(
        fitxa_id=fitxa_id, activa=True
    ).first()

    if not versio_activa:
        return jsonify({'error': "No hi ha cap versió publicada"}), 400

    dist = Distribucio(
        versio_id=versio_activa.id,
        desti_id=desti.id,
        desti=desti.nom,
        estat='pendent',
    )
    db.session.add(dist)
    db.session.flush()

    try:
        _executar_distribucio(dist, fitxa, versio_activa, desti)
    except Exception as e:
        dist.estat = 'error'
        dist.missatge_error = str(e)

    db.session.commit()

    return jsonify(dist.to_dict()), 200
