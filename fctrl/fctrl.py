#!/usr/bin/env python3
# coding=utf-8
from thermal_manager import ThermalManager
from cooling_manager import CoolingManager

import json
from time import sleep
import os
import getpass
user_name = getpass.getuser()


record = False
test_clf = True


def lerp(a, b, alpha):
    """linear interpolation"""
    return b * alpha + a * (1-alpha)


class FanCurve:
    """fan curve"""
    class Point:
        """one point in thermal curve"""
        def __init__(self, temp, speed):
            self.temp = int(round(temp))
            self.speed = int(round(speed))

        def __str__(self):
            return str(self.temp) + ": " + str(self.speed)

        def get_json(self):
            """returns point as dict for json"""
            return {"temp": self.temp, "speed": self.speed}

        def pretty_print(self):
            """returns nicely formatted string representing self"""
            return str(self.temp) + "°C -> " + str(self.speed) + "%"

    def __init__(self, controller, name=None, data=None):
        self.name = ""
        self.__values = list()
        self.__thermal_zone = None
        self.__cooling_devices = []
        self.__temp_last = list()
        self.controller = controller

        self.__threshold_temp = 0
        self.__threshold_speed = 0
        self.__threshold_buffer = 0
        self.__started = False
        self._trend = 0
        return  # TODO remove
        if name is not None:
            self.name = name
        elif data is not None:
            self.load_json(data)
        else:
            raise TypeError

    @property
    def thermal_zone(self):
        """returns thermal zone"""
        return self.__thermal_zone

    @property
    def cooling_devices(self):
        """returns cooling devices"""
        return self.__cooling_devices

    def get_json(self):
        """returns FanCurve as json"""
        data = {"name": self.name,
                "values": [val.get_json() for val in self.__values]}

        if self.__thermal_zone is not None:
            data["thermal-zone"] = self.__thermal_zone.index
        else:
            data["thermal-zone"] = None

        data["cooling-devices"] = [d.index for d in self.__cooling_devices]

        return data

    def load_json(self, data):
        """load FanCurve from json"""
        try:
            self.__values = []

            for val in data["values"]:
                self.insert_point(val["temp"], val["speed"])

            self.name = data["name"]
            self.__thermal_zone = data["thermal-zone"]
            if self.__thermal_zone is not None:
                self.__thermal_zone = self.controller.thermal_manager.get_zone(index=self.__thermal_zone)

            for d in data["cooling-devices"]:
                device = self.controller.cooling_manager.get_device(index=d)
                if device is not None:
                    self.__cooling_devices.append(device)

        except KeyError:
            return False
        return True

    def get_values(self):
        """returns all values of self"""
        return list(self.__values)

    def set_thermal_zone(self, zone):
        """sets thermal zone"""
        self.__thermal_zone = zone

    def add_cooling_device(self, device):
        device = self.controller.cooling_manager.get_device(index=device)
        if device is None:
            return
        for d in self.__cooling_devices:
            if d.index == device.index:
                return
        self.__cooling_devices.append(device)
        return True

    def remove_cooling_device(self, device):
        for i, d in enumerate(self.__cooling_devices):
            if d.index == device:
                del self.__cooling_devices[i]
                return True
        return False

    def insert_point(self, temp, speed):
        """inserts point into fan curve"""
        point = FanCurve.Point(temp, speed)
        if len(self.__values) == 0 or self.__values[-1].temp < temp:
            self.__values.append(point)

        else:
            for i in range(0, len(self.__values)):
                if self.__values[i].temp > temp:
                    self.__values.insert(i, point)
                    break
                elif self.__values[i].temp == temp:
                    self.__values[i] = point
                    break

    def get_speed(self, temp):
        """return fan speed for given temp"""
        if len(self.__values) == 0:
            return 0

        if temp <= self.__values[0].temp:
            return self.__values[0].speed

        if temp >= self.__values[-1].temp:
            return self.__values[-1].speed

        for i in range(0, len(self.__values)):
            if self.__values[i].temp == temp:
                return self.__values[i].speed

            if self.__values[i].temp > temp:
                if i == 0:
                    return self.__values[i].speed
                p_max = self.__values[i]
                p_min = self.__values[i-1]
                alpha = (temp-p_min.temp)/(p_max.temp - p_min.temp)
                return int(round(lerp(p_min.speed, p_max.speed, alpha)))

    def calculate_threshold_temp(self, speed):
        for temp in range(0, 100):
            if self.get_speed(temp) >= speed:
                return temp

    def calculate_delta(self, temp):
        self.__temp_last.append(temp)
        if len(self.__temp_last) > 5:
            del self.__temp_last[0]

        if len(self.__temp_last) > 1:
            return temp - self.__temp_last[-2]
        else:
            return 0

    def update(self):
        """updates fanspeed"""
        if self.__thermal_zone is None:
            return False

        temp = self.__thermal_zone.temp

        base_speed = self.get_speed(temp)
        delta = self.calculate_delta(temp)
        speed = base_speed + max(min(delta, 5), -5)

        self._trend = self._trend*0.75 + delta*0.25

        self.__threshold_buffer = max(min(self.__threshold_buffer, 50), 0)

        print(self.name, temp, speed, ", ".join([str(int(d.started)) for d in self.cooling_devices]))

        for device in self.__cooling_devices:
            device.update(temp=temp, speed=speed, delta=delta, trend=self._trend, curve=self)


class FanControl:
    """central object, manages thermals, fans, fancurves"""
    config_path = "/etc/linux-utils/fctrl/.config"

    def __init__(self):
        data = self.load()

        self.__thermal_manager = ThermalManager()
        #self.__thermal_manager.load_thermal_zones()

        cooling_data = None
        if data is not None:
            cooling_data = data["cooling"]

        self.__cooling_manager = CoolingManager(cooling_data)

        self.__curves = []

        if data is not None:
            for curve_data in data["curves"]:
                new_curve = FanCurve(self, data=curve_data)
                self.__curves.append(new_curve)

    @property
    def thermal_manager(self):
        """returns thermal manager"""
        return self.__thermal_manager

    @property
    def cooling_manager(self):
        """returns cooling manager"""
        return self.__cooling_manager

    def new_curve(self, name):
        """creates new FanCurve"""
        new_curve = FanCurve(self, name=name)
        self.__curves.append(new_curve)
        return new_curve

    def del_curve(self, name):
        """deletes fancurve by name"""
        index = -1
        for i, curve in enumerate(self.__curves):
            if curve.name == name:
                index = i
        if index > 0:
            del self.__curves[index]

    def get_curve(self, name):
        """returns FanCurve by name"""
        select = [curve for curve in self.__curves if curve.name == name]
        if len(select) == 1:
            return select[0]

    def get_all_curves(self):
        """returns all FanCurves"""
        return list(self.__curves)

    def save(self):
        """saves to file"""
        data = dict()
        data["curves"] = [curve.get_json() for curve in self.__curves]
        data["cooling"] = self.cooling_manager.get_json()
        data = json.dumps(data)
        with open(self.config_path, "w+") as file:
            file.write(data)

        #os.system("sudo chown " + os.environ["HOME"].split("/")[-1] + " " + self.config_path)

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

    def run(self):
        """starts fancontrol"""
        while True:
            try:
                for curve in self.__curves:
                    try:
                        curve.update()
                    except:
                        raise

                print()
            except:
                raise
                pass
            sleep(1)


if __name__ == "__main__":
    control = FanControl()
    control.cooling_manager.set_all_to_manual()
    control.run()
