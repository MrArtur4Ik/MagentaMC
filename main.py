from socketserver import ThreadingTCPServer, StreamRequestHandler
import time, traceback, os, logging, packets, utils, server, socket, threading
from servertypes import *

def info(*args):
	logging.info(" ".join([str(s) for s in args]))

def get_players():
	players = []
	for entity in server.entities:
		if isinstance(entity, Player):
			players.append(entity)
	return players

def broadcast(message: str, player_id = -1):
	for player in get_players():
		player.send_message(message, player_id)
	info(message)

def command_handler(sender: CommandSender, command: str, args: list):
	if isinstance(sender, Player):
		info(sender.nickname, "issued command: /" + command, " ".join(args))
	if command == "list":
		players = []
		for player in get_players():
			players.append(player.nickname)
		sender.send_message("There is " + str(len(players)) + " players:")
		for segment in utils.segment_string(", ".join(players)):
			sender.send_message(segment)
		return
	if command == "stop":
		if not sender.has_permission("stop"):
			sender.send_message(server.no_permission_message)
			return
		shutdown_server()
		return
	if command == "save" or command == "save-all":
		broadcast("Saving world...")
		try:
			for world in server.worlds:
				file = open(world.filename, "wb")
				world.save(file)
				file.close()
			broadcast("&aAll worlds saved!")
		except:
			broadcast("&cAn error occured during saving world.")
			info(traceback.format_exc())
		return
	if command == "world":
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
						broadcast(sender.nickname + "&f went to &e" + world.name)
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
							broadcast("Generating new level \"" + new_world.name + "\"...")
							try:
								new_world.load()
								broadcast("New level \"" + new_world.name + "\" was created!")
							except:
								info(traceback.format_exc())
								broadcast("An error occured during create new level!")
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
						broadcast("Loading level \"" + new_world.name + "\"...")
						try:
							new_world.load()
							broadcast("Level \"" + new_world.name + "\" was loaded!")
						except:
							broadcast("An error occured during load level!")
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
					broadcast("Level \"" + world.name + "\" was unloaded!")
		return
	if command == "goto":
		command_handler(sender, "world", ["goto"] + args)
		return
	if command == "help":
		server.commands.sort()
		sender.send_message("Commands:")
		for segment in utils.segment_string(", ".join(server.commands)):
			sender.send_message(segment)
		return
	sender.send_message("&cUnknown command. Type \"/help\" for help.")

def message_handler(player: Player, message: str):
	if message.startswith("/"):
		args = message[1:].split()
		if len(args) == 0: args = [""]
		command_handler(player, args[0], args[1:])
		return
	if message == "": return
	broadcast(player.nickname + ": " + message.replace("%", "&"), player.entity_id)

def new_entity_id():
	vars = list(range(128))
	for entity in server.entities:
		if entity.entity_id in vars:
			vars.remove(entity.entity_id)
	if len(vars) <= 0: return None
	return vars[0]

def shutdown_server():
	info("Shutdown server...")
	for player in get_players():
		player.send_packet(packets.Disconnect("Server shutdown!"))
		player.connection.close()
	info("Saving worlds...")
	for world in server.worlds:
		file = open(world.filename, "wb")
		world.save(file)
		file.close()
	info("Worlds have saved!")
	serv.shutdown()
	info("Server was stopped!")

