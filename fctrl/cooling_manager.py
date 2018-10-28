# coding=utf-8
"""thermal interface"""
import os
from time import sleep
from cooling_device import CoolingDevice


class CoolingManager:
    """manages all CoolingDevices"""

    def __init__(self, data):
        self.cooling_devices = []
        self.load_all_cooling_devices(data)

    def load_all_cooling_devices(self, data=None):
        """load all potential cooling devices"""
        if len(self.cooling_devices) != 0 and data is None:  # return if cooling device already loaded
            return False

        self.cooling_devices = []  # empty current list

        directory = "/sys/class/hwmon/hwmon2"  # base directory for my specific pc TODO find fans on all pcs!
        all_devices = os.listdir(directory)  # list all entries in hwmon
        cooling_devices = set([device[3] for device in all_devices if device[:3] == "pwm"])  # select fans

        for d in cooling_devices:
            d_data = None
            if data is not None:  # append meta data if exists
                for pot_d_data in data["devices"]:
                    if str(pot_d_data["index"]) == d:
                        d_data = pot_d_data
                        break
            self.cooling_devices.append(CoolingDevice(d, data=d_data))  # create CoolingDevice object

        return True

    def set_all_to_manual(self):
        for d in self.cooling_devices:
            d.set_to_manual()
        sleep(1)

    def get_all_speeds(self, as_dict=False):
        """returns list of temps of all thermal_zones"""
        if as_dict:
            names = [zone.get_name() for zone in self.cooling_devices]
            temps = [zone.get_speed() for zone in self.cooling_devices]
            return dict(zip(names, temps))
        return [zone.get_speed() for zone in self.cooling_devices]

    def get_all_names(self):
        """returns list of names of all thermal_zones"""
        return [zone.get_name() for zone in self.cooling_devices]

    def get_device(self, index=None, name=None):
        """returns thermal_zone described in query, None if unavailable"""
        if name is not None:
            return [zone for zone in self.cooling_devices if zone.name == name][0]

        if index is not None and index >= 0:
            return [zone for zone in self.cooling_devices if zone.index == index][0]

        return None

    def get_speed(self, index=None, name=None):
        """returns temperature of thermal_zone described in query in °C, None if unavailable"""
        if name is not None:
            zones = [zone for zone in self.cooling_devices if zone.get_name() == name]
            return zones[0].speed
        if index is not None and index >= 0:
            return self.cooling_devices[index].speed

    @staticmethod
    def grub_setup():
        """sets up grub for acpi"""
        os.system("GRUB_CMDLINE_LINUX_DEFAULT=\"quiet splash acpi_enforce_resources=lax\"")
        os.system("sudo update-grub")
        user = input("reboot now [yes|NO]>")
        if user == "yes":
            os.system("sudo reboot")

    def get_json(self):
        """return data as dict for json"""
        data = dict()
        data["devices"] = [device.get_json() for device in self.cooling_devices]
        return data

    def set_all_safe_speed(self):
        for device in self.cooling_devices:
            device.set_speed(40)

    def user_detect_speeds(self):
        user = input("Your fans will now be turned on and off repeatedly. Continue? [YES|no]>")
        if user == "no" or user == "n":
            return False

        self.set_all_to_manual()
        sleep(1)
        self.set_all_safe_speed()
        for device in self.cooling_devices:
            device.user_detect_speeds()

        print("Finished!")

    def user_detect(self):
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
