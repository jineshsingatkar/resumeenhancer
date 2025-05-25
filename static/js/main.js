// AI Resume Modifier - Frontend JavaScript

document.addEventListener('DOMContentLoaded', function() {
    initializeFormHandling();
    initializeFileUpload();
    initializeTooltips();
});

/**
 * Initialize form handling and validation
 */
function initializeFormHandling() {
    const form = document.getElementById('resumeForm');
    const submitBtn = document.getElementById('submitBtn');
    
    if (form && submitBtn) {
        form.addEventListener('submit', function(e) {
            if (!validateForm()) {
                e.preventDefault();
                return false;
            }
            
            showProcessingState();
        });
    }
}

/**
 * Validate form inputs
 */
function validateForm() {
    const jobDescription = document.getElementById('job_description');
    const resumeFile = document.getElementById('resume_file');
    let isValid = true;
    
    // Clear previous error states
    clearErrorStates();
    
    // Validate job description
    if (!jobDescription.value.trim()) {
        showFieldError(jobDescription, 'Please provide a job description.');
        isValid = false;
    } else if (jobDescription.value.trim().length < 50) {
        showFieldError(jobDescription, 'Job description should be at least 50 characters long.');
        isValid = false;
    }
    
    // Validate file upload
    if (!resumeFile.files.length) {
        showFieldError(resumeFile, 'Please select a resume file.');
        isValid = false;
    } else {
        const file = resumeFile.files[0];
        
        // Check file type
        if (!file.name.toLowerCase().endsWith('.docx')) {
            showFieldError(resumeFile, 'Please upload a DOCX file.');
            isValid = false;
        }
        
        // Check file size (16MB limit)
        if (file.size > 16 * 1024 * 1024) {
            showFieldError(resumeFile, 'File size must be less than 16MB.');
            isValid = false;
        }
    }
    
    return isValid;
}

/**
 * Show error state for a form field
 */
function showFieldError(field, message) {
    field.classList.add('is-invalid');
    
    // Remove existing error message
    const existingError = field.parentNode.querySelector('.invalid-feedback');
    if (existingError) {
        existingError.remove();
    }
    
    // Add new error message
    const errorDiv = document.createElement('div');
    errorDiv.className = 'invalid-feedback';
    errorDiv.innerHTML = `<i class="fas fa-exclamation-circle me-1"></i>${message}`;
    field.parentNode.appendChild(errorDiv);
}

/**
 * Clear all error states from form
 */
function clearErrorStates() {
    const invalidFields = document.querySelectorAll('.is-invalid');
    const errorMessages = document.querySelectorAll('.invalid-feedback');
    
    invalidFields.forEach(field => field.classList.remove('is-invalid'));
    errorMessages.forEach(msg => msg.remove());
}

/**
 * Show processing state when form is submitted
 */
function showProcessingState() {
    const submitBtn = document.getElementById('submitBtn');
    const form = document.getElementById('resumeForm');
    
    if (submitBtn) {
        // Disable button and show loading state
        submitBtn.disabled = true;
        submitBtn.classList.add('loading');
        submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status"></span>Processing Resume...';
    }
    
    if (form) {
        // Disable form inputs
        const inputs = form.querySelectorAll('input, textarea, button');
        inputs.forEach(input => input.disabled = true);
    }
    
    // Show processing indicator
    showProcessingIndicator();
}

/**
 * Show processing indicator
 */
function showProcessingIndicator() {
    // Create processing indicator if it doesn't exist
    let indicator = document.getElementById('processing-indicator');
    if (!indicator) {
        indicator = document.createElement('div');
        indicator.id = 'processing-indicator';
        indicator.className = 'processing-indicator alert alert-info';
        indicator.innerHTML = `
            <div class="text-center">
                <div class="spinner-border text-primary mb-3" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <h5><i class="fas fa-cogs me-2"></i>Processing Your Resume</h5>
                <p class="mb-0">
                    Our AI is analyzing the job description and tailoring your resume. 
                    This may take a few moments...
                </p>
            </div>
        `;
        
        // Insert after the form
        const form = document.getElementById('resumeForm');
        if (form) {
            form.parentNode.insertBefore(indicator, form.nextSibling);
        }
    }
    
    indicator.classList.add('show');
}

