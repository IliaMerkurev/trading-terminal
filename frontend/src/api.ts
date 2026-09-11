import { invoke } from '@tauri-apps/api/core';
export const isDesktop = () => '__TAURI_INTERNALS__' in window;
export async function api<T = any>(command: string, params: Record<string, unknown> = {}): Promise<T> {
  if (!isDesktop()) throw new Error('Open the Windows desktop application to use the local research service.');
  const response = await invoke<any>('research_request', {
    message: { version: 1, id: crypto.randomUUID(), command, params },
  });
  if (response.type !== 'result') throw new Error(response.error?.message ?? 'Research service failed');
  return response.result as T;
}
