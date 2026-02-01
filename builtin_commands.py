import server, main, logging, traceback, os, packets
from servertypes import CommandSender
from typing import List
from servertypes import World, Player

import utils

from email.utils import formatdate
import time

@server.register_command("test")
def test(sender: CommandSender, name: str, args: List[str]):
    sender.send_message(f"This is a test message! Today is {formatdate(time.time())}")


@server.register_command("help")
def help(sender: CommandSender, name: str, args: List[str]):
	
    command_names = sorted([cmd.name for cmd in server.registered_commands if cmd.has_permission(sender)])
    sender.send_message("Commands:")

    for segment in utils.segment_string(", ".join(command_names)):
        sender.send_message(segment)


@server.register_command("stop", permission="stop")
def stop(sender: CommandSender, name: str, args: List[str]):
    main.shutdown_server()


@server.register_command("list")
def list(sender: CommandSender, name: str, args: List[str]):
    players = [player.nickname for player in server.get_players()]
	
    sender.send_message("There is " + str(len(players)) + " players:")
    for segment in utils.segment_string(", ".join(players)):
        sender.send_message(segment)


@server.register_command("save", permission="save")
def save(sender: CommandSender, name: str, args: List[str]):
    server.broadcast("Saving worlds...")
    try:
        for world in server.worlds:
            file = open(world.filename, "wb")
            world.save(file)
            file.close()
        server.broadcast("&aAll worlds saved!")
    except:
        server.broadcast("&cAn error occured during saving world.")
        logging.info(traceback.format_exc())


@server.register_command("world")
def world(sender: CommandSender, name: str, args: List[str]):
    if len(args) == 0:
        sender.send_message("&cUsage: /world <list|goto|create|load|unload> ...")
    else:
        subcommand = args[0]
        args = args[1:]
        if subcommand == "list":
            sender.send_message("There is " + str(len(server.worlds)) + " worlds:")
            for segment in utils.segment_string(", ".join([world.name for world in server.worlds])):
                sender.send_message(segment)
        elif subcommand == "goto":
            if isinstance(sender, Player):
                if len(args) == 0:
                    sender.send_message("&cUsage: /world goto <worldName>")
                else:
                    worldName = args[0]
                    world = None
                    for w in server.worlds:
                        if w.name == worldName:
                            world = w
                            break
                    if world == None:
                        sender.send_message("This world does not exist!")
                        return
                    sender.teleport(world.spawn)
                    server.broadcast(sender.nickname + "&f went to &e" + world.name)
        elif subcommand == "create":
            if not sender.has_permission("world.create"):
                sender.send_message(server.no_permission_message)
                return
            if len(args) >= 4:
                try:
                    new_world = World(args[0], int(args[1]), int(args[2]), int(args[3]))
                    if os.path.exists(new_world.filename):
                        sender.send_message("&cThis world already exists!")
                    else:
                        server.broadcast("Generating new level \"" + new_world.name + "\"...")
                        try:
                            new_world.load()
                            server.broadcast("New level \"" + new_world.name + "\" was created!")
                        except:
                            logging.info(traceback.format_exc())
                            server.broadcast("An error occured while creating a new level!")
                except ValueError:
                    sender.send_message("&cWrong number!")
            else:
                sender.send_message("&cUsage: /world create <worldName> <width> <height> <depth>")
        elif subcommand == "load":
            if not sender.has_permission("world.load"):
                sender.send_message(server.no_permission_message)
                return
            if len(args) > 0:
                new_world = World(args[0])
                print(new_world.filename, new_world.name)
                if not os.path.exists(new_world.filename):
                    sender.send_message("&cThis world does not exists!")
                else:
                    exist = False
                    for w in server.worlds:
                        if w.name == args[0]:
                            exist = True
                            break
                    if exist:
                        sender.send_message("&cThis world already loaded!")
                        return
                    server.broadcast("Loading level \"" + new_world.name + "\"...")
                    try:
                        new_world.load()
                        server.broadcast("Level \"" + new_world.name + "\" was loaded!")
                    except:
                        server.broadcast("An error occured during load level!")
            else:
                sender.send_message("&cUsage: /world load <worldName>")
        elif subcommand == "unload":
            if not sender.has_permission("world.unload"):
                sender.send_message(server.no_permission_message)
                return
            if len(args) == 0:
                sender.send_message("&cUsage: /world unload <worldName>")
            else:
                worldName = args[0]
                world = None
                for w in server.worlds:
                    if w.name == worldName:
                        world = w
                        break
                if world == None:
                    sender.send_message("This world does not exist!")
                    return
                if world == server.default_level:
                    sender.send_message("You can not unload the main world!")
                    return
                world.unload()
                server.broadcast("Level \"" + world.name + "\" was unloaded!")


@server.register_command("goto")
def goto(sender: CommandSender, name: str, args: List[str]):
    if isinstance(sender, Player):
        sender.execute_command("world", ["goto"] + args)


@server.register_command("op", permission=["op"])
def op(sender: CommandSender, name: str, args: List[str]):
    if len(args) == 0:
        sender.send_message("&cUsage: /op <nickname>")
    else:
        nickname = args[0]
        if nickname in server.ops:
            sender.send_message("&cThis player is already op!")
            return
        server.ops.append(nickname)
        with open(server.ops_file, "w") as file:
            file.write("\n".join(server.ops))
        player = server.get_player(nickname)
        if player:
            player.is_op = True
            player.send_packet(packets.UpdateUserType(100))
        sender.send_message(f"&a{nickname} is now OP!")



@server.register_command("deop", permission=["deop"])
def deop(sender: CommandSender, name: str, args: List[str]):
    if len(args) == 0:
        sender.send_message("&cUsage: /deop <nickname>")
    else:
        nickname = args[0]
        if nickname not in server.ops:
            sender.send_message("&cThis player is not op!")
            return
        server.ops.remove(nickname)
        with open(server.ops_file, "w") as file:
            file.write("\n".join(server.ops))
        player = server.get_player(nickname)
        if player:
            player.is_op = False
            player.send_packet(packets.UpdateUserType(0))
        sender.send_message(f"&7{nickname} is not OP anymore.")


@server.register_command("oplist", permission=["oplist"])
def oplist(sender: CommandSender, name: str, args: List[str]):
    sender.send_message("There is " + str(len(server.ops)) + " ops:")
    for segment in utils.segment_string(", ".join(server.ops)):
        sender.send_message(segment)


@server.register_command("version")
def version(sender: CommandSender, name: str, args: List[str]):
	sender.send_message(f"This server is running MagentaMC {server.git_version if server.git_version else 'Unknown version'}")


