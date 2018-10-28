#!/usr/bin/env python3.6
# coding=utf-8

from fctrl import FanControl
from cli import Cli, color
import detection_dialog

control = FanControl()
select = None


def print_all():
    print("All fancurves:")
    for curve in control.get_all_curves():
        print("\t" + curve.name)


def get_terminal_size():
    try:
        import fcntl
        import termios
        import struct
        th, tw, hp, wp = struct.unpack('HHHH', fcntl.ioctl(0, termios.TIOCGWINSZ, struct.pack('HHHH', 0, 0, 0, 0)))
        return tw, th
    except OSError:
        return None


def new_curve(args):
    if 0 < len(args.name) < 32:
        control.new_curve(args.name)
        print("New curve created: " + args.name)
        #print_all()
        #print()
        select_curve(args)
        print("You can now add thermal zones")
    else:
        print("Invalid name: invalid length")


def del_curve(args):
    control.del_curve(args.name)
    print_all()


def select_curve(args):
    new = control.get_curve(args.name)
    if new is not None:
        global select
        select = new
        cmd.context = "curves/" + select.name
        print("Selected curve: " + select.name)


def list_what(args):
    if args.what == "curves":
        print_all()
    elif args.what == "zones":
        all_zones = control.thermal_manager.get_all_names()
        all_temps = control.thermal_manager.get_all_temps()
        for i in range(0, len(all_zones)):
            print(str(i) + ": " + all_zones[i] + " " * (25 - len(all_zones[i])) + str(all_temps[i]) + "°C")
    elif args.what == "devices":
        for d in control.cooling_manager.cooling_devices:
            print(str(d.index) + ": " + d.name + " " * (25 - len(d.name)) + str(d.speed) + "%")


def info(args):
    if select is None:
        print("Error: No curve selected! Use § select <name>")
        return

    if args.graph:
        steps = 100
        terminal_size = get_terminal_size()
        if terminal_size is not None:
            steps = terminal_size[0]
        step_size = 100/steps
        vals = []
        rows = steps//10
        if terminal_size is not None and args.fullscreen:
            rows = terminal_size[1]-2
        val_per_row = 100/rows
        for i in range(0, steps):
            vals.append(int(round(select.get_speed(i * step_size) / val_per_row)))

        for row in range(0, rows):
            content = ""
            for val in vals:
                if val >= rows-row:
                    content += "#"
                else:
                    content += " "
            print(content)

        label_line = "^0" + " " * int(steps/10 - 5)
        for i in range(1, 10):
            label_line += "{0:0=2d}^".format(i*10) + " " * int(steps/10 - 3)
        label_line = label_line[:-1] + "100^"
        print(label_line)

    else:
        if args.steps is None:
            for value in select.get_values():
                print(value.pretty_print())
        else:
            if args.steps <= 1:
                print("Error: Invalid steps: must be > 1")
            else:
                for i in range(0, args.steps):
                    val = i*(100/(args.steps-1))
                    print(str(int(round(val))) + "°C -> " + str(select.get_speed(val)) + "%")

        if select.thermal_zone is None:
            print("Thermal zone: not set")
        else:
            print("Thermal zone: " + select.thermal_zone.name + " (" + str(select.thermal_zone.index) + ")")

        print("Cooling devices: " + ", ".join([d.name for d in select.cooling_devices]))


def set(args):
    if select is None:
        print("Error: No curve selected! Use § select <name>")
        return

    if args.temp is not None and args.speed is not None:
        if 0 <= args.temp <= 100 and 0 <= args.speed <= 100:
            select.insert_point(args.temp, args.speed)

    if args.zone is not None:
        zone = control.thermal_manager.get_zone(index=args.zone)
        select.set_thermal_zone(zone)


def device(args):
    if args.add is not None:
        if select is None and False:
            print("Error: No curve selected! Use § select <name>")
            return
        select.add_cooling_device(args.add)


def save(args):
    control.save()
    print("Saved succesfully")


def detect(args):
    detection_dialog.detect()
    #if args.cooling:
    #    control.cooling_manager.load_all_cooling_devices()

   #     if args.threshold:
   #         control.cooling_manager.user_detect_speeds()
   #     else:
   #         control.cooling_manager.user_detect()


def show_help(args):
    global select
    if select is not None:
        print("You are currently editing the curve \"" + select.name + "\".\n" +
              "To change your selection, type " + color("$ select <curve>", "bold") + "\n" +
              "To list all fan curves, type " + color("$ list curves", "bold") + "\n" +
              "To set the thermal zone of the curve, type " + color("$ set zone <zone>", "bold") + "\n" +
              "To list all thermal zones, type " + color("$ list zones", "bold") + "\n" +
              "To get information on the curve, type " + color("$ info", "bold"))


cmd = Cli()
cmd.location = "fctrl"
cmd.context = "menu"
cmd.add_command("new", new_curve, "name")
cmd.add_command("del", del_curve, "name")
cmd.add_command("select sl", select_curve, "name")
cmd.add_command("list", list_what, "what")

cmd.add_command("set", set, "[temp|t|-t:int] [speed|s|-s:int] [zone|z|-z:int]")
cmd.add_command("info", info, "[steps|s|-s:int] -graph|g -fullscreen|f")

cmd.add_command("device", device, "[add|a:int] [remove|rem|r:int] -list|l -all|a")

#cmd.add_command("zones", zones, "")
cmd.add_command("save", save, "[path]")

cmd.add_command("help", show_help, "")

cmd.add_command("detect", detect, "-cooling|c -threshold|thresh|max-speed|speeds")


if __name__ == "__main__":
    while True:
        cmd.get_input()

