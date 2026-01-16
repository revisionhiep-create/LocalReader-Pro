
import { state } from './modules/state.js';
import { fetchJSON, API_URL } from './modules/api.js';
import { renderIcons, showToast, switchTab, renderRules, renderIgnoreList, updateEngineStatusUI, highlightSearchTerm, escapeRegex, updateTranslations } from './modules/ui.js';
import { loadLibrary, selectDocument, renderPage, processPdfBlob, getSentencesForPage } from './modules/library.js';
import { loadVoices, togglePlayback, stopPlayback, playNext, jumpToSentence, initAudioContext, saveProgress } from './modules/tts.js';
import { startExport, cancelExport, startFFMPEGDownload, openExportLocation } from './modules/export.js';
import { initTimer } from './modules/timer.js';

// Global access for debugging
window.state = state;

async function init() {
    // 1. Setup PDF.js
    try {
        if (window.pdfjsLib) window.pdfjsLib.GlobalWorkerOptions.workerSrc = 'lib/pdf.worker.min.js';
    } catch (e) { console.error("PDF.js init error", e); }

    // 2. Load Settings
    try {
        const settings = await fetchJSON(`/api/settings`);
        state.rules = settings.pronunciationRules || [];
        state.ignoreList = settings.ignoreList || [];
        state.headerFooterMode = settings.header_footer_mode || 'off';
        state.engineMode = settings.engine_mode || 'gpu';
        state.pauseSettings = settings.pause_settings || state.pauseSettings;
        state.uiLanguage = settings.ui_language || 'en';

        // Apply UI Settings
        const speedRange = document.getElementById('speedRange');
        if (speedRange && settings.speed) {
            speedRange.value = settings.speed;
            const sv = document.getElementById('speedVal');
            if (sv) sv.textContent = parseFloat(settings.speed).toFixed(2);
        }
        const fontSizeSlider = document.getElementById('fontSizeSlider');
        if (fontSizeSlider && settings.font_size) {
            fontSizeSlider.value = settings.font_size;
            const tv = document.getElementById('textSizeVal');
            if (tv) tv.textContent = settings.font_size;
            const preview = document.getElementById('currentSentencePreview');
            if (preview) {
                preview.style.fontSize = `${settings.font_size}px`;
                preview.style.lineHeight = (parseInt(settings.font_size) * 1.5) + 'px';
            }
            // Apply to actual text content
            const textContent = document.getElementById('textContent');
            if (textContent) {
                textContent.style.fontSize = `${settings.font_size}px`;
                textContent.style.lineHeight = (parseInt(settings.font_size) * 1.6) + 'px';
            }
        }
        const headerSelect = document.getElementById('headerFooterMode');
        if (headerSelect) headerSelect.value = state.headerFooterMode;
        const engineSelect = document.getElementById('engineMode');
        if (engineSelect) engineSelect.value = state.engineMode;

        // Pause Settings UI
        ['comma', 'period', 'question', 'exclamation', 'colon', 'semicolon'].forEach(key => {
            const input = document.getElementById(`pause${key.charAt(0).toUpperCase() + key.slice(1)}`);
            const val = document.getElementById(`pause${key.charAt(0).toUpperCase() + key.slice(1)}Val`);
            if (input && val && state.pauseSettings[key] !== undefined) {
                input.value = state.pauseSettings[key];
                val.textContent = state.pauseSettings[key];
            }
        });

        // Language UI Init
        const langToggle = document.getElementById('languageToggle');
        if (langToggle) langToggle.textContent = state.uiLanguage.toUpperCase();
        await updateTranslations(state.uiLanguage);

        // Voice Selection pre-fill
        const voiceSelect = document.getElementById('voiceSelect');
        if (settings.voice_id && voiceSelect) {
            const opt = document.createElement('option');
            opt.value = settings.voice_id;
            opt.textContent = "Loading...";
            voiceSelect.appendChild(opt);
            voiceSelect.value = settings.voice_id;
        }

    } catch (e) {
        console.error("Settings load error", e);
        showToast("Settings failed to load: " + e.message);
    }

    // 3. Load Data & UI
    renderIcons();

    try { await loadVoices(); } catch (e) { console.error(e); }
    try { await loadLibrary(); } catch (e) { console.error(e); }

    renderRules();
    renderIgnoreList();
    startStatusPolling();
    initTimer();
}

