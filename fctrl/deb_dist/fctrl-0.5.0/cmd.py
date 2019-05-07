#!/usr/bin/env python3.6
# coding=utf-8

from fctrl import FanControl
import detection_dialog
import os
import click
from prettytable import PrettyTable


control = FanControl()


@click.group()
def cli():
    pass


def list_thermal_zones():
    print("Thermal Zones")

    table = PrettyTable()
    table.field_names = ["name", "°C", "score", "idle", "desired", "critical"]

    for zone in control.thermal_manager.thermal_zones:
        table.add_row([zone.full_name, zone.temp, zone.score, zone.idle, zone.desired, zone.critical])

    print(table)


def list_cooling_devices():
    print("Cooling Devices")

    table = PrettyTable()
    table.field_names = ["name", "%", "rpm", "started", "thermal zones", "is pump"]
    for device in control.cooling_manager.cooling_devices:
        table.add_row([device.name, device.speed, device.rpm,device.started,
                       [z.full_name for z in device.thermal_zones],
                       "yes" if device.is_pump else "no"])
    print(table)


@cli.command("list")
@click.option("--thermal", "-t", is_flag=True, help="List all thermal zones")
@click.option("--cooling", "-c", is_flag=True, help="List all cooling zones")
def print_list(thermal, cooling):
    if thermal:
        list_thermal_zones()
    if cooling:
        list_cooling_devices()


@cli.command("set")
@click.argument("zone")
@click.option("--idletemp", "-it", type=int, help="Set the idle temp for thermal zone")
@click.option("--desiredtemp", "-dt", type=int, help="Set the desired temp for thermal zone")
@click.option("--criticaltemp", "-ct", type=int, help="Set the critical temp for thermal zone")
@click.option("--add-thermal-zone", "-at", type=str, help="Add thermal zone to cooling device")
@click.option("--rem-thermal-zone", "-rt", type=str, help="Remove thermal zone from cooling device")
def set_idle_temp(zone, idletemp, desiredtemp, criticaltemp, add_thermal_zone, rem_thermal_zone):

    if any((criticaltemp, idletemp, desiredtemp)):
        zone = control.thermal_manager.get_zone(full_name=zone)

        def print_confimation(temp_name, value):
            print("Set {} temperature of zone {} to {} °C.".format(temp_name, zone.name, value))

        if idletemp:
            zone.idle = idletemp
            print_confimation("idle", zone.idle)

        if desiredtemp:
            zone.desired = desiredtemp
            print_confimation("desired", zone.desired)
        if criticaltemp:
            zone.critical = criticaltemp
            print_confimation("critical", zone.critical)

    if any((add_thermal_zone, rem_thermal_zone)):
        device = control.cooling_manager.get_device(name=zone)
        if add_thermal_zone:
            thermal_zone = control.thermal_manager.get_zone(full_name=add_thermal_zone)
            if thermal_zone and thermal_zone not in device.thermal_zones:
                device.thermal_zones.append(thermal_zone)

        if rem_thermal_zone:
            device.thermal_zones = [z for z in device.thermal_zones if z.full_name != rem_thermal_zone]

    control.save()


@cli.command("add")
@click.argument("zone")
@click.option("--idletemp", "-it", is_flag=True, help="Set the idle temp for specified zone")
def set_idle_temp(zone, idletemp, desiredtemp, criticaltemp, value):
    try:
        value = int(value)
    except ValueError:
        value = None
    if not value:
        print("No value provided!")
        return

    if sum((criticaltemp, idletemp, desiredtemp)) == 1:
        zone = control.thermal_manager.get_zone(full_name=zone)
        temp_name = None
        if idletemp:
            zone.idle = value
            temp_name = "idle"
        elif desiredtemp:
            zone.idle = value
            temp_name = "desired"
        elif criticaltemp:
            zone.critical = value
            temp_name = "critical"
        if temp_name:
            print("Set {} temperature of zone {} to {} °C.".format(temp_name, zone.name, value))
        control.save()


@cli.command("detect")
def detect():
    global control
    detection_dialog.detect(control)
    control.save()
    print("Saved succesfully")


if __name__ == "__main__":
    os.system("sudo systemctl stop fctrl.service")
    try:
        cli()
    finally:
        os.system("sudo systemctl start fctrl.service")

