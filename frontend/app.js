// Configuration
const API_BASE_URL = 'https://paymenttrace-api.onrender.com';

// DOM Elements
const orderIdInput = document.getElementById('orderIdInput');
const diagnoseBtn = document.getElementById('diagnoseBtn');
const retryBtn = document.getElementById('retryBtn');
const loadingState = document.getElementById('loadingState');
const loadingMessage = document.getElementById('loadingMessage');
const errorState = document.getElementById('errorState');
const errorTitle = document.getElementById('errorTitle');
const errorMessage = document.getElementById('errorMessage');
const errorSuggestion = document.getElementById('errorSuggestion');
const resultsSection = document.getElementById('resultsSection');

// State
let currentOrderId = '';
let currentResponse = null;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    // Diagnose button click
    diagnoseBtn.addEventListener('click', handleDiagnose);
    
    // Retry button click
    retryBtn.addEventListener('click', () => {
        hideError();
        if (currentOrderId) {
            handleDiagnose();
        }
    });
    
    // Enter key in input
    orderIdInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !diagnoseBtn.disabled) {
            handleDiagnose();
        }
    });
    
    // Scenario buttons (new grid layout)
    document.querySelectorAll('.scenario-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const button = e.currentTarget;
            const orderId = button.dataset.orderId;
            orderIdInput.value = orderId;
            handleDiagnose();
        });
    });
    
    // Evidence tabs
    document.querySelectorAll('.evidence-tab').forEach(tab => {
        tab.addEventListener('click', (e) => {
            const category = e.target.closest('.evidence-tab').dataset.category;
            switchEvidenceTab(category);
        });
    });
    
    // Check backend status
    checkBackendStatus();
});

// Main handler
async function handleDiagnose() {
    const orderId = orderIdInput.value.trim();
    
    if (!orderId) {
        showError('Empty Order ID', 'Please enter an order ID to diagnose.', '');
        return;
    }
    
    currentOrderId = orderId;
    
    showLoading();
    hideError();
    hideResults();
    
    try {
        // Call API
        const response = await fetch(`${API_BASE_URL}/journeys/${orderId}/diagnosis`);
        
        if (!response.ok) {
            await handleErrorResponse(response);
            return;
        }
        
        const data = await response.json();
        currentResponse = data;
        
        // Render results
        hideLoading();
        renderResults(data);
        showResults();
        
    } catch (error) {
        hideLoading();
        if (error.name === 'TypeError' && error.message.includes('fetch')) {
            showError(
                'API Unavailable',
                'Unable to connect to the PaymentTrace backend.',
                `Please ensure the backend is running at ${API_BASE_URL}. Check /health endpoint.`
            );
        } else {
            showError(
                'Unexpected Error',
                error.message || 'An unexpected error occurred.',
                'Please try again or check the console for details.'
            );
        }
    }
}

// Check backend status
async function checkBackendStatus() {
    try {
        const response = await fetch(`${API_BASE_URL}/health`);
        if (response.ok) {
            updateStatusIndicator(true);
        } else {
            updateStatusIndicator(false);
        }
    } catch (error) {
        updateStatusIndicator(false);
    }
}

function updateStatusIndicator(connected) {
    const indicator = document.getElementById('statusIndicator');
    if (!indicator) return;
    
    const dot = indicator.querySelector('.status-dot');
    const text = indicator.querySelector('.status-text');
    
    if (connected) {
        dot.style.background = '#10b981';
        text.textContent = 'Backend Connected';
        indicator.style.background = 'rgba(16, 185, 129, 0.15)';
        indicator.style.borderColor = 'rgba(16, 185, 129, 0.3)';
        text.style.color = '#10b981';
    } else {
        dot.style.background = '#ef4444';
        text.textContent = 'Backend Offline';
        indicator.style.background = 'rgba(239, 68, 68, 0.15)';
        indicator.style.borderColor = 'rgba(239, 68, 68, 0.3)';
        text.style.color = '#ef4444';
    }
}