document.addEventListener('DOMContentLoaded', init);

// --- Event Listeners ---

// Playback
document.getElementById('playBtn').onclick = togglePlayback;
document.getElementById('stopBtn').onclick = () => {
    stopPlayback();
    // Reset to beginning
    if (state.readingSentences.length > 0) {
        jumpToSentence(0);
    }
};
document.getElementById('skipBack').onclick = () => { 
    if (state.currentSentenceIndex > 0) jumpToSentence(state.currentSentenceIndex - 1); 
};
document.getElementById('skipForward').onclick = async () => {
    if (state.currentSentenceIndex < state.readingSentences.length - 1) {
        jumpToSentence(state.currentSentenceIndex + 1);
    } else if (state.readingPageIndex < state.currentPages.length - 1) {
        state.readingPageIndex++;
        state.readingSentences = await getSentencesForPage(state.readingPageIndex);
        jumpToSentence(0);
    }
};

// Keyboard Shortcuts
window.addEventListener('keydown', (e) => {
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.isContentEditable) return;
    if (e.code === 'Space') { e.preventDefault(); togglePlayback(); }
    else if (e.code === 'ArrowLeft') { e.preventDefault(); document.getElementById('skipBack').click(); }
    else if (e.code === 'ArrowRight') { e.preventDefault(); document.getElementById('skipForward').click(); }
    else if ((e.ctrlKey || e.metaKey) && e.key === 'f' && state.currentDoc) { e.preventDefault(); document.getElementById('searchBtn').click(); }
    else if (e.key === 'Escape') document.getElementById('closeSearchBtn').click();
});

// Page Navigation (Viewing)
document.getElementById('prevPage').onclick = async () => { 
    if (state.viewPageIndex > 0) { 
        state.viewPageIndex--; 
        state.autoScrollEnabled = false; 
        await renderPage(); 
    } 
};
document.getElementById('nextPage').onclick = async () => { 
    if (state.viewPageIndex < state.currentPages.length - 1) { 
        state.viewPageIndex++; 
        state.autoScrollEnabled = false; 
        await renderPage(); 
    } 
};
document.getElementById('pageInput').onchange = async (e) => {
    let v = parseInt(e.target.value) - 1;
    if (v >= 0 && v < state.currentPages.length) { 
        state.viewPageIndex = v; 
        state.autoScrollEnabled = false; 
        await renderPage(); 
    }
};

// Back to Reading Logic
document.getElementById('backToReadingBtn').onclick = async () => {
    state.viewPageIndex = state.readingPageIndex;
    state.autoScrollEnabled = true;
    await renderPage();
    // After render, auto-scroll will center the active sentence
    const active = document.querySelector('.active-sentence');
    if (active) active.scrollIntoView({ behavior: 'smooth', block: 'center' });
};

// Auto-Flip on Scroll
let isAutoFlipping = false;
const scrollContainer = document.querySelector('.content-area');
if (scrollContainer) {
    scrollContainer.addEventListener('wheel', async (e) => {
        if (isAutoFlipping) return;
        const bottom = scrollContainer.scrollTop + scrollContainer.clientHeight >= scrollContainer.scrollHeight - 10;
        const top = scrollContainer.scrollTop <= 10;
        
        // If user is manually scrolling, disable auto-alignment
        if (state.autoScrollEnabled) {
            state.autoScrollEnabled = false;
        }

        if (e.deltaY > 0 && bottom && state.viewPageIndex < state.currentPages.length - 1) {
            isAutoFlipping = true; state.viewPageIndex++;
            await renderPage(); scrollContainer.scrollTop = 0;
            setTimeout(() => { isAutoFlipping = false }, 700);
        } else if (e.deltaY < 0 && top && state.viewPageIndex > 0) {
            isAutoFlipping = true; state.viewPageIndex--;
            await renderPage(); scrollContainer.scrollTop = scrollContainer.scrollHeight;
            setTimeout(() => { isAutoFlipping = false }, 700);
        }
    }, { passive: true });
}

