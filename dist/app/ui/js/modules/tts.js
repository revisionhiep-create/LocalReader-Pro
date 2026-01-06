
import { state } from './state.js';
import { fetchJSON, fetchBlob, API_URL } from './api.js';
import { showToast, stripHTML, renderIcons } from './ui.js';
import { renderPage } from './library.js';

export function initAudioContext() {
    if (!state.audioContext) {
        state.audioContext = new (window.AudioContext || window.webkitAudioContext)();
        console.log('[WebAudio] AudioContext initialized');
    }
    if (state.audioContext.state === 'suspended') {
        state.audioContext.resume();
    }
}

export function playAudioBuffer(audioBuffer) {
    if (state.currentAudioSource) {
        try {
            state.currentAudioSource.stop();
            state.currentAudioSource.disconnect();
        } catch (e) { }
    }

    // Create new source node
    const source = state.audioContext.createBufferSource();
    source.buffer = audioBuffer;
    source.connect(state.audioContext.destination);

    source.onended = () => {
        state.currentAudioSource = null;
        state.currentSentenceIndex++;
        console.log(`Sentence ended, moving to ${state.currentSentenceIndex}`);
        playNext();
        preCacheNextSentences();
    };

    state.currentAudioSource = source;
    source.start(0);
    console.log(`[WebAudio] Playing buffer: ${audioBuffer.duration.toFixed(2)}s`);
}

export function stopPlayback() {
    state.isPlaying = false;
    // Update UI directly for speed
    const playIcon = document.getElementById('playIcon');
    if (playIcon) {
        playIcon.setAttribute('data-lucide', 'play');
        renderIcons();
    }

    if (state.currentAudioSource) {
        try {
            state.currentAudioSource.stop();
            state.currentAudioSource.disconnect();
        } catch (e) { }
        state.currentAudioSource = null;
    }
}

export async function playNext() {
    if (!state.isPlaying || !window.isEngineReady) { // isEngineReady is global/window for now
        stopPlayback();
        return;
    }

    const text = state.sentences[state.currentSentenceIndex];
    if (!text || typeof text !== 'string') {
        if (state.currentPageIndex < state.currentPages.length - 1) {
            state.currentPageIndex++;
            state.currentSentenceIndex = 0;
            await renderPage();
            playNext();
        } else {
            stopPlayback();
        }
        return;
    }

    // Update UI Highlight
    state.sentenceElements.forEach((el, i) => el.className = `sentence ${i === state.currentSentenceIndex ? 'active-sentence' : ''}`);
    const active = state.sentenceElements[state.currentSentenceIndex];
    if (active) active.scrollIntoView({ behavior: 'smooth', block: 'center' });

    const currentSentencePreview = document.getElementById('currentSentencePreview');
    if (currentSentencePreview) currentSentencePreview.textContent = stripHTML(text);

    saveProgress();

    const cleanText = stripHTML(text);
    console.log(`Synthesizing sentence ${state.currentSentenceIndex}: "${cleanText.substring(0, 30)}..."`);

    const voiceSelect = document.getElementById('voiceSelect');
    const speedRange = document.getElementById('speedRange');

    const lookupKey = `${state.currentPageIndex}_${state.currentSentenceIndex}_${voiceSelect.value}_${speedRange.value}`;

    if (state.audioBufferCache.has(lookupKey)) {
        console.log(`[WebAudio] CACHE HIT - Playing cached buffer instantly`);
        playAudioBuffer(state.audioBufferCache.get(lookupKey));
        return;
    }

    try {
        const res = await fetch(`${API_URL}/api/synthesize`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                text: cleanText,
                voice: voiceSelect.value,
                speed: parseFloat(speedRange.value),
                rules: state.rules,
                ignore_list: state.ignoreList,
                pause_settings: state.pauseSettings
            })
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || "Synthesis failed");
        }

        const blob = await res.blob();
        initAudioContext();

        const arrayBuffer = await blob.arrayBuffer();
        const audioBuffer = await state.audioContext.decodeAudioData(arrayBuffer);

        state.audioBufferCache.set(lookupKey, audioBuffer);

        if (state.audioBufferCache.size > state.MAX_AUDIO_CACHE) {
            const firstKey = state.audioBufferCache.keys().next().value;
            state.audioBufferCache.delete(firstKey);
        }

        playAudioBuffer(audioBuffer);

    } catch (e) {
        console.error("Synthesis error:", e);
        showToast(e.message);
        stopPlayback();
    }
}

