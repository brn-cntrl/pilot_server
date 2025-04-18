document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".toggle").forEach(button => {
        button.addEventListener("click", function () {
            let nextDiv = this.nextElementSibling;

            while (nextDiv && nextDiv.tagName !== "DIV") {
                nextDiv = nextDiv.nextElementSibling;
            }

            if (nextDiv) {
                // Toggle between display: none and display: block
                nextDiv.style.display = nextDiv.style.display === "none" ? "block" : "none";
            }
        });
    });
});

function processAudioFiles(statusElement, pathElement){
    fetch('/process_audio_files', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        console.log(data.message);
        statusElement.style.display = 'block';
        statusElement.innerText = data.message;
        pathElement.style.display = 'block';
        pathElement.innerText = `Transcription/SER CSV location: ${data.path}`;
    })
    .catch(error => {
        console.error('Error:', error);
        statusElement.style.display = 'block';
        statusElement.innerText = "Error processing audio files.";
    });
}

function setNextTest(){
    fetch('/set_next_test', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        console.log(data.message);
    })
    .catch(error => {
        console.error('Error:', error);
    });
}

function completeTask(taskId) {
    fetch('/complete_task', { 
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'},
        body: JSON.stringify({ task_id: taskId })
    })
    .then(response => console.log(`Task ${taskId} completed`))
    .catch(error => console.error('Error:', error));
}

function sendStatus() {
    fetch('/status_update', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: 'Subject is ready' })
    });
}

function updateCondition(parentDiv, event) {
    const selectElement = document.querySelector(`#${parentDiv} select`);
    const selectedCondition = selectElement.value;
    // let currentEventMarker = `${event}_${selectedCondition}`
    localStorage.setItem('currentEventMarker', event);
    localStorage.setItem('currentCondition', selectedCondition);
    console.log(selectedCondition);
    console.log(event);
}

function setCondition(condition){
    fetch('/set_condition', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            'condition': condition
        })
    })
    .then(response => response.json())
    .then(data => {
        console.log(data.status);
    })
    .catch(error => console.error('status:', error));
}

function setEventMarker(eventMarker){
    fetch('/set_event_marker', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            'event_marker': eventMarker
        })
    })
    .then(response => response.json())
    .then(data => {
        console.log(data.status);
    })
    .catch(error => console.error('status:', error));
}

function recordTaskAudio(eventMarker, condition, action, question, divID){
    fetch('/record_task_audio', { method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            'event_marker': eventMarker,
            'condition': condition,
            'action': action,
            'question': question
        })
     })
    .then(response => response.json())
    .then(data => {
        if (data.message === 'Error starting recording.'|| data.message === 'Invalid action.') {
            console.error(data.message);
            divID.style.display = 'block';
            divID.innerText = `Please stop playback... ${data.message}`;
            return;
        } else {
            console.log(data.message);
            divID.style.display = 'block';
            divID.innerText = data.message;
        }
    })
    .catch(error => {
        console.error('Error:', error);
        divID.style.display = 'block';
        divID.innerText = `Please stop playback... ${error}`;
    });
}
    
async function startRecording() {
    try {
        const response = await fetch('/start_recording', {
            method: 'POST'
        });
        const data = await response.json();
        console.log("Recording started", data.status);
    } catch (error) {
        console.error('Recording Error:', error);
    }
}

async function stopRecording(){
    try{
        const response = await fetch('/stop_recording', {
            method: 'POST'
        });
        const data = await response.json();
        console.log(data.status);
    } catch (error) {   
        console.error('Recording Error:', error);
    }
}
function getTranscription() {
    try {
        const response = fetch('/get_test_transcription', {
            method: 'POST'
        })
        const data = response.json();
        console.log(data.transcription);
        return data.transcription;
    } catch (error) {
        console.error('Error getting transcription:', error);
    }
}
async function processSERTest() {
    try {
        const response = await fetch('/process_ser_test', {
            method: 'POST'
        });
        const data = await response.json();
        console.log(data.status);
    } catch (error) {
        console.error('SER Test Error:', error);
    }
}
function getSERQuestion(){
    fetch('/get_ser_question', {
        method: 'GET'
    })
    .then(response => response.json())
    .then(data => {
        return data.question; 
    })
    .catch(error => {
        console.error('Error fetching SER question:', error);
        return "Couldn't get question"; 
    });
}
async function submitSERAnswer(){
    fetch("/process_ser_answer", { method: "POST" })
        .then(response => {
            return response.json();
        })
        .then(data => {
            if (data.status === 'error') {
                document.getElementById("status").innerHTML = data.message;
                document.getElementById("status").style.display = "block";
                document.getElementById("status").disabled = false;
            } else {
                document.getElementById("status").innerHTML = data.message;
                document.getElementById("status").style.display = "block";
                document.getElementById("status").disabled = false;
            }
        })
        .catch(error => {
            console.error('Error processing SER answer:', error);
            document.getElementById("status").innerHTML = "Error occurred while processing the answer.";
            document.getElementById("status").style.display = "block";
            document.getElementById("status").disabled = false;
        });
}

