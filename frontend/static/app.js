'use strict';

// ── State ──────────────────────────────────────────────────────────────────
const state = {
  resumeMode: 'pdf',       // 'pdf' | 'text'
  selectedFile: null,
  jds: [],
  analysisData: null,
  activeTab: 0,
  loadingStep: 0,
  loadingTimer: null,
};

// ── DOM refs ───────────────────────────────────────────────────────────────
const $ = id => document.getElementById(id);
const $$ = sel => document.querySelectorAll(sel);

// ── Init ───────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  setupToggle();
  setupDropzone();
  setupAccordion();
  setupProviderSwitch();
  setupTabs();
  setupAnalyzeBtn();
});

// ── Resume Input Toggle ────────────────────────────────────────────────────
function setupToggle() {
  $$('.toggle-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      $$('.toggle-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      state.resumeMode = btn.dataset.mode;
      $('dropzone-section').classList.toggle('hidden', state.resumeMode !== 'pdf');
      $('text-section').classList.toggle('hidden', state.resumeMode !== 'text');
    });
  });
}

// ── Drag & Drop ────────────────────────────────────────────────────────────
function setupDropzone() {
  const zone = $('dropzone');
  const fileInput = $('file-input');

  zone.addEventListener('click', () => fileInput.click());
  fileInput.addEventListener('change', e => handleFile(e.target.files[0]));

  zone.addEventListener('dragover', e => {
    e.preventDefault();
    zone.classList.add('dragover');
  });
  zone.addEventListener('dragleave', () => zone.classList.remove('dragover'));
  zone.addEventListener('drop', e => {
    e.preventDefault();
    zone.classList.remove('dragover');
    handleFile(e.dataTransfer.files[0]);
  });
}

function handleFile(file) {
  if (!file) return;
  if (!file.name.toLowerCase().endsWith('.pdf')) {
    showError('Only PDF files are supported.');
    return;
  }
  state.selectedFile = file;
  $('dropzone-text').textContent = `${file.name} (${(file.size / 1024).toFixed(0)} KB)`;
  $('dropzone-text').style.color = 'var(--green)';
}

// ── Multiple JDs Accordion ─────────────────────────────────────────────────
function setupAccordion() {
  $('accordion-header').addEventListener('click', () => {
    const body = $('accordion-body');
    body.classList.toggle('open');
    $('accordion-arrow').classList.toggle('open', body.classList.contains('open'));
  });

  $('add-jd-btn').addEventListener('click', addJdField);
  addJdField();
}

function addJdField() {
  const list = $('jd-list');
  const idx = list.children.length;
  const div = document.createElement('div');
  div.className = 'jd-item';
  div.dataset.idx = idx;
  div.innerHTML = `
    <textarea placeholder="Paste job description #${idx + 1}…" rows="3"></textarea>
    <button class="btn-remove" onclick="removeJd(this)">✕</button>
  `;
  list.appendChild(div);
}

function removeJd(btn) {
  btn.closest('.jd-item').remove();
}

// ── Provider / Model Switch ────────────────────────────────────────────────
const MODELS = {
  openai: ['gpt-4o-mini', 'gpt-4o', 'gpt-4-turbo'],
  groq: ['llama-3.3-70b-versatile', 'llama-3.1-8b-instant', 'mixtral-8x7b-32768'],
};

let activeProvider = 'groq';

function setupProviderSwitch() {
  $$('.provider-pill').forEach(pill => {
    pill.addEventListener('click', () => switchProvider(pill.dataset.provider));
  });
  // Groq is active by default — ensure UI reflects it on load
  switchProvider('groq');
}

function switchProvider(provider) {
  activeProvider = provider;

  // Update pill active states
  $$('.provider-pill').forEach(p => p.classList.toggle('active', p.dataset.provider === provider));

  // Swap model list
  const sel = $('model');
  sel.innerHTML = '';
  MODELS[provider].forEach(m => {
    const opt = document.createElement('option');
    opt.value = m; opt.textContent = m;
    sel.appendChild(opt);
  });

  // Toggle API key field vs pre-configured badge
  const keyField = $('key-field');
  const groqStatus = $('groq-key-status');
  if (provider === 'groq') {
    keyField.style.display = 'none';
    groqStatus.style.display = 'flex';
  } else {
    keyField.style.display = 'flex';
    groqStatus.style.display = 'none';
  }
}