export function togglePlayback() {
    const playIcon = document.getElementById('playIcon');
    if (state.isPlaying) {
        stopPlayback();
    } else {
        initAudioContext();
        state.isPlaying = true;
        if (playIcon) {
            playIcon.setAttribute('data-lucide', 'pause');
            renderIcons();
        }
        playNext();
    }
}

export async function jumpToSentence(i) {
    if (state.currentAudioSource) {
        try {
            state.currentAudioSource.stop();
            state.currentAudioSource.disconnect();
        } catch (e) { }
        state.currentAudioSource = null;
    }

    state.currentSentenceIndex = i;
    await renderPage();

    if (!state.isPlaying) {
        initAudioContext();
        state.isPlaying = true;
        const playIcon = document.getElementById('playIcon');
        if (playIcon) {
            playIcon.setAttribute('data-lucide', 'pause');
            renderIcons();
        }
    }
    playNext();
}

export async function saveProgress() {
    if (state.currentDoc) {
        // Optimistic UI
        const statusEl = document.getElementById('bookmarkStatus');
        if (statusEl) {
            statusEl.classList.remove('opacity-0');
            statusEl.classList.add('animate-pulse');
            setTimeout(() => {
                statusEl.classList.remove('animate-pulse');
                // Optional: Fade out after 2s if desired, or keep it visible as "Last saved..."
            }, 1000);
        }

        try {
            await fetchJSON(`/api/library`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    ...state.currentDoc,
                    currentPage: state.currentPageIndex,
                    lastSentenceIndex: state.currentSentenceIndex,
                    lastAccessed: Date.now()
                })
            });
        } catch (e) { console.error("Save progress failed", e); }
    }
}

export async function preCacheNextSentences() {
    const sentencesToPreCache = 2;
    if (!state.audioContext) return;

    const voiceSelect = document.getElementById('voiceSelect');
    const speedRange = document.getElementById('speedRange');

    for (let i = 1; i <= sentencesToPreCache; i++) {
        let targetPageIndex = state.currentPageIndex;
        let targetSentenceIndex = state.currentSentenceIndex + i;
        let targetSentences = state.sentences;

        if (targetSentenceIndex >= state.sentences.length) {
            if (state.currentPageIndex < state.currentPages.length - 1) {
                targetPageIndex = state.currentPageIndex + 1;
                targetSentenceIndex = 0;
                try {
                    const nextPageText = state.currentPages[targetPageIndex];
                    if (!nextPageText) continue;
                    // Simplified parsing for pre-cache (reuse logic ideally, but just quick splitting here)
                    const rawSentences = nextPageText.match(/[^.!?]+[.!?]+[\"\'\u201c\u2018\u201d\u2019]*(?:\s|$)|[^.!?]+$/g) || [nextPageText];
                    targetSentences = rawSentences.map(s => s.trim()).filter(s => s);
                    if (targetSentences.length === 0) continue;
                } catch (err) { continue; }
            } else { break; }
        }

        const nextText = targetSentences[targetSentenceIndex];
        if (!nextText || typeof nextText !== 'string') continue;

        const cleanText = stripHTML(nextText);
        const cacheKey = `${targetPageIndex}_${targetSentenceIndex}_${voiceSelect.value}_${speedRange.value}`;

        if (state.audioBufferCache.has(cacheKey)) continue;

        fetch(`${API_URL}/api/synthesize`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                text: cleanText,
                voice: voiceSelect.value,
                speed: parseFloat(speedRange.value),
                rules: state.rules,
                ignore_list: state.ignoreList,
                pause_settings: state.pauseSettings
            })
        }).then(async res => {
            if (res.ok) {
                const blob = await res.blob();
                const arrayBuffer = await blob.arrayBuffer();
                const audioBuffer = await state.audioContext.decodeAudioData(arrayBuffer);
                state.audioBufferCache.set(cacheKey, audioBuffer);
                console.log(`[PreCache] Cached page ${targetPageIndex} seq ${targetSentenceIndex}`);
            }
        }).catch(() => { });
    }
}

