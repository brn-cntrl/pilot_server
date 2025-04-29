import pytest
from metrics_functions import *
import csv

def read_csv_file(filename):
    pg_values = []
    bi_values = []

    with open(filename, newline='', encoding='utf-8') as csvfile:
        csvreader = csv.reader(csvfile)

        for row in csvreader:
            if len(row) >= 7:
                sensor_type = row[3]
                payload = row[6]
                
                try:
                    values = [float(x) for x in payload.split(',') if x.strip() != '']
                except ValueError:
                    continue

                if sensor_type == 'PG':
                    pg_values.extend(values)
                elif sensor_type == 'BI':
                    bi_values.extend(values)

    print("PG values: ", pg_values)
    print("BI values: ", bi_values)

    return pg_values, bi_values

def window_data(values, window_size, step_size): # Experiment with the window size and step size to check results

    for start in range(0, len(values) - window_size + 1, step_size):
        end = start + window_size
        yield values[start:end]

def test_calculate_hrv(bi_values):
    results = []
    max_print = 20 # Change this to print more or less to terminal

    for window_values in window_data(bi_values, window_size=30, step_size=10):
        hrv = calculate_hrv(window_values)
        assert hrv is not None
        results.append(hrv)

    assert len(results) > 0

    print(f"HRV results (showing first {min(len(results), max_print)} of {len(results)}):")

    for i, val in enumerate(results[:max_print]):
        print(f" Window {i + 1}: HRV = {val:.4f}")

    print("calculate_hrv passed.")

def test_calculate_rr(ppg_values):
    results = []
    max_print = 20 # Change this to print more or less to terminal

    for window_values in window_data(ppg_values, window_size=100, step_size=50):
        rr_result = calculate_rr(window_values)

        assert rr_result is not None, f"RR calculation failed for window {window_values}"
        results.append(rr_result)

    assert len(results) > 0, "No RR results were generated"

    print(f"RR results (showing first {min(len(results), max_print)} of {len(results)}):")

    for i, val in enumerate(results[:max_print]):
        print(f" Window {i + 1}: RR = {val:.4f}")

    print("calculate_rr passed.")

def main():
    pg_values, bi_values = read_csv_file('emotibit_data.csv')
    print("Running unit tests...")
    print("Testing calculate_hrv...")
    test_calculate_hrv(bi_values)
    print("Testing calculate_rr...")
    test_calculate_rr(pg_values)

if __name__ == "__main__":
    main()