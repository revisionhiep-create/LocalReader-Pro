import { state } from "./state.js";
import { fetchJSON, fetchBlob } from "./api.js";
import {
  showToast,
  renderIcons,
  stripHTML,
  highlightSearchTerm,
} from "./ui.js";

export async function loadLibrary() {
  const libraryPanel = document.getElementById("libraryPanel");
  try {
    const items = await fetchJSON(`/api/library?t=${Date.now()}`);
    console.log("Library items loaded:", items);
    libraryPanel.innerHTML = "";
    if (!Array.isArray(items) || items.length === 0) {
      libraryPanel.innerHTML =
        '<div class="p-4 text-xs text-zinc-500 italic">Library is empty. Upload a PDF to start.</div>';
      return;
    }
    const fragment = document.createDocumentFragment();
    // Sort by last accessed desc
    items
      .sort((a, b) => (b.lastAccessed || 0) - (a.lastAccessed || 0))
      .forEach((item) => {
        const isSelected = state.currentDoc?.id === item.id;
        const div = document.createElement("div");
        div.className = `group p-3 rounded-xl cursor-pointer border transition-all ${
          isSelected
            ? "bg-blue-600/10 border-blue-600/50 text-blue-400"
            : "bg-zinc-900/50 border-zinc-800 text-zinc-400 hover:border-zinc-700"
        }`;

        div.innerHTML = `
                <div class="flex items-start justify-between gap-2">
                    <div class="flex items-start gap-3 min-w-0" data-action="select-doc" data-id="${
                      item.id
                    }">
                        <i data-lucide="file" class="w-4 h-4 mt-0.5 shrink-0"></i>
                        <div class="min-w-0">
                            <p class="text-xs font-bold leading-tight break-words">${
                              item.fileName
                            }</p>
                            <p class="text-[10px] opacity-60 mt-1">Page ${
                              (item.currentPage || 0) + 1
                            }/${item.totalPages}</p>
                        </div>
                    </div>
                    <button data-action="delete-doc" data-id="${
                      item.id
                    }" class="p-1 hover:bg-red-500/20 hover:text-red-500 rounded-md transition-colors opacity-0 group-hover:opacity-100 shrink-0">
                        <i data-lucide="x" class="w-3.5 h-3.5"></i>
                    </button>
                </div>`;
        fragment.appendChild(div);
      });
    libraryPanel.appendChild(fragment);
    renderIcons();
  } catch (e) {
    console.error("Load library error:", e);
    libraryPanel.innerHTML =
      '<div class="p-4 text-xs text-red-500 italic">Failed to load library.</div>';
  }
}

export async function selectDocument(item) {
  state.currentDoc = item;
  try {
    const data = await fetchJSON(`/api/library/content/${item.id}`);
    state.currentPages = data.pages;
    state.smartStartPage = data.smart_start_page || 0;

    // Apply Smart Start if this is first time opening (currentPage is 0)
    if ((item.currentPage || 0) === 0 && state.smartStartPage > 0) {
      state.readingPageIndex = state.smartStartPage;
      state.viewPageIndex = state.smartStartPage;
      state.currentSentenceIndex = 0;
      showToast(
        `⚡ Skipped to start of content (Page ${state.smartStartPage + 1})`
      );
    } else {
      state.readingPageIndex = item.currentPage || 0;
      state.viewPageIndex = item.currentPage || 0;
      state.currentSentenceIndex = item.lastSentenceIndex || 0;
    }

    // Initialize reading sentences
    state.readingSentences = await getSentencesForPage(state.readingPageIndex);

    // Update UI
    const docTitle = document.getElementById("docTitle");
    const pageNav = document.getElementById("pageNav");
    const controls = document.getElementById("controls");
    const emptyState = document.getElementById("emptyState");
    const textContent = document.getElementById("textContent");
    const prevPage = document.getElementById("prevPage");
    const nextPage = document.getElementById("nextPage");
    const pageInput = document.getElementById("pageInput");
    const searchBtn = document.getElementById("searchBtn");
    const exportArea = document.getElementById("exportArea");
    const textSizeArea = document.getElementById("textSizeArea");

    if (docTitle) docTitle.textContent = item.fileName;

    if (pageNav) {
      pageNav.classList.remove("opacity-50", "pointer-events-none");
      pageNav.removeAttribute("data-inactive");
    }
    if (prevPage) prevPage.disabled = false;
    if (nextPage) nextPage.disabled = false;
    if (pageInput) pageInput.disabled = false;
    if (controls) controls.classList.remove("hidden");
    if (emptyState) emptyState.classList.add("hidden");
    if (textContent) textContent.classList.remove("hidden");
    if (searchBtn) searchBtn.classList.remove("hidden");

    // Note: engine status check should handle these
    if (exportArea) exportArea.style.display = "block";
    if (textSizeArea) textSizeArea.style.display = "block";

    renderPage();
    loadLibrary(); // Update active state in list
  } catch (e) {
    console.error("Select document error:", e);
    showToast("Failed to load document content");
  }
}