// Error response handler
async function handleErrorResponse(response) {
    hideLoading();
    
    const statusCode = response.status;
    let errorData;
    
    try {
        errorData = await response.json();
    } catch {
        errorData = { detail: 'Unknown error' };
    }
    
    const errorDetail = errorData.detail || 'Unknown error';
    
    switch (statusCode) {
        case 404:
            showError(
                'Order Not Found',
                `Order "${currentOrderId}" was not found in the database.`,
                'Please check the order ID and try again. Available test orders: order_scenario_a, order_scenario_b'
            );
            break;
        
        case 503:
            if (errorDetail.includes('LLM') || errorDetail.includes('GEMINI_API_KEY')) {
                showError(
                    'Diagnostic Service Unavailable',
                    'The LLM diagnostic service is not configured or temporarily unavailable.',
                    'GEMINI_API_KEY may not be configured. The deterministic journey reconstruction is available via /journeys/{order_id} endpoint.'
                );
            } else {
                showError(
                    'Service Temporarily Unavailable',
                    errorDetail,
                    'Please try again in a moment.'
                );
            }
            break;
        
        case 500:
            showError(
                'Diagnosis Generation Failed',
                errorDetail,
                'The backend encountered an error while generating the diagnosis. Check backend logs for details.'
            );
            break;
        
        default:
            showError(
                `Error ${statusCode}`,
                errorDetail,
                'Please try again or contact support.'
            );
    }
}

// Render all results
function renderResults(data) {
    renderOrderSummary(data);
    renderTimeline(data.journey);
    renderAttempts(data.journey);
    renderEvidence(data.journey);
    renderDiagnosis(data);
}

// Render order summary
function renderOrderSummary(data) {
    const { journey } = data;
    const { order } = journey;
    
    const summaryHtml = `
        <div class="summary-item">
            <div class="summary-label">Order ID</div>
            <div class="summary-value">${escapeHtml(journey.order_id)}</div>
        </div>
        <div class="summary-item">
            <div class="summary-label">Amount</div>
            <div class="summary-value">${formatAmount(order.amount, order.currency)}</div>
        </div>
        <div class="summary-item">
            <div class="summary-label">Merchant Status</div>
            <div class="summary-value status ${getStatusClass(order.merchant_status)}">
                ${escapeHtml(order.merchant_status || 'N/A')}
            </div>
        </div>
        <div class="summary-item">
            <div class="summary-label">Final Status</div>
            <div class="summary-value status ${getStatusClass(journey.final_status)}">
                ${escapeHtml(journey.final_status)}
            </div>
        </div>
        <div class="summary-item">
            <div class="summary-label">Attempts</div>
            <div class="summary-value">${journey.attempt_count}</div>
        </div>
        <div class="summary-item">
            <div class="summary-label">Retries</div>
            <div class="summary-value">${journey.retry_count}</div>
        </div>
        <div class="summary-item">
            <div class="summary-label">Duration</div>
            <div class="summary-value">${formatDuration(journey.journey_duration_seconds)}</div>
        </div>
        <div class="summary-item">
            <div class="summary-label">Events</div>
            <div class="summary-value">${journey.event_count}</div>
        </div>
    `;
    
    document.getElementById('orderSummary').innerHTML = summaryHtml;
}

// Render timeline
function renderTimeline(journey) {
    const { events } = journey;
    
    if (!events || events.length === 0) {
        document.getElementById('paymentTimeline').innerHTML = '<p class="evidence-empty">No events recorded</p>';
        return;
    }
    
    const timelineHtml = events.map(event => {
        const statusClass = getStatusClass(event.status);
        const errorHtml = event.error_code ? `
            <div class="timeline-error">
                Error: ${escapeHtml(event.error_code)}
            </div>
        ` : '';
        
        const metadataHtml = event.metadata ? `
            <div class="timeline-detail">
                <span class="timeline-detail-label">Metadata:</span>
                <span class="timeline-detail-value">${formatMetadata(event.metadata)}</span>
            </div>
        ` : '';
        
        return `
            <div class="timeline-item">
                <div class="timeline-marker ${statusClass}"></div>
                <div class="timeline-content">
                    <div class="timeline-header">
                        <div class="timeline-event-type">${escapeHtml(event.event_type)}</div>
                        <div class="timeline-timestamp">${formatTimestamp(event.timestamp)}</div>
                    </div>
                    <div class="timeline-details">
                        <div class="timeline-detail">
                            <span class="timeline-detail-label">Status:</span>
                            <span class="timeline-detail-value">${escapeHtml(event.status || 'N/A')}</span>
                        </div>
                        <div class="timeline-detail">
                            <span class="timeline-detail-label">Payment ID:</span>
                            <span class="timeline-detail-value">${escapeHtml(event.payment_id || 'N/A')}</span>
                        </div>
                        ${metadataHtml}
                    </div>
                    ${errorHtml}
                </div>
            </div>
        `;
    }).join('');
    
    document.getElementById('paymentTimeline').innerHTML = timelineHtml;
}

