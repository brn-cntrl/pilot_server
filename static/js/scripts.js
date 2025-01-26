function updateCondition(parentDiv, event) {
    const selectElement = document.querySelector(`#${parentDiv} select`);
    const selectedCondition = selectElement.value;
    let currentEventMarker = `${event}_${selectedCondition}`
    localStorage.setItem('currentEventMarker', currentEventMarker);
    console.log(currentEventMarker);
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

function recordTask(eventMarker, action, question){
    fetch('/record_task_audio', { method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            'event_marker': eventMarker,
            'action': action,
            'question': question
        })
     })
    .then(response => response.json())
    .then(data => {
        console.log(data.status);
    })
    .catch(error => console.error('status:', error));
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

// function playTickSound() {
//     const audioContext = new (window.AudioContext || window.webkitAudioContext)();
//     const oscillator = audioContext.createOscillator();
//     oscillator.type = 'sine'; 
//     oscillator.frequency.setValueAtTime(1000, audioContext.currentTime); 
//     oscillator.connect(audioContext.destination);
//     oscillator.start();
//     oscillator.stop(audioContext.currentTime + 0.001); 
// }

function checkActiveStream() {
    return fetch('/get_stream_active', {
        method: 'GET'
    })
    .then(response => response.json())
    .then(data => {
        return data.stream_active; 
    })
    .catch(error => {
        console.error('Error fetching stream status:', error);
        return false; 
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
function compareToBaseline() {
    fetch('/baseline_comparison', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`Error: ${response.statusText}`);
        }
        return response.json();
    })
    .then(data => {
        let baselineElevatedCount = 0;
        let liveElevatedCount = 0;
        Object.keys(data).forEach(key => {
            const result = data[key];
            if (result.elevated === "Live data") {
                liveElevatedCount++;
            } else if (result.elevated === "Baseline data") {
                baselineElevatedCount++;
            }
        });
        if (baselineElevatedCount > liveElevatedCount) {
            restTime = 3;
        } else if (liveElevatedCount > baselineElevatedCount) {
            restTime = 8;
        } else {
            restTime = 3;
        }
        console.log('Determined restTime:', restTime);
    })
    .catch(error => {
        console.error('Error comparing to baseline:', error);
    });
}
async function startEmotibit(){
    try{
        const response = await fetch('/start_emotibit_stream', {
            method: 'POST'
        });
        const data = await response.json();
        console.log(data.status);
        return data.status;
    } catch (error) {
        console.error('Error starting EmotiBit stream:', error);
        return 'error';
    }
}
function startBaseline() {
    fetch('/start_biometric_baseline', {
        method: 'POST'
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok ' + response.statusText);
        }
        return response.json();
    })
    .then(data => {
        console.log(data.status);
    })
    .catch(error => {
        console.error('Error:', error);
    });
}
function stopBaseline() {
    fetch("/stop_biometric_baseline", {
        method: "POST",
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        console.log(data.status);
    })
    .catch(error => {
        console.error('Error:', error);
    });
}
function emotibitRecording(button, action){
    /*
    Function to start or stop recording from EmotiBit
    Requires taskID to identify label of particular task. 
    This is used to label the EmotiBit data in the database.
    */
    const taskID = button.id;
    statusId1 = document.getElementById("emotibitStatus1");
    statusId2 = document.getElementById("emoitbitStatus2");
    if(action == 'start'){
        fetch('/start_emotibit', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok ' + response.statusText);
            }
            return response.json();
        })
        .then(data => {
            console.log('Success:', data);
        })
        .catch(error => {
            console.error('Error:', error);
        });
        if (taskID == 'taskID1'){
            statusId1.style.display = 'block';
        } else if (taskID == 'taskID2'){
            statusId2.style.display = 'block';
        }
    } else if (action == 'stop'){
        fetch('/stop_emotibit', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok ' + response.statusText);
            }
            return response.json();
        })
        .then(data => {
            console.log('Success:', data);
        })
        .catch(error => {
            console.error('Error:', error);
        });
        fetch('/push_emotibit_data', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                label: taskID
            })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok ' + response.statusText);
            }
            return response.json();
        })
        .then(data => {
            console.log('Success:', data);
            if (taskID == 'taskID1'){
                statusId1.style.display = 'block';
                statusId1.innerHTML = 'EmotiBit data saved.';
            } else if (taskID == 'taskID2'){
                statusId2.style.display = 'block';
                statusId2.innerHTML = 'EmotiBit data saved.';
            }
        })
        .catch(error => {
            console.error('Error:', error);
            if (taskID == 'taskID1'){
                statusId1.style.display = 'block';
                statusId1.innerHTML = 'An error occurred. EmotiBit data not saved.';
            } else if (taskID == 'taskID2'){
                statusId2.style.display = 'block';
                statusId2.innerHTML = 'An error occurred. EmotiBit data not saved.';
            }
        });
    }
}
async function loadSurveys(){
    try {
        const response = await fetch('/get_surveys');
        const surveys = await response.json();
        const container = document.getElementById('surveyButtons');
        container.innerHTML = '';
        console.log(surveys);
        surveys.forEach(survey => {
            if (survey.url.trim()) {
                const button = document.createElement('button');
                button.textContent = survey.name.charAt(0).toUpperCase() + survey.name.slice(1);
                button.onclick = () => window.open(`/survey/${survey.name}`, '_blank');
                container.appendChild(button);
                const br1 = document.createElement('br');
                const br2 = document.createElement('br');
                container.appendChild(br1);
                container.appendChild(br2);
            }
        });
        // document.getElementById("surveyStatus").style.display = "none";
    } catch(error){
        console.error('Error fetching surveys:', error);
        // document.getElementById("surveyStatus").style.display = "block";
    } 
}