export async function renderPage() {
  const textContent = document.getElementById("textContent");
  const pageInput = document.getElementById("pageInput");
  const pageTotal = document.getElementById("pageTotal");
  const scrollContainer = document.querySelector(".content-area");
  const currentSentencePreview = document.getElementById(
    "currentSentencePreview"
  );
  const backToReadingBtn = document.getElementById("backToReadingBtn");

  if (!state.currentPages || !state.currentPages[state.viewPageIndex]) {
    if (textContent)
      textContent.innerHTML =
        '<div class="text-zinc-500 p-4">Error: Page not found</div>';
    return;
  }

  // Update "Back to Reading" button visibility
  if (backToReadingBtn) {
    if (state.viewPageIndex !== state.readingPageIndex) {
        backToReadingBtn.classList.remove('hidden');
    } else {
        backToReadingBtn.classList.add('hidden');
    }
  }

  state.viewSentences = await getSentencesForPage(state.viewPageIndex);

  const fragment = document.createDocumentFragment();
  const isReadingCurrentPage = state.viewPageIndex === state.readingPageIndex;

  state.viewSentences.forEach((s, i) => {
    const span = document.createElement("span");
    span.className = `sentence ${
      (isReadingCurrentPage && i === state.currentSentenceIndex) ? "active-sentence" : ""
    }`;

    // Fix broken DIM tags caused by sentence splitting
    let cleanS = s;
    if (cleanS.includes("[DIM]") && !cleanS.includes("[/DIM]"))
      cleanS += "[/DIM]";
    if (!cleanS.includes("[DIM]") && cleanS.includes("[/DIM]"))
      cleanS = "[DIM]" + cleanS;

    if (cleanS.includes("[DIM]")) {
      const dimRegex = /\[DIM\](.*?)\[\/DIM\]/g;
      span.innerHTML = cleanS.replace(
        dimRegex,
        '<span class="dimmed-text">$1</span>'
      );
    } else {
      span.textContent = cleanS;
    }

    // Clicking a line SYNCs reading to that spot (with buffer)
    span.onclick = () => {
      state.readingPageIndex = state.viewPageIndex;
      state.readingSentences = [...state.viewSentences];
      state.autoScrollEnabled = true; // Re-enable auto-scroll on click
      window.dispatchEvent(new CustomEvent("jump-to-sentence", { detail: i }));
    };
    fragment.appendChild(span);
  });

  if (textContent) {
    textContent.innerHTML = "";
    textContent.appendChild(fragment);
    state.sentenceElements = Array.from(
      textContent.querySelectorAll(".sentence")
    );
  }

  if (pageInput) pageInput.value = state.viewPageIndex + 1;
  if (pageTotal) pageTotal.textContent = state.currentPages.length;
  
  // Standard behavior: Scroll to top of page on change if autoScroll is enabled
  if (scrollContainer && state.autoScrollEnabled) scrollContainer.scrollTop = 0;

  const currentReadingSentence = state.readingSentences[state.currentSentenceIndex];
  if (currentSentencePreview) {
    currentReadingSentencePreviewText(currentReadingSentence, currentSentencePreview);
  }

  if (state.currentSearchQuery) {
    highlightSearchTerm(state.currentSearchQuery);
  }
}

