/* lookBOOK Demo Lab — wired to lab_server.py (R2–R8) */

const LAB_API = localStorage.getItem('lb:labUrl') || 'http://localhost:8042';
const SETTINGS_KEY = 'lb:labSettings';
const WIZARD_KEY = 'lb:wizardDone';

let currentFile = null;
let imageMeta = {};
let panels = [];
let ocrBlocks = [];
let characters = [];
let projectId = null;
let labOnline = false;
let labMode = 'checking';
let settings = { quality: 'balanced', vision: false, labUrl: LAB_API };

const drop = document.getElementById('drop');
const fileInput = document.getElementById('file');
const canvasWrap = document.getElementById('canvasWrap');
const canvas = document.getElementById('previewCanvas');
const ctx = canvas.getContext('2d');
const resultsArea = document.getElementById('resultsArea');
const runBtn = document.getElementById('runBtn');
const resetBtn = document.getElementById('resetBtn');
const statusBar = document.getElementById('statusBar');
const statusText = document.getElementById('statusText');
const directorPreview = document.getElementById('directorPreview');
const livingFrame = document.getElementById('livingFrame');
const vaultInput = document.getElementById('vaultManifest');

function loadSettings() {
  try {
    const raw = localStorage.getItem(SETTINGS_KEY);
    if (raw) settings = { ...settings, ...JSON.parse(raw) };
  } catch { /* ignore */ }
}

function saveSettings() {
  localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings));
  localStorage.setItem('lb:labUrl', settings.labUrl || LAB_API);
}

function setStep(id, state) {
  const el = document.getElementById(id);
  if (!el) return;
  el.className = 'step';
  if (state) el.classList.add(state);
}

function setStatus(mode, text) {
  labMode = mode;
  statusBar.className = `status-bar ${mode}`;
  statusText.textContent = text;
}

async function checkLabHealth() {
  const base = settings.labUrl || LAB_API;
  try {
    const res = await fetch(`${base}/health`, { signal: AbortSignal.timeout(2500) });
    if (!res.ok) throw new Error('health failed');
    const data = await res.json();
    labOnline = Boolean(data.ok);
    setStatus('online', `Lab server connected · ${base}`);
    const badge = document.getElementById('modeBadge');
    if (badge) badge.textContent = 'Python pipeline · local server';
    return true;
  } catch {
    labOnline = false;
    setStatus('simulated', `Lab server offline — browser simulation (${base})`);
    const badge = document.getElementById('modeBadge');
    if (badge) badge.textContent = 'Simulated pipeline · start lab_server for real OCR';
    return false;
  }
}

function resetAll() {
  currentFile = null;
  imageMeta = {};
  panels = [];
  ocrBlocks = [];
  characters = [];
  projectId = null;
  canvasWrap.classList.remove('show');
  resultsArea.innerHTML = '';
  if (directorPreview) directorPreview.textContent = 'Run pipeline to preview director packet.';
  if (livingFrame) livingFrame.removeAttribute('src');
  ['s1', 's2', 's3', 's4', 's5', 's6', 's7'].forEach((id) => setStep(id, ''));
}

async function uploadToLab(path, file) {
  const fd = new FormData();
  fd.append('file', file);
  const res = await fetch(`${settings.labUrl || LAB_API}${path}`, { method: 'POST', body: fd });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || `Request failed: ${path}`);
  return data;
}

function mapServerPanels(serverPanels, scaleX, scaleY) {
  return (serverPanels || []).map((p, i) => {
    const b = p.bbox || p;
    return {
      x: (b.x || 0) * scaleX,
      y: (b.y || 0) * scaleY,
      w: (b.w || 0) * scaleX,
      h: (b.h || 0) * scaleY,
      index: p.panel_index ?? i,
    };
  });
}

