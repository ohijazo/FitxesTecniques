"""Endpoints per gestionar JobBulk (operacions massives en background)."""

from datetime import datetime, timezone
from flask import Blueprint, request, jsonify

from app import db
from app.models import (JobBulk, JobItem, FitxaTecnica, DestiDistribucio,
                        VersioFitxa, Distribucio)
from app.auth import login_required, rol_requerit

jobs_bp = Blueprint('jobs', __name__)


@jobs_bp.route('/jobs/distribucio-massiva', methods=['POST'])
@rol_requerit('admin', 'editor', 'distribuidor')
def crear_job_distribucio_massiva():
    """Crea un JobBulk per distribuir un conjunt de fitxes a un conjunt de destins."""
    data = request.get_json() or {}
    fitxa_ids = data.get('fitxa_ids') or []
    desti_ids = data.get('desti_ids') or []

    if not isinstance(fitxa_ids, list) or not fitxa_ids:
        return jsonify({'error': "Cal indicar fitxa_ids (llista no buida)"}), 400
    if not isinstance(desti_ids, list) or not desti_ids:
        return jsonify({'error': "Cal indicar desti_ids (llista no buida)"}), 400

    fitxa_ids = list(dict.fromkeys(int(x) for x in fitxa_ids))
    desti_ids = list(dict.fromkeys(int(x) for x in desti_ids))

    # Validar existència de fitxes i destins
    fitxes = FitxaTecnica.query.filter(FitxaTecnica.id.in_(fitxa_ids)).all()
    fitxes_map = {f.id: f for f in fitxes}
    destins = DestiDistribucio.query.filter(DestiDistribucio.id.in_(desti_ids)).all()
    destins_map = {d.id: d for d in destins}

    if not fitxes_map:
        return jsonify({'error': "Cap fitxa vàlida"}), 400
    if not destins_map:
        return jsonify({'error': "Cap destí vàlid"}), 400

    # Detectar solapaments: items en curs amb mateix fitxa+desti
    en_curs = set()
    rows = db.session.query(JobItem.fitxa_id, JobItem.desti_id).filter(
        JobItem.estat.in_(('pendent', 'processant')),
        JobItem.fitxa_id.in_(list(fitxes_map.keys())),
        JobItem.desti_id.in_(list(destins_map.keys())),
    ).all()
    for fid, did in rows:
        en_curs.add((fid, did))

    job = JobBulk(
        tipus='distribucio_massiva',
        estat='creat',
        params={'fitxa_ids': fitxa_ids, 'desti_ids': desti_ids},
        created_by=request.usuari.get('email', ''),
        total_items=0,
        items_ok=0,
        items_error=0,
        items_pendents=0,
    )
    db.session.add(job)
    db.session.flush()

    total = 0
    pendents = 0
    omesos = 0
    for fid in fitxes_map:
        for did in destins_map:
            if not destins_map[did].actiu:
                continue
            estat_inicial = 'pendent'
            missatge = None
            if (fid, did) in en_curs:
                estat_inicial = 'omes'
                missatge = 'Ja en curs en un altre job'
                omesos += 1
            else:
                pendents += 1
            item = JobItem(
                job_id=job.id,
                fitxa_id=fid,
                desti_id=did,
                estat=estat_inicial,
                missatge_error=missatge,
            )
            db.session.add(item)
            total += 1

    job.total_items = total
    job.items_pendents = pendents
    job.items_error = 0
    if omesos > 0:
        # els omesos no compten com error, només informa via items
        pass
    db.session.commit()

    return jsonify(job.to_dict()), 201


def _parells_distribuits():
    """Parells (fitxa_id, desti_id) que la BD dona per distribuits ARA.

    Per cada parell nomes compta l'ultima distribucio: si va ser 'ok', la fitxa
    hi es; si va ser 'retirat' o 'error', no. Es la mateixa regla que fa servir
    el detall de la fitxa.
    """
    sql = db.text("""
        SELECT DISTINCT ON (v.fitxa_id, d.desti_id) v.fitxa_id, d.desti_id, d.estat
        FROM distribucio d JOIN versio_fitxa v ON v.id = d.versio_id
        WHERE d.desti_id IS NOT NULL
        ORDER BY v.fitxa_id, d.desti_id, d.executat_at DESC NULLS LAST, d.id DESC
    """)
    return {(fid, did) for fid, did, estat in db.session.execute(sql) if estat == 'ok'}


