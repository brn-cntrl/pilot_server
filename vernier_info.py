from godirect import GoDirect
godirect = GoDirect()
device = godirect.get_device()
device.enable_sensors([1,2])
if device != None and device.open(auto_start=True):
    sensors = device.get_enabled_sensors()
    print("Connected to "+device.name)
    print("Available sensors:")
    if device.read():
        for sensor in sensors:
            print(sensor.sensor_description)
    device.stop()
    device.close()
	
# if device != None and device.open(auto_start=True):
# 	sensors = device.get_enabled_sensors()
# 	print("Connected to "+device.name)
# 	print("Reading 10 measurements")
# 	for i in range(0,10):
# 		if device.read():
# 			for sensor in sensors:
# 				print(sensor.sensor_description+": "+str(sensor.values))
# 				sensor.clear()
# device.stop()
# device.close()
godirect.quit()