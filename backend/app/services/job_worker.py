"""Worker resident per executar JobBulk en background.

Disseny:
- Un thread daemon llançat un sol cop a `create_app()`.
- Loop infinit que cada N segons agafa un JobItem 'pendent' amb FOR UPDATE SKIP LOCKED.
- Executa la distribució amb _executar_distribucio existent.
- Marca items encallats (processant > 10 min) com a error.
- Marca jobs amb tots els items terminals com a 'acabat'.
- A startup, marca com 'interromput' els jobs que estaven 'processant' i retorna els seus items
  'processant' a 'pendent' (recovery senzilla).

Amb 2 workers de Gunicorn tindrem 2 threads worker en processos separats. El
SELECT ... FOR UPDATE SKIP LOCKED garanteix que no agafin el mateix item.
"""

import logging
import os
import threading
import time
from datetime import datetime, timedelta, timezone

from sqlalchemy import text

LOG = logging.getLogger('job_worker')

POLL_INTERVAL = 2          # segons entre intents d'agafar item
STUCK_CHECK_INTERVAL = 30  # segons entre comprovacions d'items encallats
JOB_CHECK_INTERVAL = 60    # segons entre comprovacions de jobs acabats
HEARTBEAT_INTERVAL = 30    # segons entre actualitzacions del heartbeat al disc
STUCK_TIMEOUT_MIN = 10     # un item processant més de 10 min es considera encallat


_worker_started = False
_worker_lock = threading.Lock()


def iniciar_worker(app):
    """Llança el worker resident un sol cop per procés.

    Cridar des de create_app(). Idempotent — si ja està engegat dins el procés actual,
    no en llança un altre. Cada procés Gunicorn tindrà el seu (2 workers = 2 threads).
    """
    global _worker_started
    with _worker_lock:
        if _worker_started:
            return
        if os.environ.get('ENABLE_JOB_WORKER', '1') != '1':
            LOG.info('[JOB_WORKER] desactivat per ENABLE_JOB_WORKER=0')
            return
        _worker_started = True

    # Recovery de jobs interromputs (idempotent — segur si s'executa diversos cops)
    try:
        _recovery_startup(app)
    except Exception as e:
        LOG.exception('[JOB_WORKER] Error a recovery startup: %s', e)

    t = threading.Thread(target=_worker_loop, args=(app,), daemon=True, name='job-worker')
    t.start()
    LOG.info('[JOB_WORKER] thread arrencat (PID %s)', os.getpid())


def _recovery_startup(app):
    """Marca com 'interromput' tots els jobs que estaven 'processant'."""
    from app import db
    from app.models import JobBulk, JobItem

    with app.app_context():
        jobs_proc = JobBulk.query.filter_by(estat='processant').all()
        if not jobs_proc:
            return
        ids = [j.id for j in jobs_proc]
        for j in jobs_proc:
            j.estat = 'interromput'
        # Items 'processant' d'aquests jobs tornen a pendent
        JobItem.query.filter(
            JobItem.job_id.in_(ids),
            JobItem.estat == 'processant',
        ).update({'estat': 'pendent', 'locked_at': None}, synchronize_session=False)
        db.session.commit()
        LOG.info('[JOB_WORKER] Recovery: %d jobs marcats interromput', len(ids))


def _worker_loop(app):
    """Loop principal del worker."""
    from app import db
    from app.services import heartbeat

    ultim_stuck_check = 0
    ultim_job_check = 0
    ultim_heartbeat = 0

    # Toc inicial perquè l'estat sigui visible immediatament
    heartbeat.escriure()

    while True:
        try:
            with app.app_context():
                # Processar fins a N items consecutius si n'hi ha (evita esperes innecessàries)
                for _ in range(10):
                    if not _processar_seguent_item(app):
                        break
                    db.session.remove()

            ara = time.time()
            if ara - ultim_heartbeat >= HEARTBEAT_INTERVAL:
                ultim_heartbeat = ara
                heartbeat.escriure()

            if ara - ultim_stuck_check >= STUCK_CHECK_INTERVAL:
                ultim_stuck_check = ara
                try:
                    with app.app_context():
                        _marcar_encallats(app)
                except Exception as e:
                    LOG.exception('[JOB_WORKER] Error marcant encallats: %s', e)

            if ara - ultim_job_check >= JOB_CHECK_INTERVAL:
                ultim_job_check = ara
                try:
                    with app.app_context():
                        _finalitzar_jobs_acabats(app)
                except Exception as e:
                    LOG.exception('[JOB_WORKER] Error finalitzant jobs: %s', e)

        except Exception as e:
            LOG.exception('[JOB_WORKER] Error inesperat al loop: %s', e)

        time.sleep(POLL_INTERVAL)


