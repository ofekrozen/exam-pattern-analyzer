document.getElementById('analyze-form').addEventListener('submit', async (e) => {
    e.preventDefault();

    const driveUrl = document.getElementById('driveUrl').value;
    const lecturerName = document.getElementById('lecturerName').value;
    const submitBtn = document.getElementById('submitBtn');
    const terminalSection = document.getElementById('terminal-section');
    const terminalOutput = document.getElementById('terminal-output');
    const resultsSection = document.getElementById('results-section');
    const resultsGrid = document.getElementById('results-grid');

    // Reset UI
    submitBtn.disabled = true;
    submitBtn.textContent = 'Analyzing...';
    terminalSection.classList.remove('hidden');
    resultsSection.classList.add('hidden');
    terminalOutput.innerHTML = '';
    resultsGrid.innerHTML = '';

    const addLog = (msg, isError = false) => {
        const div = document.createElement('div');
        div.textContent = `> ${msg}`;
        if (isError) div.style.color = '#f87171';
        terminalOutput.appendChild(div);
        terminalOutput.scrollTop = terminalOutput.scrollHeight;
    };

    try {
        // We will fetch from the API endpoint
        // To handle CORS during development, the user might run frontend separately or combined
        // Using relative or absolute path based on setup. Assuming backend is on port 8000
        const apiUrl = `http://localhost:8000/api/analyze/stream?drive_folder_url=${encodeURIComponent(driveUrl)}&lecturer_name=${encodeURIComponent(lecturerName)}`;

        const response = await fetch(apiUrl, {
            method: 'GET',
            headers: {
                'Accept': 'text/event-stream',
            }
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder('utf-8');
        let buffer = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });

            // Process complete events separated by \n\n
            const events = buffer.split('\n\n');
            buffer = events.pop(); // Keep the incomplete part

            for (const eventString of events) {
                if (!eventString.trim()) continue;

                // Parse SSE format
                const lines = eventString.split('\n');
                let eventType = 'message';
                let eventData = '';

                for (const line of lines) {
                    if (line.startsWith('event:')) {
                        eventType = line.substring(6).trim();
                    } else if (line.startsWith('data:')) {
                        eventData = line.substring(5).trim();
                    }
                }

                if (eventData) {
                    let parsedData;
                    try {
                        parsedData = JSON.parse(eventData);
                    } catch (e) {
                        parsedData = eventData;
                    }

                    if (eventType === 'status' || eventType === 'progress') {
                        addLog(parsedData);
                    } else if (eventType === 'error') {
                        addLog(parsedData, true);
                        submitBtn.disabled = false;
                        submitBtn.textContent = 'Start Analysis';
                    } else if (eventType === 'result') {
                        addLog('Analysis complete!');
                        renderResults(parsedData);
                    }
                }
            }
        }
    } catch (err) {
        addLog(`Connection Error: ${err.message}`, true);
        submitBtn.disabled = false;
        submitBtn.textContent = 'Start Analysis';
    }
});

function renderResults(data) {
    const resultsSection = document.getElementById('results-section');
    const resultsGrid = document.getElementById('results-grid');
    const submitBtn = document.getElementById('submitBtn');

    // Extract inner data if nested
    const finalReport = data.final_report || data;

    submitBtn.disabled = false;
    submitBtn.textContent = 'Start Analysis';
    resultsSection.classList.remove('hidden');

    let html = '';

    // Topics
    if (finalReport.topic_frequency && finalReport.topic_frequency.length > 0) {
        html += `<div class="result-card">
            <h3>Frequent Topics</h3>
            <div class="badge-container">
                ${finalReport.topic_frequency.map(t => `<span class="badge">${t.topic} (${t.frequency})</span>`).join('')}
            </div>
        </div>`;
    }

    // Recommendations
    if (finalReport.study_recommendations && finalReport.study_recommendations.length > 0) {
        html += `<div class="result-card">
            <h3>Study Recommendations</h3>
            <ul class="recommendations">
                ${finalReport.study_recommendations.map(r => `<li>${r}</li>`).join('')}
            </ul>
        </div>`;
    }

    // Lecturer Style
    if (finalReport.lecturer_style_summary && finalReport.lecturer_style_summary.length > 0) {
        html += `<div class="result-card">
            <h3>Lecturer Style</h3>
            <ul class="recommendations">
                ${finalReport.lecturer_style_summary.map(s => `<li>${s}</li>`).join('')}
            </ul>
        </div>`;
    }

    // Question Types
    if (finalReport.question_type_distribution) {
        html += `<div class="result-card">
            <h3>Question Distribution</h3>
            <div class="badge-container">
                ${Object.entries(finalReport.question_type_distribution).map(([type, pct]) =>
                    `<span class="badge">${type.replace('_', ' ')}: ${pct}</span>`
                ).join('')}
            </div>
        </div>`;
    }

    // If we have raw output instead
    if (data.raw_output) {
        html += `<div class="result-card">
            <h3>Raw Output</h3>
            <pre style="white-space: pre-wrap; font-size: 0.8rem; overflow-x: auto;">${data.raw_output}</pre>
        </div>`;
    }

    resultsGrid.innerHTML = html || '<div class="result-card"><p>No structured data found in the response.</p></div>';
}