@jobs_bp.route('/jobs/verificacio-massiva', methods=['POST'])
@rol_requerit('admin', 'distribuidor')
def crear_job_verificacio_massiva():
    """Crea un JobBulk que comprova si les fitxes hi son realment als destins.

    Body (tot opcional):
      fitxa_ids: llista; per defecte totes les fitxes amb versio activa
      desti_ids: llista; per defecte tots els destins actius
      nomes_distribuides: bool (default True) - nomes els parells que la BD
        dona per distribuits. Amb False es comprova el producte cartesia, que
        tambe troba copies que haurien d'estar retirades.

    Aquest job NOMES informa: no crea cap Distribucio ni toca l'audit trail.
    """
    data = request.get_json(silent=True) or {}
    nomes_distribuides = data.get('nomes_distribuides', True)

    q_destins = DestiDistribucio.query.filter_by(actiu=True)
    if data.get('desti_ids'):
        ids = [int(x) for x in data['desti_ids']]
        q_destins = q_destins.filter(DestiDistribucio.id.in_(ids))
    destins = q_destins.all()
    if not destins:
        return jsonify({'error': "Cap destí vàlid"}), 400

    q_fitxes = (db.session.query(FitxaTecnica.id)
                .join(VersioFitxa, VersioFitxa.fitxa_id == FitxaTecnica.id)
                .filter(VersioFitxa.activa.is_(True)))
    if data.get('fitxa_ids'):
        ids = [int(x) for x in data['fitxa_ids']]
        q_fitxes = q_fitxes.filter(FitxaTecnica.id.in_(ids))
    fitxa_ids = [r[0] for r in q_fitxes.order_by(FitxaTecnica.art_codi).all()]
    if not fitxa_ids:
        return jsonify({'error': "Cap fitxa amb versió activa"}), 400

    parells_ok = _parells_distribuits() if nomes_distribuides else None

    parells = []
    for fid in fitxa_ids:
        for d in destins:
            if parells_ok is not None and (fid, d.id) not in parells_ok:
                continue
            parells.append((fid, d.id))

    if not parells:
        return jsonify({
            'error': "Cap fitxa consta distribuïda als destins seleccionats. "
                     "Desmarca 'Només on consta distribuïda' per comprovar-los tots."
        }), 400

    # Solapament: nomes contra altres verificacions en curs. Sense el filtre
    # per tipus, una distribucio massiva en curs ometria items de comprovacio.
    en_curs = {
        (fid, did) for fid, did in
        db.session.query(JobItem.fitxa_id, JobItem.desti_id)
        .join(JobBulk, JobBulk.id == JobItem.job_id)
        .filter(JobBulk.tipus == 'verificacio_massiva',
                JobItem.estat.in_(('pendent', 'processant'))).all()
    }

    job = JobBulk(
        tipus='verificacio_massiva',
        estat='creat',
        params={
            'abast': 'seleccio' if data.get('fitxa_ids') else 'totes',
            'desti_ids': [d.id for d in destins],
            'nomes_distribuides': bool(nomes_distribuides),
            'total_fitxes': len(fitxa_ids),
        },
        created_by=request.usuari.get('email', ''),
        total_items=0, items_ok=0, items_error=0, items_pendents=0,
    )
    db.session.add(job)
    db.session.flush()

    pendents = 0
    for fid, did in parells:
        omes = (fid, did) in en_curs
        db.session.add(JobItem(
            job_id=job.id, fitxa_id=fid, desti_id=did,
            estat='omes' if omes else 'pendent',
            missatge_error='Ja en curs en un altre job' if omes else None,
        ))
        if not omes:
            pendents += 1

    job.total_items = len(parells)
    job.items_pendents = pendents
    db.session.commit()

    return jsonify(job.to_dict()), 201


