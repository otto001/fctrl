from hwmon import get_all_hwmons
from thermal_zone import ThermalZone
from time import sleep
import os


def detect():
    hwmons = get_all_hwmons()
    print("Finding all hardware monitors...")
    sleep(2)
    print("The following hardware monitors were found on you system:")
    for hwmon in hwmons:
        print("\t" + hwmon.name +
              "\n\t\tvendor: " + hwmon.vendor.name + "\t" * 5 + "type: " + hwmon.type +
              "\n\t\tcooling devices: " + str(len(hwmon.cooling_devices)) + "\t" * 3 + "thermal zones: " + str(len(hwmon.thermal_zones)))

    sleep(1)
    print("\nListing all thermal zones...")
    sleep(2)

    for hwmon in hwmons:
        if len(hwmon.thermal_zones) == 0:
            continue
        print("\n" + hwmon.name + ":")
        for thermal_zone in hwmon.thermal_zones:
            print(thermal_zone.name + "\t"*2 + str(thermal_zone.temp) + "°C")

    print("\nAttempting to filter out irrelevant thermal zones...")

    for hwmon in hwmons:
        if len(hwmon.thermal_zones) == 0:
            continue
        print("\n" + hwmon.name + ":")
        i = 0
        while i < (len(hwmon.thermal_zones)):
            if hwmon.thermal_zones[i].seems_legit():
                print(hwmon.thermal_zones[i].name + "\t" * 2 + str(hwmon.thermal_zones[i].temp) + "°C")
                i += 1
            else:
                del hwmon.thermal_zones[i]











    """allow user to detect and name relevant CoolingDevices"""

    user = input("Your fans will now be turned on and off repeatedly. Continue? [YES|no]>")
    if user == "no" or user == "n":
        return False

    detect_threshold_mode = None

    self.set_all_to_manual()

    for device in self.cooling_devices:
        print("\nCooling device " + str(device.index) + " ramping up, stopping all others briefly")
        for i in range(0, len(self.cooling_devices)):
            if self.cooling_devices[i].index == device.index:
                device.set_speed(100)
            else:
                self.cooling_devices[i].set_speed(0)

        sleep(3)
        user = input("Enter new name for cooling device>")
        skipped = False
        if len(user) > 0:
            device.set_name(user)
            print("New name is set")
        else:
            print("Skipped")
            skipped = True

        for d in self.cooling_devices:
            d.set_speed(50)

        if not skipped:
            detect_threshold = True
            if detect_threshold_mode is None:
                user = input("Do you want to detect the devices threshold now? [always|YES|no|never]")
                if user == "always":
                    detect_threshold = detect_threshold_mode = True
                elif user == "never":
                    detect_threshold = detect_threshold_mode = False
                elif user in ["no", "n"]:
                    detect_threshold = False
            else:
                detect_threshold = detect_threshold_mode

            if detect_threshold:
                device.user_detect_speeds()

        device.set_speed(50)
        print("Briefly restoring temperatures")
        sleep(3)

    for device in self.cooling_devices:
        device.set_speed(50)

    print("Finished")

    return True
