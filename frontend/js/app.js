/**
 * IEEE Report Restructurer - Frontend Application
 * Handles file upload, processing progress, and document preview
 */

// ===========================================
// Configuration
// ===========================================
// Use relative URL so it works when served from backend
const API_BASE_URL = '/api';
const POLLING_INTERVAL = 1500; // ms

// ===========================================
// State Management
// ===========================================
const state = {
    documentId: null,
    selectedFile: null,
    isProcessing: false,
    isEditing: false,
    sections: [],
    context: null,
    stats: null,
    pollingTimer: null,
};

// ===========================================
// DOM Elements
// ===========================================
const elements = {
    // Sections
    uploadSection: document.getElementById('upload-section'),
    processingSection: document.getElementById('processing-section'),
    previewSection: document.getElementById('preview-section'),
    errorSection: document.getElementById('error-section'),
    
    // Upload
    uploadZone: document.getElementById('upload-zone'),
    fileInput: document.getElementById('file-input'),
    fileInfo: document.getElementById('file-info'),
    fileName: document.getElementById('file-name'),
    fileSize: document.getElementById('file-size'),
    btnRemove: document.getElementById('btn-remove'),
    btnProcess: document.getElementById('btn-process'),
    
    // Processing
    processingTitle: document.getElementById('processing-title'),
    processingStatus: document.getElementById('processing-status'),
    progressFill: document.getElementById('progress-fill'),
    progressText: document.getElementById('progress-text'),
    steps: {
        1: document.getElementById('step-1'),
        2: document.getElementById('step-2'),
        3: document.getElementById('step-3'),
        4: document.getElementById('step-4'),
        5: document.getElementById('step-5'),
    },
    
    // Preview
    navPreview: document.getElementById('nav-preview'),
    btnEditToggle: document.getElementById('btn-edit-toggle'),
    btnDownloadDocx: document.getElementById('btn-download-docx'),
    btnDownloadPdf: document.getElementById('btn-download-pdf'),
    btnStartOver: document.getElementById('btn-start-over'),
    btnRegenerate: document.getElementById('btn-regenerate'),
    sectionsContainer: document.getElementById('sections-container'),
    
    // Stats
    statSections: document.getElementById('stat-sections'),
    statWords: document.getElementById('stat-words'),
    statBalanced: document.getElementById('stat-balanced'),
    
    // Context
    ctxTitle: document.getElementById('ctx-title'),
    ctxDomain: document.getElementById('ctx-domain'),
    ctxObjective: document.getElementById('ctx-objective'),
    ctxKeywords: document.getElementById('ctx-keywords'),
    
    // Error
    errorMessage: document.getElementById('error-message'),
    btnTryAgain: document.getElementById('btn-try-again'),
};

// ===========================================
// Initialization
// ===========================================
function init() {
    setupEventListeners();
}

function setupEventListeners() {
    // Upload zone
    elements.uploadZone.addEventListener('click', () => elements.fileInput.click());
    elements.uploadZone.addEventListener('dragover', handleDragOver);
    elements.uploadZone.addEventListener('dragleave', handleDragLeave);
    elements.uploadZone.addEventListener('drop', handleDrop);
    elements.fileInput.addEventListener('change', handleFileSelect);
    
    // File actions
    elements.btnRemove.addEventListener('click', removeFile);
    elements.btnProcess.addEventListener('click', processDocument);
    
    // Preview actions
    elements.btnEditToggle.addEventListener('click', toggleEditMode);
    elements.btnDownloadDocx.addEventListener('click', () => downloadDocument('docx'));
    elements.btnDownloadPdf.addEventListener('click', () => downloadDocument('pdf'));
    elements.btnStartOver.addEventListener('click', startOver);
    elements.btnRegenerate.addEventListener('click', regenerateDocument);
    
    // Error actions
    elements.btnTryAgain.addEventListener('click', startOver);
}

// ===========================================
// File Upload Handlers
// ===========================================
function handleDragOver(e) {
    e.preventDefault();
    elements.uploadZone.classList.add('dragover');
}

function handleDragLeave(e) {
    e.preventDefault();
    elements.uploadZone.classList.remove('dragover');
}

function handleDrop(e) {
    e.preventDefault();
    elements.uploadZone.classList.remove('dragover');
    
    const files = e.dataTransfer.files;
    if (files.length > 0) {
        selectFile(files[0]);
    }
}

function handleFileSelect(e) {
    const files = e.target.files;
    if (files.length > 0) {
        selectFile(files[0]);
    }
}

