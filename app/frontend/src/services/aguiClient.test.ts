import { describe, expect, it, vi } from 'vitest';
import { aguiClient } from './aguiClient';
import * as isolationSession from '../utils/isolationSession';

describe('aguiClient', () => {
  it('posts to the thread abort endpoint', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true });
    vi.stubGlobal('fetch', fetchMock);
    vi.spyOn(isolationSession, 'getIsolationSessionId').mockReturnValue('iso-test');

    await aguiClient.abortThread('thread/123');

    expect(fetchMock).toHaveBeenCalledWith('/api/v1/threads/thread%2F123/abort', {
      method: 'POST',
      headers: { 'X-Isolation-Session-ID': 'iso-test' },
    });

    vi.unstubAllGlobals();
  });
});
