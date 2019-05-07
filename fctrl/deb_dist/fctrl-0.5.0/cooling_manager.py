# coding=utf-8
"""thermal interface"""
import os
from time import sleep
from cooling_device import CoolingDevice


class CoolingManager:
    """manages all CoolingDevices"""

    def __init__(self, control, data):
        self.cooling_devices = []
        self.control = control
        self.load_all_cooling_devices(data)

    def load_all_cooling_devices(self, data):
        """load all thermal_zones in self"""
        if data is None:
            return False
        for device in data["devices"]:
            self.cooling_devices.append(CoolingDevice(self, device))

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
        try:
            if name is not None:
                return [device for device in self.cooling_devices if device.name == name][0]

            if index is not None and index >= 0:
                return [zone for zone in self.cooling_devices if zone.index == index][0]
        except IndexError:
            return None
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
            device.set_speed(32)

    def update_devices(self):
        for device in self.cooling_devices:
            device.update()
