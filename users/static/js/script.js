// Cybersecurity Training App - Main JavaScript File

// Password Show/Hide Toggle Function
function togglePasswordVisibility(fieldId) {
    const passwordField = document.getElementById(fieldId);
    const toggleButton = document.getElementById('togglePassword');
    
    if (!passwordField || !toggleButton) return;
    
    if (passwordField.type === 'password') {
        passwordField.type = 'text';
        toggleButton.innerHTML = '<i class="fas fa-eye-slash"></i>';
        toggleButton.classList.add('show');
    } else {
        passwordField.type = 'password';
        toggleButton.innerHTML = '<i class="fas fa-eye"></i>';
        toggleButton.classList.remove('show');
    }
}

document.addEventListener('DOMContentLoaded', function() {
    // Auto-dismiss alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            if (alert.classList.contains('show')) {
                const bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            }
        }, 5000);
    });

    // Progress bar animation
    const progressBars = document.querySelectorAll('.progress-bar');
    progressBars.forEach(bar => {
        const width = bar.style.width;
        bar.style.width = '0%';
        setTimeout(() => {
            bar.style.width = width;
            bar.style.transition = 'width 1s ease-in-out';
        }, 100);
    });

    // Quiz functionality
    initializeQuizHandlers();
    
    // URL checker functionality
    initializeURLChecker();
    
    // Dashboard animations
    initializeDashboardAnimations();
});

function initializeQuizHandlers() {
    // Quiz start handlers are already in the quiz.html template
    // Additional quiz-related functionality can be added here
    
    // Handle quiz question navigation
    const questionContainers = document.querySelectorAll('.question-container');
    if (questionContainers.length > 0) {
        questionContainers.forEach((container, index) => {
            if (index > 0) {
                container.style.display = 'none';
            }
        });
        
        // Add navigation buttons if not present
        if (!document.querySelector('.quiz-navigation')) {
            addQuizNavigation();
        }
    }
}

function addQuizNavigation() {
    const quizForm = document.getElementById('quizForm');
    if (quizForm) {
        const navigation = document.createElement('div');
        navigation.className = 'quiz-navigation d-flex justify-content-between mt-3';
        navigation.innerHTML = `
            <button type="button" class="btn btn-secondary prev-question" disabled>Previous</button>
            <button type="button" class="btn btn-primary next-question">Next Question</button>
        `;
        quizForm.appendChild(navigation);
        
        // Add navigation handlers
        initializeQuizNavigation();
    }
}

function initializeQuizNavigation() {
    const prevBtn = document.querySelector('.prev-question');
    const nextBtn = document.querySelector('.next-question');
    const questions = document.querySelectorAll('.question-container');
    let currentQuestion = 0;
    
    if (prevBtn && nextBtn && questions.length > 0) {
        updateNavigationButtons();
        
        prevBtn.addEventListener('click', () => {
            if (currentQuestion > 0) {
                questions[currentQuestion].style.display = 'none';
                currentQuestion--;
                questions[currentQuestion].style.display = 'block';
                updateNavigationButtons();
                updateProgressBar();
            }
        });
        
        nextBtn.addEventListener('click', () => {
            if (currentQuestion < questions.length - 1) {
                questions[currentQuestion].style.display = 'none';
                currentQuestion++;
                questions[currentQuestion].style.display = 'block';
                updateNavigationButtons();
                updateProgressBar();
            }
        });
    }
    
    function updateNavigationButtons() {
        prevBtn.disabled = currentQuestion === 0;
        nextBtn.disabled = currentQuestion === questions.length - 1;
        
        if (currentQuestion === questions.length - 1) {
            nextBtn.textContent = 'Submit Quiz';
            nextBtn.className = 'btn btn-success next-question';
        } else {
            nextBtn.textContent = 'Next Question';
            nextBtn.className = 'btn btn-primary next-question';
        }
    }
    
    function updateProgressBar() {
        const progress = ((currentQuestion + 1) / questions.length) * 100;
        const progressBar = document.querySelector('.progress-bar');
        if (progressBar) {
            progressBar.style.width = `${progress}%`;
            progressBar.textContent = `${Math.round(progress)}%`;
        }
    }
}

