import socket, packets, server, worldgenerator, io, utils, random, os, server, logging

class Location:
	def __init__(self, x: float, y: float, z: float, yaw: float = 0, pitch: float = 0, world = None):
		self.x = x
		self.y = y
		self.z = z
		self.yaw = yaw
		self.pitch = pitch
		self.world = world

class World:
	def __init__(self, name: str, width: int = 0, height: int = 0, depth: int = 0, seed: int =random.randint(0, 2**64), spawn: Location = None):
		self.width = width
		self.height = height
		self.depth = depth
		self.name = name
		self.seed = seed
		self.level = bytearray(width*height*depth)
		self.filename = name + ".mw"
		self.spawn = Location(spawn.x, spawn.y, spawn.z, spawn.yaw, spawn.pitch, self) if spawn != None else self.get_default_spawn()
	def get_default_spawn(self):
		return Location(self.width//2, self.height, self.depth//2, 0, 0, self)
	def generate(self, generator: worldgenerator.WorldGenerator):
		self.level = bytearray(self.width*self.height*self.depth)
		generator.generate(self)
	def get_players(self) -> list:
		players = []
		for player in server.get_players():
			if player.location.world == self:
				players.append(player)
		return players
	def set_block(self, x: int, y: int, z: int, block_type: int, send_packet: bool = True):
		#self.level[(x + y*self.width) + z*self.width*self.height] = block_type
		#^ Хз почему но эта формула получения позиции в массиве даёт неверный результат
		try:
			self.level[x+self.depth*(z+self.width*y)] = block_type
		except:
			return
		if send_packet:
			for player in self.get_players():
				player.send_packet(packets.SetBlockToClient(x, y, z, block_type))
	def get_block(self, x: int, y: int, z: int):
		return self.level[x+self.depth*(z+self.width*y)]
	def serialize(self) -> io.BytesIO:
		b = io.BytesIO()
		b.write(utils.compress(len(self.level).to_bytes(4, "big") + bytes(self.level)))
		return b
	def save(self, f: io.BufferedWriter):
		f.write(self.width.to_bytes(2, "big", signed=True) + \
			self.height.to_bytes(2, "big", signed=True) + \
			self.depth.to_bytes(2, "big", signed=True) + \
			bytes(self.level))
	def open(self, f: io.BufferedReader):
		x = int.from_bytes(f.read(2), "big", signed=True)
		y = int.from_bytes(f.read(2), "big", signed=True)
		z = int.from_bytes(f.read(2), "big", signed=True)
		b = f.read(x*y*z)
		self.width = x
		self.height = y
		self.depth = z
		self.level = bytearray(b)
	def load(self, generator: worldgenerator.WorldGenerator = ..., output=True):
		if output: logging.info("Loading level \"" + self.name + "\"...")
		if os.path.exists(self.filename) and os.path.isfile(self.filename):
			with open(self.filename, "rb") as file:
				self.open(file)
			if output: logging.info("World loaded from file " + self.filename)
		else:
			if output: logging.info(f"Generating...")
			if generator == ...:
				server.default_generator.generate(self)
			else:
				generator.generate(self)
			if output: logging.info(f"Level was generated!")
			with open(self.filename, "wb") as file:
				self.save(file)
			if output: logging.info("World saved to file " + self.filename)
		server.worlds.append(self)
		self.spawn = self.get_default_spawn()
	def unload(self):
		self.__init__(self.name)
		for p in self.get_players():
			p.teleport(server.default_level.spawn)
		server.worlds.remove(self)

class CommandSender:
	is_op = False
	def has_permission(self, permission: str):
		if self.is_op:
			return True
		return False
	def send_message(self, message: str):
		pass

class Entity:
	def __init__(self, nickname: str, location: Location, entity_id: int):
		self.nickname = nickname
		self.location = location
		self.entity_id = entity_id

class Player(Entity, CommandSender):
	def __init__(self, nickname: str, location: Location, entity_id: int, connection: socket.socket, client_address: tuple):
		super().__init__(nickname, location, entity_id)
		self.connection = connection
		self.client_address = client_address
	def send_packet(self, packet: packets.PacketSerializer):
		packets.send_packet(self.connection, packet)
	def send_message(self, message: str, player_id: int = -1):
		self.send_packet(packets.MessageToClient(player_id, message))
	def teleport(self, location: Location):
		if location.world != self.location.world:
			for p in self.location.world.get_players():
				if p != self:
					p.send_packet(packets.DespawnPlayer(self.entity_id))
			server.send_world(location.world, self)
		else:
			self.send_packet(packets.PositionAndOrientationToClient(-1, location.x, location.y, location.z, location.yaw, location.pitch))
			for p in location.world.get_players():
				if p != self:
					p.send_packet(packets.PositionAndOrientationToClient(self.entity_id, location.x, location.y, location.z, location.yaw, location.pitch))
	def kick(self, reason: str):
		self.send_packet(packets.Disconnect(reason))
		self.connection.close()