function currentReadingSentencePreviewText(currentReadingSentence, currentSentencePreview) {
  currentSentencePreview.textContent =
    currentReadingSentence && typeof currentReadingSentence === "string"
      ? stripHTML(currentReadingSentence)
      : "Ready";
}

export async function extractTextFromPage(page) {
  const content = await page.getTextContent();
  let text = "",
    lastItem = null;
  let totalWidth = 0,
    charCount = 0;
  for (let item of content.items) {
    if (item.str.trim().length > 0) {
      totalWidth += item.width;
      charCount += item.str.length;
    }
  }
  const avgCharWidth = charCount > 0 ? totalWidth / charCount : 5;

  for (let item of content.items) {
    let str = item.str.replace(/\ufffd/g, '"');
    str = str.normalize("NFKC");

    if (!str.trim() && str !== " ") continue;

    if (lastItem) {
      const lastY = lastItem.transform[5],
        currentY = item.transform[5];
      const lastX = lastItem.transform[4],
        lastWidth = lastItem.width;
      const lastHeight = Math.abs(lastItem.transform[0]);
      const currentX = item.transform[4];

      const verticalGap = Math.abs(currentY - lastY);

      if (verticalGap > lastHeight * 0.4) {
        // Check if line ends with terminal punctuation
        const textEnd = text.trimEnd();
        const lastChar = textEnd.slice(-1);
        const isTerminalChar = /[.!?;:。！？：；]/.test(lastChar);

        // Don't treat common abbreviations as terminal (prevents breaking "Mr. Smith" into lines)
        const abbreviations = [
          "Mr.",
          "Mrs.",
          "Ms.",
          "Dr.",
          "Prof.",
          "St.",
          "Rd.",
          "Ave.",
          "Capt.",
          "Gen.",
          "Sen.",
          "Rep.",
          "Gov.",
          "Fig.",
          "No.",
          "Op.",
          "vs.",
          "etc.",
          "e.g.",
          "i.e.",
          "Inc.",
          "Ltd.",
          "Co.",
        ];
        const isAbbreviation = abbreviations.some((abbr) =>
          textEnd.endsWith(abbr)
        );

        const isTerminal = isTerminalChar && !isAbbreviation;

        if (!isTerminal && verticalGap < lastHeight * 2.5) {
          const lastChar = text.trimEnd().slice(-1);
          const nextChar = str.trimStart().charAt(0);
          const isCJK = (c) =>
            /[\u3000-\u303f\u3040-\u309f\u30a0-\u30ff\uff00-\uff9f\u4e00-\u9faf\u3400-\u4dbf]/.test(
              c
            );

          if (
            !text.endsWith(" ") &&
            !str.startsWith(" ") &&
            !isCJK(lastChar) &&
            !isCJK(nextChar)
          ) {
            text += " ";
          }
        } else {
          text = text.trimEnd() + "\n";
        }
      } else {
        const gap = currentX - (lastX + lastWidth);
        if (gap > Math.max(1.5, avgCharWidth * 0.25)) {
          const lastChar = text.trimEnd().slice(-1);
          const nextChar = str.trimStart().charAt(0);
          const noSpaceBefore = /[\"\'\(\[\{\u201c\u2018]/.test(lastChar);
          const noSpaceAfter = /[\"\'\)\\\}\]\u201d\u2019]/.test(nextChar);
          const isCJK = (c) =>
            /[\u3000-\u303f\u3040-\u309f\u30a0-\u30ff\uff00-\uff9f\u4e00-\u9faf\u3400-\u4dbf]/.test(
              c
            );

          if (
            !text.endsWith(" ") &&
            !str.startsWith(" ") &&
            !noSpaceBefore &&
            !noSpaceAfter &&
            (!isCJK(lastChar) || !isCJK(nextChar))
          ) {
            text += " ";
          }
        }
      }
    }
    text += str;
    lastItem = item;
  }
  return text
    .trim()
    .replace(/[ \t]+/g, " ")
    .replace(/\n\s+/g, "\n")
    .replace(/-\s*\n\s*/g, "");
}

export async function processPdfBlob(blob, fileName) {
  // Requires pdfjsLib to be available globally (loaded via script tag)
  if (!window.pdfjsLib) {
    showToast("PDF.js library not loaded");
    return;
  }

  const reader = new FileReader();
  reader.onload = async function () {
    try {
      const pdf = await window.pdfjsLib.getDocument(new Uint8Array(this.result))
        .promise;
      const pagesText = [];
      for (let i = 1; i <= pdf.numPages; i++) {
        const page = await pdf.getPage(i);
        pagesText.push(await extractTextFromPage(page));
      }
      const docId = crypto.randomUUID();
      const newDoc = {
        id: docId,
        fileName: fileName,
        totalPages: pdf.numPages,
        currentPage: 0,
        lastSentenceIndex: 0,
        lastAccessed: Date.now(),
      };

      await fetchJSON("/api/library", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(newDoc),
      });
      await fetchJSON("/api/library/content", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id: docId, pages: pagesText }),
      });

      selectDocument(newDoc);
      showToast("Book added to library");
    } catch (err) {
      console.error("PDF processing error:", err);
      showToast("Failed to process document: " + err.message);
    }
  };
  reader.readAsArrayBuffer(blob);
}