function setDevice() {
    const audioDevices = document.getElementById('audioDevices');
    const selectedDeviceIndex = audioDevices.value;
    console.log('Selected Device Index:');
    console.log(selectedDeviceIndex);
    fetch('/set_device', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({device_index: selectedDeviceIndex})
    })
    .then(response => response.json())
    .then(data => {
            console.log(data.message);
    })
    .catch(error => alert('Error:' + error));
}
function toggleVis(divID) {
    const element = document.getElementById(divID);
    if (element.style.display === "none") {
        element.style.display = "block";
        element.disabled = false;
    } else {
        element.style.display = "none";
        element.disabled = true;
    }
}
function shutdownServer(){
    fetch('/shutdown', {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
            console.log(data.message);
    })
    .catch(error => alert('Error:' + error));
}
function fetchAudioDevices(){
    fetch('/get_audio_devices')
    .then(response => response.json())
    .then(data => {
        console.log(data)
        const audioDevicesDropdown = document.getElementById('audioDevices');
        data.forEach(device => {
            const option = document.createElement('option');
            option.value = device.index;
            option.text = device.name;
            audioDevicesDropdown.appendChild(option);
        });
        // Handle for only one device
        if(data.length === 1){
            setDevice();
        }
    })
    .catch(error => alert('Error:' + error));
}

// NOT SURE WHAT THIS IS BUT LEAVE FOR NOW
function handleOtherOption() {
    const otherOption = document.getElementById('otherOption');
    const otherText = document.getElementById('otherTextbox');
    if (otherOption.checked) {
        otherText.style.display = 'block'; 
    } else {
        otherText.style.display = 'none';  
    }
}
var restTime = 3;
// function compareToBaseline(divID) {
//     divID.style.display = 'block';
//     divID.innerText = "Comparing to baseline... Please wait.";  
//     fetch('/baseline_comparison', {
//         method: 'POST',
//         headers: {
//             'Content-Type': 'application/json'
//         }
//     })
//     .then(response => {
//         if (!response.ok) {
//             throw new Error(`Error: ${response.statusText}`);
//         }
//         return response.json();
//     })
//     .then(data => {
//         let baselineElevatedCount = 0;
//         let liveElevatedCount = 0;

//         Object.keys(data).forEach(key => {
//             const result = data[key];
//             // Check if result is valid and not null/undefined/NaN
//             if (!result || result.status === null || result.status === "NaN" || result.status === undefined) {
//                 console.warn(`Skipping ${key} due to invalid data:`, result);
//                 return;
//             }
//             if (result.status === "Elevated") {
//                 liveElevatedCount++;
//             } else if (result.status === "Lowered") {
//                 baselineElevatedCount++;
//             } else if (result.status === "Same") {
//                 baselineElevatedCount++;
//                 liveElevatedCount++;
//             }
//             console.log(data);
//         });
//         if (baselineElevatedCount > liveElevatedCount) {
//             restTime = 3;
//             divID.innerText = `Baseline comparison complete. Subject is below baseline. Rest time: ${restTime} minutes.`;
//         } else if (liveElevatedCount > baselineElevatedCount) {
//             restTime = 5;
//             divID.innerText = `Baseline comparison complete. Subject is above baseline. Rest time: ${restTime} minutes.`;
//         } else {
//             restTime = 3;
//             divID.innerText = `Baseline comparison complete. Subject is within baseline. Rest time: ${restTime} minutes.`;
//         }
//     })
//     .catch(error => {
//         console.error('Error comparing to baseline:', error);
//         divID.innerText = "Error comparing to baseline. Please try again.";
//     });
// }

async function startEmotibit(){
    fetch('/start_emotibit', {
            method: 'POST'
        })
        .then (response => {
            if (!response.ok) {
                throw new Error(`Error: ${response.statusText}`);
            }
            return response.json();
        })
        .then(data => {
            console.log(data.message);
            emotibitStatus.forEach(status => {  
                status.style.display = 'block';
                status.innerText = data.message;
            });
        })
        .catch(error => {
            console.error('Error starting EmotiBit stream:', error);
            emotibitStatus.forEach(status => {
                status.style.display = 'block';
                status.innerText = "Error starting EmotiBit stream.";
            });
        });
}

// function startBaseline() {
//     fetch('/start_biometric_baseline', {
//         method: 'POST'
//     })
//     .then(response => {
//         if (!response.ok) {
//             throw new Error('Network response was not ok ' + response.statusText);
//         }
//         return response.json();
//     })
//     .then(data => {
//         console.log(data.status);
//         biometricStatusMessage.style.display = 'block';
//         biometricStatusMessage.innerText = data.status;
//     })
//     .catch(error => {
//         console.error('Error:', error);
//     });
// }

// function stopBaseline() {
//     fetch("/stop_biometric_baseline", {
//         method: "POST",
//     })
//     .then(response => {
//         if (!response.ok) {
//             throw new Error(`HTTP error! status: ${response.status}`);
//         }
//         return response.json();
//     })
//     .then(data => {
//         console.log(data.status);
//         biometricStatusMessage.style.display = 'block';
//         biometricStatusMessage.innerText = data.status;
//     })
//     .catch(error => {
//         console.error('Error:', error);
//     });
// }

function playTickSound() {
    const audioContext = new (window.AudioContext || window.webkitAudioContext)();
    const oscillator = audioContext.createOscillator();
    oscillator.type = 'sine'; 
    oscillator.frequency.setValueAtTime(1000, audioContext.currentTime); 
    oscillator.connect(audioContext.destination);
    oscillator.start();
    oscillator.stop(audioContext.currentTime + 0.001); 
}

function playBeep() {
    const beepContext = new AudioContext();
    const oscillator = beepContext.createOscillator();
    const gainNode = beepContext.createGain();
    oscillator.type = 'sine'; 
    oscillator.frequency.setValueAtTime(500, beepContext.currentTime);
    gainNode.gain.setValueAtTime(0.07, beepContext.currentTime);
    oscillator.connect(gainNode);
    gainNode.connect(beepContext.destination);
    oscillator.start();
    setTimeout(() => {
        oscillator.stop();
        // audioContext.close();
    }, 300); 
}