/**
 * Initialize file upload enhancements
 */
function initializeFileUpload() {
    const fileInput = document.getElementById('resume_file');
    const uploadArea = document.getElementById('uploadArea');
    
    if (fileInput && uploadArea) {
        // File input change handler
        fileInput.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                showFileSelected(file);
                validateFileSelection(file);
            }
        });
        
        // Make upload area clickable
        uploadArea.addEventListener('click', function(e) {
            if (!e.target.closest('button')) {
                fileInput.click();
            }
        });
        
        // Add drag and drop functionality
        addEnhancedDragDrop(uploadArea, fileInput);
    }
}

/**
 * Show file selected state in enhanced upload area
 */
function showFileSelected(file) {
    const uploadArea = document.getElementById('uploadArea');
    const uploadContent = uploadArea.querySelector('.upload-content');
    const uploadSuccess = uploadArea.querySelector('.upload-success');
    const fileName = uploadSuccess.querySelector('.file-name');
    const fileDetails = uploadSuccess.querySelector('.file-details');
    
    // Hide upload content and show success state
    uploadContent.classList.add('d-none');
    uploadSuccess.classList.remove('d-none');
    
    // Update file information
    const fileSize = (file.size / 1024 / 1024).toFixed(2);
    const fileType = file.name.split('.').pop().toUpperCase();
    
    fileName.textContent = file.name;
    fileDetails.innerHTML = `
        <i class="fas fa-file-${fileType.toLowerCase() === 'pdf' ? 'pdf' : 'word'} me-2"></i>
        ${fileType} File • ${fileSize} MB
    `;
    
    // Add success styling to upload area
    uploadArea.classList.add('file-selected');
}

/**
 * Reset file upload to initial state
 */
function resetFileUpload() {
    const fileInput = document.getElementById('resume_file');
    const uploadArea = document.getElementById('uploadArea');
    const uploadContent = uploadArea.querySelector('.upload-content');
    const uploadSuccess = uploadArea.querySelector('.upload-success');
    
    // Reset file input
    fileInput.value = '';
    
    // Reset UI state
    uploadContent.classList.remove('d-none');
    uploadSuccess.classList.add('d-none');
    uploadArea.classList.remove('file-selected');
    
    // Clear any validation states
    fileInput.classList.remove('is-invalid', 'is-valid');
    const errorMessage = uploadArea.parentNode.querySelector('.invalid-feedback');
    if (errorMessage) {
        errorMessage.remove();
    }
}

/**
 * Update file input label with selected file info
 */
function updateFileInputLabel(file) {
    const fileInput = document.getElementById('resume_file');
    const formText = fileInput.parentNode.querySelector('.form-text');
    
    if (formText) {
        const fileSize = (file.size / 1024 / 1024).toFixed(2);
        formText.innerHTML = `
            <i class="fas fa-check-circle text-success me-1"></i>
            Selected: <strong>${file.name}</strong> (${fileSize} MB)
        `;
    }
}

/**
 * Validate file selection and show immediate feedback
 */
function validateFileSelection(file) {
    const fileInput = document.getElementById('resume_file');
    
    // Clear previous states
    fileInput.classList.remove('is-invalid', 'is-valid');
    
    // Validate file type
    if (!file.name.toLowerCase().endsWith('.docx')) {
        showFieldError(fileInput, 'Only DOCX files are supported.');
        return false;
    }
    
    // Validate file size
    if (file.size > 16 * 1024 * 1024) {
        showFieldError(fileInput, 'File size must be less than 16MB.');
        return false;
    }
    
    // File is valid
    fileInput.classList.add('is-valid');
    return true;
}

/**
 * Add enhanced drag and drop support for file upload
 */