// Upload
document.getElementById('pdfUpload').onchange = async (e) => {
    const file = e.target.files[0];
    if (file) {
        if (file.name.toLowerCase().endsWith('.epub')) {
            showToast("Converting EPUB...");
            const formData = new FormData();
            formData.append('file', file);
            try {
                const res = await fetch('/api/convert/epub', { method: 'POST', body: formData });
                if (!res.ok) throw new Error("Conversion failed");
                const blob = await res.blob();
                processPdfBlob(blob, file.name.replace('.epub', '.pdf'));
            } catch (err) {
                console.error(err);
                showToast("EPUB conversion failed: " + err.message);
            }
        } else {
            processPdfBlob(file, file.name);
        }
        e.target.value = '';
    }
};

// Tabs
document.getElementById('tabLibrary').onclick = () => switchTab(document.getElementById('tabLibrary'), document.getElementById('libraryPanel'));
document.getElementById('tabRules').onclick = () => switchTab(document.getElementById('tabRules'), document.getElementById('rulesPanel'));
document.getElementById('tabIgnore').onclick = () => switchTab(document.getElementById('tabIgnore'), document.getElementById('ignorePanel'));

// Settings
async function saveSettings() {
    try {
        await fetchJSON(`/api/settings`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({
                pronunciationRules: state.rules, ignoreList: state.ignoreList,
                voice_id: document.getElementById('voiceSelect').value,
                speed: parseFloat(document.getElementById('speedRange').value),
                font_size: parseInt(document.getElementById('fontSizeSlider').value),
                header_footer_mode: state.headerFooterMode, engine_mode: state.engineMode,
                pause_settings: state.pauseSettings,
                ui_language: state.uiLanguage
            })
        });
    } catch (e) { console.error(e); }
}

document.getElementById('speedRange').onchange = saveSettings;
document.getElementById('speedRange').oninput = (e) => document.getElementById('speedVal').textContent = parseFloat(e.target.value).toFixed(2);
document.getElementById('fontSizeSlider').onchange = saveSettings;
document.getElementById('fontSizeSlider').oninput = (e) => {
    const newSize = e.target.value;
    document.getElementById('textSizeVal').textContent = newSize;
    
    // Update HUD preview
    const preview = document.getElementById('currentSentencePreview');
    if (preview) { 
        preview.style.fontSize = `${newSize}px`; 
        preview.style.lineHeight = (parseInt(newSize) * 1.5) + 'px'; 
    }
    
    // Update actual text content
    const textContent = document.getElementById('textContent');
    if (textContent) {
        textContent.style.fontSize = `${newSize}px`;
        textContent.style.lineHeight = (parseInt(newSize) * 1.6) + 'px';
    }
};
document.getElementById('voiceSelect').onchange = async () => { 
    stopPlayback(); 
    state.audioBufferCache.clear(); 
    try {
        await fetchJSON('/api/system/clear-cache', { method: 'POST' });
    } catch (e) {
        console.error("Failed to clear backend cache", e);
    }
    await saveSettings(); 
};
document.getElementById('headerFooterMode').onchange = async (e) => { state.headerFooterMode = e.target.value; await saveSettings(); if (state.currentDoc) await renderPage(); };
document.getElementById('engineMode').onchange = async (e) => { state.engineMode = e.target.value; await saveSettings(); };
document.getElementById('setupBtn').onclick = async () => { try { await fetchJSON(`/api/system/setup?model_type=${state.engineMode}`, { method: 'POST' }); showToast("Started downloading..."); } catch (e) { showToast(e.message); } };