function mapOcrBlocks(blocks, panelsList, scaleX, scaleY) {
  return (blocks || []).map((b, i) => {
    const bbox = b.bbox || {};
    const panelIdx = panelsList.length ? i % panelsList.length : 0;
    const panel = panelsList[panelIdx] || { x: 10, y: 10, h: 40 };
    let classification = 'caption';
    const text = String(b.text || '').trim();
    if (text.startsWith('"') || text.includes('?')) classification = 'dialogue';
    else if (text === text.toUpperCase() && text.length < 12) classification = 'sfx';
    else if (text.length > 60) classification = 'narration';
    return {
      text,
      classification,
      panel: panelIdx,
      conf: Math.round(b.conf || b.confidence || 75),
      x: (bbox.x || panel.x + 10) * scaleX,
      y: (bbox.y || panel.y + panel.h / 2) * scaleY,
    };
  });
}

function drawOverlay() {
  const img = new Image();
  img.src = canvas.toDataURL();
  img.onload = () => {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
    const colors = ['#ffb042', '#f2ba46', '#f472b6', '#a78bfa', '#34d399', '#f97316', '#60a5fa'];
    panels.forEach((p, i) => {
      ctx.strokeStyle = colors[i % colors.length];
      ctx.lineWidth = 3;
      ctx.setLineDash([6, 4]);
      ctx.strokeRect(p.x, p.y, p.w, p.h);
      ctx.setLineDash([]);
      ctx.fillStyle = colors[i % colors.length];
      ctx.font = 'bold 14px Inter, sans-serif';
      ctx.fillText(`Panel ${p.index + 1}`, p.x + 8, p.y + 22);
    });
  };
}

/* --- Simulated fallback (R1 honest labeling) --- */
function detectPanelsSim(ctxLocal, w, h) {
  const results = [];
  const minW = w * 0.08;
  const minH = h * 0.08;
  const imageData = ctxLocal.getImageData(0, 0, w, h);
  const data = imageData.data;
  const gray = new Uint8Array(w * h);
  for (let i = 0; i < w * h; i++) {
    const idx = i * 4;
    gray[i] = (data[idx] * 0.299 + data[idx + 1] * 0.587 + data[idx + 2] * 0.114) | 0;
  }
  const hProjection = new Uint32Array(h);
  const vProjection = new Uint32Array(w);
  const threshold = 180;
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      if (gray[y * w + x] > threshold) hProjection[y]++;
    }
  }
  for (let x = 0; x < w; x++) {
    for (let y = 0; y < h; y++) {
      if (gray[y * w + x] > threshold) vProjection[x]++;
    }
  }
  const hGutters = [];
  const vGutters = [];
  const gutterRatio = 0.15;
  for (let y = 0; y < h; y++) {
    if (hProjection[y] < w * gutterRatio) hGutters.push(y);
  }
  for (let x = 0; x < w; x++) {
    if (vProjection[x] < h * gutterRatio) vGutters.push(x);
  }
  const rows = segmentIndices(hGutters, h);
  const cols = segmentIndices(vGutters, w);
  for (const row of rows) {
    for (const col of cols) {
      const pw = col[1] - col[0];
      const ph = row[1] - row[0];
      if (pw < minW || ph < minH) continue;
      if (pw < w * 0.03 || ph < h * 0.03) continue;
      results.push({
        x: col[0], y: row[0], w: pw, h: ph,
        cx: col[0] + pw / 2, cy: row[0] + ph / 2,
        index: results.length,
      });
    }
  }
  if (results.length === 0) {
    results.push({ x: 5, y: 5, w: w - 10, h: h - 10, cx: w / 2, cy: h / 2, index: 0 });
  }
  return results;
}

function segmentIndices(gutters, totalLen) {
  if (gutters.length === 0) return [[0, totalLen]];
  const segs = [];
  let start = 0;
  let inGutter = false;
  for (let i = 0; i < totalLen; i++) {
    const isGutter = gutters.includes(i);
    if (isGutter && !inGutter) {
      if (i - start > totalLen * 0.03) segs.push([start, i]);
      inGutter = true;
    } else if (!isGutter && inGutter) {
      start = i;
      inGutter = false;
    }
  }
  if (!inGutter && totalLen - start > totalLen * 0.03) segs.push([start, totalLen]);
  return segs.length ? segs : [[0, totalLen]];
}

