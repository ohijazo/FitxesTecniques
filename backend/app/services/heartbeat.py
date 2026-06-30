"""Heartbeat dels workers residents.

Cada worker (un per procés Gunicorn) toca un fitxer al directori
`HEARTBEAT_DIR` cada N segons. El health endpoint mira l'mtime dels fitxers
per saber si hi ha algun worker viu.

Per què fitxers i no una taula: evita una migració per a un mecanisme que
viu en cooperació amb sysadmin. Els fitxers són efímers (a /tmp per defecte)
i es netegen sols a cada arrencada de procés.

Variable d'entorn:
    HEARTBEAT_DIR — directori de fitxers .beat (default /tmp)
"""
import logging
import os
import time

LOG = logging.getLogger(__name__)

DEFAULT_DIR = '/tmp'
FILE_PREFIX = 'fitxes-worker-'
FILE_SUFFIX = '.beat'
STALE_SECONDS = 120  # si l'últim heartbeat és més vell, el worker és 'stale'


def _dir():
    return os.environ.get('HEARTBEAT_DIR', DEFAULT_DIR).strip() or DEFAULT_DIR


def _path(pid):
    return os.path.join(_dir(), f'{FILE_PREFIX}{pid}{FILE_SUFFIX}')


def escriure(pid=None):
    """Toca el fitxer del worker actual. Captura errors silenciosament."""
    if pid is None:
        pid = os.getpid()
    try:
        d = _dir()
        if not os.path.isdir(d):
            os.makedirs(d, exist_ok=True)
        path = _path(pid)
        # Sols actualitzem mtime; el contingut és el timestamp llegible
        with open(path, 'w') as f:
            f.write(str(int(time.time())))
    except OSError as e:
        LOG.warning('[HEARTBEAT] No s\'ha pogut escriure (pid=%s): %s', pid, e)


def estat():
    """Retorna l'estat del worker basat en els fitxers heartbeat existents.

    Returns:
        dict amb:
          - 'ok' (bool)
          - 'workers': llista de {pid, last_seen_epoch, age_seconds}
          - 'estat': 'ok' | 'stale' | 'unknown'
    """
    try:
        d = _dir()
        if not os.path.isdir(d):
            return {'ok': False, 'workers': [], 'estat': 'unknown'}

        ara = time.time()
        workers = []
        for nom in os.listdir(d):
            if nom.startswith(FILE_PREFIX) and nom.endswith(FILE_SUFFIX):
                path = os.path.join(d, nom)
                try:
                    mtime = os.path.getmtime(path)
                except OSError:
                    continue
                pid_str = nom[len(FILE_PREFIX):-len(FILE_SUFFIX)]
                try:
                    pid = int(pid_str)
                except ValueError:
                    continue
                workers.append({
                    'pid': pid,
                    'last_seen_epoch': int(mtime),
                    'age_seconds': int(ara - mtime),
                })

        if not workers:
            return {'ok': False, 'workers': [], 'estat': 'unknown'}

        viu = any(w['age_seconds'] <= STALE_SECONDS for w in workers)
        return {
            'ok': viu,
            'workers': workers,
            'estat': 'ok' if viu else 'stale',
        }
    except OSError as e:
        LOG.warning('[HEARTBEAT] Error llegint estat: %s', e)
        return {'ok': False, 'workers': [], 'estat': 'unknown'}
