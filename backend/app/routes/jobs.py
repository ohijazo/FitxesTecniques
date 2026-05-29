"""Endpoints per gestionar JobBulk (operacions massives en background)."""

from datetime import datetime, timezone
from flask import Blueprint, request, jsonify

from app import db
from app.models import JobBulk, JobItem, FitxaTecnica, DestiDistribucio
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

    q = JobItem.query.filter_by(job_id=job_id)
    if estat:
        q = q.filter(JobItem.estat == estat)
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
    ).update({'estat': 'pendent', 'locked_at': None, 'missatge_error': None}, synchronize_session=False)

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
