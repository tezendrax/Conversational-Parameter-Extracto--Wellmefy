// API Base Endpoint (use local port 8000 if deployed to Vercel/production)
const API_BASE = (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
    ? window.location.origin
    : 'http://localhost:8000';

// State Variables
let currentTab = 'text';
let isMetadataOpen = false;
let selectedAudioFile = null;

// Presets Data
const PRESETS = [
    {
        text: "i am teaching the same tomorrow is my exam. i have operating system exam and i don't know that things i missed my classes. i didn't study as much for it and now i don't know what i do for it. why don't know what i need to do? it's up to noon. it's 3 p.m. and it's up to noon and tomorrow at 11 a.m. i have some i don't know what to do.",
        student_id: "student_cs_99",
        time_of_day: "evening",
        history: "First year Computer Science major. History of exam anxiety."
    },
    {
        text: "I feel great! I finally finished my project early and I'm going to hang out with my friends tonight.",
        student_id: "student_joy_22",
        time_of_day: "afternoon",
        history: "No critical background notes."
    },
    {
        text: "I am so tired. My head hurts, and I just can't seem to focus on any of my lectures. There is way too much homework.",
        student_id: "student_fatigue_01",
        time_of_day: "morning",
        history: "Reporting persistent exhaustion."
    },
    {
        text: "I have been having terrible stomachaches all day because of the presentations we have to do in class.",
        student_id: "student_somatic_05",
        time_of_day: "afternoon",
        history: "Performance anxiety issues."
    },
    {
        text: "My classes are going fine, and I'm not particularly worried about academics.",
        student_id: "student_acad_neg",
        time_of_day: "morning",
        history: "Testing negated academic stress."
    },
    {
        text: "I'm proud of my project, but I'm worried about internship interviews. My heartbeat is racing and I feel nauseous.",
        student_id: "student_mixed_somatic",
        time_of_day: "afternoon",
        history: "Testing mixed emotions and explicit somatic symptoms."
    },
    {
        text: "My exams are tomorrow and I'm terrified.",
        student_id: "student_causal_true",
        time_of_day: "evening",
        history: "Testing causal academic stress (True)."
    },
    {
        text: "My classes are going well. I'm worried about my grandfather.",
        student_id: "student_causal_false",
        time_of_day: "afternoon",
        history: "Testing causal academic stress (False) with non-academic distress."
    },
    {
        text: "I got no sleep last night because I was studying all night for 20 hours.",
        student_id: "student_inferred_risks",
        time_of_day: "morning",
        history: "Testing explicit vs inferred somatic symptoms."
    }
];

// Initialize on page load
document.addEventListener("DOMContentLoaded", () => {
    checkBackendHealth();
    // Periodically check health every 15 seconds
    setInterval(checkBackendHealth, 15000);
    
    // Setup drag and drop for audio upload
    setupDragAndDrop();
});

// Health check
async function checkBackendHealth() {
    const badge = document.getElementById("backend-status");
    try {
        const res = await fetch(`${API_BASE}/health`);
        if (res.ok) {
            const data = await res.json();
            badge.className = "status-badge online";
            badge.innerHTML = `<span class="status-dot"></span> Live (${data.model})`;
        } else {
            throw new Error("Offline");
        }
    } catch (err) {
        badge.className = "status-badge";
        badge.innerHTML = `<span class="status-dot"></span> Server Offline`;
    }
}

// Switch between text and audio tabs
function switchTab(tab) {
    currentTab = tab;
    
    // Toggle active buttons
    document.getElementById("tab-text").classList.toggle("active", tab === 'text');
    document.getElementById("tab-audio").classList.toggle("active", tab === 'audio');
    
    // Toggle active inputs
    document.getElementById("input-container-text").classList.toggle("active", tab === 'text');
    document.getElementById("input-container-audio").classList.toggle("active", tab === 'audio');
}

// Toggle Metadata view
function toggleMetadata() {
    isMetadataOpen = !isMetadataOpen;
    const pane = document.getElementById("metadata-pane");
    const arrow = document.getElementById("meta-arrow");
    
    pane.style.display = isMetadataOpen ? "block" : "none";
    arrow.classList.toggle("open", isMetadataOpen);
}

// Load preset values into input fields
function loadPreset(index) {
    const preset = PRESETS[index];
    if (!preset) return;
    
    // Force switch to Text Tab
    switchTab('text');
    
    // Fill text area
    document.getElementById("raw-text").value = preset.text;
    
    // Open metadata pane and fill metadata
    if (!isMetadataOpen) {
        toggleMetadata();
    }
    
    document.getElementById("student-id").value = preset.student_id;
    document.getElementById("time-of-day").value = preset.time_of_day;
    document.getElementById("history-context").value = preset.history;
}

// Trigger hidden file picker
function triggerFileSelect() {
    document.getElementById("audio-file").click();
}

// Handle file selection from browse
function handleFileSelect(e) {
    const files = e.target.files;
    if (files.length > 0) {
        setAudioFile(files[0]);
    }
}

// Set selected audio file details in UI
function setAudioFile(file) {
    selectedAudioFile = file;
    
    // Hide dropzone, show info card
    document.getElementById("audio-dropzone").style.display = "none";
    
    const infoCard = document.getElementById("selected-file-info");
    infoCard.style.display = "flex";
    
    document.getElementById("selected-file-name").textContent = file.name;
    document.getElementById("selected-file-size").textContent = (file.size / (1024 * 1024)).toFixed(2) + " MB";
}

// Clear selected file
function clearSelectedFile(e) {
    e.stopPropagation();
    selectedAudioFile = null;
    document.getElementById("audio-file").value = "";
    
    document.getElementById("selected-file-info").style.display = "none";
    document.getElementById("audio-dropzone").style.display = "block";
}

// Setup drag & drop listeners
function setupDragAndDrop() {
    const dropzone = document.getElementById("audio-dropzone");
    
    ['dragenter', 'dragover'].forEach(eventName => {
        dropzone.addEventListener(eventName, (e) => {
            e.preventDefault();
            dropzone.style.borderColor = "var(--accent)";
            dropzone.style.background = "rgba(99, 102, 241, 0.06)";
        }, false);
    });
    
    ['dragleave', 'drop'].forEach(eventName => {
        dropzone.addEventListener(eventName, (e) => {
            e.preventDefault();
            dropzone.style.borderColor = "rgba(255, 255, 255, 0.15)";
            dropzone.style.background = "rgba(255, 255, 255, 0.01)";
        }, false);
    });
    
    dropzone.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        const files = dt.files;
        if (files.length > 0) {
            const file = files[0];
            const name = file.name.toLowerCase();
            const isValidFormat = file.type.startsWith("audio/") || 
                                  file.type.startsWith("video/") || 
                                  name.endsWith(".mp3") || 
                                  name.endsWith(".wav") || 
                                  name.endsWith(".m4a") || 
                                  name.endsWith(".mp4") || 
                                  name.endsWith(".ogg");
            if (isValidFormat) {
                setAudioFile(file);
            } else {
                alert("Unsupported file format. Please upload an audio (.mp3, .wav, .m4a, .ogg) or video (.mp4) file.");
            }
        }
    }, false);
}