def packet_handler(connection: socket.socket, client_address: tuple, p: packets.PacketSerializer):
	if isinstance(p, packets.PlayerIdentification):
		info(client_address, "authorized as", p.username)
		packets.send_packet(connection, packets.ServerIdentification(7, "Hello", "world!", 0x64))
		new_eid = new_entity_id()
		if new_eid == None:
			packets.send_packet(connection, packets.Disconnect("Too many entities!"))
			connection.close()
			return
		player_already_play = False
		for player in get_players():
			if p.username == player.nickname:
				player_already_play = True
				break
		if player_already_play:
			packets.send_packet(connection, packets.Disconnect("This player already playing!"))
			connection.close()
			return
		if len(get_players()) >= 10:
			packets.send_packet(connection, packets.Disconnect("Too many players!"))
			connection.close()
			return
		new_location = server.default_level.spawn
		new_player = Player(p.username, new_location, new_eid, connection, client_address)
		if p.username in server.ops:
			new_player.is_op = True
		server.connections[client_address]["authorized"] = True
		server.connections[client_address]["player"] = new_player
		server.entities.append(new_player)
		server.send_world(new_location.world, new_player)
		'''packets.send_packet(connection, packets.LevelInitialize())
		map_data = new_location.world.serialize().getvalue()
		for chunk in utils.segment_byte_array(map_data):
			packets.send_packet(connection, packets.LevelDataChunk(chunk, 0))
		packets.send_packet(connection, packets.LevelFinalize(new_location.world.width, new_location.world.height, new_location.world.depth))
		packets.send_packet(connection, packets.SpawnPlayer(-1, p.username, new_location.x, new_location.y, new_location.z, new_location.yaw, new_location.pitch))
		for player in new_location.world.get_players():
			if player.entity_id != new_eid:
				#Отправляем каждому игроку спавн нового игрока
				player.send_packet(packets.SpawnPlayer(new_eid, new_player.nickname,
					new_location.x, new_location.y, new_location.z, new_location.yaw, new_location.pitch))
				location = player.location
				#Новому игроку отправляем спавн каждого игрока
				new_player.send_packet(packets.SpawnPlayer(player.entity_id, player.nickname,
					location.x, location.y, location.z, location.yaw, location.pitch))'''
		broadcast(new_player.nickname + " joined the game.")
		new_player.send_message("&6Welcome to my server written on Python!")
	elif isinstance(p, packets.SetBlockToServer):
		if not server.connections[client_address]["authorized"]: return
		try:
			player = server.connections[client_address]["player"]
			world = player.location.world
			block_type = p.block_type if p.mode != 0 else 0
			if world.get_block(p.x, p.y, p.z) != block_type:
				world.set_block(p.x, p.y, p.z, block_type)
				#player.send_packet(packets.SetBlockToClient(p.x, p.y, p.z, world.get_block(p.x, p.y, p.z)))
				if server.debug: player.send_message("[DEBUG] Placed block "
				 + str(block_type)
				 + " at " + str(p.x) + " " + str(p.y) + " " + str(p.z))
		except:
			pass
	elif isinstance(p, packets.PositionAndOrientationToServer):
		player = server.connections[client_address]["player"]
		location = Location(p.x, p.y, p.z, p.yaw, p.pitch, player.location.world)
		if player.location != location:
			player.location = location
			for p in player.location.world.get_players():
				if p.entity_id != player.entity_id:
					p.send_packet(packets.PositionAndOrientationToClient(player.entity_id,
						location.x,
						location.y,
						location.z,
						location.yaw,
						location.pitch))
	elif isinstance(p, packets.MessageToServer):
		message_handler(server.connections[client_address]["player"], p.message)

class ServerHandler(StreamRequestHandler):
	last_ping = int()
	def handle(self):
		self.connection.setblocking(False)
		self.connection.settimeout(10)
		self.last_ping = time.time()
		server.connections[self.client_address] = {"connection": self.connection, "authorized": False}
		info(self.client_address, "connected. Auth...")
		try:
			while True:
				try:
					ps = packets.read_packets(self.connection)
				except ConnectionAbortedError:
					#Соединение разорвалось
					break
				except ConnectionResetError:
					break
				except packets.UnknownPacketError:
					break
				if time.time() - self.last_ping > 5:
					#Отправляем пинг игроку каждые 5 секунд
					self.last_ping = time.time()
					packets.send_packet(self.connection, packets.Ping())
				if ps == []:
					#Никакой пакет не пришёл идём дальше
					time.sleep(1/120)
					continue
				#Обработка пакета...
				for p in ps:
					threading.Thread(target=packet_handler, name="PacketHandler-" + os.urandom(4).hex(), args=[self.connection, self.client_address, p]).start()
		except:
			info(traceback.format_exc())
		conn = server.connections[self.client_address]
		if conn["authorized"]:
			try:
				player = conn["player"]
				server.entities.remove(conn["player"])
				for p in player.location.world.get_players():
					if player.entity_id != p.entity_id:
						p.send_packet(packets.DespawnPlayer(player.entity_id))
				broadcast(player.nickname + " left the game.")
			except:
				info(traceback.format_exc())
		info(self.client_address,"disconnected.")
		del server.connections[self.client_address]

def main():
	global serv
	level = World("world", 196, 128, 196)
	level.load()
	server.default_level = level
	info("Server started on port " + str(server.port))
	serv = ThreadingTCPServer(("", server.port), ServerHandler)
	try:
		serv.serve_forever()
	except KeyboardInterrupt:
		shutdown_server()


if __name__ == "__main__":
	main()
