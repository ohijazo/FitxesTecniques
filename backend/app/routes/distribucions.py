import os
from datetime import datetime, timezone
from urllib.parse import unquote
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


def _filename_de_referencia(ref):
    """Nom del fitxer a partir de la URL/path guardats a Distribucio.missatge_error.

    Quan estat='ok', missatge_error conte la URL publica (ftp/sftp/sharepoint) o
    el path complet (xarxa). Retorna None si la referencia no apunta a cap .pdf
    (per exemple quan es un motiu de retirada o un missatge d'error).

    L'unquote es imprescindible: el webUrl de Graph percent-encodeja els espais
    i sense desfer-ho es construiria un nom com '60360%20Farina.pdf' que no
    existeix al desti.
    """
    if not ref:
        return None
    candidate = unquote(ref.split('/')[-1].split('\\')[-1].split('?')[0])
    return candidate if candidate.lower().endswith('.pdf') else None


def _referencia_al_desti(fitxa, versio, desti):
    """(nom_fitxer, enllac) del fitxer d'aquesta fitxa en aquest desti.

    Tots dos surten de l'ultima distribucio 'ok', que es la que sap amb quin
    nom i a quina URL es va pujar realment. Si no n'hi ha cap, el nom s'obte
    del patro configurat i l'enllac queda a None (el calcula el verificador a
    partir de la configuracio del desti).

    Nota: es busca l'ultima 'ok' encara que despres s'hagi retirat, perque
    justament aleshores l'enllac serveix per anar a mirar si el PDF hi ha
    quedat (un 'sobrant').
    """
    dist_ok = Distribucio.query.join(VersioFitxa).filter(
        VersioFitxa.fitxa_id == fitxa.id,
        Distribucio.desti_id == desti.id,
        Distribucio.estat == 'ok',
    ).order_by(Distribucio.executat_at.desc()).first()

    ref = dist_ok.missatge_error if dist_ok else None
    nom = _filename_de_referencia(ref)
    if nom:
        return nom, ref
    return _generar_nom_fitxer(desti.patro_nom_fitxer, fitxa, versio), None


def _nom_fitxer_al_desti(fitxa, versio, desti):
    """Nom real del fitxer en aquest desti (veure _referencia_al_desti)."""
    return _referencia_al_desti(fitxa, versio, desti)[0]


