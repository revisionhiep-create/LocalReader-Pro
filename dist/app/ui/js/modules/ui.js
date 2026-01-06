
import { state } from './state.js';
import { fetchJSON, API_URL } from './api.js';

// --- Icon Management ---
export function renderIcons() {
    // Debounced icon rendering
    if (window.iconRenderTimeout) clearTimeout(window.iconRenderTimeout);
    window.iconRenderTimeout = setTimeout(() => {
        if (window.lucide) window.lucide.createIcons();
    }, 50);
}

// --- Text Helpers ---
export function stripHTML(text) {
    if (!text) return '';
    text = text.replace(/<[^>]*>/g, '');
    text = text.replace(/[\u{1F300}-\u{1F9FF}]|[\u{2600}-\u{26FF}]|[\u{2700}-\u{27BF}]|[\u{1F000}-\u{1F02F}]|[\u{1F0A0}-\u{1F0FF}]/gu, '');
    return text.trim();
}

// --- Toast ---
export function showToast(msg) {
    const toast = document.getElementById('toast');
    const toastMsg = document.getElementById('toastMsg');
    if (toast && toastMsg) {
        toastMsg.textContent = msg;
        toast.classList.remove('hidden');
        setTimeout(() => toast.classList.add('hidden'), 5000);
    }
}

// --- Tabs ---
export function switchTab(activeTab, activePanel) {
    const tabs = [document.getElementById('tabLibrary'), document.getElementById('tabRules'), document.getElementById('tabIgnore')];
    const panels = [document.getElementById('libraryPanel'), document.getElementById('rulesPanel'), document.getElementById('ignorePanel')];
    const activeClass = "flex-1 py-3 flex items-center justify-center gap-1.5 text-[10px] font-bold uppercase tracking-widest border-b-2 border-blue-600 text-blue-500 bg-white/5";
    const inactiveClass = "flex-1 py-3 flex items-center justify-center gap-1.5 text-[10px] font-bold uppercase tracking-widest border-b-2 border-transparent text-zinc-500 hover:text-zinc-300";

    tabs.forEach(tab => {
        if (tab) tab.className = tab === activeTab ? activeClass : inactiveClass;
    });
    panels.forEach(panel => {
        if (panel) panel.classList.toggle('hidden', panel !== activePanel);
    });
    renderIcons();
}

