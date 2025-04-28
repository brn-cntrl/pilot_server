from godirect import GoDirect
import time

def print_data(data):
    if data is not None:
        print(f"Force: {data['force']} N, Respiration Rate: {data['respirationRate']} breaths/min")

def main():
    try:
        gd = GoDirect()
        print("Connecting to Go Direct device...")
        device_name = "GDX-RB"
        device = gd.find_or_connect(device_name)

        if device is None:
            print(f"Could not connect to {device_name}.")
            return

        print(f"Connected to {device_name} - {device.name()}")

        device.start()
        print("Starting data collection...")

        try:
            while True:
                time.sleep(1)
                data = {}
                sensor_data = device.read()
                if sensor_data:
                    for item in sensor_data:
                        if item['channelName'] == 'Force':
                            data['force'] = item['values'][0]
                        elif item['channelName'] == 'Respiration Rate':
                            data['respirationRate'] = item['values'][0]
                    print_data(data)
        except KeyboardInterrupt:
            print("\nStopping data collection...")
        finally:
            device.stop()
            gd.close()
            print("Disconnected.")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()