function addEnhancedDragDrop(uploadArea, fileInput) {
    // Prevent default drag behaviors
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        uploadArea.addEventListener(eventName, preventDefaults, false);
        document.body.addEventListener(eventName, preventDefaults, false);
    });
    
    // Highlight drop area when item is dragged over it
    ['dragenter', 'dragover'].forEach(eventName => {
        uploadArea.addEventListener(eventName, highlight, false);
    });
    
    ['dragleave', 'drop'].forEach(eventName => {
        uploadArea.addEventListener(eventName, unhighlight, false);
    });
    
    // Handle dropped files
    uploadArea.addEventListener('drop', handleDrop, false);
    
    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }
    
    function highlight(e) {
        uploadArea.classList.add('dragover');
    }
    
    function unhighlight(e) {
        uploadArea.classList.remove('dragover');
    }
    
    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        
        if (files.length > 0) {
            fileInput.files = files;
            fileInput.dispatchEvent(new Event('change', { bubbles: true }));
        }
    }
}

/**
 * Initialize Bootstrap tooltips
 */
function initializeTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

/**
 * Auto-dismiss alerts after 5 seconds
 */
document.addEventListener('DOMContentLoaded', function() {
    const alerts = document.querySelectorAll('.alert:not(.alert-info)');
    alerts.forEach(alert => {
        if (!alert.querySelector('.btn-close')) return;
        
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });
});

/**
 * Smooth scroll for anchor links
 */
document.addEventListener('click', function(e) {
    if (e.target.matches('a[href^="#"]')) {
        e.preventDefault();
        const target = document.querySelector(e.target.getAttribute('href'));
        if (target) {
            target.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    }
});

/**
 * Form auto-save to localStorage (for job description)
 */
function initializeAutoSave() {
    const jobDescriptionField = document.getElementById('job_description');
    
    if (jobDescriptionField) {
        // Load saved content
        const savedContent = localStorage.getItem('ai-resume-modifier-job-description');
        if (savedContent) {
            jobDescriptionField.value = savedContent;
        }
        
        // Save content on input
        jobDescriptionField.addEventListener('input', function() {
            localStorage.setItem('ai-resume-modifier-job-description', this.value);
        });
        
        // Clear saved content when form is successfully submitted
        const form = document.getElementById('resumeForm');
        if (form) {
            form.addEventListener('submit', function() {
                // Clear after a short delay to ensure form validation passes
                setTimeout(() => {
                    localStorage.removeItem('ai-resume-modifier-job-description');
                }, 1000);
            });
        }
    }
}

// Initialize auto-save
document.addEventListener('DOMContentLoaded', initializeAutoSave);

/**
 * Copy to clipboard functionality
 */
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(function() {
        showToast('Copied to clipboard!', 'success');
    }, function(err) {
        console.error('Could not copy text: ', err);
        showToast('Failed to copy to clipboard', 'error');
    });
}

/**
 * Show toast notification
 */
function showToast(message, type = 'info') {
    // Create toast container if it doesn't exist
    let toastContainer = document.querySelector('.toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.className = 'toast-container position-fixed top-0 end-0 p-3';
        document.body.appendChild(toastContainer);
    }
    
    // Create toast element
    const toastId = 'toast-' + Date.now();
    const toastHtml = `
        <div id="${toastId}" class="toast" role="alert" aria-live="assertive" aria-atomic="true">
            <div class="toast-header">
                <i class="fas fa-${type === 'success' ? 'check-circle text-success' : type === 'error' ? 'exclamation-circle text-danger' : 'info-circle text-info'} me-2"></i>
                <strong class="me-auto">Notification</strong>
                <button type="button" class="btn-close" data-bs-dismiss="toast"></button>
            </div>
            <div class="toast-body">
                ${message}
            </div>
        </div>
    `;
    
    toastContainer.insertAdjacentHTML('beforeend', toastHtml);
    
    // Initialize and show toast
    const toastElement = document.getElementById(toastId);
    const toast = new bootstrap.Toast(toastElement);
    toast.show();
    
    // Remove toast element after it's hidden
    toastElement.addEventListener('hidden.bs.toast', function() {
        toastElement.remove();
    });
}
