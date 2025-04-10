import pytest
from metrics_functions import *
import csv

def read_csv_file(filename):
    data = []
    with open(filename, newline='', encoding='utf-8') as csvfile:
        csvreader = csv.reader(csvfile)
        for row in csvreader:
            data.append(row)
    return data

def window_data(data, window_size, step_size): # Experiment with the window size and step size to check results
    for i in range(0, len(data) - window_size + 1, step_size):
        yield data[i:i + window_size]

def test_calculate_hrv():
    # Simulate 5 minutes of beat intervals at 75 bpm → BI ~ 800ms ± 50ms
    # This is assuming a mean of 800ms BI for healthy adults but maybe we should check against real data.
    bi_values = np.random.normal(loc=800, scale=50, size=300) 
    results = []

    for window in window_data(bi_values, window_size=30, step_size=10):
        hrv = calculate_hrv(window)
        assert hrv is not None
        results.append(hrv)
    assert len(results) > 0
    print("HRV results")
    for i, r in enumerate(results):
        print(f"  Window {i + 1}: {r:.4f}")

    print("calculate_hrv passed.")

def test_calculate_rr():
    # Simulate 5 minutes of PPG data sampled at 25 Hz (We can change "size" to 100 if need be)
    # This seems to be a reasonable way to simulate ppg and fluctuation but we should use real data.
    ppg_values = np.random.normal(loc=1, scale=0.05, size=25 * 60 * 5)
    
    results = []
    
    # Apply the window function 
    for window in window_data(ppg_values, window_size=100, step_size=50): # Change window and step size here
        rr_result = calculate_rr(window) 
        assert rr_result is not None, f"RR calculation failed for window {window}"

        # HELP - This assertion will always fail because the math is producing values of 0.0
        assert 10 < rr_result < 25, f"RR result {rr_result} out of expected range" # 10 and 25 are representative of normal human resp rates
        results.append(rr_result)
    
    # Check that we got some results
    assert len(results) > 0, "No RR results were generated"
    
    # Print out all results for inspection (you can remove this or log it as needed)
    print("RR Results: ", results)

def main():
    # sample_data = read_csv_file('sample_data.csv')
    

    print("Running unit tests...")
    print("Testing calculate_hrv...")
    test_calculate_hrv()
    print("Testing calculate_rr...")
    test_calculate_rr()

if __name__ == "__main__":
    main()