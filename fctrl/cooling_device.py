from time import sleep
from file_ops import *
import cli


def lerp(a, b, alpha):
    """linear interpolation"""
    return b * alpha + a * (1-alpha)


def sleep_print(s):
    for i in range(0, s):
        print("#", end="", flush=True)
        sleep(1)


class CoolingDevice:
    """CoolingDevice object"""
    __base_path = "/sys/class/hwmon/hwmon2/"

    @property
    def dir(self):
        """get base directory of thermal_zone files"""
        return self.get_dir()

    def get_dir(self, fan=False):
        """get base directory of thermal_zone files"""
        if fan:
            return self.__base_path + "fan" + str(self.__index)
        else:
            return self.__base_path + "pwm" + str(self.__index)

    def __init__(self, index, data=None):
        self.__index = int(index)
        self.__name = ""
        self.__threshold_speed = 0
        self.__rpm_curve = []
        self.__is_pump = False

        self.__threshold_buffer = 0
        self.__threshold_temp = None
        self.__started = False

        self.__responsiveness = 10

        self.__buffer_speed = 0

        if data is not None:
            self.load_json(data)

    @property
    def index(self):
        """returns index of ThermalZone"""
        return self.__index

    @property
    def name(self):
        """returns name"""
        return self.__name

    @property
    def threshold_speed(self):
        """returns threshold speed"""
        return self.__threshold_speed

    @property
    def max_speed(self):
        """returns max speed"""
        return self.__rpm_curve[-1]

    @property
    def started(self):
        """returns started"""
        return self.__started

    def set_name(self, name):
        """sets name"""
        self.__name = name

    def get_json(self):
        """return data as dict for json"""
        return {"name": self.__name, "index": self.__index,
                "threshold-speed": self.__threshold_speed, "rpm-curve": self.__rpm_curve,
                "is-pump": self.__is_pump}

    def load_json(self, data):
        self.set_name(data["name"])

        try:
            self.__threshold_speed = int(data["threshold-speed"])
        except (ValueError, TypeError, KeyError):
            self.__threshold_speed = 0

        try:
            self.__rpm_curve = data["rpm-curve"]
        except (ValueError, TypeError, KeyError):
            self.__rpm_curve = []

        if "is-pump" in data:
            self.__is_pump = data["is-pump"]

    @property
    def speed(self):
        """returns current speed in %"""
        content = read_all(self.get_dir())
        try:
            speed = int(content)
        except (ValueError, TypeError):
            return None

        return int(round((speed/255) * 100))

    def set_speed(self, new_speed):
        """sets speed"""
        self.__buffer_speed = new_speed
        new_speed = int(round(max(min(new_speed/100*255, 255), 0)))
        return write(self.get_dir(), new_speed)

    @property
    def rpm(self):
        """returns current fan rpm"""
        data = read_all(self.get_dir(fan=True) + "_input")
        try:
            return int(data)
        except (TypeError, ValueError):
            return None

    def __get_actual_speed(self):
        accuracy = 2
        start = -1
        end = -1
        rpm = self.rpm
        for i, val in enumerate(self.__rpm_curve):

            if val >= rpm and end == -1:
                end = (10 * i, val)

            if val <= rpm:
                start = (10 * i, val)

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
        pass
        write(self.get_dir() + "_enable", "1")
        write(self.get_dir(), 100)

    def user_detect_speeds(self):
        old_speed = self.speed
        success = self._user_detect_speeds(user=True)
        self.set_speed(old_speed)
        return success

    def _user_detect_max_speed(self):
        cli.printl("Ramping up fan to full speed: ")
        self.set_speed(100)
        success = self.wait_for_fan_response(response=(lambda d: d.rpm > 0), p=True)
        if not success:
            print("ERROR: Device unavailable")
            return False

        slept = 0
        last_rpm = self.rpm
        count = 0
        while True:
            sleep_print(1)
            if self.rpm*0.95 <= last_rpm:
                count += 1
                if count >= 3:
                    break
            else:
                count = 0
            last_rpm = self.rpm
            slept += 1
            if slept > 10:
                break

        print(" OK")

        return True

    def _user_is_pump(self):
        user_in = input("Is the fan actually a pump? [yes|NO]: ")
        if user_in in ["yes", "y"]:
            self.__is_pump = True
            self.__threshold_speed = 0
            return True
        else:
            self.__is_pump = False
            return False

    def _user_detect_threshold(self):

        cli.printl("Ramping up fan to full speed: ")
        self.set_speed(100)
        success = self.wait_for_fan_response(response=(lambda d: d.rpm > 0), p=True)
        if not success:
            print(" ERROR: Device unavailable")
            return False

        print(" OK")

        cli.printl("Stopping fan: ")
        self.set_speed(0)

        success = self.wait_for_fan_response(response=(lambda d: d.rpm == 0), p=True)
        if not success:
            print(" ERROR: Could not stop fan")
            self.__threshold_speed = 0

            self._user_is_pump()

        if not self.__is_pump:
            sleep_print(6)
            print(" OK")

        data = [self.rpm]
        threshold_found = False

        cli.printl("Slowly ramping up fan: ")
        self.set_speed(8)

        while self.speed < 100:
            cur_speed = self.speed
            if not threshold_found:
                cur_speed += 2
                self.set_speed(cur_speed)
                sleep_print(3)
                if self.rpm > 0:
                    threshold_found = True
                    self.__threshold_speed = cur_speed + 2
                    self.set_speed(cur_speed - cur_speed % 10)
            else:
                cur_speed += 10
                self.set_speed(cur_speed)
                sleep_print(4)

            if cur_speed % 10 == 0:
                data.append(self.rpm)

        print(" OK")
        self.__rpm_curve = data
        print(data)
        return True

    def _user_check_threshold(self):
        cli.printl("Checking threshold speed: ")

        self.set_speed(0)
        success = self.wait_for_fan_response(response=(lambda d: d.rpm == 0), p=True)
        if not success:
            print(" ERROR: Could not stop fan")
            return False

        sleep_print(12)

        self.set_speed(self.__threshold_speed)
        success = self.wait_for_fan_response(response=(lambda d: d.rpm > 0), p=True)
        if success:
            print(" OK")
        else:
            print(" ERROR: Could not start fan")
            return False
        return True

    def _user_detect_speeds(self, user=True):
        print("\nDetecting max & threshold speed of device " + self.name + " (" + str(self.index) + ")")

        success = self._user_detect_threshold()
        if not success:
            return False
        elif self.__is_pump:
            print("Success! Detected: \n\t\tmax-speed: " + str(self.max_speed) + "rpm\n\t\tis pump:    yes")
            return True

        success = self._user_check_threshold()
        if not success:
            return False

        print("Success! Detected: \n\t\tmax-speed: " + str(self.max_speed) + "rpm\n\t\tthreshold: " + str(
            self.threshold_speed)+"%")

    def update(self, temp, speed, delta, trend, curve):
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

        if self.__threshold_temp is None:
            self.__threshold_temp = curve.calculate_threshold_temp(self.__threshold_speed)
            print(self.name, self.__threshold_speed, self.__threshold_temp)

        if self.__threshold_temp + 2 < temp or temp < self.__threshold_temp - 2:
            self.__threshold_buffer += temp - self.__threshold_temp
        elif abs(trend) < 0.5:
            self.__threshold_buffer -= 3

        self.__threshold_buffer = max(min(self.__threshold_buffer, 50), 0)

        if not self.__started:
            self.__started = self.__threshold_buffer > 30
        else:
            self.__started = self.__threshold_buffer > 20

        # print(temp, trend, base_speed, self.__started, self.__threshold_buffer)
        if not self.__started:
            self.set_speed(0)
        else:
            speed = max(speed, self.__threshold_speed)

            own_speed = self.speed
            speed_delta = speed - own_speed
            result = own_speed

            if speed_delta > 15:
                result = speed
                print("PEAK detected")
            elif abs(speed_delta) > 5:
                result = own_speed + speed_delta*0.5
            self.set_speed(result)