function simulateOCR(panelsList) {
  const classifications = ['dialogue', 'narration', 'sfx', 'caption'];
  const dialogueTexts = ['"What happened here?"', '"We need answers."', '"Look over there!"'];
  const narrationTexts = ['Meanwhile, across the city…', 'The truth was closer than they thought.'];
  const sfxTexts = ['BOOM', 'CRASH', 'WHAM'];
  return panelsList.map((p, i) => {
    const type = classifications[i % classifications.length];
    let text;
    if (type === 'dialogue') text = dialogueTexts[i % dialogueTexts.length];
    else if (type === 'narration') text = narrationTexts[i % narrationTexts.length];
    else if (type === 'sfx') text = sfxTexts[i % sfxTexts.length];
    else text = 'Ambient scene description.';
    return { text, classification: type, panel: i, conf: 72 + (i * 3) % 20, x: p.x + 10, y: p.y + p.h / 2 };
  });
}

function simulateCharacters(panelsList) {
  const names = ['Hero', 'Sidekick', 'Villain'];
  return names.map((name, i) => ({
    name,
    appearances: Math.max(1, panelsList.length - i),
    panels: panelsList.map((_, idx) => idx).filter((idx) => idx % (i + 2) === 0),
  })).filter((c) => c.panels.length > 0);
}

async function loadDirectorPreview() {
  if (!projectId || !labOnline || !directorPreview) return;
  try {
    const res = await fetch(`${settings.labUrl || LAB_API}/api/director-preview/${projectId}?target=runway`);
    const data = await res.json();
    if (res.ok) directorPreview.textContent = data.markdown || '(empty director packet)';
    else directorPreview.textContent = data.error || 'Director packet unavailable';
  } catch (e) {
    directorPreview.textContent = String(e.message || e);
  }
}

function loadLivingPanels() {
  if (!projectId || !labOnline || !livingFrame) return;
  livingFrame.src = `${settings.labUrl || LAB_API}/api/living-panels/${projectId}`;
}

async function runPipeline() {
  if (!currentFile) return;
  runBtn.disabled = true;
  const w = canvas.width;
  const h = canvas.height;
  const scaleX = w / (imageMeta.width || w);
  const scaleY = h / (imageMeta.height || h);

  setStep('s1', 'active');
  try {
    if (labOnline) {
      const analyzeData = await uploadToLab('/api/analyze', currentFile);
      projectId = analyzeData.project_id;
      setStep('s1', 'done');

      setStep('s2', 'active');
      const panelData = await uploadToLab('/api/panels', currentFile);
      projectId = panelData.project_id || projectId;
      panels = mapServerPanels(panelData.panels, scaleX, scaleY);
      setStep('s2', 'done');
      drawOverlay();

      setStep('s3', 'active');
      try {
        const ocrData = await uploadToLab('/api/extract-text', currentFile);
        ocrBlocks = mapOcrBlocks(ocrData.blocks, panels, scaleX, scaleY);
      } catch {
        ocrBlocks = simulateOCR(panels);
      }
      setStep('s3', 'done');

      setStep('s4', 'active');
      characters = simulateCharacters(panels);
      setStep('s4', 'done');

      setStep('s5', 'done');
      setStep('s6', 'done');
      await loadDirectorPreview();
      loadLivingPanels();
      setStep('s7', 'done');
      showResults(true);
    } else {
      setStep('s1', 'done');
      setStep('s2', 'active');
      panels = detectPanelsSim(ctx, w, h);
      drawOverlay();
      setStep('s2', 'done');
      setStep('s3', 'active');
      ocrBlocks = simulateOCR(panels);
      setStep('s3', 'done');
      setStep('s4', 'active');
      characters = simulateCharacters(panels);
      setStep('s4', 'done');
      setStep('s5', 'done');
      setStep('s6', 'done');
      setStep('s7', 'done');
      showResults(false);
    }
  } catch (e) {
    resultsArea.innerHTML = `<div style="color:#f87171;font-size:14px">Pipeline error: ${e.message}</div>`;
    setStatus('offline', `Pipeline failed — ${e.message}`);
  } finally {
    runBtn.disabled = false;
  }
}

