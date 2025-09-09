// frontend/js/main.js

// --- Configuration ---
const API_BASE_URL = "http://127.0.0.1:5000/api";

// --- DOM Elements ---
const loadingOverlay = document.getElementById('loading-overlay');
const loadingText = document.getElementById('loading-text');

// --- Helper Functions ---
function showLoading(message = "Đang xử lý...") {
    loadingText.textContent = message;
    loadingOverlay.classList.remove('hidden');
}

function hideLoading() {
    loadingOverlay.classList.add('hidden');
}

async function apiCall(endpoint, body, method = 'POST') {
    try {
        const response = await fetch(`${API_BASE_URL}${endpoint}`, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `Lỗi HTTP: ${response.status}`);
        }
        return response.json();
    } catch (error) {
        console.error(`API Call Error (${endpoint}):`, error);
        alert(`Đã xảy ra lỗi: ${error.message}`);
        return null; // Return null on failure
    }
}

// --- Tab Switching Logic ---
function openTab(evt, tabName) {
    document.querySelectorAll(".tab-content").forEach(tab => tab.style.display = "none");
    document.querySelectorAll(".tab-link").forEach(link => link.classList.remove("active"));
    document.getElementById(tabName).style.display = "block";
    evt.currentTarget.classList.add("active");
}
document.addEventListener('DOMContentLoaded', () => document.querySelector('.tab-link').click());


// --- Shared Functions to get user settings ---
function getAuthInfo() {
    return {
        username: document.getElementById('username').value,
        password: document.getElementById('password').value, // In a real app, never send password like this.
    };
}

function getSimulationSettings() {
    return {
        sheetId: document.getElementById('sheet-id').value,
        region: document.getElementById('sim-region').value,
        universe: document.getElementById('sim-universe').value,
        decay: parseInt(document.getElementById('sim-decay').value, 10),
    };
}


// --- Tab 1: AI Generator ---
document.getElementById('generate-ai-btn').addEventListener('click', async () => {
    const prompt = document.getElementById('ai-prompt').value;
    if (!prompt) return alert("Vui lòng nhập mô tả ý tưởng.");
    
    showLoading("AI đang suy nghĩ...");
    const data = await apiCall('/generate-alpha', { prompt });
    hideLoading();
    
    if (data) {
        document.getElementById('ai-result').textContent = data.alpha || 'Không tạo được alpha.';
    }
});


// --- Tab 2: Exhaustive Search ---
document.getElementById('search-btn').addEventListener('click', async () => {
    const baseAlpha = document.getElementById('base-alpha-input').value;
    if (!baseAlpha) return alert("Vui lòng nhập alpha gốc.");

    const options = {
        replace_fields: document.getElementById('opt-replace-fields').checked,
        replace_operators: document.getElementById('opt-replace-operators').checked,
        replace_day_group: document.getElementById('opt-replace-day-group').checked,
    };

    if (!Object.values(options).some(v => v)) return alert("Vui lòng chọn ít nhất một tùy chọn vét cạn.");

    showLoading("Đang vét cạn các biểu thức...");
    const data = await apiCall('/exhaustive-search', { alpha: baseAlpha, options });
    hideLoading();
    
    if (data && data.generated_alphas) {
        const resultTextArea = document.getElementById('search-result');
        resultTextArea.value = data.generated_alphas.join('\n');
        document.getElementById('alpha-count').textContent = data.generated_alphas.length;
    }
});

document.getElementById('send-to-simulate-btn').addEventListener('click', () => {
    const alphaList = document.getElementById('search-result').value;
    if (!alphaList) return alert("Không có danh sách alpha nào để gửi đi.");
    
    document.getElementById('alpha-list-input').value = alphaList;
    document.querySelector('button[onclick*="tab-simulation"]').click();
});


// --- Tab 3: Simulation ---
document.getElementById('simulate-btn').addEventListener('click', async () => {
    const alphaList = document.getElementById('alpha-list-input').value.split('\n').filter(line => line.trim());
    if (alphaList.length === 0) return alert("Vui lòng nhập danh sách alpha.");
    
    const auth = getAuthInfo();
    if (!auth.username) return alert("Vui lòng nhập tài khoản WorldQuant Brain.");

    showLoading(`Đang mô phỏng ${alphaList.length} alpha...`);
    const payload = {
        alphas: alphaList,
        settings: getSimulationSettings(),
        auth: auth,
    };
    const data = await apiCall('/simulate-list', payload);
    hideLoading();
    
    if (data && data.results) {
        renderSimulationResults(data.results);
    }
});

function renderSimulationResults(results) {
    const tableContainer = document.getElementById('simulation-result-table');
    if (!results || results.length === 0) {
        tableContainer.innerHTML = '<p>Không có kết quả trả về.</p>';
        return;
    }
    
    // Check for error on all alphas
    if (results[0].error) {
        tableContainer.innerHTML = `<p style="color: red; font-weight: bold;">Lỗi: ${results[0].error} (Alpha: ${results[0].alpha})</p>`;
        return;
    }

    const headers = Object.keys(results[0]);
    const table = document.createElement('table');
    
    // Header
    const thead = table.createTHead();
    const headerRow = thead.insertRow();
    headers.forEach(headerText => {
        const th = document.createElement('th');
        th.textContent = headerText.toUpperCase();
        headerRow.appendChild(th);
    });

    // Body
    const tbody = table.createTBody();
    results.forEach(rowData => {
        const row = tbody.insertRow();
        headers.forEach(header => {
            const cell = row.insertCell();
            let value = rowData[header];
            if (typeof value === 'number') {
                value = value.toFixed(3); // Display numbers with 3 decimal places
            }
            cell.textContent = value;
            if (header === 'sharpe' || header === 'fitness') {
                 if (rowData[header] > 2.0) cell.style.backgroundColor = '#d4edda'; // green
                 if (rowData[header] < 0.5) cell.style.backgroundColor = '#f8d7da'; // red
            }
        });
    });

    tableContainer.innerHTML = '';
    tableContainer.appendChild(table);
}