function initializeURLChecker() {
    const urlCheckForm = document.getElementById('urlCheckForm');
    if (urlCheckForm) {
        urlCheckForm.addEventListener('submit', function(e) {
            e.preventDefault();
            checkURL();
        });
        
        // Add URL validation
        const urlInput = document.getElementById('urlInput');
        if (urlInput) {
            urlInput.addEventListener('input', function() {
                validateURL(this.value);
            });
        }
    }
}

function validateURL(url) {
    // URL pattern: accepts http/https URLs
    const urlPattern = /^(https?:\/\/)?([\da-z\.-]+)\.([a-z\.]{2,6})([\/\w \.-]*)*\/?$/i;
    // Email pattern: accepts email-like formats (e.g., inst@gram.com, user@domain.com)
    const emailPattern = /^[a-zA-Z0-9._%-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
    const submitBtn = document.querySelector('#urlCheckForm button[type="submit"]');
    
    // Allow if it matches URL pattern OR email pattern OR is empty
    if (urlPattern.test(url) || emailPattern.test(url) || url === '') {
        submitBtn.disabled = false;
        return true;
    } else {
        submitBtn.disabled = true;
        return false;
    }
}

function checkURL() {
    const url = document.getElementById('urlInput').value;
    const loading = document.getElementById('loading');
    const results = document.getElementById('results');
    
    if (!url) {
        showNotification('Please enter a URL to check', 'danger');
        return;
    }
    
    // Show loading, hide previous results
    if (loading) loading.style.display = 'block';
    if (results) results.style.display = 'none';
    
    // Disable form during request
    const submitBtn = document.querySelector('#urlCheckForm button[type="submit"]');
    if (submitBtn) submitBtn.disabled = true;
    
    fetch('/users/url_checker', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ url: url })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return response.json();
    })
    .then(data => {
        if (loading) loading.style.display = 'none';
        displayURLResults(data);
        
        // Re-enable form
        if (submitBtn) submitBtn.disabled = false;
    })
    .catch(error => {
        console.error('Error:', error);
        if (loading) loading.style.display = 'none';
        
        const results = document.getElementById('results');
        if (results) {
            results.innerHTML = `
                <div class="alert alert-danger">
                    <h5>Error Analyzing URL</h5>
                    <p>There was an error analyzing the URL. Please try again later.</p>
                    <small>Error: ${error.message}</small>
                </div>
            `;
            results.style.display = 'block';
        }
        
        // Re-enable form
        if (submitBtn) submitBtn.disabled = false;
    });
}