// Drawer & Sidebar Resize
const toggleDrawer = (open) => {
    const d = document.getElementById('voiceSettingsDrawer');
    const o = document.getElementById('drawerOverlay');
    if (open) { d.classList.add('open'); o.classList.add('active'); }
    else { d.classList.remove('open'); o.classList.remove('active'); }
};
document.getElementById('voiceSettingsBtn').onclick = () => toggleDrawer(true);
document.getElementById('closeDrawerBtn').onclick = () => toggleDrawer(false);
document.getElementById('drawerOverlay').onclick = () => toggleDrawer(false);

const sidebar = document.querySelector('.sidebar');
const dragHandle = document.getElementById('sidebarDragHandle');
let isResizing = false;
if (dragHandle && sidebar) {
    dragHandle.addEventListener('mousedown', (e) => { isResizing = true; document.body.style.cursor = 'col-resize'; e.preventDefault(); });
    window.addEventListener('mousemove', (e) => {
        if (!isResizing) return;
        const newWidth = e.clientX;
        if (newWidth > 200 && newWidth < 600) sidebar.style.width = `${newWidth}px`;
    });
    window.addEventListener('mouseup', () => { isResizing = false; document.body.style.cursor = ''; });
}

// Language Toggle
document.getElementById('languageToggle').onclick = async () => {
    const langs = ['en', 'es', 'fr', 'zh'];
    let cur = langs.includes(state.uiLanguage) ? state.uiLanguage : 'en';
    const next = langs[(langs.indexOf(cur) + 1) % langs.length];

    state.uiLanguage = next;
    document.getElementById('languageToggle').textContent = next.toUpperCase();

    await updateTranslations(next);
    renderIcons();
    saveSettings();
    loadVoices();
    showToast(`Language set to ${next.toUpperCase()}`);
};

// Search
document.getElementById('searchBtn').onclick = () => { if (!state.currentDoc) { showToast("No document loaded"); return; } document.getElementById('searchModal').classList.remove('hidden'); document.getElementById('searchInput').focus(); };
document.getElementById('closeSearchBtn').onclick = () => document.getElementById('searchModal').classList.add('hidden');

let searchDebounce = null;
document.getElementById('searchInput').oninput = (e) => {
    clearTimeout(searchDebounce);
    searchDebounce = setTimeout(async () => {
        const query = e.target.value.trim();
        const resultsList = document.getElementById('searchResultsList');
        if (!query || query.length < 2) { resultsList.innerHTML = ''; return; }
        try {
            const data = await fetchJSON(`/api/library/search/${state.currentDoc.id}?q=${encodeURIComponent(query)}`);
            resultsList.innerHTML = '';
            if (data.results.length === 0) { document.getElementById('searchEmpty').classList.remove('hidden'); return; }
            document.getElementById('searchEmpty').classList.add('hidden');
            const fragment = document.createDocumentFragment();
            data.results.forEach(result => {
                result.matches.forEach(match => {
                    const div = document.createElement('div');
                    div.className = 'search-result-item';
                    div.innerHTML = `<div class="flex justify-between mb-2"><span class="text-xs font-bold text-blue-400">Page ${result.page_index + 1}</span></div><div class="search-result-snippet">${match.snippet}</div>`;
                    div.onclick = async () => { 
                        state.currentSearchQuery = data.query; 
                        state.viewPageIndex = result.page_index; 
                        state.autoScrollEnabled = false; 
                        document.getElementById('searchModal').classList.add('hidden'); 
                        await renderPage(); 
                        highlightSearchTerm(state.currentSearchQuery); 
                    };
                    fragment.appendChild(div);
                });
            });
            resultsList.appendChild(fragment);
        } catch (e) { }
    }, 300);
};

// Export
document.getElementById('exportBtn').onclick = startExport;
document.getElementById('cancelExportBtn').onclick = cancelExport;
document.getElementById('startFFMPEGDownload').onclick = startFFMPEGDownload;
document.getElementById('cancelFFMPEGBtn').onclick = () => document.getElementById('ffmpegModal').classList.add('hidden');
document.getElementById('openFileLocationBtn').onclick = openExportLocation;