// ── Tabs ───────────────────────────────────────────────────────────────────
function setupTabs() {
  $$('.tab-btn').forEach((btn, i) => {
    btn.addEventListener('click', () => switchTab(i));
  });
}

function switchTab(idx) {
  $$('.tab-btn').forEach((b, i) => b.classList.toggle('active', i === idx));
  $$('.tab-panel').forEach((p, i) => p.classList.toggle('active', i === idx));
  state.activeTab = idx;
}

// ── Analyze ────────────────────────────────────────────────────────────────
function setupAnalyzeBtn() {
  $('analyze-btn').addEventListener('click', runAnalysis);
}

async function runAnalysis() {
  clearError();

  const provider = activeProvider;
  const apiKey = activeProvider === 'openai' ? ($('api-key').value.trim()) : '';
  const jobDesc = $('job-desc').value.trim();
  const targetRole = $('target-role').value.trim();

  // Validate resume
  if (state.resumeMode === 'pdf' && !state.selectedFile) {
    showError('Please upload a resume PDF or switch to text mode.');
    return;
  }
  if (state.resumeMode === 'text' && !$('resume-text-input').value.trim()) {
    showError('Please paste your resume text.');
    return;
  }
  // Only require key for OpenAI
  if (provider === 'openai' && !apiKey) {
    showError('Please enter your OpenAI API key.');
    return;
  }

  // Collect multiple JDs
  const jdItems = [...$$('#jd-list .jd-item textarea')]
    .map(t => t.value.trim()).filter(Boolean);

  // Build form data
  const form = new FormData();
  if (state.resumeMode === 'pdf') {
    form.append('resume_file', state.selectedFile);
  } else {
    form.append('resume_text', $('resume-text-input').value.trim());
  }
  if (jobDesc) form.append('job_description', jobDesc);
  if (jdItems.length) form.append('job_descriptions', JSON.stringify(jdItems));
  if (targetRole) form.append('target_role', targetRole);
  form.append('provider', provider);
  form.append('model', $('model').value);
  if (apiKey) form.append('api_key', apiKey);

  // Show loading
  showLoading();

  try {
    const res = await fetch('/api/analyze', { method: 'POST', body: form });
    const json = await res.json();

    if (!res.ok || !json.success) {
      throw new Error(json.detail || json.message || 'Analysis failed. Check your API key and try again.');
    }

    state.analysisData = json.data;
    renderResults(json.data);
    showResults();
  } catch (err) {
    showForm();
    showError(err.message);
  }
}

// ── Loading pipeline ───────────────────────────────────────────────────────
const PIPELINE_STEPS = [
  { icon: 'file-text',    name: 'Resume Parser',      desc: 'Extracting structured data…' },
  { icon: 'layers',       name: 'Skills Extractor',   desc: 'Classifying your skills…' },
  { icon: 'bar-chart-2',  name: 'ATS Scorer',         desc: 'Matching against job description…' },
  { icon: 'phone-incoming', name: 'Interview Predictor', desc: 'Calculating call probability…' },
  { icon: 'edit-3',       name: 'Resume Rewriter',    desc: 'Crafting stronger bullets…' },
  { icon: 'trending-up',  name: 'Skill Gap Analyzer', desc: 'Identifying learning plan…' },
  { icon: 'mail',         name: 'Cover Letter',       desc: 'Writing tailored letter…' },
];

