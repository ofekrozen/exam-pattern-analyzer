document.getElementById('analyze-form').addEventListener('submit', async (e) => {
    e.preventDefault();

    const driveUrl = document.getElementById('driveUrl').value;
    const lecturerName = document.getElementById('lecturerName').value;
    const courseName = document.getElementById('courseName').value;
    const syllabus = document.getElementById('syllabus').value;

    const submitBtn = document.getElementById('submitBtn');
    const terminalSection = document.getElementById('terminal-section');
    const terminalOutput = document.getElementById('terminal-output');
    const resultsSection = document.getElementById('results-section');
    const topNav = document.getElementById('top-nav');
    const resultsContent = document.getElementById('results-content');

    // Reset UI
    submitBtn.disabled = true;
    submitBtn.textContent = 'Analyzing...';
    terminalSection.classList.remove('hidden');
    resultsSection.classList.add('hidden');
    terminalOutput.innerHTML = '';
    topNav.innerHTML = '';
    resultsContent.innerHTML = '';

    const addLog = (msg, isError = false) => {
        const div = document.createElement('div');
        div.textContent = `> ${msg}`;
        if (isError) div.style.color = '#f87171';
        terminalOutput.appendChild(div);
        terminalOutput.scrollTop = terminalOutput.scrollHeight;
    };

    try {
        const apiUrl = `http://localhost:8000/api/analyze/stream?drive_folder_url=${encodeURIComponent(driveUrl)}&lecturer_name=${encodeURIComponent(lecturerName)}&course_name=${encodeURIComponent(courseName)}&syllabus=${encodeURIComponent(syllabus)}`;

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

            const events = buffer.split('\n\n');
            buffer = events.pop();

            for (const eventString of events) {
                if (!eventString.trim()) continue;

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
                        addLog(typeof parsedData === 'object' ? (parsedData.message || parsedData.data || JSON.stringify(parsedData)) : parsedData);
                    } else if (eventType === 'error') {
                        addLog(typeof parsedData === 'object' ? (parsedData.error || parsedData.data || JSON.stringify(parsedData)) : parsedData, true);
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

let currentReportData = null;

function renderResults(data) {
    const resultsSection = document.getElementById('results-section');
    const topNav = document.getElementById('top-nav');
    const resultsContent = document.getElementById('results-content');
    const submitBtn = document.getElementById('submitBtn');

    currentReportData = data.final_report || data;

    submitBtn.disabled = false;
    submitBtn.textContent = 'Start Analysis';
    resultsSection.classList.remove('hidden');

    if (currentReportData.raw_output) {
        resultsContent.innerHTML = `<div class="result-card">
            <h3>Raw Output</h3>
            <pre style="white-space: pre-wrap; font-size: 0.8rem; overflow-x: auto;">${currentReportData.raw_output}</pre>
        </div>`;
        return;
    }

    // Build Navigation
    let navHtml = `<button class="nav-btn active" onclick="showTab('summary', this)">Summary</button>`;

    if (currentReportData.exams && Array.isArray(currentReportData.exams)) {
        currentReportData.exams.forEach((exam, index) => {
            const name = exam.file_name || exam.exam_name || `Exam ${index + 1}`;
            navHtml += `<button class="nav-btn" onclick="showTab('exam-${index}', this)">${name}</button>`;
        });
    }

    topNav.innerHTML = navHtml;

    // Render Summary by default
    showTab('summary', topNav.firstElementChild);
}

function showTab(tabId, btnElement) {
    const topNav = document.getElementById('top-nav');
    const resultsContent = document.getElementById('results-content');

    // Update active button state
    Array.from(topNav.children).forEach(btn => btn.classList.remove('active'));
    if (btnElement) btnElement.classList.add('active');

    let html = '';

    if (tabId === 'summary') {
        const summaryText = currentReportData.summary || "No summary available.";
        html = `<div class="result-card">
            <h3>Professor's Style & Study Report</h3>
            <div style="white-space: pre-wrap; line-height: 1.6;">${summaryText}</div>
        </div>`;
    } else if (tabId.startsWith('exam-')) {
        const index = parseInt(tabId.split('-')[1]);
        const exam = currentReportData.exams[index];
        const name = exam.file_name || exam.exam_name || `Exam ${index + 1}`;

        html = `<div class="result-card">
            <h3>${name}</h3>`;

        if (exam.questions && exam.questions.length > 0) {
            exam.questions.forEach(q => {
                const tagsHtml = q.tags ? q.tags.map(t => `<span class="badge">${t}</span>`).join('') : '';
                html += `
                <div class="question-card">
                    <div class="question-header">
                        <h4>Question ${q.q_number}</h4>
                        ${q.type ? `<span style="font-size: 0.8rem; color: #94a3b8;">${q.type.replace('_', ' ')}</span>` : ''}
                    </div>
                    <div class="question-body">${q.q_content || "No content extracted."}</div>
                    <div class="badge-container" style="margin-top: 0.5rem;">${tagsHtml}</div>
                </div>`;
            });
        } else {
            html += `<p>No questions extracted for this exam.</p>`;
        }
        html += `</div>`;
    }

    resultsContent.innerHTML = html;
}