// --- Rules Rendering ---
export function renderRules() {
    const rulesList = document.getElementById('rulesList');
    if (!rulesList) return;

    const fragment = document.createDocumentFragment();
    state.rules.forEach(r => {
        const isExpanded = r.isExpanded || false;
        const div = document.createElement('div');
        div.className = `rule-item bg-zinc-900/80 rounded-xl border border-zinc-800 ${isExpanded ? 'rule-expanded' : ''}`;

        const hasOriginal = r.original && r.original.trim();
        const hasReplacement = r.replacement && r.replacement.trim();
        const isEmpty = !hasOriginal && !hasReplacement;

        const escapeHtml = (text) => {
            const d = document.createElement('div');
            d.textContent = text;
            return d.innerHTML;
        };

        const originalText = hasOriginal ? escapeHtml(r.original) : '<span class="rule-empty">(Empty)</span>';
        const replacementText = hasReplacement ? escapeHtml(r.replacement) : '<span class="rule-empty">(Empty)</span>';

        div.innerHTML = `
            <div class="rule-collapsed p-3 flex items-center" data-action="toggle-rule" data-id="${r.id}">
                ${isEmpty ?
                '<div class="flex-1"><span class="text-xs rule-empty">Empty rule - click to edit</span></div>' :
                `<div class="rule-original text-xs">${originalText}</div>
                     <div class="rule-arrow"><i data-lucide="arrow-right" class="w-3 h-3"></i></div>
                     <div class="rule-replacement text-xs">${replacementText}</div>`
            }
                <div class="rule-meta">
                    ${r.match_case ? '<span class="rule-badge bg-blue-600/20 text-blue-400">Case</span>' : ''}
                    ${r.word_boundary ? '<span class="rule-badge bg-green-600/20 text-green-400">Word</span>' : ''}
                    ${r.is_regex ? '<span class="rule-badge bg-purple-600/20 text-purple-400">Regex</span>' : ''}
                    <i data-lucide="${isExpanded ? 'chevron-up' : 'chevron-down'}" class="w-4 h-4 text-zinc-500 ml-2"></i>
                </div>
            </div>
            <div class="rule-content ${isExpanded ? 'expanded' : ''}">
                <div class="px-3 pb-3 space-y-3">
                    <div class="h-px bg-zinc-800"></div>
                    <div class="grid grid-cols-1 gap-2">
                        <input type="text" placeholder="Original Text" value="${r.original}" class="bg-black text-xs p-2.5 border border-zinc-800 rounded-md text-zinc-300 placeholder-zinc-600" data-action="update-rule" data-field="original" data-id="${r.id}">
                        <input type="text" placeholder="Replacement Text" value="${r.replacement}" class="bg-black text-xs p-2.5 border border-zinc-800 rounded-md text-zinc-300 placeholder-zinc-600" data-action="update-rule" data-field="replacement" data-id="${r.id}">
                    </div>
                    <div class="space-y-2">
                        <label class="flex items-center gap-2 text-xs text-zinc-400 cursor-pointer hover:text-zinc-300">
                            <input type="checkbox" ${r.match_case ? 'checked' : ''} data-action="update-rule" data-field="match_case" data-id="${r.id}" class="w-3.5 h-3.5 rounded border-zinc-700 bg-zinc-800 text-blue-600 focus:ring-blue-600 focus:ring-offset-0">
                            <span>Match Case</span>
                        </label>
                        <label class="flex items-center gap-2 text-xs text-zinc-400 cursor-pointer hover:text-zinc-300">
                            <input type="checkbox" ${r.word_boundary ? 'checked' : ''} data-action="update-rule" data-field="word_boundary" data-id="${r.id}" class="w-3.5 h-3.5 rounded border-zinc-700 bg-zinc-800 text-blue-600 focus:ring-blue-600 focus:ring-offset-0">
                            <span>Whole Word</span>
                        </label>
                        <label class="flex items-center gap-2 text-xs text-zinc-400 cursor-pointer hover:text-zinc-300">
                            <input type="checkbox" ${r.is_regex ? 'checked' : ''} data-action="update-rule" data-field="is_regex" data-id="${r.id}" class="w-3.5 h-3.5 rounded border-zinc-700 bg-zinc-800 text-blue-600 focus:ring-blue-600 focus:ring-offset-0">
                            <span>Use Pattern Matching</span>
                        </label>
                    </div>
                    <div class="flex justify-between items-center pt-2">
                        <button data-action="toggle-rule" data-id="${r.id}" class="text-xs text-zinc-500 hover:text-zinc-300 flex items-center gap-1">
                            <i data-lucide="check" class="w-3 h-3"></i>
                            <span>Done</span>
                        </button>
                        <button data-action="delete-rule" data-id="${r.id}" class="text-zinc-600 hover:text-red-500 p-1.5">
                            <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
                        </button>
                    </div>
                </div>
            </div>
        `;
        fragment.appendChild(div);
    });
    rulesList.innerHTML = '';
    rulesList.appendChild(fragment);
    renderIcons();

    // Attach event listeners for the newly created elements
    // Note: We use global delegation in app.js for better performance, 
    // but the inputs need 'change' events. 
    // We'll rely on app.js to handle these via delegation on #rulesList
}

// --- Ignore List Rendering ---
export function renderIgnoreList() {
    const ignoreListUI = document.getElementById('ignoreListUI');
    if (!ignoreListUI) return;

    const fragment = document.createDocumentFragment();
    state.ignoreList.forEach((item, i) => {
        const div = document.createElement('div');
        div.className = 'flex items-center gap-2 bg-zinc-900/80 p-2 rounded-lg border border-zinc-800';
        div.innerHTML = `<input type="text" value="${item}" class="flex-1 bg-black text-[10px] p-1.5 border border-zinc-800 rounded outline-none text-zinc-300" data-action="update-ignore" data-index="${i}">
                         <button data-action="delete-ignore" data-index="${i}" class="text-zinc-600 hover:text-red-500 p-1"><i data-lucide="x" class="w-3.5 h-3.5"></i></button>`;
        fragment.appendChild(div);
    });
    ignoreListUI.innerHTML = '';
    ignoreListUI.appendChild(fragment);
    renderIcons();
}

