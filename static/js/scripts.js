//Booleans to control flow.
var surveysComplete = true;
var biometricBaselineComplete = false;
var stressBaselineComplete = true;
var audioTestComplete = false;
var emotionBaselineComplete = false;
var firstStressTaskComplete = false;
var firstVRTaskComplete = false;
var firstBreak = false;
var secondStressTaskComplete = false;
var secondVRTaskComplete = false;
var secondBreak = false;

function pushTaskId(taskId){
    fetch('/set_task_id', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            task_id: taskId
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

function startClock() {
    // startTime = Date.now() - elapsedTime;  
    // clockInterval = setInterval(updateClock, 1000); 
    if(!timerInterval) {
        timerInterval = setInterval(updateClock, 1000);
    }
}

function stopClock() {
    // clearInterval(timerInterval); 
    // elapsedTime = Date.now() - startTime;
    clearInterval(timerInterval); 
    timerInterval = null;
}
        
function resetClock(){
    stopClock();
    timeLeft = initialTime;
    timerDisplay.textContent = '05:00';
}

function updateClock() {
    let minutes = Math.floor(timeLeft / 60);
    let seconds = timeLeft % 60;
    seconds = seconds < 10 ? '0' + seconds : seconds;
    timeDisplay.textContent = `${minutes}:${seconds}`;
    playTickSound();
    timeLeft--;
    if(timeLeft < 0) {
        clearInterval(timerInterval);
        timer.textContent = 'Time is up!';
        endTest();
    }
}

function playTickSound() {
    const audioContext = new (window.AudioContext || window.webkitAudioContext)();
    const oscillator = audioContext.createOscillator();
    oscillator.type = 'sine'; 
    oscillator.frequency.setValueAtTime(1000, audioContext.currentTime); 
    oscillator.connect(audioContext.destination);
    oscillator.start();
    oscillator.stop(audioContext.currentTime + 0.001); 
}

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

function getNextQuestion() {
    document.getElementById('submitAnswerButton').disabled = true;  
    fetch('/get_question', {
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
        if (data.question) {
            let testContainerId = `test_${data.test_number}_container`;
            let testContainer = document.getElementById(testContainerId);
            
            testContainer.style.display = 'block';
            testContainer.innerHTML = `
                <h2>Test ${data.test_number}</h2>
                <div id="questionsContainer_${data.test_number}">${data.question}</div>
            `;
            document.getElementById(`questionsContainer_${data.test_number}`).innerText = data.question;

            startRecording()
                .then(() => {
                    document.getElementById('submitAnswerButton').disabled = false;  
                })
                .catch(error => {
                    console.error('Error starting recording:', error);
                });
        } else {
            document.getElementById('status').innerText = "No more questions.";
            document.getElementById('submitAnswerButton').style.display = 'none';
            document.getElementById('uploadData').style.display = 'block';

            stopClock();
        }
    })
    .catch(error => console.error('Error fetching next question:', error));
}

function handleOtherOption() {
    const otherOption = document.getElementById('otherOption');
    const otherText = document.getElementById('otherTextbox');

    if (otherOption.checked) {
        otherText.style.display = 'block'; 
    } else {
        otherText.style.display = 'none';  
    }
}

var restTime = 8;

function compareToBaseline(label){
    fetch('/baseline_comparison', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            label: label
        })
    })
    .then(response => response.json())
    .then(data => {
        biometricBaselineData = data.baseline_means;
        biometricData = data.data_means;
        restTime = calculateTimeToRest(biometricBaselineData, biometricData);
    })
    .catch(error => {
        console.error('Error comparing to baseline:', error);
    });
}

function calculateTimeToRest(bioBaseline, bioData){
    let lowerCount = 0;
    let higherCount = 0;

    for (const key in bioBaseline){
        if(bioBaseline.hasOwnProperty(key) && bioData.hasOwnProperty(key)){
            const baselineValue = bioBaseline[key];
            const dataValue = bioData[key];
            if(baselineValue < dataValue){
                lowerCount++;
            } else if (baselineValue > dataValue){
                higherCount++;
            }
        }
    }
    let time
    if (lowerCount > higherCount){
        time = 8;
    } else {
        time = 5;
    }
    console.log(`Rest time is set to ${time} minutes.`);

    return time;
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