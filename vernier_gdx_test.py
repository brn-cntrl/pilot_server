from gdx import gdx
gdx = gdx.gdx()


gdx.open(connection='ble')   # change to 'ble' for Bluetooth connection

print('Device information: ')
print('-------------------')
device_info = gdx.device_info() 
device_name = device_info[0]
device_description = device_info[1]  
battery = device_info[2]  
charger_state = device_info[3]
rssi = device_info[4]  
print("device name = ", device_name)
print("device description = ", device_description)
print("battery charge % = ", battery)
print("charging state of the battery = ", charger_state)
print("rssi (bluetooth signal) = ", rssi)
print('\n')

print('Sensor information: ')
print('-------------------')
sensor_info = gdx.sensor_info() 
for info in sensor_info:
    sensor_number = info[0]
    sensor_description = info[1]  
    sensor_units = info[2]  
    incompatible_sensors = info[3]  
    print("sensor number = ", sensor_number)
    print("sensor description = ", sensor_description)
    print("sensor units = ", sensor_units)
    print("incompatible sensors = ", incompatible_sensors)
    print()

# Disconnect the Go Direct connection
gdx.close()