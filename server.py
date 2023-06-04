from servertypes import *
import worldgenerator, logging

debug = False
logging.basicConfig(format="%(asctime)s [%(levelname)s]: %(message)s", level=logging.DEBUG)

no_permission_message = "&cYou not have permissions!"

entities = []
worlds = []
connections = {}
ops = ["MrArtur4Ik"]
port = 25565
config_file = "server.ini"

default_level = None
default_generator = worldgenerator.ClassicGenerator()
commands = ["list", "save", "stop", "world", "goto"]

def get_players():
	players = []
	for entity in entities:
		if isinstance(entity, Player):
			players.append(entity)
	return players

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