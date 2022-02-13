import argparse
import getpass
import json
import random
import sys

import requests

parser = argparse.ArgumentParser()
parser.add_argument("-c", "--configfile")
config = parser.parse_args()


# logging.basicConfig(level=logging.DEBUG)


class ArgumentParserNoExit(argparse.ArgumentParser):
    def error(self, message):
        self.print_help(sys.stderr)
        print(2, '%s: error: %s\n' % (self.prog, message))

    def exit(self, status=0, message=None):
        if message:
            self._print_message(message, sys.stderr)


class ApplicationCommand:
    def __init__(self, order, id, application_id, name, description, options=[], **kwargs):
        self.order = order
        self.id = int(id)
        self.app_id = application_id
        self.name = name
        self.description = description
        self.guild = kwargs.pop("guild_id", None)
        self.default_permission = kwargs.pop("default_permission", True)
        self.version = kwargs.pop("version", None)
        self.type = kwargs.pop("type", None)
        self.options = [ApplicationCommandOption(order + 1, **params) for order, params in enumerate(options)]

        if kwargs != {}:
            print(f"Unknown param passed for {self.name}: {kwargs}")

    def pretty_str(self, offset=0, long=False):
        optionstring = ""
        if not long:
            optionstring = " ".join(o.get_short_name() for o in self.options)
            if optionstring != "":
                optionstring = " " + optionstring

        ret = f"{' ' * offset}{self.order}. {'Guild-only' if self.guild else 'Global'} Command '{self.name}{optionstring}'\n"

        if self.description != "No Description.":
            ret += f"{' ' * offset}   Description: {self.description}\n"
        if len(self.options) > 0:
            if long:
                ret += f"{' ' * offset}   Arguments: \n"
                ret += "".join([op.pretty_str(offset=offset + 6) for op in self.options])
                '''else:
                ret += f"{' ' * offset}   Arguments: {', '.join([o.get_short_name() for o in self.options])} \n"'''
        return ret

    def get_dict(self):
        ret = {k: self.__dict__[k] for k in ["name", "description", "default_permission"]}
        ret["options"] = [o.get_dict() for o in self.options]
        return ret

    def __eq__(self, other):
        return self.id == other.id

    def __hash__(self):
        return self.id

    def __lt__(self, other):
        return self.order < other.order


class ApplicationCommandOption:
    def __init__(self, order, type, name, description, *, required=False, choices=None, options=None):
        self.order = order
        self.type = OptionType(type)
        self.name = name
        self.description = description
        self.required = required
        self.options = options or []
        self.choices = choices or []
        self.choices = [ApplicationCommandOptionChoice(d["name"], d["value"]) for d in self.choices]
        if type in (1, 2):
            self.options = [ApplicationCommandOption(order, **o) for order, o in enumerate(self.options)]

    def pretty_str(self, offset=0):
        ret = f"{' ' * offset}{'Required ' if self.required else ''}Argument {self.order}: '{self.name}'\n"
        if self.description != "No Description.":
            ret += f"{' ' * offset}    Description: {self.description}\n"
        ret += f"{' ' * offset}    Type: {self.type.get_name()}\n"
        if len(self.choices) > 0:
            ret += f"{' ' * offset}    Choices: \n"
            for c in self.choices:
                ret += f"{' ' * offset}       {c.name}: {c.value} \n"
        return ret

    def get_short_name(self):
        return f"[{'?' if not self.required else ''}{self.name}: {self.type.get_name()}{' (choices)' if len(self.choices) > 0 else ''}]"

    def get_dict(self):
        ret = {k: self.__dict__[k] for k in ["name", "description", "required"]}
        if len(self.options) > 0:
            ret["options"] = [o.get_dict() for o in self.options]
        if len(self.choices) > 0:
            ret["choices"] = [c.get_dict() for c in self.choices]
        ret["type"] = self.type.num
        return ret


class ApplicationCommandOptionChoice:
    def __init__(self, name, value):
        self.name = name
        self.value = value

    def get_dict(self):
        return {"name": self.name, "value": self.value}


class OptionType:
    types = [None, "subcommand", "subcommand group", "string", "integer", "boolean", "user", "channel", "role"]

    def __init__(self, type):
        self.num = type
        self.name = self.types[type]

    def get_name(self):
        return self.name


