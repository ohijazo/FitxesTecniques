"""Test end-to-end de bulk distribution + bulk-edit.

Fa crides HTTP reals contra el backend localhost:50002.
"""
import time
import json
import urllib.request
import urllib.error

BASE = 'http://localhost:50002/api'
EMAIL = 'test_bulk@test.local'
PASSWORD = 'testbulk123'


def call(method, path, body=None, token=None):
    url = f'{BASE}{path}'
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header('Content-Type', 'application/json')
    if token:
        req.add_header('Authorization', f'Bearer {token}')
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        try:
            return e.code, json.loads(body)
        except Exception:
            return e.code, {'error': body}


def log(msg):
    print(f'  >> {msg}')


def main():
    print('=' * 60)
    print('TEST E2E: bulk distribution + bulk-edit')
    print('=' * 60)

    # 1. LOGIN
    print('\n[1] Login')
    status, data = call('POST', '/auth/login', {'email': EMAIL, 'password': PASSWORD})
    assert status == 200, f'Login failed: {status} {data}'
    token = data['token']
    log(f'token obtingut ({len(token)} chars)')

    # 2. LIST FITXES (get 2 IDs)
    print('\n[2] Llistar fitxes publicades')
    status, data = call('GET', '/fitxes?estat=publicada&per_page=3', token=token)
    assert status == 200, f'Llistar failed: {status} {data}'
    fitxes = data['fitxes']
    assert len(fitxes) >= 2, f'Cal almenys 2 fitxes publicades, hi ha {len(fitxes)}'
    fid1, fid2 = fitxes[0]['id'], fitxes[1]['id']
    log(f'fitxes per tests: {fitxes[0]["art_codi"]} (id={fid1}), {fitxes[1]["art_codi"]} (id={fid2})')

    # 3. LIST DESTINS (find TEST_BULK_xarxa)
    print('\n[3] Buscar destí TEST_BULK_xarxa')
    status, data = call('GET', '/admin/destins', token=token)
    assert status == 200, f'Llistar destins failed: {status} {data}'
    test_desti = next((d for d in data if d['nom'] == 'TEST_BULK_xarxa'), None)
    assert test_desti, 'Destí TEST_BULK_xarxa no trobat'
    desti_id = test_desti['id']
    log(f'destí test id={desti_id}')

    # 4. CREATE JOB
    print('\n[4] Crear job distribució massiva')
    status, data = call('POST', '/jobs/distribucio-massiva',
                        {'fitxa_ids': [fid1, fid2], 'desti_ids': [desti_id]}, token=token)
    assert status == 201, f'Crear job failed: {status} {data}'
    job_id = data['id']
    log(f'job id={job_id}, total={data["total_items"]}, estat={data["estat"]}')
    assert data['total_items'] == 2, f'Esperava 2 items, hi ha {data["total_items"]}'

    # 5. POLL JOB UNTIL DONE (or timeout)
    print('\n[5] Esperar que el worker processi el job (timeout 30s)')
    start = time.time()
    while time.time() - start < 30:
        status, job = call('GET', f'/jobs/{job_id}', token=token)
        log(f'estat={job["estat"]}, ok={job["items_ok"]}, error={job["items_error"]}, pendents={job["items_pendents"]}')
        if job['estat'] in ('acabat', 'interromput', 'error'):
            break
        time.sleep(2)
    else:
        print('  [FAIL] TIMEOUT: el job no s\'ha acabat en 30s')
        return False

    # 6. CHECK ITEMS
    print('\n[6] Comprovar items del job')
    status, data = call('GET', f'/jobs/{job_id}/items', token=token)
    for it in data['items']:
        log(f'item {it["id"]}: fitxa={it["fitxa_codi"]}, desti={it["desti_nom"]}, estat={it["estat"]}, msg={it.get("missatge_error", "")[:80]}')

    # 7. BULK EDIT
    print('\n[7] Bulk edit: canviar vida_util en 2 fitxes')
    nou_valor = f'Test bulk edit {int(time.time())}'
    status, data = call('POST', '/fitxes/bulk-edit', {
        'fitxa_ids': [fid1, fid2],
        'canvis': {'vida_util': nou_valor},
        'descripcio_canvi': 'Test e2e bulk edit — actualització programada',
        'password': PASSWORD,
    }, token=token)
    assert status == 200, f'Bulk edit failed: {status} {data}'
    log(f'lot_uuid={data["lot_uuid"]}, ok={len(data["ok"])}, errors={len(data["errors"])}')
    for err in data['errors']:
        log(f'  error: {err}')
    assert len(data['ok']) == 2, f'Esperava 2 ok, hi ha {len(data["ok"])}'

    # 8. CHECK NEW VERSIONS
    print('\n[8] Verificar nova versió a cada fitxa')
    for fid in [fid1, fid2]:
        status, data = call('GET', f'/fitxes/{fid}', token=token)
        versions = data['versions']
        # la primera versió a la llista ha de ser l'activa nova
        activa = next((v for v in versions if v['activa']), None)
        assert activa, f'Fitxa {fid} sense versió activa'
        assert nou_valor in str(activa['contingut'].get('vida_util', '')), \
            f'Nou valor no aplicat. vida_util={activa["contingut"].get("vida_util")}'
        assert '[BULK ' in activa['descripcio_canvi'], \
            f'descripcio_canvi no conté [BULK ...]: {activa["descripcio_canvi"]}'
        log(f'fitxa {data["art_codi"]}: v{activa["num_versio"]} activa, descripcio="{activa["descripcio_canvi"][:60]}..."')

    # 9. TEST EDGE CASE: art_codi prohibit
    print('\n[9] Test camp prohibit (art_codi)')
    status, data = call('POST', '/fitxes/bulk-edit', {
        'fitxa_ids': [fid1],
        'canvis': {'art_codi': 'BAD'},
        'descripcio_canvi': 'Should fail validation',
        'password': PASSWORD,
    }, token=token)
    assert status == 400, f'Esperava 400, hi ha {status}'
    log(f'rebutjat correctament: {data["error"]}')

    # 10. TEST EDGE CASE: contrasenya errònia
    print('\n[10] Test contrasenya errònia')
    status, data = call('POST', '/fitxes/bulk-edit', {
        'fitxa_ids': [fid1],
        'canvis': {'vida_util': 'x'},
        'descripcio_canvi': 'Should fail auth',
        'password': 'WRONG',
    }, token=token)
    assert status == 403, f'Esperava 403, hi ha {status}'
    log(f'rebutjat correctament: {data["error"]}')

    print('\n' + '=' * 60)
    print('[OK] TOTS ELS TESTS PASSATS')
    print('=' * 60)
    return True


if __name__ == '__main__':
    import sys
    try:
        ok = main()
        sys.exit(0 if ok else 1)
    except AssertionError as e:
        print(f'\n[FAIL] ASSERTION FAILED: {e}')
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f'\n[FAIL] EXCEPTION: {e}')
        import traceback
        traceback.print_exc()
        sys.exit(1)
