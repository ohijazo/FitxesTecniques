/**
 * Smoke test: el cami que fa el departament de qualitat cada dia.
 *
 * Nomes lectura. No crea, edita, publica ni distribueix res: aixi es pot
 * executar tantes vegades com calgui sense embrutar la BD ni tocar el FTP.
 *
 * Credencials per variable d'entorn — mai al repo (regla del CLAUDE.md).
 */

import { test, expect } from '@playwright/test';

const EMAIL = process.env.E2E_EMAIL;
const PASSWORD = process.env.E2E_PASSWORD;

test.beforeAll(() => {
  if (!EMAIL || !PASSWORD) {
    throw new Error(
      'Falten les credencials. Defineix E2E_EMAIL i E2E_PASSWORD abans d\'executar:\n' +
      '  $env:E2E_EMAIL = "usuari@farineracoromina.com"\n' +
      '  $env:E2E_PASSWORD = "..."'
    );
  }
});

async function entrar(page) {
  await page.goto('/login');
  await page.getByRole('textbox', { name: 'Correu electrònic' }).fill(EMAIL);
  await page.getByLabel('Contrasenya').fill(PASSWORD);
  await page.getByRole('button', { name: 'Iniciar sessió' }).click();
  await expect(page.getByRole('heading', { name: 'Fitxes tècniques' })).toBeVisible();
}

test.describe('Fitxes tècniques — smoke', () => {

  test('el login correcte porta a la llista de fitxes', async ({ page }) => {
    await entrar(page);

    // La barra de navegacio nomes apareix amb sessio iniciada
    await expect(page.getByRole('link', { name: 'FC Fitxes Tècniques' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Sortir' })).toBeVisible();
    // El token s'ha de guardar: sense ell, cada recarrega tornaria al login
    expect(await page.evaluate(() => localStorage.getItem('token'))).toBeTruthy();
  });

  test('el login incorrecte mostra error i no deixa entrar', async ({ page }) => {
    await page.goto('/login');
    await page.getByRole('textbox', { name: 'Correu electrònic' }).fill(EMAIL);
    await page.getByLabel('Contrasenya').fill('contrasenya-incorrecta');
    await page.getByRole('button', { name: 'Iniciar sessió' }).click();

    // Comprovar el missatge concret, no nomes que hi hagi un alert: si el
    // backend no respon, el 502 tambe pinta un alert i el test passaria sense
    // haver provat res.
    await expect(page.getByRole('alert')).toContainText('Email o contrasenya incorrectes');
    await expect(page).toHaveURL(/\/login/);
    expect(await page.evaluate(() => localStorage.getItem('token'))).toBeNull();
  });

  test('una ruta protegida sense sessio redirigeix al login', async ({ page }) => {
    await page.goto('/fitxes/1');
    await expect(page).toHaveURL(/\/login/);
    await expect(page.getByRole('button', { name: 'Iniciar sessió' })).toBeVisible();
  });

  test('la llista carrega fitxes i la cerca filtra', async ({ page }) => {
    await entrar(page);

    const files = page.locator('tbody tr');
    await expect(files.first()).toBeVisible();
    const totalInicial = await files.count();
    expect(totalInicial).toBeGreaterThan(0);

    // Cercar pel codi de la primera fitxa ha de reduir la llista
    const primerCodi = (await files.first().locator('code').innerText()).trim();
    await page.getByLabel('Cercar fitxes').fill(primerCodi);
    await page.getByLabel('Cercar fitxes').press('Enter');

    await expect(files.first().locator('code')).toHaveText(primerCodi);
    expect(await files.count()).toBeLessThanOrEqual(totalInicial);
  });

  test('des de la llista s\'obre el detall de la fitxa', async ({ page }) => {
    await entrar(page);

    const primeraFila = page.locator('tbody tr').first();
    const codi = (await primeraFila.locator('code').innerText()).trim();
    await primeraFila.locator('code').click();

    await expect(page).toHaveURL(/\/fitxes\/\d+$/);
    // El breadcrumb confirma que hem canviat de context
    await expect(page.getByLabel('Breadcrumb')).toContainText('Fitxa #');
    // El codi d'article es la clau del sistema: ha de sortir al detall
    await expect(page.getByText(codi, { exact: false }).first()).toBeVisible();
  });

  test('sortir tanca la sessio i neteja el token', async ({ page }) => {
    await entrar(page);
    await page.getByRole('button', { name: 'Sortir' }).click();

    await expect(page.getByRole('button', { name: 'Iniciar sessió' })).toBeVisible();
    expect(await page.evaluate(() => localStorage.getItem('token'))).toBeNull();
  });
});