def list_commands(guild=None):
    geturl = url

    geturl += f"/guilds/{guild}/commands" if guild else "/commands"
    commands = set()
    offset = 1
    if guild is not None:
        commands.update(list_commands())
        offset += len(commands)
    with session.get(geturl, headers=headers) as resp:
        if resp.status_code != 200:
            print("Error retrieving commands! Code: {0} Reason: {1}".format(resp.status_code, resp.text))
        else:
            for i, c in enumerate(resp.json()):
                commands.add(ApplicationCommand(i + offset, **c))
    return sorted(commands)


def print_all_commands(long=False, guild=None):
    allcmds = list_commands(params.guild)
    for c in allcmds:
        print(c.pretty_str(offset=0, long=long))


def prompt(name, default_value, is_bool=False, convertor=str):
    while True:
        if is_bool:
            if default_value:
                extra = "(Y/n)"
            else:
                extra = "(y/N)"

            inp = input(f"{name} {extra}: ")
            if inp.lower() in ("y", "n"):
                return inp.lower() == "y"
            elif inp == "":
                return default_value
        else:
            inp = input(f"Enter {name} ['{default_value}']: ")
            if inp == "":
                return default_value
            try:
                newinp = convertor(inp)
                return newinp
            except Exception as e:
                print(str(e))


def edit_options(base):
    print(f"-- Now editing options of '{base.name}' --")
    for opt in base.options:
        if prompt(f"Do you want to edit the option '{opt.name}'?", default_value=False, is_bool=True):
            edit_option(opt, base)
    while prompt("Do you want to add an option?", default_value=False, is_bool=True):
        new_option = ApplicationCommandOption(len(base.options) + 1, 3, "new option", "No Description.")
        base.options.append(new_option)
        edit_option(new_option, base)

    print(f"-- Finished editing the options of '{base.name}' --")


def edit_option(opt, parent):
    if prompt(f"Do you want to REMOVE the option '{opt.name}'?", default_value=False, is_bool=True):
        parent.options.remove(opt)
    else:
        print(f"-- Editing the option '{opt.name}' of '{parent.name}' --")
        opt.type = OptionType(prompt("type", default_value=opt.type.num, convertor=int))
        opt.name = prompt("option name", default_value=opt.name)
        opt.description = prompt("option description", default_value=opt.description)
        if opt.type.num not in (1, 2):
            opt.required = prompt("Is this argument required?", default_value=opt.required, is_bool=True)
        else:
            edit_options(opt)

        if isinstance(opt, ApplicationCommandOption):
            if opt.type.num in (3, 4):
                convert = str if opt.type.num == 3 else int
                if len(opt.choices) == 0:
                    if prompt("There are no choices. Do you want to populate this option with choices?",
                              default_value=False, is_bool=True):
                        while True:
                            name = prompt("name (empty for end)", default_value="")
                            if name == "":
                                break
                            value = prompt("value", str(random.randrange(0, 10000)), convertor=convert)
                            opt.choices.append(ApplicationCommandOptionChoice(name, value))
                else:
                    for choice in opt.choices:
                        inp = prompt(f"'{choice.name}' e to edit, r to remove, blank to move on", default_value="")
                        if inp == "e":
                            choice.name = prompt("name", default_value=choice.name)
                            choice.value = prompt("value", default_value=choice.value, convertor=convert)
                        elif inp == "r":
                            opt.choices.remove(choice)

        print(f"-- Back to editing '{parent.name}' --")


def create_command(name=None, guild=None):
    name = prompt("name", "New command") if not name else name
    # description = prompt("description", "No description.")
    new_order = len(list_commands(guild=guild)) + 1

    class NewCommand:
        def __init__(self):
            self.name = name
            self.description = "No Description."
            self.guild = guild

        def get_dict(self):
            return {"name": self.name, "description": self.description}

    newcmd = ApplicationCommand(new_order, **post_command(NewCommand()))
    edit_command(newcmd)


def edit_command(command_id=None, guild=None):
    if not isinstance(command_id, ApplicationCommand):
        command_id = command_id or int(input("Order of the command you want to edit: "))
        cmds = list_commands(guild=guild)
        editing = cmds[command_id - 1]
    else:
        editing = command_id
    print(f"-- Now editing the command '{editing.name}' --")
    # editing.name = prompt("name", editing.name)  # Name can't be edited
    editing.description = prompt("description", editing.description)
    editing.default_permission = prompt("default_permission", default_value=editing.default_permission, convertor=bool)

    edit_options(editing)

    post_command(editing)


def post_command(command):
    posturl = url

    posturl += f"/guilds/{command.guild}/commands" if command.guild else "/commands"
    js = command.get_dict()
    with session.post(posturl, headers=headers, json=js) as resp:
        if not 200 <= resp.status_code < 300:
            print("Update failed! Your changes were not recorded. Code: {0} Reason: {1}".format(resp.status_code,
                                                                                                resp.text))
        else:
            print("Updated successfully!")
            return resp.json()


