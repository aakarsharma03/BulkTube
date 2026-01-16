document.addEventListener('DOMContentLoaded', () => {
    const videoInput = document.getElementById('encodedVideoUrl');
    const addBtn = document.getElementById('addBtn');
    const videoList = document.getElementById('videoList');
    const queueCount = document.getElementById('queueCount');
    const downloadAllBtn = document.getElementById('downloadAllBtn');

    let videoQueue = [];

    const stopBtn = document.getElementById('stopBtn');
    let isDownloading = false;
    let shouldStop = false;

    // Event Listeners
    addBtn.addEventListener('click', handleAddVideo);
    videoInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') handleAddVideo();
    });

    downloadAllBtn.addEventListener('click', handleDownloadAll);

    if (stopBtn) {
        stopBtn.addEventListener('click', () => {
            if (isDownloading) {
                shouldStop = true;
                stopBtn.innerHTML = '<i class="fa-solid fa-hand"></i> Stopping...';
            }
        });
    }

    async function handleAddVideo() {
        const rawInput = videoInput.value.trim();
        if (!rawInput) return;

        // Split by comma or newline to handle bulk paste
        const urls = rawInput.split(/[\n,]+/).map(u => u.trim()).filter(u => u.length > 0);

        // Visual feedback on button
        const originalBtnContent = addBtn.innerHTML;
        addBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';
        addBtn.disabled = true;

        // Process URLs sequentially to avoid overwhelming server
        for (const url of urls) {
            try {
                const response = await fetch('/api/info', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ url })
                });

                const data = await response.json();

                if (response.ok) {
                    addVideoToQueue(data);
                } else {
                    console.error('Error for ' + url + ': ' + data.error);
                    // Optional: Show toast or alert for specific failure
                }
            } catch (error) {
                console.error('Error fetching video info:', error);
            }
        }

        videoInput.value = '';
        addBtn.innerHTML = originalBtnContent;
        addBtn.disabled = false;
        videoInput.focus();
    }

    function addVideoToQueue(videoData) {
        const id = Date.now().toString(); // Simple unique ID for frontend tracking
        const video = {
            id,
            ...videoData,
            status: 'pending' // pending, downloading, complete, error
        };

        videoQueue.push(video);
        updateQueueUI();
        renderVideoCard(video);
    }

    function removeVideo(id) {
        videoQueue = videoQueue.filter(v => v.id !== id);
        updateQueueUI();
        const card = document.querySelector(`.video-card[data-id="${id}"]`);
        if (card) {
            card.style.opacity = '0';
            card.style.transform = 'translateX(20px)';
            setTimeout(() => card.remove(), 300);
        }
    }

    function updateQueueUI() {
        queueCount.textContent = videoQueue.length;
        downloadAllBtn.disabled = videoQueue.length === 0;
    }

    function renderVideoCard(video) {
        const card = document.createElement('div');
        card.className = 'video-card';
        card.dataset.id = video.id;

        // Quality Options
        const qualityOptions = video.qualities.map(q =>
            `<option value="${q.id}">${q.label}</option>`
        ).join('');

        card.innerHTML = `
            <img src="${video.thumbnail}" alt="Thumb" class="video-thumb">
            <div class="video-info">
                <div class="video-title" title="${video.title}">${video.title}</div>
                <div class="video-meta">
                    <span><i class="fa-regular fa-clock"></i> ${video.duration}</span>
                    <span class="status-badge status-pending" id="status-${video.id}">Pending</span>
                </div>
            </div>
            <div class="video-controls">
                <select id="quality-${video.id}">
                    ${qualityOptions}
                </select>
                <button class="download-btn" onclick="startDownload('${video.id}')" title="Download">
                    <i class="fa-solid fa-download download-icon"></i>
                    <div class="loader"></div>
                </button>
                <button class="remove-btn" onclick="removeCard('${video.id}')" title="Remove">
                    <i class="fa-solid fa-trash"></i>
                </button>
            </div>
        `;

        // We bind functions to window or handle via event delegation. 
        // For simplicity, I'll attach them to window with unique IDs or just use event listener on container.
        // Let's use specific event listeners after creation for cleaner code (avoids global scope pollution)

        // Re-implementing without inline onclicks for better practice:
        const downloadBtn = card.querySelector('.download-btn');
        downloadBtn.onclick = () => handleDownloadSingle(video.id);

        const removeBtn = card.querySelector('.remove-btn');
        removeBtn.onclick = () => removeVideo(video.id);

        // Prepend to list (newest first)
        videoList.prepend(card);
    }

    async function handleDownloadSingle(id) {
        const video = videoQueue.find(v => v.id === id);
        if (!video) return;

        const card = document.querySelector(`.video-card[data-id="${id}"]`);
        const qualitySelect = card.querySelector(`select`);
        const selectedQuality = qualitySelect.value;
        const statusBadge = card.querySelector(`#status-${id}`);
        const downloadBtn = card.querySelector('.download-btn');

        // Update UI state
        card.classList.add('downloading');
        statusBadge.className = 'status-badge status-downloading';
        statusBadge.textContent = 'Downloading...';
        downloadBtn.disabled = true;

        try {
            const response = await fetch('/api/download', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    url: video.url,
                    quality: selectedQuality
                })
            });

            const resData = await response.json();

            if (response.ok) {
                statusBadge.className = 'status-badge status-complete';
                statusBadge.textContent = 'Completed';
                video.status = 'complete';
            } else {
                throw new Error(resData.error);
            }
        } catch (error) {
            console.error('Download failed:', error);
            statusBadge.className = 'status-badge status-error';
            statusBadge.textContent = 'Failed';
            video.status = 'error';
        } finally {
            card.classList.remove('downloading');
            downloadBtn.disabled = false;
        }
    }

    async function handleDownloadAll() {
        const pendingVideos = videoQueue.filter(v => v.status === 'pending');

        if (pendingVideos.length === 0) {
            alert("No pending videos to download.");
            return;
        }

        isDownloading = true;
        shouldStop = false;
        downloadAllBtn.disabled = true;
        stopBtn.disabled = false; // Enable stop button

        // Show stop, Hide download
        downloadAllBtn.style.display = 'none';
        stopBtn.style.display = 'inline-flex';

        for (const video of pendingVideos) {
            if (shouldStop) {
                break;
            }
            await handleDownloadSingle(video.id);
        }

        isDownloading = false;
        shouldStop = false;
        downloadAllBtn.disabled = false;
        stopBtn.disabled = true;

        // Reset buttons
        downloadAllBtn.style.display = 'inline-flex';
        stopBtn.style.display = 'none';
        stopBtn.innerHTML = '<i class="fa-solid fa-stop"></i> Stop';
        downloadAllBtn.innerHTML = '<i class="fa-solid fa-cloud-arrow-down"></i> Download All';
    }
});
