from servertypes import *
import worldgenerator, logging, configparser, random, time, requests, event, traceback, command
from typing import List, Callable, Optional


debug = False
logging.basicConfig(format="%(asctime)s [%(levelname)s]: %(message)s", level=logging.DEBUG)

git_version: Optional[str]
no_permission_message = "&cYou have no permissions!"

entities: List[Entity] = []
worlds: List[World] = []
connections = {}
ops = []
port = 25565
config_file = "server.ini"
ops_file = "ops.txt"
max_players = 10

config = configparser.ConfigParser()

heartbeat_url = "http://www.classicube.net/server/heartbeat"
heartbeat_running = False
heartbeat_interval = 45.0 #time between heartbeats

registered_events: List[event.Event] = []
registered_commands: List[command.Command] = []

allowed_blocks_ids = range(0, 50) #vanilla minecraft (0-49 block ids)


#Нужно для верификации игроков
salt = "".join([random.choice("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz") for i in range(16)])
available_nickname_chars = "_0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
legal_chat_chars = " _~?!@#$%^&*()+-=[]{};:'\",./\\<>()0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"

default_level: World = None
default_generator: worldgenerator.WorldGenerator = worldgenerator.ClassicGenerator()

def send_heartbeat():
	params = {
		"port": port,
		"max": max_players,
		"name": config["OnlineMode"]["display-name"],
		"software": config["OnlineMode"]["software"],
		"public": True,
		"version": 7,
		"salt": salt,
		"users": len(get_players())
	}
	requests.get(heartbeat_url, params)

def heartbeat_thread():
	last_heartbeat = 0.0
	while heartbeat_running:
		if time.time()-last_heartbeat >= heartbeat_interval:
			last_heartbeat = time.time()
			send_heartbeat()

def get_players() -> List[Player]:
	players = []
	for entity in entities:
		if isinstance(entity, Player):
			players.append(entity)
	return players

def get_player(nickname: str) -> Optional[Player]:
	for player in get_players():
		if player.nickname == nickname:
			return player

def send_world(world: World, player: Player):
	player.send_packet(packets.LevelInitialize())
	map_data = world.serialize().getvalue()
	for chunk in utils.segment_byte_array(map_data):
		player.send_packet(packets.LevelDataChunk(chunk, 0))
	player.send_packet(packets.LevelFinalize(world.width, world.height, world.depth))
	spawn = world.spawn
	player.location = spawn
	player.send_packet(packets.SpawnPlayer(-1, player.nickname, spawn.x, spawn.y, spawn.z, spawn.yaw, spawn.pitch))
	for p in world.get_players():
		if p != player:
			#Отправляем каждому игроку спавн нового игрока
			p.send_packet(packets.SpawnPlayer(player.entity_id, player.nickname, spawn.x, spawn.y, spawn.z, spawn.yaw, spawn.pitch))
			l = p.location
			#Новому игроку отправляем спавн каждого игрока
			player.send_packet(packets.SpawnPlayer(p.entity_id, p.nickname, l.x, l.y, l.z, l.yaw, l.pitch))

def broadcast(message: str, player_id = -1):
	for player in get_players():
		player.send_message(message, player_id)
	logging.info(message)

'''
Example usage:

@server.register_event(event.PreLoginEvent)
def login_event(e: event.PreLoginEvent):
	if e.identify_packet.verify_key != "let me join":
		e.disallow("Put \"let me join\" to the key parameter to join")

'''
def register_event(type: event.Event = None, types: List[event.Event] = [], filter = lambda event: True):
	def wrapper(func):
		registered_events.append(event.EventHandler(func, types if not type else [type], filter))
		return func
	return wrapper

'''
Example usage:

#a simple broadcast command
@server.register_command("broadcast", aliases=["bc", "say"], permission = "myplugin.broadcast")
def broadcast_command(sender: CommandSender, command: str, args: List[str]):
	if len(args) == 0:
		sender.send_message("&cUsage: /bc <your message...>")
		return
	broadcast(f"[{sender.nickname if sender is Player else '*'}] {' '.join(args)}")
'''

def register_command(name: str, aliases: List[str] = [], permission: str = None):
	def wrapper(func: Callable[[CommandSender, str, List[str]]]):
		registered_commands.append(
			command.Command(name, command.LambdaCommandExecutor(func), aliases, permission))
		return func
	return wrapper

def call_event(event: event.Event):
	for handler in registered_events:
		try:
			if any([isinstance(event, e) for e in handler.events]) and handler.filter(event):
				handler.func(event)
		except:
			traceback.print_exc()