from file_ops import *


def load_thermal_zone(mng, data):
    if data["class"] == "ThermalZone":
        return ThermalZone(mng, data)
    elif data["class"] == "ThermalGpu":
        return ThermalGpu(mng, data)
    elif data["class"] == "ThermalCpu":
        return ThermalCpu(mng, data)


class ThermalZone:
    """thermal_zone object"""

    def __init__(self, mng, data=None):
        self.mng = mng
        self.__base_path = ""
        self.hwmon_name = ""
        self.hwmon = None
        self.name = "None"
        self.critical = 80
        self.desired = 60
        self.idle = 50

        if data is not None:
            self.__base_path = data["base-path"]
            self.name = data["name"]
            self.hwmon_name = data["hwmon"]
            self.critical = data.get("critical")
            self.desired = data.get("desired")
            self.idle = data.get("idle")

    def from_hwmon(self, base_path, hwmon):
        self.__base_path = base_path
        self.hwmon_name = hwmon.name
        self.hwmon = hwmon

        try:
            self.name = read_all(self.__base_path + "_label").strip()
        except AttributeError:
            self.name = "unnamed"
        return self

    def get_json(self):
        """return data as dict for json"""
        return {"name": self.name, "hwmon": self.hwmon_name,
                "base-path": self.__base_path, "class": self.__class__.__name__,
                "critical": self.critical, "desired": self.desired, "idle": self.idle}

    @property
    def base_path(self):
        return self.__base_path

    @property
    def temp(self):
        """returns current temparture of thermal zone in °C"""
        return self.get_temp()

    @property
    def score(self):
        return self.get_score()

    @property
    def full_name(self):
        """returns current temparture of thermal zone in °C"""
        if self.hwmon_name is "":
            return self.name
        return self.hwmon_name + "/" + self.name

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

    def _get_score(self):
        temp = self.temp
        if temp < self.idle:
            return 0 + temp/self.idle
        elif temp < self.desired:
            return 1 + (temp-self.idle)/(self.desired - self.idle)
        elif temp < self.critical:
            return 2 + (temp-self.desired)/(self.critical - self.desired)
        elif temp >= self.critical:
            return 3

    def get_score(self):
        return round(self._get_score(), 1)


class ThermalGpu(ThermalZone):
    def from_hwmon(self, base_path, hwmon):
        super().from_hwmon(base_path, hwmon)
        self.name = "GPU"
        self.hwmon_name = ""
        return self


class ThermalCpu(ThermalZone):
    def __init__(self, mng, data=None):
        super().__init__(mng, data)
        self.name = "CPU"
        self.hwmon_name = ""
        self.__zones = []

        if data is not None and "zones" in data:
            self.__zones = data["zones"]

    def from_hwmon(self, base_path, hwmon):
        super().from_hwmon("", hwmon)
        self.name = "CPU"
        self.hwmon_name = ""
        self.__zones = [zone.base_path for zone in hwmon.thermal_zones]
        return self

    def get_json(self):
        """return data as dict for json"""
        data = super().get_json()
        data["zones"] = self.__zones
        return data

    def get_temp(self):
        """returns current temparture of thermal zone in °C"""
        max_temp = 0
        for zone in self.__zones:
            content = read_all(zone + "_input")
            try:
                temp = int(content)
            except (ValueError, TypeError):
                continue

            max_temp = max(max_temp, temp // 1000)

        if max_temp == 0:
            return None
        return max_temp