function showLoading() {
  $('form-section').classList.add('hidden');
  $('results-section').classList.add('hidden');
  $('loading-section').classList.remove('hidden');

  // Render pipeline
  const container = $('pipeline-container');
  container.innerHTML = '';
  PIPELINE_STEPS.forEach((s, i) => {
    if (i > 0) {
      const line = document.createElement('div');
      line.className = 'step-line';
      line.id = `line-${i}`;
      container.appendChild(line);
    }
    const el = document.createElement('div');
    el.className = 'pipeline-step';
    el.id = `step-${i}`;
    el.innerHTML = `
      <div class="step-icon"><i data-lucide="${s.icon}"></i></div>
      <div class="step-info">
        <div class="step-name">${s.name}</div>
        <div class="step-desc">${s.desc}</div>
      </div>
    `;
    container.appendChild(el);
  });

  lucide.createIcons();

  // Animate steps
  state.loadingStep = 0;
  animateStep();
}

function animateStep() {
  const step = $(`step-${state.loadingStep}`);
  if (step) {
    // Mark previous as done
    if (state.loadingStep > 0) {
      $(`step-${state.loadingStep - 1}`)?.classList.replace('active', 'done');
      $(`line-${state.loadingStep}`)?.classList.add('done');
    }
    step.classList.add('active');
  }
  state.loadingStep++;
  if (state.loadingStep <= PIPELINE_STEPS.length) {
    state.loadingTimer = setTimeout(animateStep, 1800);
  }
}

// ── Show/hide sections ─────────────────────────────────────────────────────
function showForm() {
  clearTimeout(state.loadingTimer);
  $('loading-section').classList.add('hidden');
  $('results-section').classList.add('hidden');
  $('form-section').classList.remove('hidden');
  $('analyze-btn').disabled = false;
}

function showResults() {
  clearTimeout(state.loadingTimer);
  $('loading-section').classList.add('hidden');
  $('form-section').classList.add('hidden');
  $('results-section').classList.remove('hidden');
  // Animate rings/bars after a tick
  setTimeout(animateMetrics, 100);
}

// ── Error handling ─────────────────────────────────────────────────────────
function showError(msg) {
  const el = $('error-banner');
  el.classList.add('visible');
  el.querySelector('.error-msg').textContent = msg;
  el.scrollIntoView({ behavior: 'smooth', block: 'center' });
}
function clearError() {
  $('error-banner').classList.remove('visible');
}

// ── Render Results ─────────────────────────────────────────────────────────
function renderResults(data) {
  renderScoreCards(data);
  renderProfileTab(data.profile);
  renderATSTab(data.ats);
  renderInterviewTab(data.interview);
  renderBulletsTab(data.resume_bullets);
  renderSkillGapsTab(data.skill_gaps);
  renderCoverLetterTab(data.cover_letter, data.errors || []);
  renderJobRankingsTab(data.job_rankings);
  switchTab(0);
  lucide.createIcons();
}

// Score color helper
function scoreColor(val) {
  if (val >= 70) return { text: 'color-green', stroke: 'stroke-green' };
  if (val >= 50) return { text: 'color-yellow', stroke: 'stroke-yellow' };
  return { text: 'color-red', stroke: 'stroke-red' };
}

// Score cards
function renderScoreCards(data) {
  const cards = [
    { id: 'card-ats', label: 'ATS SCORE', val: data.ats?.score, title: 'Keyword Match', sub: 'vs job description' },
    { id: 'card-interview', label: 'INTERVIEW ODDS', val: data.interview?.probability, title: 'Call Probability', sub: 'predicted likelihood' },
    { id: 'card-readability', label: 'READABILITY', val: data.ats?.readability_score, title: 'Recruiter Score', sub: 'format & clarity' },
  ];

  cards.forEach(({ id, label, val, title, sub }) => {
    const el = $(id);
    if (!el || val == null) return;
    const c = scoreColor(val);
    el.querySelector('.score-label').textContent = label;
    el.querySelector('.score-title').textContent = title;
    el.querySelector('.score-sub').textContent = sub;
    el.querySelector('.ring-text').textContent = `${Math.round(val)}`;
    el.querySelector('.ring-text').className = `ring-text ${c.text}`;
    const fill = el.querySelector('.ring-fill');
    fill.setAttribute('class', `ring-fill ${c.stroke}`);
    fill.setAttribute('data-val', val);
  });
}

