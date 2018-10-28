from file_ops import *


class ThermalZone:
    """thermal_zone object"""

    def __init__(self, base_path, hwmon):
        self.__index = -1
        self.__base_path = base_path
        self.hwmon = hwmon
        try:
            self.__name = read_all(self.__base_path + "_label").strip()
        except AttributeError:
            self.__name = "unnamed"

    @property
    def index(self):
        """returns index of ThermalZone"""
        return self.__index

    def get_index(self):
        """returns index of ThermalZone"""
        return self.__index

    @property
    def name(self):
        """returns name (/type) of ThermalZone"""
        return self.__name

    def get_name(self):
        """returns name (/type) of ThermalZone"""
        return self.__name

    @property
    def temp(self):
        """returns current temparture of thermal zone in °C"""
        return self.get_temp()

    def get_temp(self):
        """returns current temparture of thermal zone in °C"""
        content = read_all(self.__base_path + "_input")
        try:
            temp = int(content)
        except (ValueError, TypeError):
            return None

        return temp//1000

    def seems_legit(self):
        return 10 < self.temp < 95
