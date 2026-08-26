import { defineConfig, devices } from '@playwright/test';

/**
 * Tests E2E contra l'entorn de desenvolupament local.
 *
 * NO executar contra produccio (ae01farwebsrv): encara que els tests son de
 * nomes lectura, no toquen dades reals de qualitat per principi.
 *
 * Requereix backend (port 5000) i frontend (port 5173) engegats, i les
 * credencials a variables d'entorn:
 *
 *   $env:E2E_EMAIL = "..."
 *   $env:E2E_PASSWORD = "..."
 *   npx playwright test
 */
export default defineConfig({
  testDir: './e2e',
  timeout: 30_000,
  expect: { timeout: 10_000 },
  // Sense reintents: si un smoke test es inestable, el problema es el test.
  retries: 0,
  reporter: [['list']],
  use: {
    baseURL: process.env.E2E_BASE_URL || 'http://localhost:5173',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    locale: 'ca-ES',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],
});