@jobs_bp.route('/jobs', methods=['GET'])
@login_required
def llistar_jobs():
    """Llista jobs amb paginació. Per defecte exclou arxivats."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    estat = request.args.get('estat', '', type=str)
    tipus = request.args.get('tipus', '', type=str)
    incloure_arxivats = request.args.get('incloure_arxivats', '0') == '1'

    q = JobBulk.query
    if not incloure_arxivats:
        q = q.filter(JobBulk.arxivat.isnot(True))
    if estat:
        q = q.filter(JobBulk.estat == estat)
    if tipus:
        q = q.filter(JobBulk.tipus == tipus)

    q = q.order_by(JobBulk.id.desc())
    pag = q.paginate(page=page, per_page=per_page, error_out=False)
    return jsonify({
        'jobs': [j.to_dict() for j in pag.items],
        'total': pag.total,
        'pages': pag.pages,
        'page': page,
    })


@jobs_bp.route('/jobs/<int:job_id>', methods=['GET'])
@login_required
def detall_job(job_id):
    job = db.get_or_404(JobBulk, job_id)
    return jsonify(job.to_dict())


@jobs_bp.route('/jobs/<int:job_id>/items', methods=['GET'])
@login_required
def llistar_items_job(job_id):
    db.get_or_404(JobBulk, job_id)
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 100, type=int)
    estat = request.args.get('estat', '', type=str)
    verificacio = request.args.get('verificacio', '', type=str)

    q = JobItem.query.filter_by(job_id=job_id)
    if estat:
        q = q.filter(JobItem.estat == estat)
    if verificacio:
        q = q.filter(JobItem.resultat['estat_verificacio'].as_string() == verificacio)
    q = q.order_by(JobItem.id)

    pag = q.paginate(page=page, per_page=per_page, error_out=False)
    return jsonify({
        'items': [it.to_dict() for it in pag.items],
        'total': pag.total,
        'pages': pag.pages,
        'page': page,
    })


@jobs_bp.route('/jobs/<int:job_id>/reprendre', methods=['POST'])
@rol_requerit('admin', 'editor', 'distribuidor')
def reprendre_job(job_id):
    """Reactiva un job interromput: items que estaven pendent o processant tornen a pendent."""
    job = db.get_or_404(JobBulk, job_id)
    if job.estat != 'interromput':
        return jsonify({'error': f"Només es poden reprendre jobs interromputs (estat actual: {job.estat})"}), 400

    # Els items 'processant' (queden si crash sense recovery) i 'pendent' ja existents tornen a pendent
    JobItem.query.filter(
        JobItem.job_id == job_id,
        JobItem.estat.in_(('processant', 'pendent')),
    ).update({'estat': 'pendent', 'locked_at': None, 'missatge_error': None,
              'resultat': None}, synchronize_session=False)

    job.estat = 'processant'
    job.finished_at = None

    pendents = JobItem.query.filter_by(job_id=job_id, estat='pendent').count()
    job.items_pendents = pendents

    db.session.commit()
    return jsonify(job.to_dict())


@jobs_bp.route('/jobs/<int:job_id>/arxivar', methods=['POST'])
@rol_requerit('admin', 'editor', 'distribuidor')
def arxivar_job(job_id):
    """Marca el job com arxivat (no s'esborra, audit trail intacte)."""
    job = db.get_or_404(JobBulk, job_id)
    if job.estat in ('creat', 'processant'):
        return jsonify({'error': "No es pot arxivar un job actiu"}), 400
    job.arxivat = True
    db.session.commit()
    return jsonify(job.to_dict())


@jobs_bp.route('/jobs/<int:job_id>/informe-verificacio', methods=['GET'])
@login_required
def informe_verificacio(job_id):
    """Recompte d'items per estat de comprovació (per a la pàgina d'informe)."""
    job = db.get_or_404(JobBulk, job_id)
    col = JobItem.resultat['estat_verificacio'].as_string()
    rows = (db.session.query(col, db.func.count())
            .filter(JobItem.job_id == job_id)
            .group_by(col).all())

    per_estat = {estat: total for estat, total in rows if estat}
    sense_resultat = (JobItem.query
                      .filter(JobItem.job_id == job_id,
                              JobItem.resultat.is_(None)).count())
    return jsonify({
        'job_id': job.id,
        'tipus': job.tipus,
        'per_estat': per_estat,
        'sense_resultat': sense_resultat,
    })