function animateMetrics() {
  // Animate SVG rings
  $$('.ring-fill').forEach(el => {
    const val = parseFloat(el.getAttribute('data-val') || 0);
    const offset = 283 - (283 * val / 100);
    el.style.strokeDashoffset = offset;
  });
  // Animate bars
  $$('[data-pct]').forEach(el => {
    el.style.width = el.dataset.pct + '%';
  });
}

// Profile
function renderProfileTab(profile) {
  if (!profile) return;
  const initials = (profile.name || 'R A').split(' ').map(w => w[0]).slice(0, 2).join('');
  $('profile-initials').textContent = initials;
  $('profile-name').textContent = profile.name || 'Unknown Candidate';
  $('profile-meta').textContent = [profile.email, profile.location, profile.years_of_experience && `${profile.years_of_experience} yrs exp`].filter(Boolean).join(' · ');
  $('profile-summary').textContent = profile.summary || '';

  renderSkillCloud('tech-skills', profile.technical_skills || [], 'tech');
  renderSkillCloud('soft-skills', profile.soft_skills || [], 'soft');
  renderSkillCloud('domain-skills', profile.domain_expertise || [], 'domain');
  $('education-text').textContent = profile.education || '—';
}

function renderSkillCloud(containerId, skills, type) {
  const el = $(containerId);
  if (!el) return;
  el.innerHTML = skills.map(s => `<span class="skill-tag ${type}">${s}</span>`).join('') || '<span class="skill-tag">—</span>';
}

// ATS
function renderATSTab(ats) {
  if (!ats) return;
  const breakdown = ats.breakdown || {};
  const grid = $('ats-breakdown-grid');
  grid.innerHTML = '';

  Object.entries(breakdown).forEach(([key, val]) => {
    const numVal = typeof val === 'number' ? val : parseFloat(val) || 0;
    const pct = Math.min(100, numVal);
    const label = key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
    const c = scoreColor(pct);
    grid.innerHTML += `
      <div class="breakdown-item">
        <div class="breakdown-label">${label}</div>
        <div class="breakdown-bar"><div class="breakdown-fill" data-pct="${pct}"></div></div>
        <div class="breakdown-score ${c.text}">${Math.round(pct)}</div>
      </div>`;
  });

  const keywords = $('missing-keywords');
  keywords.innerHTML = (ats.missing_keywords || []).map(k =>
    `<span class="keyword missing">${k}</span>`).join('') || '<span style="color:var(--green)">None — excellent keyword coverage!</span>';

  $('keyword-density').textContent = ats.keyword_density != null ? `${(ats.keyword_density * 100).toFixed(1)}%` : '—';
}

// Interview
function renderInterviewTab(interview) {
  if (!interview) return;
  const val = interview.probability ?? 0;
  const c = scoreColor(val);
  $('prob-value').textContent = `${Math.round(val)}%`;
  $('prob-value').className = `prob-big ${c.text}`;

  const breakdown = interview.breakdown || {};
  const factors = $('prob-factors');
  factors.innerHTML = '';
  Object.entries(breakdown).forEach(([key, val]) => {
    const numVal = typeof val === 'number' ? val : parseFloat(val) || 0;
    const label = key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
    const fc = scoreColor(numVal);
    factors.innerHTML += `
      <div class="factor-card">
        <div class="factor-top">
          <span class="factor-name">${label}</span>
          <span class="factor-score ${fc.text}">${Math.round(numVal)}</span>
        </div>
        <div class="factor-bar"><div class="factor-fill" data-pct="${Math.min(100, numVal)}"></div></div>
      </div>`;
  });

  $('interview-strengths').innerHTML = (interview.strengths || []).map(s =>
    `<div class="strength-item">${s}</div>`).join('') || '<div style="color:var(--txt-3)">—</div>';
  $('interview-weaknesses').innerHTML = (interview.weaknesses || []).map(w =>
    `<div class="weakness-item">${w}</div>`).join('') || '<div style="color:var(--txt-3)">—</div>';
}

