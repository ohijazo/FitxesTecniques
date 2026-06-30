import os
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify
from app import db
from app.models import FitxaTecnica, VersioFitxa, Distribucio, DestiDistribucio, Usuari
from app.auth import login_required, rol_requerit

distribucions_bp = Blueprint('distribucions', __name__)


def _generar_nom_fitxer(patro, fitxa, versio):
    """Genera el nom del fitxer a partir del patró configurat."""
    if not patro:
        return f'{fitxa.art_codi}.pdf'
    nom = patro.replace('{art_codi}', fitxa.art_codi)
    nom = nom.replace('{nom_producte}', fitxa.nom_producte or '')
    nom = nom.replace('{versio}', str(versio.num_versio) if versio else '0')
    nom = nom.replace('{data}', datetime.now(timezone.utc).strftime('%Y%m%d'))
    # Netejar caràcters no vàlids per noms de fitxer (Windows/SMB) i per URL/SharePoint
    for char in ['\\', '/', ':', '*', '?', '"', '<', '>', '|', '#', '%', '&']:
        nom = nom.replace(char, '_')
    # Eliminar caràcters de control (salts de línia, tabuladors, etc.) que
    # tot i percent-encoded són rebutjats per IIS/SharePoint amb 400 'Invalid URL'.
    nom = ''.join(c for c in nom if ord(c) >= 32)
    # SharePoint/Windows no permeten espais ni dots al final del nom.
    nom = nom.strip().rstrip('.').strip()
    if not nom:
        nom = f'{fitxa.art_codi}.pdf'
    return nom


def _executar_distribucio(dist, fitxa, versio, desti, executat_by=None):
    """Executa la distribució segons el tipus de destí.

    executat_by: email de l'usuari (si None, intenta llegir-lo de request.usuari
    per compatibilitat amb endpoints HTTP; el worker resident l'ha de passar explícit).
    """
    dist.intents += 1
    dist.executat_at = datetime.now(timezone.utc)
    if executat_by is None:
        try:
            executat_by = request.usuari.get('email', '')
        except (RuntimeError, AttributeError):
            executat_by = ''
    dist.executat_by = executat_by

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
        filename = _generar_nom_fitxer(desti.patro_nom_fitxer, fitxa, versio)
        result = distribuir_ftp(pdf_path, fitxa.art_codi, config, filename)

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
        filename = _generar_nom_fitxer(desti.patro_nom_fitxer, fitxa, versio)
        result = distribuir_xarxa(pdf_path, fitxa.art_codi, config, filename)

        if result['ok']:
            dist.estat = 'ok'
            dist.missatge_error = result.get('path', '')
        else:
            dist.estat = 'error'
            dist.missatge_error = result['error']

    elif desti.tipus == 'sharepoint':
        from app.services.sharepoint_distributor import distribuir_sharepoint

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
        filename = _generar_nom_fitxer(desti.patro_nom_fitxer, fitxa, versio)
        result = distribuir_sharepoint(pdf_path, fitxa.art_codi, config, filename)

        if result['ok']:
            dist.estat = 'ok'
            dist.missatge_error = result.get('url', '')
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
@rol_requerit('admin', 'editor', 'distribuidor')
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


@distribucions_bp.route('/fitxes/<int:fitxa_id>/retirar/<int:desti_id>', methods=['POST'])
@rol_requerit('admin', 'editor', 'distribuidor')
def retirar_desti(fitxa_id, desti_id):
    """Retira (elimina) el PDF d'una fitxa d'un destí concret sense esborrar la fitxa.

    Crea un nou registre de Distribucio amb estat='retirat' per preservar
    l'audit trail (el registre 'ok' original es manté intacte).
    """
    fitxa = db.get_or_404(FitxaTecnica, fitxa_id)
    desti = db.get_or_404(DestiDistribucio, desti_id)
    data = request.get_json() or {}

    motiu = (data.get('motiu') or '').strip()
    if not motiu:
        return jsonify({'error': "Cal indicar un motiu"}), 400

    password = data.get('password', '')
    if not password:
        return jsonify({'error': "Cal confirmar amb la teva contrasenya"}), 400

    usuari = Usuari.query.filter_by(email=request.usuari.get('email')).first()
    if not usuari or not usuari.check_password(password):
        return jsonify({'error': "Contrasenya incorrecta"}), 403

    versio_activa = VersioFitxa.query.filter_by(
        fitxa_id=fitxa_id, activa=True
    ).first()
    if not versio_activa:
        return jsonify({'error': "No hi ha cap versió activa"}), 400

    # Buscar l'última distribució 'ok' per inferir el nom de fitxer al destí.
    dist_ok = Distribucio.query.join(VersioFitxa).filter(
        VersioFitxa.fitxa_id == fitxa_id,
        Distribucio.desti_id == desti_id,
        Distribucio.estat == 'ok',
    ).order_by(Distribucio.executat_at.desc()).first()

    filename = None
    if dist_ok and dist_ok.missatge_error:
        ref = dist_ok.missatge_error
        candidate = ref.split('/')[-1].split('\\')[-1].split('?')[0]
        if candidate and candidate.lower().endswith('.pdf'):
            filename = candidate
    if not filename:
        filename = _generar_nom_fitxer(desti.patro_nom_fitxer, fitxa, versio_activa)

    config = desti.configuracio or {}

    if desti.tipus == 'ftp':
        from app.services.ftp_distributor import eliminar_ftp
        result = eliminar_ftp(fitxa.art_codi, config, filename)
    elif desti.tipus == 'xarxa':
        from app.services.smb_distributor import eliminar_xarxa
        result = eliminar_xarxa(fitxa.art_codi, config, filename)
    elif desti.tipus == 'sharepoint':
        from app.services.sharepoint_distributor import eliminar_sharepoint
        result = eliminar_sharepoint(fitxa.art_codi, config, filename)
    else:
        return jsonify({'error': f"Tipus de destí no suportat: {desti.tipus}"}), 400

    # Crear NOU registre Distribucio amb estat 'retirat' (preserva audit trail).
    nou = Distribucio(
        versio_id=versio_activa.id,
        desti_id=desti.id,
        desti=desti.nom,
        estat='retirat' if result.get('ok') else 'error',
        intents=1,
        missatge_error=motiu if result.get('ok') else (result.get('error') or ''),
        executat_at=datetime.now(timezone.utc),
        executat_by=request.usuari.get('email', ''),
    )
    db.session.add(nou)
    fitxa.updated_at = datetime.now(timezone.utc)
    db.session.commit()

    if not result.get('ok'):
        return jsonify({
            'ok': False,
            'error': result.get('error') or 'Error retirant del destí',
            'distribucio': nou.to_dict(),
        }), 500

    return jsonify({
        'ok': True,
        'missatge': f"Retirat de '{desti.nom}' correctament",
        'fitxer': filename,
        'distribucio': nou.to_dict(),
    }), 200


@distribucions_bp.route('/fitxes/<int:fitxa_id>/distribuir/<int:desti_id>', methods=['POST'])
@rol_requerit('admin', 'editor', 'distribuidor')
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