def _processar_seguent_item(app):
    """Agafa un JobItem pendent amb SELECT FOR UPDATE SKIP LOCKED i l'executa.

    Retorna True si ha processat un item, False si no n'hi havia cap pendent.
    """
    from app import db
    from app.models import JobBulk, JobItem, FitxaTecnica, VersioFitxa, DestiDistribucio, Distribucio
    from app.routes.distribucions import _executar_distribucio, _generar_nom_fitxer

    # 1) Agafar item de manera atòmica
    session = db.session
    try:
        # Exclou items de jobs cancel·lats/interromputs: el job ja ha canviat
        # d'estat i no se n'han de processar més items.
        result = session.execute(
            text("""
                SELECT ji.id FROM job_item ji
                JOIN job_bulk jb ON jb.id = ji.job_id
                WHERE ji.estat = 'pendent'
                  AND jb.estat NOT IN ('cancellat', 'interromput')
                ORDER BY ji.id
                FOR UPDATE SKIP LOCKED
                LIMIT 1
            """)
        )
        row = result.first()
        if not row:
            session.rollback()
            return False

        item_id = row[0]
        ara = datetime.now(timezone.utc)
        session.execute(
            text("""
                UPDATE job_item
                SET estat = 'processant', locked_at = :ara, intent_count = COALESCE(intent_count, 0) + 1
                WHERE id = :id
            """),
            {'ara': ara, 'id': item_id},
        )
        session.commit()
    except Exception as e:
        session.rollback()
        LOG.exception('[JOB_WORKER] Error agafant item: %s', e)
        return False

    # 2) Carregar entitats relacionades i executar
    item = JobItem.query.get(item_id)
    if not item:
        return True  # ha desaparegut, segueix

    # Marcar started_at del job si és la primera vegada
    job = JobBulk.query.get(item.job_id)
    if job and not job.started_at:
        job.started_at = ara
    if job and job.estat == 'creat':
        job.estat = 'processant'
    session.commit()

    estat_final = 'error'
    missatge_error = None

    try:
        if item.job and item.job.tipus == 'distribucio_massiva':
            estat_final, missatge_error = _executar_item_distribucio(item)
        else:
            missatge_error = f"Tipus de job desconegut: {item.job.tipus if item.job else '?'}"
    except Exception as e:
        LOG.exception('[JOB_WORKER] Error executant item %s: %s', item_id, e)
        missatge_error = str(e)
        estat_final = 'error'

    # 3) Marcar resultat + actualitzar contadors del job
    try:
        item.estat = estat_final
        item.missatge_error = missatge_error
        item.executat_at = datetime.now(timezone.utc)
        item.locked_at = None

        job = JobBulk.query.get(item.job_id)
        if job:
            if estat_final == 'ok':
                job.items_ok = (job.items_ok or 0) + 1
            elif estat_final == 'error':
                job.items_error = (job.items_error or 0) + 1
            pendents_count = JobItem.query.filter(
                JobItem.job_id == job.id,
                JobItem.estat.in_(('pendent', 'processant')),
            ).count()
            job.items_pendents = pendents_count
            # Si era l'últim item, marca el job com acabat (no toquem si està cancel·lat)
            if pendents_count == 0 and job.estat == 'processant':
                job.estat = 'acabat'
                job.finished_at = datetime.now(timezone.utc)

        session.commit()
    except Exception as e:
        session.rollback()
        LOG.exception('[JOB_WORKER] Error guardant resultat item %s: %s', item_id, e)

    return True


def _executar_item_distribucio(item):
    """Executa un JobItem de tipus distribucio_massiva.

    Retorna tupla (estat_final, missatge_error).
    """
    from app import db
    from app.models import FitxaTecnica, VersioFitxa, DestiDistribucio, Distribucio
    from app.routes.distribucions import _executar_distribucio

    if not item.fitxa_id or not item.desti_id:
        return 'error', 'Item incomplet (falta fitxa o destí)'

    fitxa = FitxaTecnica.query.get(item.fitxa_id)
    if not fitxa:
        return 'error', f'Fitxa {item.fitxa_id} no trobada'

    desti = DestiDistribucio.query.get(item.desti_id)
    if not desti or not desti.actiu:
        return 'error', f'Destí {item.desti_id} no actiu o no trobat'

    versio_activa = VersioFitxa.query.filter_by(fitxa_id=fitxa.id, activa=True).first()
    if not versio_activa:
        return 'error', f'Fitxa {fitxa.art_codi} sense versió publicada'

    # Crear registre Distribucio (audit trail tradicional)
    dist = Distribucio(
        versio_id=versio_activa.id,
        desti_id=desti.id,
        desti=desti.nom,
        estat='pendent',
    )
    db.session.add(dist)
    db.session.flush()

    executat_by = (item.job.created_by or '') if item.job else ''

    try:
        _executar_distribucio(dist, fitxa, versio_activa, desti, executat_by=executat_by)
        db.session.commit()
    except Exception as e:
        dist.estat = 'error'
        dist.missatge_error = str(e)
        db.session.commit()
        return 'error', str(e)

    if dist.estat == 'ok':
        return 'ok', dist.missatge_error  # contains url/path on success
    return 'error', dist.missatge_error or 'Error desconegut'


def _marcar_encallats(app):
    """Marca com a error els items que porten massa estona en 'processant'."""
    from app import db
    from app.models import JobItem

    limit = datetime.now(timezone.utc) - timedelta(minutes=STUCK_TIMEOUT_MIN)
    encallats = JobItem.query.filter(
        JobItem.estat == 'processant',
        JobItem.locked_at != None,
        JobItem.locked_at < limit,
    ).all()
    if not encallats:
        return
    for it in encallats:
        it.estat = 'error'
        it.missatge_error = f'Timeout (>{STUCK_TIMEOUT_MIN} min processant)'
        it.executat_at = datetime.now(timezone.utc)
        it.locked_at = None
    db.session.commit()
    LOG.warning('[JOB_WORKER] Marcats %d items com encallats', len(encallats))


def _finalitzar_jobs_acabats(app):
    """Marca com 'acabat' els JobBulk on tots els items són terminals."""
    from app import db
    from app.models import JobBulk, JobItem

    jobs_proc = JobBulk.query.filter_by(estat='processant').all()
    for job in jobs_proc:
        pendents = JobItem.query.filter(
            JobItem.job_id == job.id,
            JobItem.estat.in_(('pendent', 'processant')),
        ).count()
        if pendents == 0:
            job.estat = 'acabat'
            job.finished_at = datetime.now(timezone.utc)
            job.items_pendents = 0
    if jobs_proc:
        db.session.commit()