// Bullets
function renderBulletsTab(bullets) {
  const container = $('bullets-container');
  if (!bullets?.length) {
    container.innerHTML = '<p style="color:var(--txt-3)">No bullet rewrites available (requires primary job description).</p>';
    return;
  }
  container.innerHTML = bullets.map((b, i) => `
    <div class="bullet-pair">
      <div class="bullet-original">
        <div class="bullet-label">⚠ Original</div>
        ${escHtml(b.original || '—')}
      </div>
      <div class="bullet-rewritten">
        <div class="bullet-label">✓ Improved</div>
        ${escHtml(b.rewritten || '—')}
      </div>
      ${b.improvement_note ? `<div class="bullet-note">${escHtml(b.improvement_note)}</div>` : ''}
    </div>`).join('');
}

// Skill Gaps
function renderSkillGapsTab(gaps) {
  if (!gaps) return;
  $('critical-gaps').innerHTML = (gaps.critical || []).map(g =>
    `<div class="gap-item critical"><span class="gap-dot critical"></span>${escHtml(g)}</div>`
  ).join('') || '<div style="color:var(--green)">No critical gaps — great match!</div>';

  $('nice-gaps').innerHTML = (gaps.nice_to_have || []).map(g =>
    `<div class="gap-item nice"><span class="gap-dot nice"></span>${escHtml(g)}</div>`
  ).join('') || '<div style="color:var(--green)">None</div>';

  $('learning-list').innerHTML = (gaps.learning_recommendations || []).map(r => `
    <div class="learning-item">
      <div class="learning-skill">${escHtml(r.skill || r.topic || '—')}</div>
      <div class="learning-resource">${escHtml(r.resource || r.recommendation || '')}</div>
      <div class="learning-timeline">${escHtml(r.timeline || r.duration || '')}</div>
    </div>`).join('') || '<div style="color:var(--txt-3)">—</div>';
}

// Cover Letter
function renderCoverLetterTab(letter, errors) {
  const el = $('cover-letter-text');
  if (!letter) {
    const clError = (errors || []).find(e => e.startsWith('cover_letter_generator:'));
    if (clError) {
      el.textContent = `Cover letter generation failed: ${clError.replace('cover_letter_generator: ', '')}`;
    } else {
      el.textContent = 'No cover letter generated (requires primary job description).';
    }
    return;
  }
  el.textContent = letter;

  $('copy-btn').addEventListener('click', async () => {
    await navigator.clipboard.writeText(letter).catch(() => {});
    $('copy-btn').textContent = '✓ Copied!';
    $('copy-btn').classList.add('copied');
    setTimeout(() => {
      $('copy-btn').innerHTML = '<i data-lucide="clipboard"></i> Copy';
      lucide.createIcons();
      $('copy-btn').classList.remove('copied');
    }, 2000);
  });

  $('download-btn').addEventListener('click', () => {
    const blob = new Blob([letter], { type: 'text/plain' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'cover_letter.txt';
    a.click();
  });
}

// Job Rankings
function renderJobRankingsTab(rankings) {
  const container = $('job-rankings-container');
  if (!rankings?.length) {
    container.innerHTML = '<p style="color:var(--txt-3)">No job rankings (provide multiple job descriptions to rank them).</p>';
    return;
  }
  container.innerHTML = rankings.map(job => {
    const score = job.match_score ?? 0;
    const c = scoreColor(score);
    return `
    <div class="job-card">
      <div class="job-rank">#${job.rank || '?'}</div>
      <div class="job-info">
        <div class="job-title">${escHtml(job.title || 'Job ' + job.rank)}</div>
        <div class="job-rec">${escHtml(job.recommendation || '')}</div>
        <div>
          ${(job.matched_skills || []).slice(0, 5).map(s => `<span class="skill-tag tech" style="font-size:0.72rem">${s}</span>`).join(' ')}
        </div>
        <div class="job-score-bar">
          <div class="job-score-label">
            <span>Match Score</span>
            <span class="${c.text}">${Math.round(score)}%</span>
          </div>
          <div class="bar"><div class="bar-fill" data-pct="${Math.min(100, score)}"></div></div>
        </div>
      </div>
    </div>`;
  }).join('');
}

// ── Utils ──────────────────────────────────────────────────────────────────
function escHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// Expose for inline onclick
window.removeJd = removeJd;
window.showForm = showForm;