function displayURLResults(data) {
    const results = document.getElementById('results');
    if (!results) return;
    
    let resultsHTML = '<h5 class="mb-3">Security Analysis Results</h5>';
    
    // Overall Risk Assessment
    let riskLevel = 'Unknown';
    let riskClass = 'secondary';
    let riskIcon = 'fa-question-circle';
    
    if (data.virustotal) {
        const vt = data.virustotal;
        const malicious = vt.mock_data ? vt.malicious : (vt.data?.attributes?.stats?.malicious || 0);
        const suspicious = vt.mock_data ? vt.suspicious : (vt.data?.attributes?.stats?.suspicious || 0);
        
        if (malicious > 5 || suspicious > 10) {
            riskLevel = 'High Risk';
            riskClass = 'danger';
            riskIcon = 'fa-exclamation-triangle';
        } else if (malicious > 0 || suspicious > 3) {
            riskLevel = 'Medium Risk';
            riskClass = 'warning';
            riskIcon = 'fa-exclamation-circle';
        } else {
            riskLevel = 'Low Risk';
            riskClass = 'success';
            riskIcon = 'fa-check-circle';
        }
    }
    
    // resultsHTML += `
    //     <div class="alert alert-${riskClass}">
    //         <h6><i class="fas ${riskIcon}"></i> Overall Risk: ${riskLevel}</h6>
    //     </div>
    // `;
    
    // VirusTotal Results
    if (data.virustotal) {
        const vt = data.virustotal;
        
        if (vt.mock_data) {
            resultsHTML += createVTMockResults(vt);
        } else if (vt.data && vt.data.attributes) {
            resultsHTML += createVTRealResults(vt);
        } else if (vt.error) {
            resultsHTML += `
                <div class="alert alert-warning">
                    <h6><i class="fas fa-exclamation-triangle"></i> VirusTotal Analysis</h6>
                    <p>Error: ${vt.error}</p>
                </div>
            `;
        }
    }
    
    // Gemini Analysis
    if (data.gemini_analysis) {
        console.log(data.gemini_analysis)
        resultsHTML += `
            <div class="card mt-3">
                <div class="card-header">
                    <h6><i class="fas fa-robot"></i> AI Security Analysis & Recommendations</h6>
                </div>
                <div class="card-body">
                    <div class="gemini-analysis">${formatGeminiAnalysis(data.gemini_analysis)}</div>
                </div>
            </div>
        `;
    }
    
    // Security Recommendations
    resultsHTML += createSecurityRecommendations(riskLevel);
    
    results.innerHTML = resultsHTML;
    results.style.display = 'block';
    
    // Animate results appearance
    animateResults();
}

function createVTMockResults(vt) {
    return `
        <div class="card mb-3">
            <div class="card-header">
                <h6><i class="fas fa-chart-bar"></i> Security Vendor Analysis (Demo Data)</h6>
            </div>
            <div class="card-body">
                <div class="row text-center">
                    <div class="col-3">
                        <div class="text-danger">
                            <h4>${vt.malicious}</h4>
                            <small>Malicious</small>
                        </div>
                    </div>
                    <div class="col-3">
                        <div class="text-warning">
                            <h4>${vt.suspicious}</h4>
                            <small>Suspicious</small>
                        </div>
                    </div>
                    <div class="col-3">
                        <div class="text-success">
                            <h4>${vt.harmless}</h4>
                            <small>Harmless</small>
                        </div>
                    </div>
                    <div class="col-3">
                        <div class="text-muted">
                            <h4>${vt.undetected}</h4>
                            <small>Undetected</small>
                        </div>
                    </div>
                </div>
                <div class="mt-3">
                    <div class="alert alert-info">
                        <i class="fas fa-info-circle"></i> This is demo data. With a real VirusTotal API key, you would see actual security vendor results.
                    </div>
                </div>
            </div>
        </div>
    `;
}


