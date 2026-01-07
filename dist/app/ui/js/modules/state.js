
export const state = {
    // Documents
    currentDoc: null,
    currentPages: [],
    
    // Decoupled Pointers
    readingPageIndex: 0,    // Where the voice is
    readingSentences: [],   // The sentences being spoken
    currentSentenceIndex: 0, // Current line index
    viewPageIndex: 0,       // What the user is seeing
    viewSentences: [],      // The sentences currently rendered on screen
    
    sentenceElements: [],   // Cache for current view
    smartStartPage: 0,
    autoScrollEnabled: true,

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
    jumpTimer: null,
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
