# coding=utf-8
"""provides clever cli interface woth custom commands and callbacks"""
from time import sleep


class Colors:
    header = '\033[95m'
    blue = '\033[94m'
    green = '\033[92m'
    warning = '\033[93m'
    fail = '\033[91m'
    end = '\033[0m'
    bold = '\033[1m'
    underline = '\033[4m'


def color(text, color, color2=None):
    if color2 is None:
        return getattr(Colors, color) + text + Colors.end
    return getattr(Colors, color) + getattr(Colors, color2) + text + Colors.end


class Arguments:
    """argument container"""
    def __init__(self, args: dict):
        for arg in args.keys():
            arg_name = arg
            if arg[0] == "-":
                arg_name = arg[1:]

            setattr(self, arg_name, args[arg])

    def __getitem__(self, item: str):
        return getattr(self, item)

    def has(self, name: str):
        """returns waether self{Arguments} contains give argument"""
        return hasattr(self, name)


class ArgumentBp:
    """argument blueprint: contains argument name(s), type, optional(T/F), flag(T/F)"""
    def __init__(self, raw):
        self.__name = ""
        self.__aliases = []
        self.__type = "str"
        self.__optional = False
        self.__flag = False
        self.parse_raw(raw)

    @property
    def aliases(self):
        """returns aliases"""
        return self.__aliases

    @property
    def name(self):
        """returns name"""
        return self.__name

    @property
    def type(self):
        """returns type (e.g. str, int, float...)"""
        return self.__type

    @property
    def optional(self):
        """returns whether argument is optional"""
        return self.__optional

    @property
    def flag(self):
        """returns whether argument is a flag"""
        return self.__flag

    def parse_raw(self, raw):
        """parses raw argument into self {ArgumentBP}"""
        raw = str(raw)

        if raw[0] == "[" and raw[-1] == "]":
            self.__optional = True
            raw = raw[1:-1]
        else:
            self.__optional = False

        if raw[0] == "-":
            self.__flag = self.__optional = True
            raw = raw[1:]
        else:
            self.__flag = False

        if ":" in raw:
            split = raw.split(":", 1)
            names, self.__type = split
        else:
            names = raw
            self.__type = "str"

        names = names.split("|")
        self.__name = names[0]
        if len(names) > 1:
            self.__aliases = names[1:]

    def convert(self, raw):
        """converts give value into self.type"""
        try:
            if self.__flag:
                return bool(raw)
            elif self.__type == "str" or self.__type == "":
                return str(raw)
            elif self.__type == "int":
                return int(raw)
            elif self.__type == "float":
                return float(raw)
        except ValueError:
            return None

    def is_name_or_alias(self, name):
        """returns whether give name is the name or an alias of self"""
        return name == self.__name or name in self.__aliases

    def is_in(self, d: dict):
        for argument in d:
            if argument.is_name_or_alias(argument):
                return True
        return False


class CommandBp:
    """command blueprint: contains command name(s), arguments, flags, etc..."""
    def __init__(self, name, callback, arguments, context="*", exclude=True):
        self.context = context
        self.name = name
        self.exclude = exclude

        self.arguments = []
        for raw_argument in arguments.split(" "):
            if raw_argument == "":
                continue
            self.arguments.append(ArgumentBp(raw_argument))

        self.callback = callback

    def has_argument(self, name):
        """return bool whether self{CommandBp} has an specified argument with given name"""
        for argument in self.arguments:
            if argument.is_name_or_alias(name):
                return True
        return False

    def get_argument_name(self, alias):
        """return name of argument with given alias, None when not found"""
        for argument in self.arguments:
            if argument.is_name_or_alias(alias):
                return argument.name
        return None

    def parse_arguments(self, cmd):
        """return parsed arguments from raw input to {Arguments} object"""
        cmd = cmd.strip().split(" ")
        result = {}

        for index in range(1, len(cmd)):
            if "=" in cmd[index]:
                split_arg = cmd[index].split("=", 1)
                if len(split_arg) == 2:
                    name = self.get_argument_name(split_arg[0])
                    if not self.exclude or name is not None:
                        result[name] = split_arg[1]

            elif cmd[index][0] == "-":
                flag = cmd[index][1:]
                flag = self.get_argument_name(flag)
                if flag is not None:
                    result[flag] = True

            else:
                for arg in self.arguments[index - 1:]:
                    if not arg.flag:
                        result[arg.name] = cmd[index]

        for argument in self.arguments:

            if argument.name not in result:
                if argument.optional:
                    if argument.flag:
                        result[argument.name] = False
                    else:
                        result[argument.name] = None
                else:
                    try:
                        result[argument.name] = input(argument.name + ": ").strip()
                    except KeyboardInterrupt:
                        return None

            val = result[argument.name]
            if val is not None:
                result[argument.name] = argument.convert(val)
        return Arguments(result)

    def execute(self, cmd):
        """executes command line callback with args give in command string"""
        args = self.parse_arguments(cmd)
        if args is not None:
            self.callback(args)


class Cli:
    """command line interface"""
    def __init__(self):
        self.commands = {}  # list of available CommandBps
        self.context = ""
        self.location = ""

    def add_command(self, name, callback, args, context="*", exclude=True):
        """adds command blueprint to list of availiable commands"""
        command = CommandBp(name, callback, args, context=context, exclude=exclude)

        names = name.split(" ")
        for n in names:
            self.commands[n] = command

    def get_input(self):
        """gets command from user input and tries to execute it"""
        try:
            cmd = input(color(self.location, "green", "bold") + ":" +
                        color(self.context, "blue", "bold") + "$ ").strip()
            command = cmd.split(" ", 1)[0]
            if command in self.commands:
                if wildcard_compare(self.commands[command].context, self.context):
                    self.commands[command].execute(cmd)
        except KeyboardInterrupt:
            raise


def print_table(names, data, spacing=None):

    if names is not None:
        data.insert(0, names)
    if len(data) == 0:
        return

    if spacing is None or len(spacing) < len(data[0]):
        spacing = [0]*len(data[0])
        for row in data:
            for i, col in enumerate(row):
                spacing[i] = max(spacing[i], len(col)+2)
    else:
        spacing = [x*4 for x in spacing]

    for i, row in enumerate(data):
        line = ''.join(str(x).ljust(spacing[ix]) for ix, x in enumerate(row))
        print(line)
        if i == 0 and names is not None:
            print('-' * len(line))


def printl(*args, **kwargs):
    kwargs["end"] = ""
    kwargs["flush"] = True
    print(*args, **kwargs)


def sleep_print(s):
    for i in range(0, s):
        print("#", end="", flush=True)
        sleep(1)