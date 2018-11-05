import os
import vendors
from thermal_zone import ThermalZone
from cooling_device import CoolingDevice


def find_files(root, file_querys, max_depth=3, exclude=[]):
    rval = dict.fromkeys(file_querys, [])

    def do_scan(start_dir, output, depth=0):
        for f in os.scandir(start_dir):
            # ff = os.path.join(start_dir, f)
            if f.is_dir():
                if depth < max_depth and f.name not in exclude:
                    do_scan(f.path, output, depth + 1)
            else:
                for query in file_querys:
                    if query in f.name:
                        output[query].append(f.path)

    do_scan(root, rval, 0)
    return rval


class HwMon:
    def __init__(self, control, path):
        self.control = control
        self.path = path
        self.name = ""
        self.vendor = None
        self.type = "unknown"
        self.confidence = 0
        self.thermal_zones = []
        self.cooling_devices = []
        self.get_meta_data()
        self.get_thermal_zones()
        self.get_cooling_devices()

    def get_meta_data(self):
        self.name = open(os.path.join(self.path, "name"), "r").read().strip()

        results = find_files(self.path, ["vendor"], 3, exclude=["subsystem"])
        vendor_ids = set([])
        for file in results["vendor"]:
            try:
                vendor_ids.add(open(file, "r").read().strip())
            except IOError:
                continue
        if len(vendor_ids) == 0:
            self.vendor = vendors.get(-1)
        else:
            for vendor_id in vendor_ids:
                vendor = vendors.get(vendor_id)
                if vendor is not None:
                    self.vendor = vendor
                    self.type = vendor.type
                    self.confidence = 95

            if self.vendor is None:
                self.vendor = vendors.get(0)

        if "core" in self.name:
            self.type = "CPU"
            self.confidence = 30

    def _get_attributes(self, type):
        result = []
        entries = [file.name for file in os.scandir(self.path) if file.is_file() and file.name.startswith(type)]
        attributes = [attribute for attribute in entries if "_" not in attribute or attribute.endswith("_input")]
        for attribute in attributes:
            if "_" in attribute:
                attribute_number = attribute[len(type):attribute.find("_")]
            else:
                attribute_number = attribute[len(type):]
            result.append((int(attribute_number), type + str(attribute_number)))

        result = sorted(result, key=lambda x: x[0])
        return result

    def get_thermal_zones(self):
        thermal_zones = self._get_attributes("temp")
        for thermal_zone_data in thermal_zones:
            thermal_zone = ThermalZone(self.control.thermal_manager)
            thermal_zone.from_hwmon(os.path.join(self.path, thermal_zone_data[1]), hwmon=self)
            self.thermal_zones.append(thermal_zone)

    def get_cooling_devices(self):
        cooling_devices = self._get_attributes("pwm")
        for cooling_device_data in cooling_devices:
            cooling_device = CoolingDevice(self.control.cooling_manager)
            cooling_device.from_hwmon(os.path.join(self.path, cooling_device_data[1]), hwmon=self)
            self.cooling_devices.append(cooling_device)


def get_all_hwmons(control):
    """find all thermal zones"""

    base = "/sys/class/hwmon"  # base directory for hwmons
    hwmons = os.listdir(base)  # list all hwmons in hwmons
    result = []
    for hwmon_path in hwmons:
        path = os.path.join(base, hwmon_path)
        hwmon = HwMon(control, path)
        result.append(hwmon)

    return result

