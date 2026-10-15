/* Session secrets stay in memory; the HttpOnly cookie is managed by the browser. */
(() => {
  const endpoint = '/api/v1/access/session';
  const form = document.getElementById('access-form');
  const input = document.getElementById('invitation-code');
  const message = document.getElementById('access-message');
  const submit = document.getElementById('access-submit');
  let session = null;

  function locked(copy) {
    session = null;
    document.body.dataset.access = 'locked';
    message.textContent = copy;
  }

  function entered(value) {
    session = value;
    input.value = '';
    document.body.dataset.access = 'ready';
    document.body.dataset.public = String(!value.local_mode);
    document.getElementById('access-logout').hidden = Boolean(value.local_mode);
    if (!value.environment_readonly) selectEnvironmentMode('manual');
  }

  async function restore() {
    try {
      const response = await fetch(endpoint, {cache: 'no-store', credentials: 'same-origin'});
      if (!response.ok) {
        locked(response.status === 401 ? '请输入收到的邀请码。' : '服务暂时不可用，请稍后刷新。');
        return;
      }
      entered(await response.json());
    } catch {
      locked('连接失败，请检查网络后刷新。');
    }
  }

  const ready = restore();
  window.ResearchOpsAccess = {
    async fetch(url, options = {}) {
      await ready;
      if (!session) throw new Error('请先输入邀请码。');
      const headers = new Headers(options.headers || {});
      if (session.csrf_token) headers.set('X-CSRF-Token', session.csrf_token);
      const response = await fetch(url, {...options, headers, cache: 'no-store', credentials: 'same-origin'});
      if (response.status === 401) {
        locked('会话已过期，请重新输入邀请码。');
        window.dispatchEvent(new Event('researchops-access-lost'));
        // Reload erases result DOM, pending polling and all prior in-memory data.
        window.location.replace('/mvp/');
        throw new Error('会话已过期，请重新进入。');
      }
      return response;
    }
  };

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    submit.disabled = true;
    message.textContent = '正在验证…';
    try {
      const response = await fetch('/api/v1/access/sessions', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({invitation_code: input.value.trim()}),
        cache: 'no-store', credentials: 'same-origin'
      });
      const value = await response.json().catch(() => ({}));
      if (!response.ok) {
        locked(response.status === 429 ? '尝试过于频繁，请稍后再试。' : (value.message || '暂时无法进入。'));
        return;
      }
      entered({...value, environment_readonly: false});
    } catch {
      locked('连接失败，请稍后手动重试。');
    } finally {
      input.value = '';
      submit.disabled = false;
    }
  });

  document.getElementById('access-logout').addEventListener('click', async () => {
    try {
      const response = await window.ResearchOpsAccess.fetch(endpoint, {method: 'DELETE'});
      if (!response.ok) throw new Error('退出失败，请重试。');
      window.location.replace('/mvp/');
    } catch (error) {
      window.alert(error.message || '退出失败，请稍后重试。');
    }
  });
})();
