from hwmon import get_all_hwmons
from thermal_zone import ThermalZone, ThermalCpu, ThermalGpu
from time import sleep
import os
from cli import color, print_table, printl, sleep_print


def _detect_thermal_zones(control, hwmons):
    print(color("\nListing all thermal zones:", "bold"))

    # prints all found thermale_zones
    for hwmon in hwmons:
        if len(hwmon.thermal_zones) == 0:
            continue
        print("\n" + hwmon.name + ":")
        print_table(None, [[zone.name, str(zone.temp) + "°C"] for zone in hwmon.thermal_zones])

    print(color("\nAttempting to filter out irrelevant thermal zones...", "bold"))
    # filter out every temp zone with invalid temps
    for hwmon in hwmons:
        if len(hwmon.thermal_zones) == 0:
            continue
        i = 0
        while i < (len(hwmon.thermal_zones)):
            if hwmon.thermal_zones[i].seems_legit():
                i += 1
            else:
                del hwmon.thermal_zones[i]

    thermal_zones = []

    # adding all thermazones to thermal_zones list
    # creating thermalgroups (CPU, GPU)
    for hwmon in hwmons:
        for thermal_zone in hwmon.thermal_zones:
            thermal_zones.append(thermal_zone)
        if hwmon.type == "GPU" and len(hwmon.thermal_zones) == 1:
            hwmon.thermal_zones[0].name = "GPU1"
            thermal_gpu = ThermalGpu(control.thermal_manager).from_hwmon(hwmon.thermal_zones[0].base_path, hwmon)
            thermal_zones.append(thermal_gpu)

        if hwmon.type == "CPU":
            thermal_cpu = ThermalCpu(control.thermal_manager).from_hwmon("", hwmon)
            thermal_zones.append(thermal_cpu)

    print(color("Found following thermal zones:", "bold"))
    thermal_zones = sorted(thermal_zones, key=lambda x: x.full_name)
    print_table(["name", "temp"], [[zone.full_name, str(zone.temp) + "°C"] for zone in thermal_zones])

    return thermal_zones


def _detect_cooling_device_threshold(device):
    printl("Getting fan started: ")
    device.set_speed(100)
    success = device.wait_for_fan_response(response=(lambda d: d.rpm > 0), p=True)
    if not success:
        print(color(" ERROR: Device unavailable", "fail"))
        return False

    print(color(" OK", "green"))

    printl("Stopping fan: ")
    device.set_speed(0)

    success = device.wait_for_fan_response(response=(lambda d: d.rpm == 0), p=True, timeout=10)
    if not success:
        print(" Unable to stop fan")
        device.threshold_speed = 0

        user_in = input("Is the fan actually a pump? [yes|NO]: ").lower().strip()
        if user_in in ["yes", "y"]:
            device.is_pump = True
        else:
            device.is_pump = False

    if not device.is_pump:
        sleep_print(6)
        print(color(" OK", "green"))

    data = [device.rpm]
    threshold_found = False

    printl("Slowly ramping up fan: ")
    device.set_speed(8)

    while device.speed < 100:
        cur_speed = device.speed
        if not threshold_found:
            cur_speed += 2
            device.set_speed(cur_speed)
            sleep_print(3)
            if device.rpm > 0:
                threshold_found = True
                device.threshold_speed = cur_speed + 2
                device.set_speed(cur_speed - cur_speed % 10)
                sleep_print(3)

        else:
            device.set_speed(cur_speed + 10)
            sleep_print(5)

        if cur_speed % 10 == 0:
            data.append(device.rpm)

    print(color(" OK", "green"))
    device.rpm_curve = data
    print(data)
    return True


def _check_cooling_device_threshold(device):
        printl("Checking threshold speed: ")

        device.set_speed(0)
        success = device.wait_for_fan_response(response=(lambda d: d.rpm == 0), p=True)
        if not success:
            print(" ERROR: Could not stop fan")
            return False

        sleep_print(12)

        device.set_speed(device.threshold_speed)
        success = device.wait_for_fan_response(response=(lambda d: d.rpm > 0), p=True)
        if success:
            print(" OK")
        else:
            print(" ERROR: Could not start fan")
            return False
        return True


