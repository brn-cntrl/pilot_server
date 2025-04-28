from godirect import GoDirect
from gdx import gdx
godirect = GoDirect(use_ble=True, use_usb=True)
print("GoDirect v"+str(godirect.get_version()))
print("\nSearching...", flush=True, end ="")
device = godirect.get_device(threshold=-100)
# gdx = gdx.gdx()
# gdx.select_sensors([0,1]

if device != None and device.open(auto_start=False):
	print("connecting.\n")
	print("Connected to "+device.name)
	sensor_list = device.list_sensors()
	print("Sensors found: "+ str(sensor_list))
	device.enable_sensors([1,2,3,4])
	device.start(period=1000)
	print('start')
	
	sensors = device.get_enabled_sensors()
	print("Available sensors:")
	if device.read():
		for sensor in sensors:
			print(sensor.sensor_description)

	print("Connected to "+device.name)
	print("Reading 100 measurements")
	for i in range(0,100):
		if device.read():
			for sensor in sensors:
				print(sensor.sensor_description+": "+str(sensor.values))
				sensor.clear()
	device.stop()
	device.close()
else:
	print("No Go Direct devices found.")

godirect.quit()