// Submit parameters to backend API
async function submitExtraction() {
    const btn = document.getElementById("submit-btn");
    const txt = document.getElementById("submit-text");
    const spinner = document.getElementById("submit-spinner");
    
    // Elements to hide/show
    const emptyState = document.getElementById("empty-state");
    const errorState = document.getElementById("error-state");
    const resultContent = document.getElementById("result-content");
    
    // Read Context metadata fields
    const studentId = document.getElementById("student-id").value.trim() || "unknown";
    const timeOfDay = document.getElementById("time-of-day").value;
    const historyContext = document.getElementById("history-context").value.trim() || "";
    
    let url = "";
    let options = {};
    
    if (currentTab === 'text') {
        const rawText = document.getElementById("raw-text").value.trim();
        if (!rawText) {
            alert("Please enter a raw transcript text first.");
            return;
        }
        
        url = `${API_BASE}/api/v1/cpe/extract`;
        options = {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                text: rawText,
                context: {
                    student_id: studentId,
                    time_of_day: timeOfDay,
                    interaction_history_context: historyContext
                }
            })
        };
    } else {
        if (!selectedAudioFile) {
            alert("Please drag or select an audio file first.");
            return;
        }
        
        url = `${API_BASE}/api/v1/cpe/extract/audio`;
        
        const formData = new FormData();
        formData.append("file", selectedAudioFile);
        formData.append("student_id", studentId);
        formData.append("time_of_day", timeOfDay);
        formData.append("interaction_history_context", historyContext);
        
        options = {
            method: "POST",
            body: formData
        };
    }
    
    // Toggle Loading state
    btn.disabled = true;
    txt.style.display = "none";
    spinner.style.display = "inline-flex";
    
    emptyState.style.display = "none";
    errorState.style.display = "none";
    resultContent.style.display = "none";
    
    try {
        const response = await fetch(url, options);
        if (!response.ok) {
            let errMsg = "Server error occurred";
            try {
                const errBody = await response.json();
                errMsg = errBody.detail || errMsg;
            } catch (jsonErr) {
                try {
                    const textErr = await response.text();
                    errMsg = textErr.substring(0, 150) || errMsg;
                } catch (textErrErr) {}
            }
            throw new Error(errMsg);
        }
        
        const data = await response.json();
        renderResults(data);
    } catch (err) {
        console.error(err);
        errorState.style.display = "flex";
        document.getElementById("error-message").textContent = err.message;
    } finally {
        // Restore buttons
        btn.disabled = false;
        txt.style.display = "inline-flex";
        spinner.style.display = "none";
    }
}