export async function loadVoices() {
    const voiceSelect = document.getElementById('voiceSelect');
    try {
        const currentVoice = voiceSelect.value;
        const data = await fetchJSON(`/api/voices/available`);
        const categories = data.categories || {};

        voiceSelect.innerHTML = '';
        const sortedKeys = Object.keys(categories).sort((a, b) => {
            if (a.startsWith('en') && !b.startsWith('en')) return -1;
            if (!a.startsWith('en') && b.startsWith('en')) return 1;
            return a.localeCompare(b);
        });

        sortedKeys.forEach(langCode => {
            const category = categories[langCode];
            const group = document.createElement('optgroup');
            // Try to translate the language code using loaded translations, fallback to label from backend
            group.label = state.translations?.languages?.[langCode] || category.label;
            category.voices.forEach(voice => {
                // Filter out voices with Indian accents as requested (handles prefixes like v0_alpha)
                const voiceId = voice.id.toLowerCase();
                const cleanId = voiceId.includes('_') ? voiceId.split('_').pop() : voiceId;
                if (['alpha', 'beta', 'omega', 'psi'].includes(cleanId)) return;

                const option = document.createElement('option');
                option.value = voice.id;

                // Dynamic label generation
                let label = voice.name;
                const attrs = state.translations?.voice_attributes || {};
                
                // Helper to get attributes
                const getAttrs = (vid) => {
                    if (vid.startsWith('af_')) return [attrs.american, attrs.female];
                    if (vid.startsWith('am_')) return [attrs.american, attrs.male];
                    if (vid.startsWith('bf_')) return [attrs.british, attrs.female];
                    if (vid.startsWith('bm_')) return [attrs.british, attrs.male];
                    if (vid.startsWith('ff_')) return [attrs.french, attrs.female];
                    if (vid.startsWith('jf_')) return [attrs.japanese, attrs.female];
                    if (vid.startsWith('jm_')) return [attrs.japanese, attrs.male];
                    if (vid.startsWith('ef_')) return [attrs.spanish, attrs.female];
                    if (vid.startsWith('em_')) return [attrs.spanish, attrs.male];
                    if (vid.startsWith('zf_')) return [attrs.chinese, attrs.female];
                    if (vid.startsWith('zm_')) return [attrs.chinese, attrs.male];
                    if (vid.startsWith('if_')) return [attrs.italian, attrs.female];
                    if (vid.startsWith('im_')) return [attrs.italian, attrs.male];
                    if (vid.startsWith('pf_')) return [attrs.portuguese, attrs.female];
                    if (vid.startsWith('pm_')) return [attrs.portuguese, attrs.male];
                    
                    if (vid === 'santa') return [attrs.spanish, attrs.male];
                    
                    return [];
                };

                const [region, gender] = getAttrs(voice.id);
                if (region && gender) {
                    label = `${voice.name} (${region} ${gender})`;
                } else {
                    // Fallback to legacy static list if available, or just name
                    label = state.translations?.voices?.[voice.id] || voice.name;
                }

                option.textContent = label;
                group.appendChild(option);
            });
            voiceSelect.appendChild(group);
        });

        if (currentVoice) {
            const exists = Array.from(voiceSelect.options).some(opt => opt.value === currentVoice);
            if (exists) voiceSelect.value = currentVoice;
        }

        if (voiceSelect.options.length === 0) {
            const option = document.createElement('option');
            option.textContent = "No voices found (Download Engine)";
            option.disabled = true;
            voiceSelect.appendChild(option);
        }
        return true;
    } catch (error) {
        console.error("Error loading voices:", error);
        voiceSelect.innerHTML = '<option disabled>Error loading voices</option>';
        return false;
    }
}