def _assegurar_pdf(fitxa, versio):
    """Ruta local del PDF de la versio; el genera si encara no existeix.

    La data de revisio impresa ha de ser `data_revisio`, no `created_at`:
    created_at es quan es va crear la fila a la BD (per exemple durant una
    carrega massiva) i no te res a veure amb la revisio del document. Fins ara
    la distribucio hi posava created_at mentre que la descarrega des de l'app
    hi posava data_revisio, de manera que el PDF del desti mostrava una data
    diferent de la de la fitxa. Aquest es el mateix criteri que /fitxes/<id>/pdf.
    """
    pdf_path = versio.fitxer_pdf
    if pdf_path and os.path.exists(pdf_path):
        return pdf_path

    from app.services.pdf_generator import generar_pdf

    contingut = versio.contingut or {}
    if 'codi_referencia' not in contingut:
        contingut['codi_referencia'] = fitxa.art_codi
    if 'denominacio_comercial' not in contingut:
        contingut['denominacio_comercial'] = fitxa.nom_producte

    data_rev = ''
    if versio.data_revisio:
        data_rev = versio.data_revisio.strftime('%d/%m/%Y')
    elif versio.created_at:
        data_rev = versio.created_at.strftime('%d/%m/%Y')
    data_comp = (versio.data_comprovacio.strftime('%d/%m/%Y')
                 if versio.data_comprovacio else data_rev)

    pdf_bytes = generar_pdf(contingut, versio.num_versio, data_rev, data_comp)

    upload_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), '..',
                              'uploads', fitxa.art_codi, f'v{versio.num_versio}')
    os.makedirs(upload_dir, exist_ok=True)
    pdf_path = os.path.join(upload_dir, f'{fitxa.art_codi}.pdf')
    with open(pdf_path, 'wb') as f:
        f.write(pdf_bytes)
    versio.fitxer_pdf = pdf_path
    return pdf_path


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

        pdf_path = _assegurar_pdf(fitxa, versio)

        config = desti.configuracio or {}
        filename = _generar_nom_fitxer(desti.patro_nom_fitxer, fitxa, versio)
        result = distribuir_ftp(pdf_path, fitxa.art_codi, config, filename)

        if result['ok']:
            dist.estat = 'ok'
            dist.missatge_error = result.get('url', '')
        else:
            dist.estat = 'error'
            dist.missatge_error = result['error']

    elif desti.tipus == 'sftp':
        from app.services.sftp_distributor import distribuir_sftp

        pdf_path = _assegurar_pdf(fitxa, versio)

        config = desti.configuracio or {}
        filename = _generar_nom_fitxer(desti.patro_nom_fitxer, fitxa, versio)
        result = distribuir_sftp(pdf_path, fitxa.art_codi, config, filename)

        if result['ok']:
            dist.estat = 'ok'
            dist.missatge_error = result.get('url', '')
        else:
            dist.estat = 'error'
            dist.missatge_error = result['error']

    elif desti.tipus == 'xarxa':
        from app.services.smb_distributor import distribuir_xarxa

        pdf_path = _assegurar_pdf(fitxa, versio)

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

        pdf_path = _assegurar_pdf(fitxa, versio)

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

    # Nom real al desti: inferit de l'ultima distribucio 'ok', amb fallback al patro.
    filename = _nom_fitxer_al_desti(fitxa, versio_activa, desti)

    config = desti.configuracio or {}

    if desti.tipus == 'ftp':
        from app.services.ftp_distributor import eliminar_ftp
        result = eliminar_ftp(fitxa.art_codi, config, filename)
    elif desti.tipus == 'sftp':
        from app.services.sftp_distributor import eliminar_sftp
        result = eliminar_sftp(fitxa.art_codi, config, filename)
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


# --- Comprovacio: la fitxa hi es realment al desti? -------------------------
# L'estat 'ok' de l'historial nomes vol dir que la pujada no va fallar. Aquests
# endpoints tornen a llegir el PDF del desti. NO escriuen res a la BD.

MAX_DESTINS_SINCRON = 6   # per sobre d'aixo cal l'auditoria massiva (job)
TIMEOUT_SINCRON = 8       # segons de connexio per desti (6*8=48s < 120s Gunicorn)


def _destins_amb_fitxa(fitxa_id):
    """Destins on la BD diu que la fitxa hi es ARA.

    Nomes compten les distribucions que canvien si el fitxer hi ha de ser o no:
    'ok' (s'hi ha posat) i 'retirat' (s'ha tret). Guanya la mes recent.

    Els 'error' i els 'pendent' s'IGNOREN a proposit. Un error vol dir que la
    pujada va fallar, no que el fitxer s'hagi de treure: el que hi havia de
    l'ultima pujada bona hi segueix sent, i legitimament. Comptar-los feia que
    una fitxa amb un intent fallit recent es considerès "no esperada" al desti
    i que el fitxer correcte que hi havia sortis marcat com a 'sobrant'.
    """
    dists = Distribucio.query.join(VersioFitxa).filter(
        VersioFitxa.fitxa_id == fitxa_id,
        Distribucio.desti_id.isnot(None),
        Distribucio.estat.in_(('ok', 'retirat')),
    ).order_by(Distribucio.executat_at.desc().nullslast(),
               Distribucio.id.desc()).all()

    ultima_per_desti = {}
    for d in dists:
        ultima_per_desti.setdefault(d.desti_id, d)
    return {did for did, d in ultima_per_desti.items() if d.estat == 'ok'}