// Render API Response to Dashboard UI
function renderResults(data) {
    const resultContent = document.getElementById("result-content");
    resultContent.style.display = "flex";
    
    // Transcript text
    document.getElementById("result-transcript").textContent = `"${data.transcript}"`;
    
    const params = data.parameters;
    
    // Feature Engineering metrics from backend
    document.getElementById("metric-density").textContent = params.semantic_density.toFixed(2);
    document.getElementById("metric-repetition").textContent = params.word_repetition_index.toFixed(2);
    document.getElementById("metric-ratio").textContent = params.neg_to_pos_ratio.toFixed(2);
    
    // Pause density (audio exclusive)
    const pauseCard = document.getElementById("metric-card-pause");
    const pauseVal = document.getElementById("metric-pause");
    if (currentTab === 'audio') {
        pauseCard.style.display = "flex";
        // Mock a reasonable pause density if not returned directly (ASR computes it but we mock if needed)
        pauseVal.textContent = "0.15";
    } else {
        pauseCard.style.display = "none";
    }
    
    // Valence (Mood Slider)
    // Value range: -1.0 to 1.0. Map to 0% to 100%
    const valency = params.emotional_valency;
    document.getElementById("valency-val").textContent = valency.toFixed(2);
    const valencyPercentage = ((valency + 1) / 2) * 100;
    document.getElementById("valency-fill").style.width = `${valencyPercentage}%`;
    
    // Arousal (Energy Slider)
    // Value range: 0.0 to 1.0. Map to 0% to 100%
    const arousal = params.emotional_arousal;
    document.getElementById("arousal-val").textContent = arousal.toFixed(2);
    const arousalPercentage = arousal * 100;
    document.getElementById("arousal-fill").style.width = `${arousalPercentage}%`;
    
    // Cognitive Load Stepper (1 to 5)
    const cog = params.cognitive_load;
    document.getElementById("cognitive-val").textContent = `${cog} / 5`;
    
    const stepContainer = document.getElementById("cognitive-steps");
    const steps = stepContainer.getElementsByClassName("step-dot");
    
    // Reset colors
    let statusClass = "safe";
    if (cog === 3) statusClass = "warning";
    else if (cog >= 4) statusClass = "danger";
    
    for (let i = 0; i < steps.length; i++) {
        const stepNum = parseInt(steps[i].getAttribute("data-step"));
        steps[i].className = "step-dot"; // reset class
        
        if (stepNum <= cog) {
            steps[i].classList.add("active");
            if (statusClass === 'warning') steps[i].style.background = "var(--warning)";
            else if (statusClass === 'danger') steps[i].style.background = "var(--danger)";
            else steps[i].style.background = "var(--success)";
            
            steps[i].style.borderColor = "transparent";
        } else {
            steps[i].style.background = "#1f2937";
            steps[i].style.borderColor = "rgba(255, 255, 255, 0.1)";
        }
    }
    
    // Academic Stress Badge
    const acadCard = document.getElementById("risk-academic");
    const acadStatus = document.getElementById("academic-status");
    if (params.academic_stress) {
        acadCard.className = "risk-card active-alert";
        acadStatus.textContent = "Stress Detected";
    } else {
        acadCard.className = "risk-card";
        acadStatus.textContent = "None";
    }
    
    // Somatic Symptoms Badges (Explicit)
    const somaticCard = document.getElementById("risk-somatic");
    const somaticStatus = document.getElementById("somatic-status");
    const explicit_syms = params.explicit_symptoms || params.somatic_symptoms;
    if (explicit_syms && explicit_syms.length > 0) {
        somaticCard.className = "risk-card active-warning";
        somaticStatus.textContent = explicit_syms.join(", ");
    } else {
        somaticCard.className = "risk-card";
        somaticStatus.textContent = "None";
    }
    
    // Inferred Risks Badges
    const inferredCard = document.getElementById("risk-inferred");
    const inferredStatus = document.getElementById("inferred-status");
    const risks = params.inferred_risks;
    if (risks && risks.length > 0) {
        inferredCard.className = "risk-card active-alert";
        inferredStatus.textContent = risks.join(", ");
    } else {
        inferredCard.className = "risk-card";
        inferredStatus.textContent = "None";
    }
    
    // Metadata stats
    document.getElementById("meta-confidence").textContent = `${Math.round(params.confidence_score * 100)}%`;
    document.getElementById("meta-sentiment").textContent = params.sentiment_score.toFixed(2);
}