function selectFile(file) {
    // Validate file type
    const validTypes = ['.docx', '.pdf'];
    const ext = '.' + file.name.split('.').pop().toLowerCase();
    
    if (!validTypes.includes(ext)) {
        alert('Invalid file type. Please upload a DOCX or PDF file.');
        return;
    }
    
    // Validate file size (50MB max)
    const maxSize = 50 * 1024 * 1024;
    if (file.size > maxSize) {
        alert('File too large. Maximum size is 50MB.');
        return;
    }
    
    state.selectedFile = file;
    
    // Update UI
    elements.fileName.textContent = file.name;
    elements.fileSize.textContent = formatFileSize(file.size);
    elements.fileInfo.style.display = 'flex';
    elements.btnProcess.disabled = false;
}

function removeFile(e) {
    e.stopPropagation();
    state.selectedFile = null;
    elements.fileInput.value = '';
    elements.fileInfo.style.display = 'none';
    elements.btnProcess.disabled = true;
}

// ===========================================
// Document Processing
// ===========================================
async function processDocument() {
    if (!state.selectedFile) return;
    
    try {
        // Show processing indicator on button
        elements.btnProcess.disabled = true;
        elements.btnProcess.querySelector('.btn-text').style.display = 'none';
        elements.btnProcess.querySelector('.btn-loader').style.display = 'block';
        
        // Upload file
        const formData = new FormData();
        formData.append('file', state.selectedFile);
        
        const uploadResponse = await fetch(`${API_BASE_URL}/upload`, {
            method: 'POST',
            body: formData,
        });
        
        if (!uploadResponse.ok) {
            const error = await uploadResponse.json();
            throw new Error(error.detail || 'Upload failed');
        }
        
        const uploadResult = await uploadResponse.json();
        state.documentId = uploadResult.id;
        
        // Start processing
        const processResponse = await fetch(`${API_BASE_URL}/process/${state.documentId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({}),
        });
        
        if (!processResponse.ok) {
            const error = await processResponse.json();
            throw new Error(error.detail || 'Processing failed to start');
        }
        
        // Switch to processing view
        showSection('processing');
        state.isProcessing = true;
        
        // Start polling for status
        startPolling();
        
    } catch (error) {
        console.error('Processing error:', error);
        showError(error.message);
    }
}

function startPolling() {
    // Clear any existing timer
    if (state.pollingTimer) {
        clearInterval(state.pollingTimer);
    }
    
    // Poll immediately and then at intervals
    checkStatus();
    state.pollingTimer = setInterval(checkStatus, POLLING_INTERVAL);
}

async function checkStatus() {
    if (!state.documentId) return;
    
    try {
        const response = await fetch(`${API_BASE_URL}/status/${state.documentId}`);
        
        if (!response.ok) {
            throw new Error('Failed to get status');
        }
        
        const status = await response.json();
        updateProcessingUI(status);
        
        // Check if processing is complete
        if (status.status === 'complete') {
            stopPolling();
            await loadPreviewData();
            showSection('preview');
        } else if (status.status === 'error') {
            stopPolling();
            showError(status.errors?.join(', ') || 'Processing failed');
        }
        
    } catch (error) {
        console.error('Status check error:', error);
    }
}

function stopPolling() {
    if (state.pollingTimer) {
        clearInterval(state.pollingTimer);
        state.pollingTimer = null;
    }
    state.isProcessing = false;
}

function updateProcessingUI(status) {
    // Update progress bar
    elements.progressFill.style.width = `${status.progress_percent}%`;
    elements.progressText.textContent = `${status.progress_percent}%`;
    
    // Update status message
    elements.processingStatus.textContent = status.status_message || 'Processing...';
    
    // Update steps
    const stepMap = {
        'uploaded': 0,
        'parsing': 1,
        'extracting_context': 2,
        'rewriting': 3,
        'structuring': 4,
        'formatting': 5,
        'complete': 5,
    };
    
    const currentStep = stepMap[status.status] || 0;
    
    for (let i = 1; i <= 5; i++) {
        const step = elements.steps[i];
        step.classList.remove('active', 'complete');
        
        if (i < currentStep) {
            step.classList.add('complete');
        } else if (i === currentStep) {
            step.classList.add('active');
        }
    }
}

// ===========================================
// Preview Data Loading
// ===========================================
async function loadPreviewData() {
    try {
        // Load sections
        const sectionsResponse = await fetch(`${API_BASE_URL}/sections/${state.documentId}`);
        if (sectionsResponse.ok) {
            state.sections = await sectionsResponse.json();
            renderSections();
        }
        
        // Load context
        const contextResponse = await fetch(`${API_BASE_URL}/context/${state.documentId}`);
        if (contextResponse.ok) {
            state.context = await contextResponse.json();
            renderContext();
        }
        
        // Load stats
        const statsResponse = await fetch(`${API_BASE_URL}/stats/${state.documentId}`);
        if (statsResponse.ok) {
            state.stats = await statsResponse.json();
            renderStats();
        }
        
        // Show preview navigation
        elements.navPreview.style.display = 'inline-block';
        
    } catch (error) {
        console.error('Error loading preview data:', error);
    }
}

function renderSections() {
    elements.sectionsContainer.innerHTML = '';
    
    state.sections.forEach((section, index) => {
        const card = createSectionCard(section, index);
        elements.sectionsContainer.appendChild(card);
    });
}

function createSectionCard(section, index) {
    const card = document.createElement('div');
    card.className = 'section-card';
    card.id = `section-card-${section.id}`;
    
    // Determine word count status
    let wordCountClass = 'balanced';
    if (section.word_count < 200) {
        wordCountClass = 'under';
    } else if (section.word_count > 400) {
        wordCountClass = 'over';
    }
    
    // Format IEEE number
    const numberDisplay = section.ieee_number || '';
    
    card.innerHTML = `
        <div class="section-header" onclick="toggleSection('${section.id}')">
            <h4>
                <span class="section-number">${numberDisplay}</span>
                ${section.title}
            </h4>
            <div class="section-meta">
                <span class="word-count ${wordCountClass}">${section.word_count} words</span>
                <button class="section-toggle">▼</button>
            </div>
        </div>
        <div class="section-content" id="section-content-${section.id}">
            <p class="section-text">${escapeHtml(section.content)}</p>
            <div class="section-actions" style="display: none;">
                <button class="btn-secondary" onclick="cancelEdit('${section.id}')">Cancel</button>
                <button class="btn-primary" onclick="saveSection('${section.id}')">Save</button>
            </div>
        </div>
    `;
    
    return card;
}

function renderContext() {
    if (!state.context) return;
    
    elements.ctxTitle.textContent = state.context.project_title || '-';
    elements.ctxDomain.textContent = state.context.domain || '-';
    elements.ctxObjective.textContent = state.context.objective || '-';
    elements.ctxKeywords.textContent = state.context.keywords?.join(', ') || '-';
}

function renderStats() {
    if (!state.stats) return;
    
    elements.statSections.textContent = state.stats.total_sections || 0;
    elements.statWords.textContent = state.stats.total_words || 0;
    elements.statBalanced.textContent = state.stats.sections_in_range || 0;
}

// ===========================================
// Section Interactions
// ===========================================
window.toggleSection = function(sectionId) {
    const card = document.getElementById(`section-card-${sectionId}`);
    card.classList.toggle('expanded');
};

function toggleEditMode() {
    state.isEditing = !state.isEditing;
    elements.btnEditToggle.querySelector('span').textContent = 
        state.isEditing ? 'View Mode' : 'Edit Sections';
    elements.btnRegenerate.style.display = state.isEditing ? 'inline-flex' : 'none';
    
    // Convert all sections to edit/view mode
    state.sections.forEach(section => {
        const contentEl = document.getElementById(`section-content-${section.id}`);
        const textEl = contentEl.querySelector('.section-text, .section-textarea');
        const actionsEl = contentEl.querySelector('.section-actions');
        
        if (state.isEditing) {
            // Convert to textarea
            const textarea = document.createElement('textarea');
            textarea.className = 'section-textarea';
            textarea.value = section.content;
            textarea.id = `textarea-${section.id}`;
            textEl.replaceWith(textarea);
            actionsEl.style.display = 'flex';
        } else {
            // Convert back to paragraph
            const p = document.createElement('p');
            p.className = 'section-text';
            p.textContent = section.content;
            textEl.replaceWith(p);
            actionsEl.style.display = 'none';
        }
    });
}

window.cancelEdit = function(sectionId) {
    const section = state.sections.find(s => s.id === sectionId);
    if (!section) return;
    
    const textarea = document.getElementById(`textarea-${sectionId}`);
    if (textarea) {
        textarea.value = section.content;
    }
};

window.saveSection = async function(sectionId) {
    const textarea = document.getElementById(`textarea-${sectionId}`);
    if (!textarea) return;
    
    const newContent = textarea.value.trim();
    if (!newContent) {
        alert('Section content cannot be empty');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/sections/${state.documentId}/${sectionId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content: newContent }),
        });
        
        if (!response.ok) {
            throw new Error('Failed to save section');
        }
        
        const result = await response.json();
        
        // Update local state
        const section = state.sections.find(s => s.id === sectionId);
        if (section) {
            section.content = newContent;
            section.word_count = result.word_count;
        }
        
        // Update word count display
        const card = document.getElementById(`section-card-${sectionId}`);
        const wordCountEl = card.querySelector('.word-count');
        wordCountEl.textContent = `${result.word_count} words`;
        
        // Update word count class
        wordCountEl.className = 'word-count';
        if (result.word_count < 200) {
            wordCountEl.classList.add('under');
        } else if (result.word_count > 400) {
            wordCountEl.classList.add('over');
        } else {
            wordCountEl.classList.add('balanced');
        }
        
        alert('Section saved successfully!');
        
    } catch (error) {
        console.error('Save error:', error);
        alert('Failed to save section: ' + error.message);
    }
};

async function regenerateDocument() {
    try {
        elements.btnRegenerate.disabled = true;
        elements.btnRegenerate.textContent = 'Regenerating...';
        
        const response = await fetch(`${API_BASE_URL}/regenerate/${state.documentId}`, {
            method: 'POST',
        });
        
        if (!response.ok) {
            throw new Error('Regeneration failed');
        }
        
        // Poll for completion
        let complete = false;
        while (!complete) {
            await new Promise(resolve => setTimeout(resolve, 1000));
            
            const statusResponse = await fetch(`${API_BASE_URL}/status/${state.documentId}`);
            const status = await statusResponse.json();
            
            if (status.status === 'complete') {
                complete = true;
            } else if (status.status === 'error') {
                throw new Error(status.errors?.join(', ') || 'Regeneration failed');
            }
        }
        
        alert('Document regenerated successfully!');
        
    } catch (error) {
        console.error('Regeneration error:', error);
        alert('Failed to regenerate: ' + error.message);
    } finally {
        elements.btnRegenerate.disabled = false;
        elements.btnRegenerate.textContent = 'Regenerate Document';
    }
}

// ===========================================
// Download
// ===========================================
async function downloadDocument(format) {
    if (!state.documentId) return;
    
    try {
        const response = await fetch(`${API_BASE_URL}/download/${state.documentId}?format=${format}`);
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Download failed');
        }
        
        // Get filename from response headers or generate one
        const contentDisposition = response.headers.get('Content-Disposition');
        let filename = `IEEE_Document.${format}`;
        if (contentDisposition) {
            const match = contentDisposition.match(/filename="?(.+)"?/);
            if (match) {
                filename = match[1];
            }
        }
        
        // Download file
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        
    } catch (error) {
        console.error('Download error:', error);
        alert('Download failed: ' + error.message);
    }
}

// ===========================================
// Navigation & UI
// ===========================================
function showSection(section) {
    // Hide all sections
    elements.uploadSection.style.display = 'none';
    elements.processingSection.style.display = 'none';
    elements.previewSection.style.display = 'none';
    elements.errorSection.style.display = 'none';
    
    // Show requested section
    switch (section) {
        case 'upload':
            elements.uploadSection.style.display = 'block';
            break;
        case 'processing':
            elements.processingSection.style.display = 'block';
            break;
        case 'preview':
            elements.previewSection.style.display = 'block';
            break;
        case 'error':
            elements.errorSection.style.display = 'block';
            break;
    }
}

function showError(message) {
    elements.errorMessage.textContent = message || 'An unexpected error occurred.';
    showSection('error');
}

function startOver() {
    // Reset state
    stopPolling();
    state.documentId = null;
    state.selectedFile = null;
    state.isProcessing = false;
    state.isEditing = false;
    state.sections = [];
    state.context = null;
    state.stats = null;
    
    // Reset UI
    elements.fileInput.value = '';
    elements.fileInfo.style.display = 'none';
    elements.btnProcess.disabled = true;
    elements.btnProcess.querySelector('.btn-text').style.display = 'inline';
    elements.btnProcess.querySelector('.btn-loader').style.display = 'none';
    elements.progressFill.style.width = '0%';
    elements.progressText.textContent = '0%';
    elements.navPreview.style.display = 'none';
    elements.sectionsContainer.innerHTML = '';
    
    // Reset steps
    for (let i = 1; i <= 5; i++) {
        elements.steps[i].classList.remove('active', 'complete');
    }
    
    showSection('upload');
}

// ===========================================
// Utility Functions
// ===========================================
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ===========================================
// Initialize on DOM Ready
// ===========================================
document.addEventListener('DOMContentLoaded', init);
