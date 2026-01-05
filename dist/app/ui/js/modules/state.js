
export const state = {
    // Documents
    currentDoc: null,
    currentPages: [],
    currentPageIndex: 0,
    currentSentenceIndex: 0,
    sentences: [],
    sentenceElements: [], // Cache
    smartStartPage: 0,

    // Playback
    isPlaying: false,
    audioContext: null,
    currentAudioSource: null,
    audioBufferCache: new Map(),
    MAX_AUDIO_CACHE: 10,

    // Settings
    rules: [],
    ignoreList: [],
    headerFooterMode: 'off',
    engineMode: 'gpu',
    currentSearchQuery: '',
    searchDebounceTimer: null,
    pauseSettings: { comma: 300, period: 600, question: 600, exclamation: 600, colon: 400, semicolon: 400, newline: 0 },

    // Voices & Language
    currentLangIndex: 0,
    currentTranslations: {},
    languages: ['en', 'fr', 'es', 'zh'],
    defaultVoices: {
        'en': 'af_bella',
        'fr': 'ff_siwis',
        'es': 'ef_dora',
        'zh': 'zf_xiaobei'
    }
};
