const modelSelect = document.getElementById('modelSelect');
const sceneDuration = document.getElementById('sceneDuration');
const sceneDurationValue = document.getElementById('sceneDurationValue');
const totalDurationInput = document.getElementById('totalDurationInput');
const durationSecondsLabel = document.getElementById('durationSecondsLabel');
const scriptInput = document.getElementById('scriptInput');
const generateBtn = document.getElementById('generateBtn');
const terminalLog = document.getElementById('terminalLog');
const progressFill = document.getElementById('progressFill');
const progressText = document.getElementById('progressText');
const timelineList = document.getElementById('timelineList');
const downloadBtn = document.getElementById('downloadBtn');
const videoPreview = document.getElementById('videoPreview');

let compiledUrl = '';

function appendLog(message, tone = 'info') {
  const line = document.createElement('div');
  line.className = `log-line ${tone}`;
  line.textContent = message;
  terminalLog.appendChild(line);
  terminalLog.scrollTop = terminalLog.scrollHeight;
}

function updateProgress(value) {
  const pct = Math.max(0, Math.min(100, Number(value) || 0));
  progressFill.style.width = pct + '%';
  progressText.textContent = Math.round(pct) + '%';
}

function parseTargetMinutes(value) {
  const raw = Number(String(value).replace(/[^\d.]/g, '')) || 120;
  return Math.max(1, raw);
}

function syncDurationMeta() {
  const seconds = Number(sceneDuration.value);
  sceneDurationValue.textContent = seconds + 's';
  const minutes = parseTargetMinutes(totalDurationInput.value);
  totalDurationInput.value = minutes;
  durationSecondsLabel.textContent = (minutes * 60) + ' seconds';
}

function splitTextIntoChunks(text, approximateWordsPerChunk) {
  const words = text.split(/\s+/).filter(Boolean);
  const chunks = [];
  for (let i = 0; i < words.length; i += approximateWordsPerChunk) {
    const part = words.slice(i, i + approximateWordsPerChunk).join(' ');
    if (part) chunks.push(part);
  }
  return chunks;
}

function parseScriptIntoScenes(scriptText, sceneSeconds) {
  const blocks = scriptText
    .split(/\n{2,}|\.\s+|\?\s+|!\s+/)
    .map((segment) => segment.replace(/\s+/g, ' ').trim())
    .filter(Boolean);

  if (!blocks.length) {
    return [{ title: 'Scene 1', text: 'Ambient cinematic intro sequence.', duration: sceneSeconds }];
  }

  const scenes = [];
  let working = '';
  let currentLength = 0;

  for (const block of blocks) {
    const blockWords = block.split(/\s+/).length;
    const estimatedDuration = Math.max(4, Math.min(sceneSeconds, Math.ceil(blockWords / 16)));
    if (working && currentLength + estimatedDuration > sceneSeconds * 1.5) {
      scenes.push({ title: 'Scene ' + (scenes.length + 1), text: working.trim(), duration: currentLength || sceneSeconds });
      working = block;
      currentLength = estimatedDuration;
    } else {
      working = working ? working + ' ' + block : block;
      currentLength += estimatedDuration;
    }
  }

  if (working) {
    scenes.push({ title: 'Scene ' + (scenes.length + 1), text: working.trim(), duration: currentLength || sceneSeconds });
  }

  const normalized = [];
  for (const scene of scenes) {
    const phraseChunks = splitTextIntoChunks(scene.text, Math.max(18, Math.ceil(sceneSeconds * 2.3)));
    if (phraseChunks.length > 1) {
      for (let i = 0; i < phraseChunks.length; i++) {
        normalized.push({ title: 'Scene ' + (normalized.length + 1), text: phraseChunks[i], duration: sceneSeconds });
      }
    } else {
      normalized.push({ title: 'Scene ' + (normalized.length + 1), text: scene.text, duration: Math.max(sceneSeconds, scene.duration) });
    }
  }

  return normalized;
}