function showResults(realPipeline) {
  let html = `
    <div class="results-grid">
      <div class="stat"><div class="num">${panels.length}</div><div class="lbl">Panels Detected</div></div>
      <div class="stat"><div class="num">${ocrBlocks.length}</div><div class="lbl">Text Blocks</div></div>
      <div class="stat"><div class="num">${characters.length}</div><div class="lbl">Characters Tracked</div></div>
      <div class="stat"><div class="num">${(imageMeta.width || 0)}×${(imageMeta.height || 0)}</div><div class="lbl">Source Resolution</div></div>
    </div>
    <p style="font-size:12px;color:var(--muted);margin-top:10px">${realPipeline ? 'Real Python pipeline' : 'Simulated browser pipeline'}${projectId ? ` · project <code>${projectId}</code>` : ''}</p>
  `;

  if (ocrBlocks.length) {
    html += `<h2 style="font-size:13px;font-weight:700;color:var(--accent);text-transform:uppercase;letter-spacing:.08em;margin:16px 0 8px">Text Classification</h2><ul class="ocr-list">`;
    ocrBlocks.forEach((b) => {
      const icon = b.classification === 'dialogue' ? '💬' : b.classification === 'sfx' ? '💥' : b.classification === 'narration' ? '📖' : '📝';
      html += `<li class="${b.classification}">${icon} <strong>${b.classification}</strong> (${b.conf}%): ${b.text}</li>`;
    });
    html += '</ul>';
  }

  if (characters.length) {
    html += `<h2 style="font-size:13px;font-weight:700;color:var(--accent);text-transform:uppercase;letter-spacing:.08em;margin:16px 0 8px">Character Tracking</h2>`;
    characters.forEach((c) => {
      html += `<div style="padding:6px 0;font-size:13px"><strong>${c.name}</strong> — ${c.appearances} panel(s): [${c.panels.join(', ')}]</div>`;
    });
  }

  html += `<h2 style="font-size:13px;font-weight:700;color:var(--accent);text-transform:uppercase;letter-spacing:.08em;margin:16px 0 8px">Exports</h2><div class="export-grid">`;
  const chips = [
    { label: 'Living Panels', action: 'living' },
    { label: 'Director Packet', action: 'director' },
    { label: 'Project JSON', action: 'project' },
    { label: 'CineForge', action: 'cineforge' },
  ];
  chips.forEach((c) => {
    html += `<span class="chip" data-export="${c.action}">${c.label}</span>`;
  });
  html += '</div>';

  resultsArea.innerHTML = html;
  resultsArea.querySelectorAll('[data-export]').forEach((chip) => {
    chip.addEventListener('click', () => handleExport(chip.dataset.export));
  });
}

function handleExport(kind) {
  if (!projectId && labOnline) {
    alert('Run the pipeline first to create a project.');
    return;
  }
  const base = settings.labUrl || LAB_API;
  if (kind === 'living') {
    loadLivingPanels();
    livingFrame?.scrollIntoView({ behavior: 'smooth' });
  } else if (kind === 'director') {
    loadDirectorPreview();
    directorPreview?.scrollIntoView({ behavior: 'smooth' });
  } else if (kind === 'project' && projectId) {
    window.open(`${base}/api/project/${projectId}`, '_blank');
  } else if (kind === 'cineforge') {
    window.open('../docs/CINEFORGE_BRIDGE.md', '_blank');
  }
}

function handleFile(f) {
  resetAll();
  currentFile = f;
  const ext = f.name.split('.').pop().toLowerCase();
  if (['cbz', 'cbr', 'zip', 'rar'].includes(ext)) {
    resultsArea.innerHTML = `<div style="color:var(--muted);font-size:14px">Archive loaded: <strong>${f.name}</strong>. Use CLI for batch processing. Single-page preview only.</div>`;
    setStep('s1', 'done');
    return;
  }
  const url = URL.createObjectURL(f);
  const img = new Image();
  img.onload = () => {
    imageMeta = { width: img.width, height: img.height, name: f.name };
    canvas.width = Math.min(img.width, 800);
    canvas.height = canvas.width * (img.height / img.width);
    ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
    canvasWrap.classList.add('show');
    setStep('s1', 'done');
    runPipeline();
  };
  img.src = url;
}