// --- Search ---
export function escapeRegex(str) {
    return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

export function highlightSearchTerm(query) {
    const textContent = document.getElementById('textContent');
    if (!query || !textContent) return;

    const textElements = textContent.querySelectorAll('.sentence');
    const escapedQuery = escapeRegex(query);
    const regex = new RegExp(`(${escapedQuery})`, 'gi');

    textElements.forEach(el => {
        highlightTextNodes(el, regex);
    });
}

function highlightTextNodes(node, regex) {
    const walker = document.createTreeWalker(node, NodeFilter.SHOW_TEXT, null, false);
    const textNodes = [];
    let currentNode;
    while (currentNode = walker.nextNode()) {
        if (regex.test(currentNode.textContent)) textNodes.push(currentNode);
    }
    textNodes.forEach(textNode => {
        const text = textNode.textContent;
        const parent = textNode.parentNode;
        if (parent.classList && parent.classList.contains('search-highlight')) return;

        const fragment = document.createDocumentFragment();
        let lastIndex = 0;
        let match;
        regex.lastIndex = 0;
        while ((match = regex.exec(text)) !== null) {
            if (match.index > lastIndex) fragment.appendChild(document.createTextNode(text.slice(lastIndex, match.index)));
            const highlight = document.createElement('span');
            highlight.className = 'search-highlight';
            highlight.textContent = match[0];
            fragment.appendChild(highlight);
            lastIndex = match.index + match[0].length;
        }
        if (lastIndex < text.length) fragment.appendChild(document.createTextNode(text.slice(lastIndex)));
        parent.replaceChild(fragment, textNode);
    });
}

// --- Setup/Status ---
// --- Translations ---
export async function updateTranslations(lang) {
    try {
        const translations = await fetchJSON(`/api/locale/${lang}`);
        state.translations = translations; // Store in global state
        document.querySelectorAll('[data-i18n]').forEach(el => {
            const key = el.dataset.i18n;
            const keys = key.split('.');
            let val = translations;
            for (const k of keys) {
                val = val ? val[k] : null;
            }
            if (val) el.textContent = val;
        });
        document.querySelectorAll('[data-i18n-title]').forEach(el => {
            const key = el.dataset.i18nTitle;
            const keys = key.split('.');
            let val = translations;
            for (const k of keys) {
                val = val ? val[k] : null;
            }
            if (val) el.title = val;
        });
    } catch (e) { console.error("Translation error", e); }
}

export function updateEngineStatusUI(status, selectedModelExists) {
    const engineStatusDot = document.getElementById('engineStatusDot');
    const setupArea = document.getElementById('setupArea');
    const uploadArea = document.getElementById('uploadArea');
    const setupBtn = document.getElementById('setupBtn');
    const exportArea = document.getElementById('exportArea');
    const textSizeArea = document.getElementById('textSizeArea');

    // Update model status text (GPU/CPU)
    const gpuStatusEl = document.getElementById('gpuStatus');
    const cpuStatusEl = document.getElementById('cpuStatus');

    if (gpuStatusEl) {
        const isGpuReady = status.available_models?.gpu;
        gpuStatusEl.innerHTML = `GPU: <span class="${isGpuReady ? 'text-green-400' : 'text-zinc-600'}">${isGpuReady ? '✓' : '✗'}</span>`;
    }

    if (cpuStatusEl) {
        const isCpuReady = status.available_models?.cpu;
        cpuStatusEl.innerHTML = `CPU: <span class="${isCpuReady ? 'text-green-400' : 'text-zinc-600'}">${isCpuReady ? '✓' : '✗'}</span>`;
    }

    if (status.is_downloading) {
        engineStatusDot.className = "w-2.5 h-2.5 rounded-full bg-blue-500 animate-pulse";
        if (setupArea) setupArea.style.display = 'block';
        if (uploadArea) uploadArea.style.display = 'none';
        if (setupBtn) {
            setupBtn.disabled = true;
            setupBtn.innerHTML = '<i data-lucide="loader-2" class="w-4 h-4 animate-spin"></i><span class="text-sm font-bold">Downloading...</span>';
        }
        renderIcons();
    } else if (status.is_loading) {
        engineStatusDot.className = "w-2.5 h-2.5 rounded-full bg-yellow-500 animate-pulse";
        if (setupArea) setupArea.style.display = 'none';
        if (uploadArea) uploadArea.style.display = 'block';
    } else if (status.model_loaded && selectedModelExists) {
        engineStatusDot.className = "w-2.5 h-2.5 rounded-full bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.6)]";
        if (setupArea) setupArea.style.display = 'none';
        if (uploadArea) uploadArea.style.display = 'block';
        if (state.currentDoc) {
            if (exportArea) exportArea.style.display = 'block';
            if (textSizeArea) textSizeArea.style.display = 'block';
        }
    } else {
        engineStatusDot.className = "w-2.5 h-2.5 rounded-full bg-red-600";
        if (setupArea) setupArea.style.display = 'block';
        if (uploadArea) uploadArea.style.display = 'none';
        if (setupBtn) {
            setupBtn.disabled = false;
            setupBtn.innerHTML = '<i data-lucide="download-cloud" class="w-4 h-4"></i><span class="text-sm font-bold">Setup Voice Engine</span>';
            // Start polling to detect when download finishes if initiated externally or previously
        }
        renderIcons();
    }
}
