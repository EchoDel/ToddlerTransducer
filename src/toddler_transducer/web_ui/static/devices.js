const DEVICES_SECTION_ID = 'devicesSection';
let devicesScanned = [];

function devicesJson(url, options) {
  const opts = options || {};
  opts.headers = Object.assign({ 'Content-Type': 'application/json' }, opts.headers || {});
  return fetch(url, opts).then(
    (resp) =>
      resp.text().then((text) => {
        let data = {};
        try {
          data = JSON.parse(text);
        } catch (err) {
          data = { error: 'Server error (' + resp.status + '): ' + String(text).slice(0, 300) };
        }
        return { ok: resp.ok, data };
      }),
    () => ({ ok: false, data: { error: 'Network error - is the server running?' } }),
  );
}

function devicesError(data) {
  return window.alert('Failed: ' + (data && data.error ? data.error : 'unknown error'));
}

function devicesEscape(text) {
  const div = document.createElement('div');
  div.textContent = text == null ? '' : String(text);
  return div.innerHTML;
}

function devicesRender(state) {
  const el = document.getElementById(DEVICES_SECTION_ID);
  if (!el) return;

  const role = state.role;
  const statusHtml = (state.last_error || state.last_synced)
    ? `<p class="mb-1"><strong>Last synced:</strong> ${devicesEscape(state.last_synced || 'never')}</p>
       <p class="mb-1"><strong>Songs:</strong> ${devicesEscape(state.song_count)}</p>
       ${state.last_error ? `<p class="mb-1 text-danger"><strong>Last error:</strong> ${devicesEscape(state.last_error)}</p>` : ''}`
    : '';

  const roleHtml = `
    <div class="mb-2">
      <label class="form-check-label me-3">
        <input type="radio" name="deviceRole" value="master" ${role === 'master' ? 'checked' : ''}> Master (song library)
      </label>
      <label class="form-check-label">
        <input type="radio" name="deviceRole" value="slave" ${role === 'slave' ? 'checked' : ''}> Slave (mirror)
      </label>
      <button type="button" class="btn btn-sm btn-outline-secondary ms-2" id="saveRoleBtn">Save</button>
    </div>`;

  let bodyHtml = '';
  if (role === 'master') {
    const slaves = state.bound_slaves || [];
    const slavesHtml = slaves.length
      ? slaves.map((name) => `
        <span class="me-3">
          ${devicesEscape(name)}
          <button type="button" class="btn btn-sm btn-outline-danger py-0 px-1" data-unpair="${devicesEscape(name)}">Unpair</button>
        </span>`).join('')
      : 'None';
    bodyHtml = `
      <div class="mb-2">
        <strong>Pairing code:</strong> <span class="font-monospace" id="pairingCode">${devicesEscape(state.pairing_code || '')}</span>
        <button type="button" class="btn btn-sm btn-outline-secondary ms-2" id="regenerateCodeBtn">Regenerate code</button>
      </div>
      <div class="mb-2">
        <strong>Bound slaves:</strong>
        <span id="boundSlaves">${slavesHtml}</span>
      </div>`;
  } else if (role === 'slave') {
    bodyHtml = `
      <div class="mb-2">
        <button type="button" class="btn btn-sm btn-outline-primary" id="scanBtn">Scan for devices</button>
        <div id="scanResults" class="mt-2"></div>
        <div class="mt-2">
          <label class="form-label" for="pairCodeInput">Pairing code (shown on the master's Devices page):</label>
          <input type="text" class="form-control form-control-sm d-inline-block w-auto" id="pairCodeInput">
          <button type="button" class="btn btn-sm btn-primary ms-2" id="bindBtn">Bind</button>
        </div>
        <div class="mt-2">
          <strong>Master:</strong> <span>${devicesEscape(state.master_hostname || 'not bound')}</span>
          <button type="button" class="btn btn-sm btn-outline-danger ms-2" id="unbindBtn">Unbind</button>
        </div>
        ${state.master_hostname ? '<button type="button" class="btn btn-sm btn-outline-secondary mt-2" id="syncNowBtn">Sync now</button>' : ''}
        ${statusHtml}
      </div>`;
  } else {
    bodyHtml = '<p>Choose a role above to get started. A master hosts the song library; a slave mirrors it.</p>';
  }

  el.innerHTML = `<h3 class="h5">This device</h3>${roleHtml}${bodyHtml}`;

  const saveRoleBtn = document.getElementById('saveRoleBtn');
  if (saveRoleBtn) {
    saveRoleBtn.addEventListener('click', async () => {
      try {
        const selected = document.querySelector('input[name="deviceRole"]:checked');
        if (!selected) return;
        const target = selected.value;
        if (target !== role && !window.confirm(`Switch this device to ${target} mode?`)) return;
        const { ok, data } = await devicesJson('/api/devices/role', { method: 'POST', body: JSON.stringify({ role: target }) });
        if (!ok) {
          devicesError(data);
          return;
        }
        devicesLoad();
      } catch (exc) {
        window.alert('Failed to save role: ' + exc);
      }
    });
  }

  const regenerateCodeBtn = document.getElementById('regenerateCodeBtn');
  if (regenerateCodeBtn) {
    regenerateCodeBtn.addEventListener('click', async () => {
      const { data } = await devicesJson('/api/devices/pairing_code', { method: 'POST' });
      if (data.ok) devicesLoad();
    });
  }

  const scanBtn = document.getElementById('scanBtn');
  if (scanBtn) {
    scanBtn.addEventListener('click', async () => {
      const results = document.getElementById('scanResults');
      results.innerHTML = '<p>Scanning...</p>';
      const { data } = await devicesJson('/api/devices/scan', { method: 'POST' });
      if (!data.ok || !data.devices || !data.devices.length) {
        results.innerHTML = '<p>No master devices found. Ensure the master has its role set to Master.</p>';
        return;
      }
      devicesScanned = data.devices;
      results.innerHTML = devicesScanned
        .map((device, index) => `
          <label class="form-check-label me-3">
            <input type="radio" name="scanResult" value="${index}" ${index === 0 ? 'checked' : ''}>
            ${devicesEscape(device.device_name)} (${devicesEscape(device.hostname)})
          </label>`)
        .join('');
    });
  }

  const bindBtn = document.getElementById('bindBtn');
  if (bindBtn) {
    bindBtn.addEventListener('click', async () => {
      const selected = document.querySelector('input[name="scanResult"]:checked');
      if (!selected) {
        window.alert('Scan for devices and select a master first.');
        return;
      }
      const device = devicesScanned[Number(selected.value)];
      const code = document.getElementById('pairCodeInput').value.trim();
      const { data } = await devicesJson('/api/devices/bind', {
        method: 'POST',
        body: JSON.stringify({ hostname: device.hostname, port: device.port, code }),
      });
      if (data.ok) {
        window.alert(`Bound to ${data.master_device_name}.`);
        devicesLoad();
      } else {
        window.alert('Binding failed: ' + (data.error || 'unknown error'));
      }
    });
  }

  const unbindBtn = document.getElementById('unbindBtn');
  if (unbindBtn) {
    unbindBtn.addEventListener('click', async () => {
      if (!window.confirm('Unbind this device from the master?')) return;
      const { data } = await devicesJson('/api/devices/unbind', { method: 'POST' });
      if (data.ok) devicesLoad();
    });
  }

  const syncNowBtn = document.getElementById('syncNowBtn');
  if (syncNowBtn) {
    syncNowBtn.addEventListener('click', async () => {
      const { data } = await devicesJson('/api/devices/sync_now', { method: 'POST' });
      if (data.ok) window.setTimeout(devicesLoad, 2000);
    });
  }

  document.querySelectorAll('[data-unpair]').forEach((btn) => {
    btn.addEventListener('click', async () => {
      if (!window.confirm(`Unpair ${btn.getAttribute('data-unpair')}?`)) return;
      const { data } = await devicesJson('/api/devices/unpair', {
        method: 'POST',
        body: JSON.stringify({ device_name: btn.getAttribute('data-unpair') }),
      });
      if (data.ok) devicesLoad();
    });
  });
}

async function devicesLoad() {
  const el = document.getElementById(DEVICES_SECTION_ID);
  if (!el) return;
  const { ok, data } = await devicesJson('/api/devices/status');
  if (!ok) {
    el.innerHTML = `<p class="text-danger">Could not load device status: ${devicesEscape(data.error || 'unknown error')}</p>`;
    return;
  }
  devicesRender(data);
}

document.addEventListener('DOMContentLoaded', devicesLoad);
