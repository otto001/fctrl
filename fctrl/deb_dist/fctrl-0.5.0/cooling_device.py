from time import sleep
from file_ops import *
from cli import print_table
import os
import math


def lerp(a, b, alpha):
    """linear interpolation"""
    return b * alpha + a * (1-alpha)


class CoolingDevice:
    """CoolingDevice object"""

    def get_path(self, fan=False):
        """get base directory of thermal_zone files"""
        if fan:
            return os.path.join(self.__base_dir, "fan" + str(self.__index))
        else:
            return os.path.join(self.__base_dir, "pwm" + str(self.__index))

    def __init__(self, mng, data=None):
        self.mng = mng

        self.__index = -1
        self.__base_path = ""
        self.__base_dir = ""
        self.hwmon = None
        self.hwmon_name = ""

        self.__name = str(self.__index)
        self.threshold_speed = 0
        self.rpm_curve = []
        self.is_pump = False

        self.thermal_zones = []

        self.__started = False

        self.__responsiveness = 10

        self.__buffer_speed = 0
        self.__build_up = 0
        self.__build_up_thresh_idle = 60
        self.__build_up_thresh_desired = 1000
        self.__idle = 0
        self.__desired = 0
        self.__critical = 0

        if data is not None:
            self.load_json(data)
        self.load_thermal_data()
        # if data is not None:
        #    self.load_json(data)

    def from_hwmon(self, base_path, hwmon):
        try:
            self.__index = int(base_path.split("/")[-1][3:])
        except ValueError:
            self.__index = -1

        self.__base_path = base_path
        self.__base_dir = os.path.dirname(base_path)
        self.hwmon = hwmon
        self.hwmon_name = hwmon.name
        self.__name = str(self.__index)

    def load_json(self, data):
        self.set_name(data["name"])
        self.__index = data["index"]
        try:
            self.threshold_speed = int(data["threshold-speed"])
        except (ValueError, TypeError, KeyError):
            self.threshold_speed = 0
        try:
            self.rpm_curve = data["rpm-curve"]
        except (ValueError, TypeError, KeyError):
            self.rpm_curve = []

        self.__base_path = data["base-path"]
        self.__base_dir = os.path.dirname(self.__base_path)
        self.hwmon_name = data["hwmon"]

        if "is-pump" in data:
            self.is_pump = data["is-pump"]

        thermal_zones_name = data["thermal-zones"]
        for i in range(len(thermal_zones_name)):
            zone = self.mng.control.thermal_manager.get_zone(full_name=thermal_zones_name[i])
            if zone is not None:
                self.thermal_zones.append(zone)

    def get_json(self):
        """return data as dict for json"""
        return {"name": self.__name, "index": self.__index, "base-path": self.__base_path, "hwmon": self.hwmon_name,
                "threshold-speed": self.threshold_speed, "rpm-curve": self.rpm_curve,
                "is-pump": self.is_pump, "thermal-zones": [z.full_name for z in self.thermal_zones]}

    @property
    def index(self):
        """returns index of ThermalZone"""
        return self.__index

    @property
    def name(self):
        """returns name"""
        return self.__name

    @property
    def full_name(self):
        """returns current temparture of thermal zone in °C"""
        if self.hwmon_name is "":
            return self.name
        return self.hwmon_name + "/" + self.name

    @property
    def max_speed(self):
        """returns max speed"""
        return self.rpm_curve[-1]

    @property
    def started(self):
        """returns started"""
        return self.__started

    def set_name(self, name):
        """sets name"""
        self.__name = name

    @property
    def speed(self):
        """returns current speed in %"""
        content = read_all(self.__base_path)
        try:
            speed = int(content)
        except (ValueError, TypeError):
            return None

        return int(round((speed/255) * 100))

    def set_speed(self, new_speed):
        """sets speed"""
        self.__buffer_speed = new_speed
        new_speed = int(round(max(min(new_speed/100*255, 255), 0)))
        return write(self.__base_path, new_speed)

    @property
    def rpm(self):
        """returns current fan rpm"""
        data = read_all(self.get_path(fan=True)+"_input")
        try:
            return int(data)
        except (TypeError, ValueError):
            return None

    def __get_actual_speed(self):
        accuracy = 2
        start = -1
        end = -1
        rpm = self.rpm
        for i, val in enumerate(self.rpm_curve):

            if val >= rpm and end == -1:
                end = (10 * i, val)

            if val <= rpm:
                start = (10 * i, val)
        if start == -1 or end == -1:
            return 0, 0

        if start[0] > end[0]:
            start, end = end, start

        if start[1] == end[1]:
            return start[0] - accuracy, end[0] + accuracy
        elif end[0] - start[0] == 10:
            alpha = (rpm - start[1]) / (end[1] - start[1])
            actual_speed = int(round(lerp(start[0], end[0], alpha)))
            return actual_speed - accuracy, actual_speed + accuracy
        else:
            return start[0] - accuracy, end[0] + accuracy

    @property
    def actual_speed(self):
        act_speed = self.__get_actual_speed()
        return min(max(act_speed[0], 0), 100), min(max(act_speed[1], 0), 100)

    def guess_is_responsive(self):
        return self.__responsiveness > 0

    def wait_for_fan_response(self, response, timeout=15, p=False):
        slept = 0
        while not (response(self)):
            sleep(1)
            if p:
                print("#", end="", flush=True)
            slept += 1
            if slept > timeout:
                return False

        if p:
            print("#", end="", flush=True)
        return True

    def set_to_manual(self):
        write(self.__base_path + "_enable", "1")

    def test_exists(self):
        self.set_to_manual()

        self.set_speed(0)
        sleep(3)
        rpm_1 = self.rpm

        self.set_speed(100)
        sleep(5)
        rpm_2 = self.rpm

        self.set_speed(40)
        return rpm_2 > rpm_1 * 1.1 and rpm_2 != 0

    def load_thermal_data(self):
        for zone in self.thermal_zones:
            self.__idle = min(self.__idle, zone.idle)
            self.__desired = min(self.__desired, zone.desired)
            self.__critical = min(self.__critical, zone.critical)
        self.__build_up_thresh_idle = 60
        self.__build_up_thresh_desired = 1000
        if self.is_pump:
            self.__build_up_thresh_desired = 300

    def get_highest_temp(self):
        temp = 0
        for zone in self.thermal_zones:
            temp = max(temp, zone.temp)
        return temp

    def get_highest_temp_score(self):
        score = 0
        for zone in self.thermal_zones:
            score = max(score, zone.score)
        return score

    def _update_responsiveness(self):
        act_speed = self.actual_speed
        if act_speed[0] <= self.__buffer_speed <= act_speed[1]:
            self.__responsiveness += 1
        else:
            self.__responsiveness -= 1

        self.__responsiveness = max(min(self.__responsiveness, 15), -15)

        if not self.guess_is_responsive():
            print("Not reponsive!")
            self.set_to_manual()
            self.__responsiveness = 10

    def respond_to_crititcal(self):
        self.set_speed(100)

    def get_curve_speed(self, speed):
        # print(math.e ** (0.046*(speed)+10) * ((100 - self.threshold_speed) / 100) + self.threshold_speed)
        return math.e ** (0.046*(speed+10)) * ((100 - self.threshold_speed) / 100) + self.threshold_speed

    def update(self):
        self._update_responsiveness()
        high_score = self.get_highest_temp_score()

        if high_score < 1:  # under idle
            self.__build_up = 0

        elif high_score < 2:  # over idle but under desired
            if self.__build_up < self.__build_up_thresh_idle:
                self.__build_up += 10 * (high_score-1)
            elif self.__build_up > self.__build_up_thresh_idle + 100:
                self.__build_up -= 100 * (1-(high_score-1))
            elif self.__build_up > self.__build_up_thresh_idle + 10:
                self.__build_up -= 10 * (1-(high_score-1))

        elif high_score < 3:  # over desired but under critical
            if self.__build_up < self.__build_up_thresh_desired*1.2:
                self.__build_up += 100 * (high_score-2)
            if high_score >= 2.7:
                self.__build_up = self.__build_up_thresh_desired

        elif high_score >= 3:  # smoke prevention
            self.respond_to_crititcal()

        if self.__build_up > self.__build_up_thresh_desired:
            self.__started = True
            speed = self.get_curve_speed(100 * (high_score-2))
        else:
            self.__started = False
            speed = 0

        debug_data = [self.full_name,
                      str(round(speed)) + "%",
                      str(high_score) + "sc",
                      str(self.get_highest_temp()) + "°C",
                      str(round(self.__build_up)) + "b"]
        print_table(None, [debug_data], spacing=[4, 2, 2, 2, 2])

        if not self.__started:
            self.set_speed(0)
        else:
            speed = max(speed, self.threshold_speed)

            own_speed = self.__buffer_speed
            speed_delta = speed - own_speed
            result = speed

            if speed_delta > 15:
                result = speed
                print("PEAK detected", own_speed, speed)
            elif abs(speed_delta) > 3:
                result = own_speed + speed_delta*0.3
            self.set_speed(result)