function renderTimeline(scenes) {
  timelineList.innerHTML = '';
  scenes.forEach((scene, index) => {
    const item = document.createElement('div');
    item.className = 'scene-chip';

    const idx = document.createElement('div');
    idx.className = 'scene-idx';
    idx.textContent = index + 1;

    const copy = document.createElement('div');
    copy.className = 'scene-copy';
    const title = document.createElement('strong');
    title.textContent = scene.title;
    const text = document.createElement('p');
    text.textContent = scene.text;
    copy.appendChild(title);
    copy.appendChild(text);

    const duration = document.createElement('div');
    duration.className = 'scene-duration';
    duration.textContent = scene.duration + 's';

    item.appendChild(idx);
    item.appendChild(copy);
    item.appendChild(duration);
    timelineList.appendChild(item);
  });
}

async function fetchModels() {
  try {
    const response = await fetch('/api/models');
    const data = await response.json();
    const options = data.models || [];
    modelSelect.innerHTML = '';
    options.forEach((model) => {
      const option = document.createElement('option');
      option.value = model.id;
      option.textContent = model.name;
      modelSelect.appendChild(option);
    });
  } catch (error) {
    appendLog('[ERROR] Could not load model catalog: ' + error.message, 'error');
  }
}

async function generateJob() {
  const prompt = scriptInput.value.trim() || 'A cinematic local render of a futuristic city awakening at dawn.';
  const modelId = modelSelect.value || 'custom-ffmpeg';
  const sceneSeconds = Number(sceneDuration.value) || 18;
  const totalMinutes = parseTargetMinutes(totalDurationInput.value);

  appendLog('[BOOT] Local AI session initialized: ' + modelSelect.options[modelSelect.selectedIndex]?.text || modelId, 'info');
  appendLog('[CORE] Parsing script narrative into sequential scene blocks...', 'info');
  updateProgress(12);

  const scenes = parseScriptIntoScenes(prompt, sceneSeconds);
  renderTimeline(scenes);
  updateProgress(36);

  try {
    const response = await fetch('/api/jobs', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        prompt,
        model_id: modelId,
        scene_duration: sceneSeconds,
        total_duration: totalMinutes,
        script_text: prompt
      })
    });

    const result = await response.json();
    console.log('Job result:', result);

    if (result.status === 'success' || result.download_url || result.status === 'completed') {
      updateProgress(100);
      appendLog('[SUCCESS] Rendering pipeline completed.', 'ok');
      if (result.download_url) {
        compiledUrl = result.download_url;
        videoPreview.src = compiledUrl;
        videoPreview.play().catch(() => {});
        appendLog('[READY] Compiled file is available for direct browser playback and download.', 'ok');
      }
    } else {
      appendLog('[WARN] ' + (result.message || 'Model is waiting for a local installation.'), 'warn');
      appendLog('[INFO] For real generation, install the selected model weights locally and rerun the job.', 'info');
      updateProgress(100);
    }
  } catch (error) {
    appendLog('[ERROR] Generation call failed: ' + error.message, 'error');
    updateProgress(0);
  }
}

function setDefaultProgress() {
  updateProgress(0);
  appendLog('[READY] Studio online. Paste or type a narrative script to begin chunk generation.', 'ok');
}

sceneDuration.addEventListener('input', syncDurationMeta);
totalDurationInput.addEventListener('input', () => {
  const clean = String(totalDurationInput.value).replace(/[^\d.]/g, '');
  totalDurationInput.value = clean || '120';
  syncDurationMeta();
});

generateBtn.addEventListener('click', async () => {
  terminalLog.innerHTML = '';
  timelineList.innerHTML = '';
  compiledUrl = '';
  videoPreview.removeAttribute('src');
  videoPreview.load();
  setDefaultProgress();
  await generateJob();
});

downloadBtn.addEventListener('click', () => {
  if (!compiledUrl) {
    appendLog('[WARN] No compiled preview exists yet. Generate a timeline first.', 'warn');
    return;
  }

  const link = document.createElement('a');
  link.href = compiledUrl;
  link.download = 'local_video_studio_output.mp4';
  document.body.appendChild(link);
  link.click();
  link.remove();
  appendLog('[DOWNLOAD] Compiled video file initiated for local browser download.', 'ok');
});

syncDurationMeta();
setDefaultProgress();
fetchModels();

