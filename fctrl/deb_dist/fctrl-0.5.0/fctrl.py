#!/usr/bin/env python3
# coding=utf-8

from thermal_manager import ThermalManager
from cooling_manager import CoolingManager

import json
from time import sleep
import os

record = False
test_clf = True


def lerp(a, b, alpha):
    """linear interpolation"""
    return b * alpha + a * (1-alpha)


class FanControl:
    """central object, manages thermals, fans, fancurves"""
    config_path = "/etc/fctrl/.config"

    def __init__(self):
        data = self.load()

        cooling_data, thermal_data = None, None
        if data is not None:
            cooling_data, thermal_data = data["cooling"], data["thermal"]
        self.__thermal_manager = ThermalManager(thermal_data)
        self.__cooling_manager = CoolingManager(self, cooling_data)

        # print(color("\n\n====LOAD SUMMARY====", "bold", "header"))
        # print_table(["name", "temp"], [[zone.full_name, str(zone.temp) + "°C"]
        #                                for zone in self.__thermal_manager.thermal_zones])
        # print()
        # print_table(["name", "speed", "rpm"], [[device.full_name, str(device.speed) + "%", str(device.rpm) + "rpm"]
        #                                        for device in self.__cooling_manager.cooling_devices])

        self.__curves = []

    def load(self):
        """load from file"""
        try:
            data = json.loads(open(self.config_path).read())
        except ValueError:
            print("save file corrupted")
            return
        except (OSError, FileNotFoundError):
            print("file not found")
            return

        return data

    @property
    def thermal_manager(self):
        """returns thermal manager"""
        return self.__thermal_manager

    @property
    def cooling_manager(self):
        """returns cooling manager"""
        return self.__cooling_manager

    def save(self):
        """saves to file"""
        data = dict()
        data["cooling"] = self.cooling_manager.get_json()
        data["thermal"] = self.thermal_manager.get_json()
        data = json.dumps(data)
        os.makedirs(os.path.basename(self.config_path))
        with open(self.config_path, "w+") as file:
            file.write(data)

    def run(self):
        """starts fancontrol"""
        while True:
            try:
                self.cooling_manager.update_devices()
            except:
                pass
            sleep(1)


if __name__ == "__main__":
    control = FanControl()
    control.cooling_manager.set_all_to_manual()
    control.cooling_manager.set_all_safe_speed()
    control.run()
