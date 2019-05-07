# coding=utf-8
"""thermal interface"""
import os
from time import sleep
from thermal_zone import ThermalZone, load_thermal_zone
from cli import print_table
import pprint


class ThermalManager:
    """manages all ThermalZones"""

    def __init__(self, data):
        self.thermal_zones = []
        self.load_thermal_zones(data)

    def get_json(self):
        """return data as dict for json"""
        data = dict()
        data["zones"] = [zone.get_json() for zone in self.thermal_zones]
        return data

    def load_thermal_zones(self, data):
        """load all thermal_zones in self"""
        if data is None:
            return False
        for zone in data["zones"]:
            self.thermal_zones.append(load_thermal_zone(self, zone))

    def get_all_temps(self, as_dict=False):
        """returns list of temps of all thermal_zones"""
        if as_dict:
            names = [zone.get_name() for zone in self.thermal_zones]
            temps = [zone.get_temp() for zone in self.thermal_zones]
            return dict(zip(names, temps))
        return [zone.get_temp() for zone in self.thermal_zones]

    def get_all_names(self):
        """returns list of names of all thermal_zones"""
        return [zone.get_name() for zone in self.thermal_zones]

    def get_zone(self, index=None, full_name=None):
        """returns thermal_zone described in query, None if unavailable"""
        if full_name is not None:
            try:
                return [zone for zone in self.thermal_zones if zone.full_name == full_name][0]
            except IndexError:
                return None

        if index is not None and index >= 0:
            return self.thermal_zones[index]
        return None

    def get_temp(self, index=None, name=None):
        """returns temperature of thermal_zone described in query in °C, None if unavailable"""
        if name is not None:
            index = [zone for zone in self.thermal_zones if zone.get_name() == name]
            index = index[0].get_index()
        if index is not None and index >= 0:
            return self.thermal_zones[index].get_temp()

    def get_cpu_temp(self):
        """returns temperature of "x86_pkg_temp" thermal_zone in °C, None if unavailable"""
        return self.get_temp(name="x86_pkg_temp")


if __name__ == "__main__":
    thermal_manager = ThermalManager()
    print(thermal_manager.get_all_names())

    while True:
        print(thermal_manager.get_cpu_temp())
        sleep(1)
