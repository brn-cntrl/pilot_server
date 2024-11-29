import os
import csv
import subprocess

FEATURE_NUM = {
    'IS09_emotion': 384,
    'IS10_paraling': 1582,
    'IS11_speaker_state': 4368,
    'IS12_speaker_trait': 6125,
    'IS13_ComParE': 6373,
    'ComParE_2016': 6373
}

def preprocess_audio(filepath: str, target_path: str):
    command = [
        "ffmpeg", "-i", filepath,
        "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", target_path, "-y"
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    print("FFmpeg STDOUT:", result.stdout)
    print("FFmpeg STDERR:", result.stderr)
    if result.returncode != 0:
        raise ValueError(f"Audio preprocessing failed: {result.stderr}")

def get_feature_opensmile(config, filepath: str) -> list:
    """
    Extract features using OpenSMILE and parse the last row of numerical data from the ARFF output.

    Args:
        config: Configuration object containing paths to OpenSMILE, configuration, and feature folder.
        filepath (str): Path to the input .wav file.

    Returns:
        list: Extracted numerical features.
    """
    # Use the raw chunk path for simplicity
    preprocessed_path = filepath  

    # Path for storing extracted features
    single_feat_path = os.path.join(config.feature_folder, f"single_feature_{os.path.basename(filepath)}.csv")
    os.makedirs(config.feature_folder, exist_ok=True)

    # Ensure OpenSMILE configuration file exists
    opensmile_config_path = config.opensmile_config
    if not os.path.exists(opensmile_config_path):
        raise FileNotFoundError(f"Configuration file not found: {opensmile_config_path}")

    # OpenSMILE command
    cmd = [
        config.opensmile_path,
        "-C", opensmile_config_path,
        "-I", preprocessed_path,
        "-O", single_feat_path,
        "-appendarff", "0"
    ]
    print("Executing OpenSMILE command:", " ".join(cmd))

    # Run the OpenSMILE command
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        print(f"OpenSMILE STDERR: {result.stderr.decode()}")
        raise RuntimeError(f"OpenSMILE execution failed for file {filepath}")

    # Ensure the feature file exists
    if not os.path.exists(single_feat_path):
        raise FileNotFoundError(f"{single_feat_path} not found. OpenSMILE execution failed.")

    # Read and parse the ARFF file
    with open(single_feat_path, 'r') as csv_file:
            reader = csv.reader(csv_file)
            rows = list(reader)
            print(f"Feature file content (first 5 lines): {rows[:5]}")
            last_line = rows[-1]
            return last_line[1: FEATURE_NUM[config.opensmile_config] + 1]