def delete_command(command_id, guild=None):
    command_id = command_id or int(input("Order of the command you want to delete: "))
    cmds = list_commands(guild=guild)
    command = cmds[command_id - 1]

    print(command.pretty_str(long=True))
    if prompt(f"Do you really want to delete the command '{command.name}'?", default_value=False, is_bool=True):
        delurl = url
        delurl += f"/guilds/{command.guild}/commands/{command.id}" if command.guild else f"/commands/{command.id}"
        with session.delete(delurl, headers=headers) as resp:
            if resp.status_code != 204:
                print("Delete failed! Code [{0}]: {1}".format(resp.status_code, resp.text))
            else:
                print(f"Command '{command.name}' deleted successfully.")


if __name__ == "__main__":
    configdict = {}
    if config.configfile is not None:
        configdict = json.loads(open(config.configfile, "r").read())

    client_id = configdict.get("client_id", None) or input("Client ID: ")
    # application_key = configdict.get("application_key", None) or input("Application key: ")
    bot_token = configdict.get("bot_token", None) or getpass.getpass(prompt="Bot token: ")
    guild_context = configdict.get("guild_context", None)
    command = "ls"
    url = "https://discord.com/api/v8/applications/{0}".format(client_id)
    headers = {
        "Authorization": f"Bot {bot_token}"
    }

    with requests.Session() as session:
        while True:
            try:
                command = input(f"{guild_context if guild_context else 'global'}> ")
            except KeyboardInterrupt:
                print("")
                break
            if command == "":
                continue
            cmd = command.split()[0]
            args = command.split()[1:]
            is_help = False
            if len(args) > 0:
                is_help = args[0] in ('-h', '--help')
            try:
                if cmd in ("ls", "list"):
                    lsparse = ArgumentParserNoExit(prog="ls")
                    lsparse.add_argument("-l", "--long", action="store_true")
                    lsparse.add_argument("-g", "--guild", default=guild_context)
                    params = lsparse.parse_args(args)
                    print_all_commands(params.long, params.guild) if not is_help else ''
                elif cmd == "edit":
                    editparse = ArgumentParserNoExit(prog="edit")
                    editparse.add_argument("command_id", nargs="?", type=int)
                    editparse.add_argument("-g", "--guild", default=guild_context)
                    params = editparse.parse_args(args)
                    edit_command(params.command_id, guild=guild_context) if not is_help else ''
                elif cmd in ("guild", "context", "ctx"):
                    guildchange_parser = ArgumentParserNoExit(prog="guild", description="Sets the guild context")
                    guildchange_parser.add_argument("guild", type=int, nargs="?")
                    guildchange_parser.add_argument("-r", "--reset", action="store_true")
                    params = guildchange_parser.parse_args(args)
                    if not params.guild and not params.reset:
                        print(
                            f"Currently working in the context of the guild {str(guild_context) if guild_context else 'GLOBAL'}")
                    if params.guild:
                        guild_context = params.guild
                    if params.reset:
                        guild_context = None
                elif cmd in ("del", "delete", "rm"):
                    del_parser = ArgumentParserNoExit(prog="delete", description="Delete a command")
                    del_parser.add_argument("command_id", type=int, nargs="?")
                    del_parser.add_argument("-g", "--guild", default=guild_context)
                    params = del_parser.parse_args(args)
                    if not is_help:
                        delete_command(params.command_id, guild=guild_context)
                elif cmd in ("create", "make", "new"):
                    create_parser = ArgumentParserNoExit(prog="create", description="Create a command")
                    create_parser.add_argument("command_name", nargs="?")
                    create_parser.add_argument("-g", "--guild", default=guild_context)
                    params = create_parser.parse_args(args)
                    if not is_help:
                        create_command(params.command_name, guild_context)

                elif cmd in ["exit", "bye"]:
                    break

                elif cmd == "help":
                    helpstr = """Commands:
    - ls     - lists commands in the current context
    - edit   - edits a command
    - guild  - Change guild context
    - del    - Delete a command
    - create - Create a new command"""
                    print(helpstr)
                else:
                    print(f"Command '{cmd}' is not a recognized command")

            except argparse.ArgumentError:
                pass
            except KeyboardInterrupt:
                print("")
                pass
            except BaseException as e:
                print("ERROR: " + str(e))
                print("Type 'exit' to exit the program")
                # traceback.print_exc()
