from socketserver import ThreadingTCPServer, StreamRequestHandler
import time, traceback, os, logging, packets, utils, server, socket, threading, hashlib, event
from server import broadcast
from command import Command
from servertypes import *
import builtin_commands

def info(*args):
	logging.info(" ".join([str(s) for s in args]))

def command_handler(sender: CommandSender, command: str, args: list):
	if isinstance(sender, Player):
		info(sender.nickname, "issued command: /" + command, " ".join(args))
	executing_command: Command = None
	for cmd in server.registered_commands:
		if cmd.name == command or command in cmd.aliases:
			executing_command = cmd
			break
	if not executing_command:
		sender.send_message("&cUnknown command. Type \"/help\" for help.")
		return
	if executing_command.permission and not sender.has_permission(executing_command.permission):
		sender.send_message(server.no_permission_message)
		return
	cmd.executor.run(sender, command, args)

def message_handler(player: Player, message: str):
	if message.startswith("/"):
		args = message[1:].split()
		if len(args) == 0: args = [""]
		logging.info(f"{player.nickname} issued command: {message}")
		player.execute_command(args[0], args[1:])
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
	server.heartbeat_running = False
	for player in server.get_players():
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
	if not server.connections[client_address]["authorized"]: #Пакеты обрабатывающиеся только в процессе авторизации
		if isinstance(p, packets.PlayerIdentification):
			if server.connections[client_address]["authorized"]: return
			
			logging.info(p.username + "[" + utils.ip_format(client_address) + "] is connecting...")
			e = event.PreLoginEvent(connection, client_address, p)
			server.call_event(e)
			
			if not e.is_allowed():
				packets.send_packet(connection, packets.Disconnect(e.get_reason()))
				connection.close()
				logging.info(p.username + " isn't allowed to join: " + e.get_reason())
				return
			
			new_eid = new_entity_id()
			
			new_location = server.default_level.spawn
			new_player = Player(p.username, new_location, new_eid, connection, client_address)
			logging.info(utils.ip_format(client_address) + " authorized as " + p.username)
			if p.username in server.ops:
				new_player.is_op = True

			#it will show up while world is loading
			title = "Loading..."
			subtitle = ""

			packets.send_packet(connection, 
					   packets.ServerIdentification(7, title, subtitle, 100 if new_player.is_op else 0))
			
			server.connections[client_address]["authorized"] = True
			server.connections[client_address]["player"] = new_player
			server.entities.append(new_player)
			server.send_world(new_location.world, new_player)

			broadcast(new_player.nickname + " joined the game.")

			new_player.send_message("&6Welcome to MagentaMC server written on Python!")
		return
	
	#Пакеты обрабатывающиеся в процессе игры (после авторизации)
	player: Player = server.connections[client_address]["player"]
	if isinstance(p, packets.SetBlockToServer):
		if not server.connections[client_address]["authorized"]: return
		try:
			world: World = player.location.world
			block_type = p.block_type if p.mode != 0 else 0
			if not block_type in server.allowed_blocks_ids:
				player.kick("This block is not allowed!")
				return
			if world.get_block(p.x, p.y, p.z) != block_type:
				e = event.BlockChangeEvent(player, p)
				server.call_event(e)
				if e.is_cancelled():
					player.send_packet(packets.SetBlockToClient(p.x, p.y, p.z, world.get_block(p.x, p.y, p.z)))
					return
				world.set_block(p.x, p.y, p.z, block_type)
				if server.debug: player.send_message("[DEBUG] Placed block "
				 + str(block_type)
				 + " at " + str(p.x) + " " + str(p.y) + " " + str(p.z))
		except:
			pass
	elif isinstance(p, packets.PositionAndOrientationToServer):
		if not server.connections[client_address]["authorized"]: return
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
		if not server.connections[client_address]["authorized"]: return
		if any([s not in server.legal_chat_chars for s in p.message]):
			player.kick("Illegal characters!")
			return
		message_handler(player, p.message)

class ServerHandler(StreamRequestHandler):
	last_ping = int()
	def handle(self):
		self.connection.setblocking(False)
		self.connection.settimeout(10)
		self.last_ping = time.time()
		server.connections[self.client_address] = {"connection": self.connection, "authorized": False}
		logging.debug("[" + utils.ip_format(self.client_address) + "] connected.")
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
		if conn["authorized"] and "player" in conn:
			player: Player = conn["player"]
			try:
				server.entities.remove(conn["player"])
				for p in player.location.world.get_players():
					if player.entity_id != p.entity_id:
						p.send_packet(packets.DespawnPlayer(player.entity_id))
				broadcast(player.nickname + " left the game.")
			except:
				info(traceback.format_exc())
			logging.info(f"{player.nickname}[{utils.ip_format(self.client_address)}] disconnected" + \
				(": " + conn["reason"] if "reason" in conn and conn["reason"] else "."))
		else:
			logging.debug("[" + utils.ip_format(self.client_address) + "] disconnected.")
		del server.connections[self.client_address]

@server.register_event(event.PreLoginEvent)
def login(e: event.PreLoginEvent):
	new_eid = new_entity_id()
	if server.config["OnlineMode"]["player-verify"] == "true" and \
		hashlib.md5((server.salt + e.identify_packet.username).encode()).hexdigest() != e.identify_packet.verify_key:
		e.disallow("Verification failed!")
		return
	if new_eid == None:
		e.disallow("Too many entities!")
		return
	for player in server.get_players():
		if e.identify_packet.username == player.nickname:
			e.disallow("This player already playing!")
			return
	if server.max_players >= 0 and len(server.get_players()) >= server.max_players:
		e.disallow("Too many players!")
		return

def main():
	global serv
	level = World("world", 256, 128, 256) #196, 128, 196
	level.load()
	server.default_level = level
	info("Server started on port " + str(server.port))
	serv = ThreadingTCPServer(("", server.port), ServerHandler)
	if server.heartbeat_running: threading.Thread(target=server.heartbeat_thread).start()
	try:
		serv.serve_forever()
	except KeyboardInterrupt:
		shutdown_server()
	except:
		traceback.print_exc()
	server.heartbeat_running = False

if __name__ == "__main__":
	print("Please launch start.py to start the server.")