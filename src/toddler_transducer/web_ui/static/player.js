(function () {
  let isPlaying = false;
  let isLooping = false;
  let isDragging = false;
  let puckLockout = false;
  let trackList = [];
  let currentTrackName = '';

  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => document.querySelectorAll(sel);

  const els = {
    trackName: $('#trackName'),
    progressFilled: $('#progressFilled'),
    progressWrapper: $('#progressWrapper'),
    timeCurrent: $('#timeCurrent'),
    timeDuration: $('#timeDuration'),
    playBtn: $('#playBtn'),
    playIcon: $('#playIcon'),
    pauseIcon: $('#pauseIcon'),
    prevBtn: $('#prevBtn'),
    nextBtn: $('#nextBtn'),
    loopBtn: $('#loopBtn'),
    puckLockoutBtn: $('#puckLockoutBtn'),
    volumeSlider: $('#volumeSlider'),
    trackListGroup: $('#trackListGroup'),
    trackFilter: $('#trackFilter'),
  };

  function formatTime(secs) {
    if (!secs || secs < 0) return '00:00';
    const m = Math.floor(secs / 60);
    const s = Math.floor(secs % 60);
    return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
  }

  function setPct(pct) {
    els.progressFilled.style.flexBasis = `${pct}%`;
  }

  function updatePlayButton() {
    els.playIcon.style.display = isPlaying ? 'none' : '';
    els.pauseIcon.style.display = isPlaying ? '' : 'none';
  }

  function updateLoopButton() {
    els.loopBtn.classList.toggle('loop-active', isLooping);
  }

  function updatePuckLockoutButton() {
    els.puckLockoutBtn.classList.toggle('puck-locked', puckLockout);
    els.puckLockoutBtn.title = puckLockout ? 'Puck Locked (tap to unlock)' : 'Puck Active (tap to lock)';
  }

  function highlightActiveTrack(name) {
    $$('[data-track]').forEach((el) => {
      el.parentElement.classList.toggle('active-track', el.dataset.track === name);
    });
  }

  // ── API helpers ───────────────────────────────────────

  async function fetchJSON(url, opts = {}) {
    try {
      const res = await fetch(url, opts);
      return res.ok ? res.json() : null;
    } catch {
      return null;
    }
  }

  async function postJSON(url, data) {
    return fetchJSON(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
  }

  // ── Puck Lockout ──────────────────────────────────────

  async function togglePuckLockout() {
    const state = await fetchJSON('/api/puck_lockout');
    const newState = !(state && state.puck_lockout);
    await postJSON('/api/puck_lockout', { puck_lockout: newState });
    puckLockout = newState;
    updatePuckLockoutButton();
  }

  // ── Play a specific track ─────────────────────────────

  async function playTrack(name) {
    await postJSON('/api/play_track', { track_name: name });
    currentTrackName = name;
    highlightActiveTrack(name);
  }

  // ── Next / Previous ───────────────────────────────────

  async function nextTrack() {
    const idx = trackList.indexOf(currentTrackName);
    if (idx < trackList.length - 1) {
      await playTrack(trackList[idx + 1]);
    } else if (trackList.length > 0) {
      await playTrack(trackList[0]);
    }
  }

  async function prevTrack() {
    const idx = trackList.indexOf(currentTrackName);
    if (idx > 0) {
      await playTrack(trackList[idx - 1]);
    } else if (trackList.length > 0) {
      await playTrack(trackList[trackList.length - 1]);
    }
  }

  // ── Poll player state ─────────────────────────────────

  async function pollState() {
    const state = await fetchJSON('/api/player_state');
    if (!state) return;

    isPlaying = state.is_playing;
    isLooping = state.is_looping || false;
    currentTrackName = state.track_name || 'Load Track';

    els.trackName.textContent = currentTrackName;

    const dur = state.track_length || 0;
    const cur = state.track_time || 0;
    els.timeDuration.textContent = formatTime(dur);
    els.timeCurrent.textContent = formatTime(cur);

    if (!isDragging) {
      const pct = dur > 0 ? (cur / dur) * 100 : 0;
      setPct(pct);
    }

    if (state.volume !== undefined) {
      els.volumeSlider.value = state.volume;
    }

    puckLockout = state.puck_lockout || false;

    updatePlayButton();
    updateLoopButton();
    updatePuckLockoutButton();
    highlightActiveTrack(currentTrackName);
  }

  // ── Fetch track list ──────────────────────────────────

  async function deleteTrack(trackName) {
    if (!confirm(`Delete "${trackName}"?`)) return;
    await postJSON('/api/delete_track', { track_name: trackName });
    fetchTrackList();
  }

  async function fetchTrackList() {
    const data = await fetchJSON('/api/tracks');
    if (data && data.tracks) {
      trackList = data.tracks.map((t) => t.track_name);
      els.trackListGroup.innerHTML = data.tracks
        .map((t) => {
          const safeName = t.track_name.replace(/"/g, '&quot;').replace(/</g, '&lt;');
          return `<div class="list-group-item list-group-item-action py-1 d-flex align-items-center" style="cursor:default">
            <button type="button" class="flex-grow-1 text-start bg-transparent border-0 py-1" data-track="${safeName}">${safeName}</button>
            <button type="button" class="btn btn-sm btn-outline-danger border-0 py-0 px-1 delete-track-btn" data-track="${safeName}" title="Delete">✕</button>
          </div>`;
        })
        .join('');
      attachTrackListEvents();
      highlightActiveTrack(currentTrackName);
    }
  }

  // ── Seek via progress bar ─────────────────────────────

  function seekFromEvent(e) {
    const rect = els.progressWrapper.getBoundingClientRect();
    const x = (e.clientX || (e.touches && e.touches[0].clientX)) - rect.left;
    const pct = Math.max(0, Math.min(100, (x / rect.width) * 100));
    setPct(pct);

    const parts = els.timeDuration.textContent.split(':');
    const dur = parseFloat(parts[0]) * 60 + parseFloat(parts[1]);
    const seekTime = (pct / 100) * dur;
    els.timeCurrent.textContent = formatTime(seekTime);
    return { pct, seekTime };
  }

  function commitSeek(e) {
    const clientX = e.clientX !== undefined ? e.clientX : (e.changedTouches && e.changedTouches[0].clientX);
    const rect = els.progressWrapper.getBoundingClientRect();
    const x = clientX - rect.left;
    const pct = Math.max(0, Math.min(100, (x / rect.width) * 100));
    const parts = els.timeDuration.textContent.split(':');
    const dur = parseFloat(parts[0]) * 60 + parseFloat(parts[1]);
    const seekTime = (pct / 100) * dur;
    postJSON('/api/seek', { position: seekTime });
  }

  // ── Volume ────────────────────────────────────────────

  function handleVolumeChange() {
    const vol = parseInt(els.volumeSlider.value, 10);
    postJSON('/api/volume', { volume: vol });
  }

  // ── Track list filtering ──────────────────────────────

  window.filterTrackList = function () {
    const filter = (els.trackFilter.value || '').toUpperCase();
    els.trackListGroup.querySelectorAll('.list-group-item').forEach((el) => {
      el.style.display = el.textContent.toUpperCase().includes(filter) ? '' : 'none';
    });
  };

  // ── Event binding ─────────────────────────────────────

  function attachTrackListEvents() {
    els.trackListGroup.querySelectorAll('[data-track]').forEach((el) => {
      el.addEventListener('click', (e) => {
        e.stopPropagation();
        playTrack(el.dataset.track);
      });
    });
    els.trackListGroup.querySelectorAll('.delete-track-btn').forEach((el) => {
      el.addEventListener('click', (e) => {
        e.stopPropagation();
        deleteTrack(el.dataset.track);
      });
    });
  }
  attachTrackListEvents();

  els.playBtn.addEventListener('click', () => postJSON('/api/toggle_playback'));

  els.prevBtn.addEventListener('click', prevTrack);
  els.nextBtn.addEventListener('click', nextTrack);

  els.loopBtn.addEventListener('click', () => postJSON('/api/toggle_loop'));

  els.puckLockoutBtn.addEventListener('click', togglePuckLockout);

  els.volumeSlider.addEventListener('input', handleVolumeChange);
  els.volumeSlider.addEventListener('change', handleVolumeChange);

  // Progress bar mouse events
  els.progressWrapper.addEventListener('mousedown', (e) => {
    isDragging = true;
    seekFromEvent(e);
  });

  document.addEventListener('mousemove', (e) => {
    if (isDragging) seekFromEvent(e);
  });

  document.addEventListener('mouseup', (e) => {
    if (isDragging) {
      isDragging = false;
      commitSeek(e);
    }
  });

  // Progress bar touch events
  els.progressWrapper.addEventListener('touchstart', (e) => {
    isDragging = true;
    seekFromEvent(e);
    e.preventDefault();
  }, { passive: false });

  document.addEventListener('touchmove', (e) => {
    if (isDragging) {
      seekFromEvent(e);
      e.preventDefault();
    }
  }, { passive: false });

  document.addEventListener('touchend', (e) => {
    if (isDragging) {
      isDragging = false;
      commitSeek(e);
    }
  });

  // ── Disk usage ────────────────────────────────────────

  function formatBytes(bytes) {
    if (bytes === 0) return '0 B';
    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return (bytes / Math.pow(1024, i)).toFixed(1) + ' ' + units[i];
  }

  async function fetchDiskUsage() {
    const data = await fetchJSON('/api/disk_usage');
    if (!data) return;
    const pct = ((data.used / data.total) * 100).toFixed(1);
    document.getElementById('diskUsage').innerHTML =
      `<p><strong>Free:</strong> ${formatBytes(data.free)}</p>
       <p><strong>Used:</strong> ${formatBytes(data.used)} / ${formatBytes(data.total)} (${pct}%)</p>
       <div class="progress" style="height:8px;">
         <div class="progress-bar bg-dark" style="width:${pct}%"></div>
       </div>`;
  }

  // ── Restart Service ────────────────────────────────────

  els.restartBtn = $('#restartBtn');
  if (els.restartBtn) {
    els.restartBtn.addEventListener('click', async () => {
      if (!confirm('Restart the application service? This will interrupt playback.')) return;
      els.restartBtn.disabled = true;
      els.restartBtn.textContent = 'Restarting...';
      await postJSON('/api/restart_service');
    });
  }

  // ── Init ──────────────────────────────────────────────

  fetchTrackList();
  pollState();
  fetchDiskUsage();
  setInterval(pollState, 1000);
  setInterval(fetchTrackList, 10000);
  setInterval(fetchDiskUsage, 30000);
})();