def _detect_cooling_device_speeds(device):
    old_speed = device.speed
    print("\nDetecting max & threshold speed of device " + device.name + " (" + str(device.index) + ")")

    success = _detect_cooling_device_threshold(device)
    if not success:
        return False
    elif device.is_pump:
        print("Success! Detected: \n\t\tmax-speed: " + str(device.max_speed) + "rpm\n\t\tis pump:    yes")
        return True

    success = _check_cooling_device_threshold(device)
    if not success:
        return False

    print("Success! Detected: \n\t\tmax-speed: " + str(device.max_speed) + "rpm\n\t\tthreshold: " + str(
        device.threshold_speed) + "%")
    device.set_speed(old_speed)
    return success


def _detect_cooling_devices(control, hwmons):
    """allow user to detect and name relevant CoolingDevices"""

    print(color("\nListing all cooling devices:", "bold"))

    # prints all found cooling devices
    for hwmon in hwmons:
        if len(hwmon.cooling_devices) == 0:
            continue
        print("\n" + hwmon.name + ":")
        print_table(None, [[device.name, str(device.speed) + "%", str(device.rpm) + "rpm"] for device in hwmon.cooling_devices])

    user = input(color("Your fans will now be turned on and off repeatedly. Continue? [YES|no]>", "bold"))
    if user == "no" or user == "n":
        return False

    cooling_devices = []

    print(color("Attempting to filter out non existent cooling devices...", "bold"))
    # filter out every cooling device which ist not connected
    for hwmon in hwmons:
        if len(hwmon.cooling_devices) == 0:
            continue
        i = 0
        while i < (len(hwmon.cooling_devices)):
            if hwmon.cooling_devices[i].test_exists():
                cooling_devices.append(hwmon.cooling_devices[i])
                i += 1
            else:
                del hwmon.cooling_devices[i]

    print(color("\nRemaining cooling devices:\n", "bold"))
    # print all remaining cooling devices
    print_table(["name", "speed", "rpm"], [[device.full_name, str(device.speed) + "%", str(device.rpm) + "rpm"]
                                           for device in cooling_devices])

    detect_threshold_mode = None

    print(color("\nWe will now start the process of identifying and naming your cooling devices.\n"
                "They will be ramping up and down one by one.", "bold"))
    try:
        input(color("Press ENTER to start or CTRL-C to cancel>", "bold"))
    except KeyboardInterrupt:
        return False

    for device in cooling_devices:
        print("\nCooling device " + str(device.index) + " ramping up, stopping all others briefly")
        for device2 in cooling_devices:
            if device2.index == device.index:
                device.set_speed(100)
            else:
                device2.set_speed(0)

        sleep(3)
        user = input("Enter new name for cooling device>")
        skipped = False
        if len(user) > 0:
            device.set_name(user)
            print("New name is set")
        else:
            print("Skipped")
            skipped = True

        for d in cooling_devices:
            d.set_speed(50)

        if not skipped:
            detect_threshold = True
            if detect_threshold_mode is None:
                user = input("Do you want to detect the devices threshold now? [always|YES|no|never]")
                if user in ["always", "a"]:
                    detect_threshold = detect_threshold_mode = True
                elif user == "never":
                    detect_threshold = detect_threshold_mode = False
                elif user in ["no", "n"]:
                    detect_threshold = False
            else:
                detect_threshold = detect_threshold_mode

            if detect_threshold:
                _detect_cooling_device_speeds(device)

        device.set_speed(50)
        print("Briefly restoring temperatures")
        sleep(3)

    for device in cooling_devices:
        device.set_speed(50)

    print("Finished")

    return cooling_devices


def detect(control):
    hwmons = get_all_hwmons(control)

    print(color("Finding all hardware monitors...", "bold"))
    print(color("The following hardware monitors were found on you system:", "bold"))

    for hwmon in hwmons:
        print("\n" + hwmon.name+":")
        print_table(None, [["vendor:" + hwmon.vendor.name, "type: " + hwmon.type],
                           ["cooling devices: " + str(len(hwmon.cooling_devices)),
                            "thermal zones: " + str(len(hwmon.thermal_zones))]])

    thermal_zones = _detect_thermal_zones(control, hwmons)
    cooling_devices = _detect_cooling_devices(control, hwmons)

    print(color("\n\n====SUMMARY====", "bold", "header"))
    print_table(["name", "temp"], [[zone.full_name, str(zone.temp) + "°C"] for zone in thermal_zones])
    print()
    print_table(["name", "speed", "rpm"], [[device.full_name, str(device.speed) + "%", str(device.rpm) + "rpm"]
                                           for device in cooling_devices])

    user = input(color("Do you want to apply the results [YES|no]>", "bold"))
    if user == "no" or user == "n":
        return False
    control.thermal_manager.thermal_zones = thermal_zones
    control.cooling_manager.cooling_devices = cooling_devices














