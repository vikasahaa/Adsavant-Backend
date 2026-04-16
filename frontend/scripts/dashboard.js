document.addEventListener('DOMContentLoaded', () => {

    // --- 0. SESSION MEMORY ---
    let sessionHistory = [];
    
    // --- 1. SIDEBAR NAVIGATION ---
    const navItems = document.querySelectorAll('.nav-item');
    const views = document.querySelectorAll('.dash-view');

    navItems.forEach(item => {
        item.addEventListener('click', () => {
            navItems.forEach(nav => nav.classList.remove('active'));
            item.classList.add('active');
            views.forEach(view => view.classList.remove('active-view'));

            const targetViewId = item.getAttribute('data-target');
            const targetView = document.getElementById(targetViewId);
            if (targetView) targetView.classList.add('active-view');

            // If user clicks on Visual Insights tab, refresh the charts/metrics
            if (targetViewId === 'view-insights') {
                updateAnalyticsTab();
                updateVisualMetricsUI();
            }
        });
    });

    // --- 2. FILE UPLOAD UI ---
    const fileInput = document.getElementById('file-input');
    const dropZoneText = document.querySelector('.upload-zone p');

    if (fileInput) {
        fileInput.addEventListener('change', (e) => {
            if (e.target.files && e.target.files.length > 0) {
                dropZoneText.innerHTML = `<strong>${e.target.files[0].name}</strong> selected.`;
            }
        });
    }

    // --- 3. RESULTS MAPPING LOGIC ---
    const loadResultsView = (apiResult, caption, imgSource) => {
        const scoreElement = document.querySelector('.score-text');
        if (scoreElement) {
            const rate = apiResult.predicted_engagement_rate || 0;
            scoreElement.textContent = `${rate.toFixed(2)}%`;

            const dial = document.querySelector('.circular-progress');
            if (dial) {
                const dialPercentage = Math.min((rate / 10.0) * 100, 100);
                dial.style.background = `conic-gradient(#2ecc71 ${dialPercentage}%, #f1f5f9 0deg)`;
            }
        }

        document.getElementById('result-image-preview').src = imgSource;
        document.getElementById('result-caption-text').textContent = caption;

        const classFill = document.getElementById('classification-fill');
        if (classFill) {
            const classification = apiResult.regression_classification;
            classFill.style.width = classification === "High" ? "95%" : classification === "Average" ? "60%" : "30%";
            classFill.style.backgroundColor = classification === "High" ? "#2ecc71" : classification === "Average" ? "#f1c40f" : "#e74c3c";
        }

        const confFill = document.getElementById('confidence-fill');
        if (confFill) {
            const confidence = apiResult.confidence;
            confFill.style.width = confidence === "High" ? "95%" : confidence === "Moderate" ? "65%" : "35%";
            confFill.style.backgroundColor = confidence === "High" ? "#2ecc71" : confidence === "Moderate" ? "#f1c40f" : "#e74c3c";
        }

        views.forEach(v => v.classList.remove('active-view'));
        document.getElementById('view-results').classList.add('active-view');
    };

    // --- 4. HISTORY & ANALYTICS RENDERING ---
    const updateHistoryTable = () => {
        const tbody = document.getElementById('history-table-body');
        if (!tbody) return;
        tbody.innerHTML = '';

        if (sessionHistory.length === 0) {
            tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; padding: 2rem; color: #64748B;">No predictions made yet.</td></tr>`;
            return;
        }

        [...sessionHistory].reverse().forEach(record => {
            let classColor = record.classification === 'High' ? '#2ecc71' : record.classification === 'Average' ? '#f1c40f' : '#e74c3c';
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td style="color: #64748B;">${record.date}</td>
                <td><img src="${record.thumbnailUrl}" style="width: 48px; height: 48px; object-fit: cover; border-radius: 6px; border: 1px solid #E2E8F0;"></td>
                <td style="font-weight: 600;">${record.engagementRate}</td>
                <td><span style="background: ${classColor}20; color: ${classColor}; padding: 4px 10px; border-radius: 12px; font-size: 0.85rem; font-weight: 600;">${record.classification}</span></td>
                <td>${record.confidence}</td>
                <td><button class="btn-icon" style="background:none; border:none; color: #64748B;"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7"/></svg></button></td>
            `;
            tbody.appendChild(tr);
        });
    };

    const updateVisualMetricsUI = () => {
        if (sessionHistory.length === 0) return;
        const latest = sessionHistory[sessionHistory.length - 1].visualMetrics;
        if (!latest) return;

        // Update progress bars (Match these IDs in your HTML)
        const updateBar = (id, val) => {
            const bar = document.getElementById(`bar-${id}`);
            const text = document.getElementById(`val-${id}`);
            if (bar) bar.style.width = `${val}%`;
            if (text) text.innerText = `${val}%`;
        };

        updateBar('lighting', latest.lighting_quality);
        updateBar('contrast', latest.colour_contrast);
        updateBar('focus', latest.subject_focus);
        updateBar('quality', latest.visual_quality_composite);
    };

// --- Helper: Convert Hex to closest Color Name ---
const colorPalette = [
    { name: "Black", hex: "#000000" }, { name: "White", hex: "#FFFFFF" },
    { name: "Red", hex: "#FF0000" }, { name: "Green", hex: "#00FF00" },
    { name: "Blue", hex: "#0000FF" }, { name: "Yellow", hex: "#FFFF00" },
    { name: "Cyan", hex: "#00FFFF" }, { name: "Magenta", hex: "#FF00FF" },
    { name: "Gray", hex: "#808080" }, { name: "Navy", hex: "#000080" },
    { name: "Maroon", hex: "#800000" }, { name: "Olive", hex: "#808000" },
    { name: "Purple", hex: "#800080" }, { name: "Teal", hex: "#008080" },
    { name: "Silver", hex: "#C0C0C0" }, { name: "Orange", hex: "#FFA500" },
    { name: "Brown", hex: "#A52A2A" }, { name: "Pink", hex: "#FFC0CB" },
    { name: "Beige", hex: "#F5F5DC" }, { name: "Light Gray", hex: "#D3D3D3" },
    { name: "Dark Gray", hex: "#A9A9A9" }, { name: "Tan", hex: "#D2B48C" },
    { name: "Khaki", hex: "#F0E68C" }, { name: "Dark Red", hex: "#8B0000" },
    { name: "Navy Blue", hex: "#0F172A" }, { name: "Burnt Orange", hex: "#E85D04" }
];

function getColorName(hex) {
    const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    if (!result) return hex;
    const rgb = { r: parseInt(result[1], 16), g: parseInt(result[2], 16), b: parseInt(result[3], 16) };

    let closest = "Unknown", minDist = Infinity;
    colorPalette.forEach(c => {
        const tr = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(c.hex);
        const r = parseInt(tr[1], 16), g = parseInt(tr[2], 16), b = parseInt(tr[3], 16);
        // Calculate Euclidean distance in RGB space to find the nearest color match
        const dist = Math.sqrt(Math.pow(rgb.r - r, 2) + Math.pow(rgb.g - g, 2) + Math.pow(rgb.b - b, 2));
        if (dist < minDist) { minDist = dist; closest = c.name; }
    });
    return closest;
}

// --- Rebuilt Analytics Tab Update ---
function updateAnalyticsTab() {
    if (sessionHistory.length === 0) return;

    // Update Top Stats
    document.getElementById('total-analysed-count').innerText = sessionHistory.length;

    const styleStats = {};
    sessionHistory.forEach(record => {
        const style = record.brandType || "Standard";
        const er = parseFloat(record.engagementRate.replace('%', ''));
        if (!styleStats[style]) styleStats[style] = { totalER: 0, count: 0 };
        styleStats[style].totalER += er;
        styleStats[style].count += 1;
    });

    let topStyle = "N/A", highestAvgER = 0;
    for (const [style, data] of Object.entries(styleStats)) {
        const avgER = data.totalER / data.count;
        if (avgER > highestAvgER) { highestAvgER = avgER; topStyle = style; }
    }

    document.getElementById('top-style-name').innerText = topStyle.charAt(0).toUpperCase() + topStyle.slice(1);
    document.getElementById('top-style-er').innerText = `${highestAvgER.toFixed(2)}% Avg ER`;

    const latestRecord = sessionHistory[sessionHistory.length - 1];

    // 1. UPDATE DOMINANT COLORS (Now with Names and mini progress bars!)
    if (latestRecord.visualMetrics && latestRecord.visualMetrics.dominant_colors) {
        const colorContainer = document.getElementById('dominant-color-container');
        colorContainer.innerHTML = '';

        latestRecord.visualMetrics.dominant_colors.forEach(colorInfo => {
            const colorName = getColorName(colorInfo.hex_code); // Translate Hex to Name

            const wrapper = document.createElement('div');
            wrapper.style.display = 'flex';
            wrapper.style.alignItems = 'center';
            wrapper.style.marginBottom = '16px';

            wrapper.innerHTML = `
                <div style="background:${colorInfo.hex_code}; width:28px; height:28px; border-radius:6px; margin-right:12px; border:1px solid #e2e8f0; flex-shrink:0;"></div>
                <div style="flex: 1;">
                    <div style="display: flex; justify-content: space-between; font-size: 0.85rem; font-weight: 600; margin-bottom: 6px; color: #1e293b;">
                        <span>${colorName} <span style="color:#94a3b8; font-weight:400; font-size:0.75rem;">(${colorInfo.hex_code})</span></span>
                        <span>${colorInfo.percentage}%</span>
                    </div>
                    <div style="width: 100%; height: 6px; background-color: #f1f5f9; border-radius: 3px; overflow: hidden;">
                        <div style="height: 100%; width: ${colorInfo.percentage}%; background-color: ${colorInfo.hex_code}; border-radius: 3px;"></div>
                    </div>
                </div>
            `;
            colorContainer.appendChild(wrapper);
        });
    }

    // 2. UPDATE VISUAL INSIGHTS PROGRESS BARS
    if (latestRecord.visualMetrics) {
        const updateInsightBar = (id, val) => {
            const bar = document.getElementById(`insight-bar-${id}`);
            const text = document.getElementById(`insight-val-${id}`);
            if (bar) bar.style.width = `${val}%`;
            if (text) text.innerText = `${val}%`;
        };

        updateInsightBar('lighting', latestRecord.visualMetrics.lighting_quality);
        updateInsightBar('contrast', latestRecord.visualMetrics.colour_contrast);
        updateInsightBar('focus', latestRecord.visualMetrics.subject_focus);
        updateInsightBar('quality', latestRecord.visualMetrics.visual_quality_composite);
    }
}
    // --- 5. FORM SUBMISSION (PARALLEL API CALLS) ---
    const predictionForm = document.getElementById('predictionForm');
    const loadingOverlay = document.getElementById('loading-overlay');

    if (predictionForm) {
        predictionForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            if (!fileInput.files[0]) return alert("Please upload an image first.");

            loadingOverlay.classList.remove('hidden');

            const predictData = new FormData();
            predictData.append('brand_type', document.getElementById('brand_category').value);
            predictData.append('followers', document.getElementById('follower_count').value);
            predictData.append('caption', document.getElementById('caption_input').value);
            predictData.append('image', fileInput.files[0]);

            const visualData = new FormData();
            visualData.append('file', fileInput.files[0]);

            try {
                // Call both endpoints at once
                const [predRes, visRes] = await Promise.all([
                    fetch('/api/v1/predict', { method: 'POST', body: predictData }),
                    fetch('/api/v1/visual-metrics', { method: 'POST', body: visualData })
                ]);

                if (!predRes.ok || !visRes.ok) throw new Error('One or more services failed');

                const result = await predRes.json();
                const visualResult = await visRes.json();
                const previewUrl = URL.createObjectURL(fileInput.files[0]);
                const selectedBrand = document.getElementById('brand_category').value;

                sessionHistory.push({
                    id: Date.now(),
                    date: new Date().toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }),
                    thumbnailUrl: previewUrl,
                    engagementRate: `${(result.predicted_engagement_rate || 0).toFixed(2)}%`,
                    classification: result.regression_classification,
                    confidence: result.confidence,
                    brandType: selectedBrand, // <--- ADD THIS LINE! We save it directly from the UI
                    fullResult: result,
                    visualMetrics: visualResult.metrics
                });

                loadResultsView(result, document.getElementById('caption_input').value, previewUrl);
                updateHistoryTable();
                updateVisualMetricsUI();
                // We don't call updateAnalyticsTab here because it's handled when clicking the tab

            } catch (error) {
                console.error(error);
                alert('Connection error: ' + error.message);
            } finally {
                loadingOverlay.classList.add('hidden');
            }
        });
    }

    // --- 6. UI HELPERS ---
    const btnBack = document.getElementById('btn-back-predict');
    if (btnBack) {
        btnBack.addEventListener('click', () => {
            views.forEach(v => v.classList.remove('active-view'));
            document.getElementById('view-predict').classList.add('active-view');
        });
    }

    updateHistoryTable(); // Initial empty state
});