function formatGeminiAnalysis(analysis) {
    // Step 1: Escape raw HTML
    let formatted = analysis
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");

    // Step 2: Handle Markdown headers (###, ##, #)
    formatted = formatted
        .replace(/^###\s*(.*)$/gm, '<h3 class="mt-4 mb-2 font-semibold">$1</h3>')
        .replace(/^##\s*(.*)$/gm, '<h2 class="mt-5 mb-3 font-bold text-lg">$1</h2>')
        .replace(/^#\s*(.*)$/gm, '<h1 class="mt-6 mb-4 text-xl font-bold">$1</h1>');

    // Step 3: Handle bold (**text**) and inline code (`code`)
    formatted = formatted
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/`([^`]+)`/g, '<code>$1</code>');

    // Step 4: Handle lines like "**Security Summary:**" or "**Recommendation:**"
    formatted = formatted
        .replace(/\*\*(.*?)\:\*\*/g, '<h3 class="mt-4 mb-2 font-semibold">$1</h3>')
        .replace(/\*\*(.*?)\:\s*/g, '<h3 class="mt-4 mb-2 font-semibold">$1</h3>');

    // Step 5: Convert numbered lists ("1. something") and bullet lists ("- something")
    formatted = formatted
        .replace(/^\s*\d+\.\s*(.*)$/gm, '<li>$1</li>')
        .replace(/^\s*-\s*(.*)$/gm, '<li>$1</li>');

    // Step 6: Wrap all consecutive <li> elements inside <ul>
    formatted = formatted.replace(/(<li>.*<\/li>)/gs, match => {
        if (!match.includes('</ul>')) return `<ul>${match}</ul>`;
        return match;
    });

    // Step 7: Replace multiple newlines with paragraph tags
    formatted = formatted
        .replace(/\n{2,}/g, '</p><p>')
        .replace(/\n/g, '<br>');

    // Step 8: Wrap everything in a paragraph tag if not already inside one
    formatted = `<p>${formatted}</p>`;

    return formatted;
}


function createSecurityRecommendations(riskLevel) {
    const recommendations = {
        'High Risk': [
            'Do not visit this URL under any circumstances',
            'Report this URL to your IT security team immediately',
            'If you already visited, run a full system antivirus scan',
            'Change any passwords that might have been entered'
        ],
        'Medium Risk': [
            'Avoid visiting this URL unless absolutely necessary',
            'Verify the legitimacy through official channels',
            'Use a virtual machine or sandboxed environment if access is required',
            'Ensure your browser and security software are updated'
        ],
        'Low Risk': [
            'The URL appears safe but remain cautious',
            'Verify SSL certificate and website identity',
            'Look for misspellings or suspicious elements',
            'Use common sense when providing personal information'
        ],
        'Unknown': [
            'Proceed with extreme caution',
            'Verify the URL through multiple sources',
            'Consider using URL scanning tools',
            'When in doubt, don\'t click'
        ]
    };
    
    const recs = recommendations[riskLevel] || recommendations['Unknown'];
    
    let html = `
        <div class="card mt-3">
            <div class="card-header">
                <h6><i class="fas fa-lightbulb"></i> Recommended Actions</h6>
            </div>
            <div class="card-body">
                <ul class="list-group list-group-flush">
    `;
    
    recs.forEach(rec => {
        html += `<li class="list-group-item"><i class="fas fa-check text-success me-2"></i>${rec}</li>`;
    });
    
    html += `
                </ul>
            </div>
        </div>
    `;
    
    return html;
}

function animateResults() {
    const cards = document.querySelectorAll('#results .card');
    cards.forEach((card, index) => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(20px)';
        
        setTimeout(() => {
            card.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
            card.style.opacity = '1';
            card.style.transform = 'translateY(0)';
        }, index * 200);
    });
}

function initializeDashboardAnimations() {
    // Animate stats cards on dashboard
    const statsCards = document.querySelectorAll('.card.text-center');
    statsCards.forEach((card, index) => {
        card.style.opacity = '0';
        card.style.transform = 'scale(0.9)';
        
        setTimeout(() => {
            card.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
            card.style.opacity = '1';
            card.style.transform = 'scale(1)';
        }, index * 150);
    });
    
    // Add hover effects to badges
    const badges = document.querySelectorAll('.badge');
    badges.forEach(badge => {
        badge.addEventListener('mouseenter', function() {
            this.style.transform = 'scale(1.1)';
            this.style.transition = 'transform 0.2s ease';
        });
        
        badge.addEventListener('mouseleave', function() {
            this.style.transform = 'scale(1)';
        });
    });
}

function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    notification.style.cssText = `
        top: 20px;
        right: 20px;
        z-index: 1050;
        min-width: 300px;
    `;
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    // Add to page
    document.body.appendChild(notification);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        if (notification.parentNode) {
            notification.remove();
        }
    }, 5000);
}

// Utility function for API calls
async function makeAPICall(url, data = {}) {
    try {
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('API call failed:', error);
        showNotification('Operation failed. Please try again.', 'danger');
        throw error;
    }
}

// Export functions for use in other modules (if needed)
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        validateURL,
        showNotification,
        makeAPICall
    };
}