// Render attempts
function renderAttempts(journey) {
    const { attempts } = journey;
    
    if (!attempts || attempts.length === 0) {
        document.getElementById('paymentAttempts').innerHTML = '<p class="evidence-empty">No payment attempts recorded</p>';
        return;
    }
    
    const attemptsHtml = attempts.map(attempt => {
        const isRetry = attempt.attempt_number > 1;
        
        return `
            <div class="attempt-item ${isRetry ? 'retry' : ''}">
                <div class="attempt-header">
                    <div class="attempt-number">
                        Attempt ${attempt.attempt_number}${isRetry ? ' (Retry)' : ''}
                    </div>
                    <div class="attempt-status ${attempt.status.toLowerCase()}">
                        ${escapeHtml(attempt.status)}
                    </div>
                </div>
                <div class="attempt-details">
                    <div class="attempt-detail">
                        <span class="attempt-detail-label">Payment ID</span>
                        <span class="attempt-detail-value">${escapeHtml(attempt.payment_id)}</span>
                    </div>
                    <div class="attempt-detail">
                        <span class="attempt-detail-label">Method</span>
                        <span class="attempt-detail-value">${escapeHtml(attempt.method).toUpperCase()}</span>
                    </div>
                    <div class="attempt-detail">
                        <span class="attempt-detail-label">Created At</span>
                        <span class="attempt-detail-value">${formatTimestamp(attempt.created_at)}</span>
                    </div>
                </div>
            </div>
        `;
    }).join('');
    
    document.getElementById('paymentAttempts').innerHTML = `
        <div class="attempts-grid">
            ${attemptsHtml}
        </div>
    `;
}

// Render evidence
function renderEvidence(journey) {
    const { evidence } = journey;
    
    if (!evidence || evidence.length === 0) {
        document.getElementById('evidenceContent').innerHTML = '<p class="evidence-empty">No evidence available</p>';
        return;
    }
    
    // Store evidence by category
    window.evidenceByCategory = {
        PROVEN: evidence.filter(e => e.category === 'PROVEN'),
        DERIVED: evidence.filter(e => e.category === 'DERIVED'),
        INCONSISTENCY: evidence.filter(e => e.category === 'INCONSISTENCY'),
        UNKNOWN: evidence.filter(e => e.category === 'UNKNOWN')
    };
    
    // Show PROVEN by default
    switchEvidenceTab('PROVEN');
}

// Switch evidence tab
function switchEvidenceTab(category) {
    // Update active tab
    document.querySelectorAll('.evidence-tab').forEach(tab => {
        tab.classList.toggle('active', tab.dataset.category === category);
    });
    
    // Get evidence for category
    const evidence = window.evidenceByCategory?.[category] || [];
    
    // Render evidence list
    if (evidence.length === 0) {
        document.getElementById('evidenceContent').innerHTML = `
            <p class="evidence-empty">No ${category} evidence</p>
        `;
        return;
    }
    
    const evidenceHtml = evidence.map(item => `
        <div class="evidence-item ${item.category}">
            <div class="evidence-statement">${escapeHtml(item.statement)}</div>
            <div class="evidence-source">Source: ${escapeHtml(item.source || 'N/A')}</div>
        </div>
    `).join('');
    
    document.getElementById('evidenceContent').innerHTML = `
        <div class="evidence-list">
            ${evidenceHtml}
        </div>
    `;
}