def _comprovar(fitxa, versio, destins, esperats):
    """Comprova cada desti en les dues direccions.

    Als destins on la fitxa consta distribuida es comprova que hi sigui; a la
    resta, que NO hi sigui (un PDF que hi ha quedat es un 'sobrant').
    """
    from app.services.verificador import ESTATS, verificar_distribucio

    resum = {e: 0 for e in ESTATS}
    resultats = []
    for desti in destins:
        res = verificar_distribucio(fitxa, versio, desti,
                                    timeout=TIMEOUT_SINCRON,
                                    esperat=desti.id in esperats)
        resum[res['estat_verificacio']] = resum.get(res['estat_verificacio'], 0) + 1
        resultats.append(res)

    return {
        'fitxa_id': fitxa.id,
        'art_codi': fitxa.art_codi,
        'num_versio': versio.num_versio if versio else None,
        'comprovat_at': datetime.now(timezone.utc).isoformat(),
        'resum': resum,
        'resultats': resultats,
    }


@distribucions_bp.route('/fitxes/<int:fitxa_id>/comprovar', methods=['POST'])
@rol_requerit('admin', 'editor', 'distribuidor')
def comprovar_destins(fitxa_id):
    """Comprova si l'estat real dels destins coincideix amb el que diu la BD.

    Per defecte mira TOTS els destins actius, en les dues direccions: on consta
    distribuida ha de ser-hi; on no hi consta, no hi ha de ser. Amb
    {"nomes_distribuides": true} nomes es miren els destins on hi consta.
    """
    fitxa = db.get_or_404(FitxaTecnica, fitxa_id)
    data = request.get_json(silent=True) or {}

    versio_activa = VersioFitxa.query.filter_by(
        fitxa_id=fitxa_id, activa=True
    ).first()
    if not versio_activa:
        return jsonify({'error': "No hi ha cap versió publicada"}), 400

    esperats = _destins_amb_fitxa(fitxa_id)

    if data.get('desti_ids'):
        destins = DestiDistribucio.query.filter(
            DestiDistribucio.id.in_(data['desti_ids'])).all()
    elif data.get('nomes_distribuides'):
        if not esperats:
            return jsonify({
                'fitxa_id': fitxa.id, 'art_codi': fitxa.art_codi,
                'num_versio': versio_activa.num_versio,
                'comprovat_at': datetime.now(timezone.utc).isoformat(),
                'resum': {}, 'resultats': [],
                'missatge': "Aquesta fitxa no consta distribuïda a cap destí",
            }), 200
        destins = DestiDistribucio.query.filter(
            DestiDistribucio.id.in_(esperats)).all()
    else:
        destins = DestiDistribucio.query.filter_by(actiu=True).all()

    if len(destins) > MAX_DESTINS_SINCRON:
        return jsonify({
            'error': f"Hi ha {len(destins)} destins a comprovar i el màxim "
                     f"immediat és {MAX_DESTINS_SINCRON}. Fes servir "
                     f"Configuració > Comprovació de destins."
        }), 400

    return jsonify(_comprovar(fitxa, versio_activa, destins, esperats)), 200


@distribucions_bp.route('/fitxes/<int:fitxa_id>/comprovar/<int:desti_id>', methods=['POST'])
@rol_requerit('admin', 'editor', 'distribuidor')
def comprovar_desti(fitxa_id, desti_id):
    """Comprova un sol desti."""
    fitxa = db.get_or_404(FitxaTecnica, fitxa_id)
    desti = db.get_or_404(DestiDistribucio, desti_id)

    versio_activa = VersioFitxa.query.filter_by(
        fitxa_id=fitxa_id, activa=True
    ).first()
    if not versio_activa:
        return jsonify({'error': "No hi ha cap versió publicada"}), 400

    esperats = _destins_amb_fitxa(fitxa_id)
    resultat = _comprovar(fitxa, versio_activa, [desti], esperats)
    return jsonify(resultat['resultats'][0]), 200
