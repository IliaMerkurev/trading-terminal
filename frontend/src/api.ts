import { invoke } from '@tauri-apps/api/core';
import { getVersion } from '@tauri-apps/api/app';

export const isDesktop = () => '__TAURI_INTERNALS__' in window;

// Transport features are separate from the backend's execution/platform limits.
export function transportCapabilities() {
  const desktop = isDesktop();
  return {mode: desktop ? 'desktop' : 'browser', localService: !stopped,
    nativeWindow: desktop, openExportsFolder: desktop, downloadArchives: !desktop,
    stopService: !desktop} as const;
}

type BrowserSession = {token: string; product_version: string};
let session: Promise<BrowserSession> | undefined;
let stopped = false;

class LocalHttpError extends Error {}

async function localFetch<T>(path: string, init: RequestInit, read: (response: Response) => Promise<T>, bootstrap = false): Promise<T> {
  const controller = new AbortController();
  let timeout: ReturnType<typeof setTimeout> | undefined;
  const deadline = new Promise<never>((_resolve,reject) => {
    timeout = setTimeout(() => {controller.abort();reject(new Error('Local response timeout'));}, bootstrap ? 10000 : 60000);
  });
  const exchange = async () => {
    const response = await fetch(path, {...init, signal: controller.signal});
    if (!response.ok) throw new LocalHttpError(response.status === 401 || response.status === 403
      ? 'Local service access was rejected. Reopen the address printed by the browser launcher.'
      : `Local service request failed (HTTP ${response.status}).`);
    return read(response);
  };
  try {return await Promise.race([exchange(),deadline]);}
  catch (error) {
    if (error instanceof LocalHttpError) throw error;
    throw new Error(bootstrap
      ? 'Could not reach the local service. Start the browser launcher and use the address it prints.'
      : 'The local service response was lost or timed out. The request may have completed. Check current status and saved results before trying again.');
  } finally {clearTimeout(timeout);}
}

function browserSession(): Promise<BrowserSession> {
  if (stopped) return Promise.reject(new Error('Local service stopped. Restart the browser launcher to reconnect.'));
  // Keep the token only in this module's memory, never in URLs or browser storage.
  if (!session) session = localFetch('/api/session', {
    method: 'GET', headers: {'X-Terminal-Bootstrap': '1'},
    credentials: 'same-origin', mode: 'same-origin', cache: 'no-store', redirect: 'error',
  }, response => response.json(), true).then(value => {
    if (typeof value?.token !== 'string' || !value.token || typeof value.product_version !== 'string') {
      throw new Error('Invalid local service session response.');
    }
    return {token: value.token, product_version: value.product_version};
  }).catch(error => {session = undefined; throw error;});
  return session;
}

async function browserPost<T = any>(path: string, body: unknown, read: (response: Response) => Promise<T> = response => response.json()): Promise<T> {
  const {token} = await browserSession();
  // Never retry a POST: a disconnected response does not mean an action failed.
  return localFetch(path, {
    method: 'POST', headers: {'Content-Type': 'application/json', 'X-Terminal-Session': token},
    body: JSON.stringify(body), credentials: 'same-origin', mode: 'same-origin',
    cache: 'no-store', redirect: 'error',
  }, read);
}

export async function productVersion(): Promise<string> {
  return isDesktop() ? getVersion() : (await browserSession()).product_version;
}

export async function api<T = any>(command: string, params: Record<string, unknown> = {}): Promise<T> {
  const message = {version: 1, id: crypto.randomUUID(), command, params};
  const response = isDesktop()
    ? await invoke<any>('research_request', {message})
    : await browserPost('/api/request', message);
  if (!response || typeof response !== 'object') throw new Error('Invalid local service response.');
  if (!isDesktop() && (response.version !== message.version || response.id !== message.id)) {
    throw new Error('Local service response does not match this request.');
  }
  if (response.type !== 'result') throw new Error(response.error?.message ?? 'Research service failed');
  return response.result as T;
}

export async function downloadArchive(filename: string): Promise<void> {
  if (!transportCapabilities().downloadArchives) throw new Error('Archive downloads require browser mode.');
  if (!filename || /[/\\\u0000-\u001f]/.test(filename) || !filename.endsWith('.zip')) {
    throw new Error('Invalid archive filename.');
  }
  const blob = await browserPost('/api/export', {filename}, response => response.blob());
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url; link.download = filename;
  document.body.appendChild(link);
  try {link.click();} finally {
    link.remove();
    // Let the browser consume the download before releasing its blob URL.
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
}

export async function stopLocalService(): Promise<void> {
  if (!transportCapabilities().stopService) throw new Error('Use the desktop window to close the application.');
  await browserPost('/api/shutdown', {});
  stopped = true;
  session = undefined;
}