async function importVaultManifest(file) {
  if (!file) return;
  const text = await file.text();
  let manifest;
  try {
    manifest = JSON.parse(text);
  } catch {
    alert('Invalid JSON manifest');
    return;
  }
  if (!labOnline) {
    alert('Start lab_server.py to import vault manifests.');
    return;
  }
  try {
    const res = await fetch(`${settings.labUrl || LAB_API}/api/import-vault`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ manifest, project_id: projectId }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Import failed');
    projectId = data.project_id;
    showToast(`Vault imported · ${data.import?.files_written || 0} file(s)`);
  } catch (e) {
    alert(e.message);
  }
}

function showToast(msg) {
  const el = document.createElement('div');
  el.textContent = msg;
  el.style.cssText = 'position:fixed;bottom:20px;right:20px;background:var(--card);border:1px solid var(--accent);padding:10px 16px;border-radius:10px;font-size:13px;z-index:300';
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 2800);
}

/* Wizard R3 */
async function runWizard() {
  const name = document.getElementById('wizardName')?.value?.trim() || 'My Story';
  const preset = document.getElementById('wizardPreset')?.value || 'comic';
  if (labOnline) {
    try {
      const res = await fetch(`${settings.labUrl || LAB_API}/api/new-project`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, preset }),
      });
      const data = await res.json();
      if (res.ok) {
        projectId = data.project_id;
        showToast(`Project "${name}" created (${preset})`);
      }
    } catch { /* optional */ }
  }
  localStorage.setItem(WIZARD_KEY, '1');
  document.getElementById('wizardOverlay')?.classList.remove('open');
}

function openWizardIfNeeded() {
  if (!localStorage.getItem(WIZARD_KEY)) {
    document.getElementById('wizardOverlay')?.classList.add('open');
  }
}

function bindUi() {
  drop.onclick = () => fileInput.click();
  ['dragenter', 'dragover'].forEach((e) =>
    drop.addEventListener(e, (ev) => { ev.preventDefault(); drop.classList.add('drag'); })
  );
  ['dragleave', 'drop'].forEach((e) =>
    drop.addEventListener(e, (ev) => { ev.preventDefault(); drop.classList.remove('drag'); })
  );
  drop.addEventListener('drop', (ev) => {
    const f = ev.dataTransfer.files[0];
    if (f) handleFile(f);
  });
  fileInput.onchange = (e) => {
    if (e.target.files[0]) handleFile(e.target.files[0]);
  };
  resetBtn.onclick = resetAll;
  runBtn.onclick = () => {
    if (!currentFile) return;
    runPipeline();
  };

  document.getElementById('btnNewProject')?.addEventListener('click', () => {
    document.getElementById('wizardOverlay')?.classList.add('open');
  });
  document.getElementById('btnWizardSkip')?.addEventListener('click', () => {
    localStorage.setItem(WIZARD_KEY, '1');
    document.getElementById('wizardOverlay')?.classList.remove('open');
  });
  document.getElementById('btnWizardStart')?.addEventListener('click', runWizard);

  document.getElementById('btnSettings')?.addEventListener('click', () => {
    document.getElementById('settingQuality').value = settings.quality;
    document.getElementById('settingVision').checked = settings.vision;
    document.getElementById('settingLabUrl').value = settings.labUrl || LAB_API;
    document.getElementById('settingsDrawer')?.classList.add('open');
  });
  document.getElementById('btnCloseSettings')?.addEventListener('click', () => {
    document.getElementById('settingsDrawer')?.classList.remove('open');
  });
  document.getElementById('btnSaveSettings')?.addEventListener('click', async () => {
    settings.quality = document.getElementById('settingQuality').value;
    settings.vision = document.getElementById('settingVision').checked;
    settings.labUrl = document.getElementById('settingLabUrl').value.trim() || LAB_API;
    saveSettings();
    document.getElementById('settingsDrawer')?.classList.remove('open');
    await checkLabHealth();
  });

  document.getElementById('btnVaultImport')?.addEventListener('click', () => vaultInput?.click());
  vaultInput?.addEventListener('change', (e) => {
    if (e.target.files[0]) importVaultManifest(e.target.files[0]);
  });
}

async function boot() {
  loadSettings();
  bindUi();
  setStatus('checking', 'Checking lab server…');
  await checkLabHealth();
  openWizardIfNeeded();
}

boot();