// Render diagnosis
function renderDiagnosis(data) {
    const { diagnosis, llm_model } = data;
    
    // Update model badge
    if (llm_model) {
        document.getElementById('llmModel').textContent = llm_model;
    }
    
    if (!diagnosis) {
        document.getElementById('diagnosisContent').innerHTML = '<p class="evidence-empty">No diagnosis available</p>';
        return;
    }
    
    const diagnosisHtml = `
        ${renderDiagnosisSection('Summary', diagnosis.summary)}
        ${renderDiagnosisSection('What Happened', diagnosis.what_happened)}
        ${renderDiagnosisList('What Is Known', diagnosis.what_is_known)}
        ${renderDiagnosisList('What Cannot Be Determined', diagnosis.what_cannot_be_determined)}
        ${renderDiagnosisSection('Recommended Action', diagnosis.recommended_action)}
    `;
    
    document.getElementById('diagnosisContent').innerHTML = diagnosisHtml;
}

// Render diagnosis section
function renderDiagnosisSection(title, content) {
    if (!content) return '';
    
    return `
        <div class="diagnosis-section">
            <h3 class="diagnosis-section-title">${escapeHtml(title)}</h3>
            <div class="diagnosis-section-content">
                <p>${escapeHtml(content)}</p>
            </div>
        </div>
    `;
}

// Render diagnosis list
function renderDiagnosisList(title, items) {
    if (!items || items.length === 0) return '';
    
    const listHtml = items.map(item => `<li>${escapeHtml(item)}</li>`).join('');
    
    return `
        <div class="diagnosis-section">
            <h3 class="diagnosis-section-title">${escapeHtml(title)}</h3>
            <div class="diagnosis-section-content">
                <ul class="diagnosis-list">
                    ${listHtml}
                </ul>
            </div>
        </div>
    `;
}

// UI State Management
function showLoading() {
    loadingState.classList.remove('hidden');
    diagnoseBtn.disabled = true;
}

function hideLoading() {
    loadingState.classList.add('hidden');
    diagnoseBtn.disabled = false;
}

function updateLoadingMessage(message) {
    loadingMessage.textContent = message;
}

function showError(title, message, suggestion) {
    errorTitle.textContent = title;
    errorMessage.textContent = message;
    errorSuggestion.textContent = suggestion;
    errorState.classList.remove('hidden');
}

function hideError() {
    errorState.classList.add('hidden');
}

function showResults() {
    resultsSection.classList.remove('hidden');
}

function hideResults() {
    resultsSection.classList.add('hidden');
}

// Utility Functions
function escapeHtml(text) {
    if (text === null || text === undefined) return '';
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return String(text).replace(/[&<>"']/g, m => map[m]);
}

function formatAmount(amount, currency) {
    // Amount is in smallest currency unit (e.g., paise for INR)
    const value = (amount / 100).toFixed(2);
    return `${currency} ${value}`;
}

function formatDuration(seconds) {
    if (seconds < 60) {
        return `${seconds.toFixed(1)}s`;
    }
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.floor(seconds % 60);
    return `${minutes}m ${remainingSeconds}s`;
}

function formatTimestamp(timestamp) {
    if (!timestamp) return 'N/A';
    
    try {
        const date = new Date(timestamp);
        return date.toLocaleString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            hour12: false
        });
    } catch {
        return timestamp;
    }
}

function formatMetadata(metadata) {
    if (!metadata || typeof metadata !== 'object') return 'N/A';
    
    try {
        return JSON.stringify(metadata);
    } catch {
        return String(metadata);
    }
}

function getStatusClass(status) {
    if (!status) return '';
    
    const statusLower = status.toLowerCase();
    
    if (statusLower.includes('captured') || statusLower.includes('paid') || statusLower.includes('success')) {
        return 'success';
    }
    if (statusLower.includes('failed') || statusLower.includes('error')) {
        return 'failed';
    }
    if (statusLower.includes('pending') || statusLower.includes('authorized')) {
        return 'pending';
    }
    if (statusLower.includes('created')) {
        return 'created';
    }
    
    return '';
}
