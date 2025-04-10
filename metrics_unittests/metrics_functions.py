import numpy as np
from scipy.signal import butter, filtfilt
from scipy.signal import hilbert

# NOTE: All algorithms in these functions were obtained from Chat and need to be verified. 

def calculate_hrv(bi_values) -> float:
        """
        Calculate the Heart Rate Variability (HRV) using the Root Mean Square of Successive Differences (RMSSD) method.
        This function computes HRV based on a series of beat interval (BI) values. The RMSSD is a commonly used metric 
        to assess the variability in heart rate, which is an indicator of autonomic nervous system activity.
        Returns:
            float: The calculated RMSSD value representing HRV, or None if there are insufficient BI values.
        Notes:
            - The input `bi_values` is expected to be a NumPy array of beat interval values in milliseconds.
            - At least 30 BI values are required to compute HRV. If fewer values are provided, the function returns None.
            - The BI values are converted to seconds before calculating the RMSSD.
        """

        # HELP - VERIFY THIS
        intervals = np.diff(bi_values) / 1000.0  # Convert to seconds
        rmssd = np.sqrt(np.mean(np.square(np.diff(intervals))))
        return rmssd

def calculate_rr(ppg_values) -> float:
    """
    Calculate the respiratory rate (RR) from photoplethysmogram (PPG) values.
    This function processes PPG values to estimate the respiratory rate in breaths per minute.
    It applies a bandpass filter to isolate the respiratory frequency range, computes the 
    signal envelope using the Hilbert transform, and performs a Fast Fourier Transform (FFT) 
    to identify the dominant respiratory frequency.
    Returns:
        float: The estimated respiratory rate in breaths per minute. Returns None if there 
        are insufficient PPG values (< 100) to perform the calculation.
    Notes:
        - Ensure the PPG values are sampled at 25 Hz.
        - Verify the bandpass filter coefficients (0.1, 0.5) and the sampling rate (100) 
          used in the `bandpass_filter` function.
    """
    # Bandpass filter
    # HELP - VERIFY THE COEFFICIENTS (0.1, 0.5) AND SAMPLING RATE (100)
    filtered_signal = bandpass_filter(ppg_values, 0.1, 0.5, 100)  # Assuming 25 Hz sampling rate
    envelope = np.abs(hilbert(filtered_signal))

    # FFT for respiratory frequency
    fft_result = np.fft.rfft(envelope)
    freqs = np.fft.rfftfreq(len(envelope), 1 / 25)  # 25 Hz sampling rate
    resp_freq = freqs[np.argmax(np.abs(fft_result))]
    return resp_freq * 60  # Convert to breaths per minute

def bandpass_filter(data, lowcut, highcut, fs, order=4): # HELP - verify the order, lowcut, and highcut
    """
    Apply a bandpass filter to the input data.
    This function uses a Butterworth filter to allow frequencies within a specified range 
    (lowcut to highcut) to pass through while attenuating frequencies outside this range.
    Parameters:
        data (array-like): The input signal to be filtered.
        lowcut (float): The lower cutoff frequency of the bandpass filter in Hz.
        highcut (float): The upper cutoff frequency of the bandpass filter in Hz.
        fs (float): The sampling frequency of the input signal in Hz.
        order (int, optional): The order of the Butterworth filter. Default is 4.
    Returns:
        numpy.ndarray: The filtered signal.
    Raises:
        ValueError: If lowcut or highcut are not within the valid range (0 < lowcut < highcut < fs/2).
        ValueError: If the sampling frequency (fs) is not greater than 0.
    Notes:
        - The function uses the `butter` function to design the filter and `filtfilt` 
          for zero-phase filtering to avoid phase distortion.
        - Ensure that the input signal `data` is properly preprocessed (e.g., detrended) 
          before applying the filter for optimal results.
    """
    nyquist = 0.5 * fs
    low = lowcut / nyquist
    high = highcut / nyquist
    b, a = butter(order, [low, high], btype="band")
    return filtfilt(b, a, data)