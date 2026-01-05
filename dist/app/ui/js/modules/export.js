
import { state } from './state.js';
import { fetchJSON } from './api.js';
import { showToast, renderIcons } from './ui.js';

let exportPollInterval = null;
let ffmpegPollInterval = null;

export async function startExport() {
    const voiceSelect = document.getElementById('voiceSelect');
    const speedRange = document.getElementById('speedRange');

    if (!state.currentDoc) {
        showToast("No document selected");
        return;
    }
    if (!window.isEngineReady) {
        showToast("Voice engine not ready");
        return;
    }

    try {
        const status = await fetchJSON(`/api/ffmpeg/status?t=${Date.now()}`);
        if (!status.is_installed) {
            showFFMPEGDownloadModal();
            return;
        }

        const totalChars = state.currentPages.join('').length;
        const estimatedSeconds = Math.ceil((totalChars / 1000) * 15);
        const estimatedMins = Math.ceil(estimatedSeconds / 60);

        if (!confirm(`This will export the entire document to MP3.\n\nEstimated time: ~${estimatedMins} minute${estimatedMins !== 1 ? 's' : ''}\n\nContinue?`)) {
            return;
        }

        const res = await fetchJSON(`/api/export/audio`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                doc_id: state.currentDoc.id,
                voice: voiceSelect.value,
                speed: parseFloat(speedRange.value),
                rules: state.rules,
                ignore_list: state.ignoreList
            })
        });

        const exportModal = document.getElementById('exportModal');
        const exportStatus = document.getElementById('exportStatus');

        exportModal.classList.remove('hidden');
        document.getElementById('exportComplete').classList.add('hidden');
        document.getElementById('exportError').classList.add('hidden');
        document.getElementById('exportProgress').textContent = '0%';
        document.getElementById('exportProgressBar').style.width = '0%';
        exportStatus.textContent = 'Initializing export...';
        document.getElementById('playBtn').disabled = true;

        startExportPolling();

    } catch (e) {
        console.error(e);
        showToast("Export failed: " + e.message);
    }
}

function startExportPolling() {
    if (exportPollInterval) clearInterval(exportPollInterval);
    exportPollInterval = setInterval(async () => {
        try {
            const status = await fetchJSON(`/api/export/status?t=${Date.now()}`);
            if (status.error) {
                clearInterval(exportPollInterval);
                document.getElementById('exportError').classList.remove('hidden');
                document.getElementById('exportErrorMsg').textContent = status.error;
                document.getElementById('exportStatus').textContent = 'Export failed';
                document.getElementById('playBtn').disabled = false;
                return;
            }

            if (status.is_exporting) {
                const percent = status.total > 0 ? Math.round((status.progress / status.total) * 100) : 0;
                document.getElementById('exportProgress').textContent = `${percent}%`;
                document.getElementById('exportProgressBar').style.width = `${percent}%`;
                document.getElementById('exportStatus').textContent = `Processing paragraph ${status.progress} of ${status.total}...`;
            } else if (status.output_file) {
                clearInterval(exportPollInterval);
                document.getElementById('exportProgress').textContent = '100%';
                document.getElementById('exportProgressBar').style.width = '100%';
                document.getElementById('exportStatus').textContent = 'Export complete!';

                document.getElementById('exportFilePath').textContent = `./userdata/${status.output_file}`;
                document.getElementById('exportComplete').classList.remove('hidden');
                document.getElementById('playBtn').disabled = false;
                renderIcons();

                // Store output file in DOM for the "Open Folder" button
                document.getElementById('exportModal').dataset.outputFile = status.output_file;
            }
        } catch (e) {
            console.error("Export polling error:", e);
        }
    }, 1000);
}

export function cancelExport() {
    if (exportPollInterval) clearInterval(exportPollInterval);
    fetchJSON(`/api/export/cancel`, { method: 'POST' }).catch(console.error);
    document.getElementById('exportModal').classList.add('hidden');
    document.getElementById('playBtn').disabled = false;
}

function showFFMPEGDownloadModal() {
    const modal = document.getElementById('ffmpegModal');
    modal.classList.remove('hidden');
    document.getElementById('ffmpegDownloadSection').classList.add('hidden');
    document.getElementById('ffmpegComplete').classList.add('hidden');
    document.getElementById('ffmpegError').classList.add('hidden');
    document.getElementById('startFFMPEGDownload').classList.remove('hidden');
    renderIcons();
}

export async function startFFMPEGDownload() {
    try {
        await fetchJSON(`/api/ffmpeg/install`, { method: 'POST' });

        document.getElementById('startFFMPEGDownload').classList.add('hidden');
        document.getElementById('ffmpegDownloadSection').classList.remove('hidden');
        document.getElementById('ffmpegProgress').textContent = '0%';
        document.getElementById('ffmpegStatus').textContent = 'Starting download...';

        startFFMPEGPolling();
    } catch (e) {
        document.getElementById('ffmpegError').classList.remove('hidden');
        document.getElementById('ffmpegErrorMsg').textContent = e.message;
    }
}

function startFFMPEGPolling() {
    if (ffmpegPollInterval) clearInterval(ffmpegPollInterval);
    ffmpegPollInterval = setInterval(async () => {
        try {
            const status = await fetchJSON(`/api/ffmpeg/status?t=${Date.now()}`);
            if (status.error) {
                clearInterval(ffmpegPollInterval);
                document.getElementById('ffmpegError').classList.remove('hidden');
                document.getElementById('ffmpegErrorMsg').textContent = status.error;
                return;
            }

            if (status.is_downloading) {
                const percent = status.total > 0 ? Math.round((status.progress / status.total) * 100) : 0;
                document.getElementById('ffmpegProgress').textContent = `${percent}%`;
                document.getElementById('ffmpegProgressBar').style.width = `${percent}%`;
                document.getElementById('ffmpegStatus').textContent = status.message || 'Downloading...';
            } else if (status.is_installed) {
                clearInterval(ffmpegPollInterval);
                document.getElementById('ffmpegDownloadSection').classList.add('hidden');
                document.getElementById('ffmpegComplete').classList.remove('hidden');
                renderIcons();
                setTimeout(() => {
                    document.getElementById('ffmpegModal').classList.add('hidden');
                    startExport();
                }, 1000);
            }
        } catch (e) { console.error("FFMPEG polling error:", e); }
    }, 500);
}

export function openExportLocation() {
    const outputFile = document.getElementById('exportModal').dataset.outputFile;
    if (outputFile) {
        fetchJSON(`/api/export/open-location/${outputFile}`, { method: 'POST' })
            .then(() => {
                showToast("Opening folder...");
                setTimeout(() => document.getElementById('exportModal').classList.add('hidden'), 1000);
            })
            .catch(e => showToast("Error: " + e.message));
    }
}
