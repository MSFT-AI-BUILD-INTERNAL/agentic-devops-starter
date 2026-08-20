/**
 * Playwright global setup: build a valid session cookie from a GitHub token
 * and save it as storageState so all tests start pre-authenticated.
 *
 * Mirrors the Python backend's Fernet-over-PBKDF2 cookie cipher exactly:
 *   key = PBKDF2(client_secret, salt, 600_000, sha256, 32 bytes)
 *   cookie = Fernet(key).encrypt(github_token)
 *
 * Required env vars (both must be set, otherwise setup is skipped):
 *   PLAYWRIGHT_GITHUB_TOKEN        — GitHub PAT with Copilot access
 *   PLAYWRIGHT_GITHUB_CLIENT_SECRET — GitHub App client secret (same value as
 *                                     COPILOT_APP_CLIENT_SECRET on the server)
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { createCipheriv, createHmac, pbkdf2Sync, randomBytes } from 'crypto';
import type { FullConfig } from '@playwright/test';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const SESSION_COOKIE = 'github_oauth_session';
const FERNET_KEY_SALT = Buffer.from(
  'agentic-devops-starter/oauth-cookie-encryption/v1',
  'utf8'
);

/**
 * Reproduce Python's `store_token`: encrypt a GitHub access token with the
 * same PBKDF2-derived Fernet cipher used by the FastAPI backend.
 */
function encryptSessionToken(clientSecret: string, token: string): string {
  const key = pbkdf2Sync(
    Buffer.from(clientSecret, 'utf8'),
    FERNET_KEY_SALT,
    600_000,
    32,
    'sha256'
  );
  const sigKey = key.subarray(0, 16);
  const encKey = key.subarray(16, 32);

  const iv = randomBytes(16);

  // AES-128-CBC with Node's default PKCS7 auto-padding
  const cipher = createCipheriv('aes-128-cbc', encKey, iv);
  const ciphertext = Buffer.concat([
    cipher.update(Buffer.from(token, 'utf8')),
    cipher.final(),
  ]);

  // Fernet header: version(1) + timestamp(8, big-endian uint64)
  const header = Buffer.allocUnsafe(9);
  header[0] = 0x80;
  header.writeBigUInt64BE(BigInt(Math.floor(Date.now() / 1000)), 1);

  const payload = Buffer.concat([header, iv, ciphertext]);
  const hmac = createHmac('sha256', sigKey).update(payload).digest();

  // URL-safe base64 without padding — Python's urlsafe_b64decode is tolerant
  return Buffer.concat([payload, hmac]).toString('base64url');
}

async function globalSetup(config: FullConfig): Promise<void> {
  const githubToken = process.env.PLAYWRIGHT_GITHUB_TOKEN;
  const clientSecret = process.env.PLAYWRIGHT_GITHUB_CLIENT_SECRET;

  if (!githubToken || !clientSecret) {
    // Not in CI with real credentials — tests will fall back to per-test mocks.
    return;
  }

  const { baseURL } = config.projects[0].use;
  if (!baseURL) throw new Error('playwright.config: baseURL must be set');

  const cookieValue = encryptSessionToken(clientSecret, githubToken);
  const { hostname } = new URL(baseURL);

  // Write storageState JSON directly — no browser needed just to set a cookie.
  const authDir = path.join(__dirname, '.auth');
  const authFile = path.join(authDir, 'user.json');
  fs.mkdirSync(authDir, { recursive: true });
  fs.writeFileSync(
    authFile,
    JSON.stringify({
      cookies: [
        {
          name: SESSION_COOKIE,
          value: cookieValue,
          domain: hostname,
          path: '/',
          expires: -1,
          httpOnly: true,
          secure: true,
          sameSite: 'Lax',
        },
      ],
      origins: [],
    }),
    'utf8'
  );

  // Round-trip check: confirm the server accepts the cookie before any test runs.
  const res = await fetch(`${baseURL}/api/auth/session`, {
    headers: { Cookie: `${SESSION_COOKIE}=${cookieValue}` },
  });
  if (res.status !== 200) {
    throw new Error(
      `Auth round-trip failed (HTTP ${res.status}). ` +
        'Check PLAYWRIGHT_GITHUB_TOKEN and PLAYWRIGHT_GITHUB_CLIENT_SECRET.'
    );
  }
}

export default globalSetup;