// Rules
document.getElementById('rulesList').addEventListener('input', (e) => {
    if (e.target.dataset.action === 'update-rule') {
        const id = e.target.dataset.id, field = e.target.dataset.field, val = e.target.type === 'checkbox' ? e.target.checked : e.target.value;
        state.rules = state.rules.map(r => r.id === id ? { ...r, [field]: val } : r); saveSettings();
    }
});
document.getElementById('rulesList').addEventListener('click', (e) => {
    const t = e.target.closest('[data-action]'); if (!t) return;
    const action = t.dataset.action, id = t.dataset.id;
    if (action === 'toggle-rule') { state.rules = state.rules.map(r => r.id === id ? { ...r, isExpanded: !r.isExpanded } : r); renderRules(); }
    else if (action === 'delete-rule') { state.rules = state.rules.filter(r => r.id !== id); renderRules(); saveSettings(); }
});
document.getElementById('addRuleBtn').onclick = () => { state.rules.push({ id: crypto.randomUUID(), original: '', replacement: '', match_case: false, word_boundary: true, is_regex: false, isExpanded: true }); renderRules(); saveSettings(); };

// Ignore List
document.getElementById('addIgnoreBtn').onclick = () => { state.ignoreList.push(''); renderIgnoreList(); saveSettings(); };
document.getElementById('ignoreListUI').addEventListener('change', (e) => { if (e.target.dataset.action === 'update-ignore') { state.ignoreList[parseInt(e.target.dataset.index)] = e.target.value; saveSettings(); } });
document.getElementById('ignoreListUI').addEventListener('click', (e) => { const t = e.target.closest('[data-action="delete-ignore"]'); if (t) { state.ignoreList.splice(parseInt(t.dataset.index), 1); renderIgnoreList(); saveSettings(); } });

// Library
document.getElementById('libraryPanel').addEventListener('click', (e) => {
    const st = e.target.closest('[data-action="select-doc"]');
    if (st) { selectDocById(st.dataset.id); return; }
    const dt = e.target.closest('[data-action="delete-doc"]');
    if (dt && confirm("Delete?")) { fetchJSON(`/api/library/${dt.dataset.id}`, { method: 'DELETE' }).then(() => { if (state.currentDoc?.id === dt.dataset.id) location.reload(); else loadLibrary(); }); }
});

window.selectDocById = async (id) => { const items = await fetchJSON(`/api/library`); const item = items.find(i => i.id === id); if (item) selectDocument(item); };

// Pause Settings
['Comma', 'Period', 'Question', 'Exclamation', 'Colon', 'Semicolon'].forEach(k => {
    const el = document.getElementById(`pause${k}`);
    if (el) { el.oninput = (e) => { state.pauseSettings[k.toLowerCase()] = parseInt(e.target.value); document.getElementById(`pause${k}Val`).textContent = e.target.value; }; el.onchange = saveSettings; }
});
document.getElementById('pauseSettingsToggle').onclick = () => { document.getElementById('pauseSettingsContent').classList.toggle('hidden'); };

window.addEventListener('jump-to-sentence', (e) => jumpToSentence(e.detail));

// Status Polling
let lastSysState = null;
async function startStatusPolling() {
    const poll = async () => {
        try {
            const status = await fetchJSON(`/api/system/status?t=${Date.now()}`);
            window.isEngineReady = status.model_loaded;
            const selModel = state.engineMode === 'gpu' ? status.available_models?.gpu : status.available_models?.cpu;
            const curState = `${status.is_downloading}-${status.is_loading}-${status.model_loaded}-${selModel}`;
            if (curState !== lastSysState) {
                lastSysState = curState;
                updateEngineStatusUI(status, selModel);
                if (status.model_loaded) loadVoices();
            }
        } catch (e) { }
        setTimeout(poll, 2000);
    };
    poll();
}