export async function getSentencesForPage(pageIndex) {
  if (!state.currentPages || !state.currentPages[pageIndex]) return [];

  let text = state.currentPages[pageIndex];

  // Apply header/footer filter if enabled
  if (state.headerFooterMode !== "off" && state.currentDoc) {
    try {
      const filterData = await fetchJSON(
        `/api/library/content/${state.currentDoc.id}/page/${pageIndex}`
      );
      text = filterData.filtered_text;
    } catch (e) {
      console.error("Filter fetch failed:", e);
    }
  }

  // Preprocessing (Join broken lines)
  text = text
    .replace(/\n\n/g, "<!PARAGRAPH!>")
    .replace(/([^.!?:;。！？：；])\n/g, "$1 ")
    .replace(/<!PARAGRAPH!>/g, "\n\n")
    .replace(/  +/g, " ");

  // Split sentences
  const abbreviations = ["Mr", "Mrs", "Ms", "Dr", "Prof", "St", "Rd", "Ave", "Capt", "Gen", "Sen", "Rep", "Gov", "Fig", "No", "Op", "vs", "etc", "e\\.g", "i\\.e", "Inc", "Ltd", "Co"];
  const abbrRegex = new RegExp(`\\b(${abbreviations.join('|')})\\.(?=\\s)`, 'gi');
  const protectedText = text.replace(abbrRegex, '$1<DOT>');

  const sentences = [];
  const segmenter = new Intl.Segmenter(state.uiLanguage || 'en', { granularity: 'sentence' });

  for (const segmentItem of segmenter.segment(protectedText)) {
    let s = segmentItem.segment.trim()
      .replace(/<DOT>/g, '.') // Restore dots
      .replace(/^[\"\'\u201c\u2018\u201d\u2019]+(?=[\"\'\u201c\u2018\u201d\u2019])/, '')
      .replace(/[\"\'\u201c\u2018\u201d\u2019]+$/, (match) => match.length > 1 ? match[0] : match);
    if (s) {
        // Fix broken DIM tags
        if (s.includes("[DIM]") && !s.includes("[/DIM]")) s += "[/DIM]";
        if (!s.includes("[DIM]") && s.includes("[/DIM]")) s = "[DIM]" + s;
        sentences.push(s);
    }
  }
  return sentences;
}
