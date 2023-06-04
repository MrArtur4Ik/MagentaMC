from enum import Enum
import io, utils, socket
import random
import traceback

class PacketDirection(Enum):
	TO_SERVER = 0
	TO_CLIENT = 1

class PacketSerializer:
	packet_id = int()
	direction = int()
	def serialize(self) -> io.BytesIO:
		pass
	def deserialize(self, rfile: io.BufferedReader):
		pass

#Packets to server:

class PlayerIdentification(PacketSerializer):
	packet_id = 0
	direction = PacketDirection.TO_SERVER
	def deserialize(self, rfile: io.BufferedReader):
		self.protocol_version = int.from_bytes(rfile.read(1), "big", signed=False)
		self.username = utils.remove_spaces(rfile.read(64))
		self.verify_key = utils.remove_spaces(rfile.read(64))
		self.unused = int.from_bytes(rfile.read(1), "big", signed=False) #0x00 for original classic, 0x42 for extension protocol

class SetBlockToServer(PacketSerializer):
	packet_id = 5
	direction = PacketDirection.TO_SERVER
	def deserialize(self, rfile: io.BufferedReader):
		self.x = int.from_bytes(rfile.read(2), "big", signed=True)
		self.y = int.from_bytes(rfile.read(2), "big", signed=True)
		self.z = int.from_bytes(rfile.read(2), "big", signed=True)
		self.mode = int.from_bytes(rfile.read(1), "big", signed=False)
		self.block_type = int.from_bytes(rfile.read(1), "big", signed=False)

class PositionAndOrientationToServer(PacketSerializer):
	packet_id = 8
	direction = PacketDirection.TO_SERVER
	def deserialize(self, rfile: io.BufferedReader):
		self.player_id = int.from_bytes(rfile.read(1), "big", signed=False) #UNUSED
		self.x = int.from_bytes(rfile.read(2), "big", signed=True)/32
		self.y = int.from_bytes(rfile.read(2), "big", signed=True)/32
		self.z = int.from_bytes(rfile.read(2), "big", signed=True)/32
		self.yaw = int.from_bytes(rfile.read(1), "big", signed=False)/255*360
		self.pitch = int.from_bytes(rfile.read(1), "big", signed=False)/255*360

class MessageToServer(PacketSerializer):
	packet_id = 0x0d
	direction = PacketDirection.TO_SERVER
	def deserialize(self, rfile: io.BufferedReader):
		self.unused = int.from_bytes(rfile.read(1), "big", signed=False)
		self.message = utils.remove_spaces(rfile.read(64))

#Packets to client:

class ServerIdentification(PacketSerializer):
	packet_id = 0
	direction = PacketDirection.TO_CLIENT
	def __init__(self, protocol_version: int, server_name: str, server_motd: str, user_type: int):
		self.protocol_version = protocol_version
		self.server_name = server_name
		self.server_motd = server_motd
		self.user_type = user_type
	def serialize(self) -> io.BytesIO:
		b = io.BytesIO()
		b.write(self.protocol_version.to_bytes(1, "big", signed=False))
		b.write(utils.add_spaces(self.server_name))
		b.write(utils.add_spaces(self.server_motd))
		b.write(self.user_type.to_bytes(1, "big", signed=False))
		return b

class Ping(PacketSerializer):
	packet_id = 1
	direction = PacketDirection.TO_CLIENT
	def serialize(self) -> io.BytesIO:
		return io.BytesIO()

class LevelInitialize(PacketSerializer):
	packet_id = 2
	direction = PacketDirection.TO_CLIENT
	def serialize(self) -> io.BytesIO:
		return io.BytesIO()

class LevelDataChunk(PacketSerializer):
	packet_id = 3
	direction = PacketDirection.TO_CLIENT
	def __init__(self, data_chunk: bytes, percent_complete: int):
		data_chunk = data_chunk[0:1024]
		self.chunk_length = len(data_chunk)
		data_chunk += b'\x00' * (1024-len(data_chunk))
		self.chunk_data = data_chunk
		self.percent_complete = percent_complete
	def serialize(self) -> io.BytesIO:
		b = io.BytesIO()
		b.write(self.chunk_length.to_bytes(2, "big", signed=True))
		b.write(self.chunk_data)
		b.write(self.percent_complete.to_bytes(1, "big", signed=False))
		return b

class LevelFinalize(PacketSerializer):
	packet_id = 4
	direction = PacketDirection.TO_CLIENT
	def __init__(self, x: int, y: int, z: int):
		self.x = x
		self.y = y
		self.z = z
	def serialize(self) -> io.BytesIO:
		b = io.BytesIO()
		b.write(self.x.to_bytes(2, "big", signed=True))
		b.write(self.y.to_bytes(2, "big", signed=True))
		b.write(self.z.to_bytes(2, "big", signed=True))
		return b

class SetBlockToClient(PacketSerializer):
	packet_id = 6
	direction = PacketDirection.TO_CLIENT
	def __init__(self, x: int, y: int, z: int, block_type: int):
		self.x = x
		self.y = y
		self.z = z
		self.block_type = block_type
	def serialize(self) -> io.BytesIO:
		b = io.BytesIO()
		b.write(self.x.to_bytes(2, "big", signed=True))
		b.write(self.y.to_bytes(2, "big", signed=True))
		b.write(self.z.to_bytes(2, "big", signed=True))
		b.write(self.block_type.to_bytes(1, "big", signed=False))
		return b

class SpawnPlayer(PacketSerializer):
	packet_id = 7
	direction = PacketDirection.TO_CLIENT
	def __init__(self, player_id: int, player_name: str, x: float, y: float, z: float, yaw: float, pitch: float):
		self.player_id = player_id
		self.player_name = player_name
		self.x = x
		self.y = y
		self.z = z
		self.yaw = yaw
		self.pitch = pitch
	def serialize(self) -> io.BytesIO:
		b = io.BytesIO()
		b.write(self.player_id.to_bytes(1, "big", signed=True))
		b.write(utils.add_spaces(self.player_name))
		b.write(int(self.x*32).to_bytes(2, "big", signed=True))
		b.write(int(self.y*32).to_bytes(2, "big", signed=True))
		b.write(int(self.z*32).to_bytes(2, "big", signed=True))
		b.write(int(self.yaw%360/360*255).to_bytes(1, "big", signed=False))
		b.write(int(self.pitch%360/360*255).to_bytes(1, "big", signed=False))
		return b

class PositionAndOrientationToClient(PacketSerializer):
	packet_id = 8
	direction = PacketDirection.TO_CLIENT
	def __init__(self, player_id: int, x: float, y: float, z: float, yaw: float, pitch: float):
		self.player_id = player_id
		self.x = x
		self.y = y
		self.z = z
		self.yaw = yaw
		self.pitch = pitch
	def serialize(self) -> io.BytesIO:
		b = io.BytesIO()
		b.write(self.player_id.to_bytes(1, "big", signed=True))
		b.write(int(self.x*32).to_bytes(2, "big", signed=True))
		b.write(int(self.y*32).to_bytes(2, "big", signed=True))
		b.write(int(self.z*32).to_bytes(2, "big", signed=True))
		b.write(int(self.yaw%360/360*255).to_bytes(1, "big", signed=False))
		b.write(int(self.pitch%360/360*255).to_bytes(1, "big", signed=False))
		return b

#Пакеты 0x09, 0x0a, 0x0b работают как 0x08 но где то меняется только поворот камеры, а где то положение в пространстве
#я их пропустил

class DespawnPlayer(PacketSerializer):
	packet_id = 0x0c
	direction = PacketDirection.TO_CLIENT
	def __init__(self, player_id: int):
		self.player_id = player_id
	def serialize(self) -> io.BytesIO:
		b = io.BytesIO()
		b.write(self.player_id.to_bytes(1, "big", signed=True))
		return b

class MessageToClient(PacketSerializer):
	packet_id = 0x0d
	direction = PacketDirection.TO_CLIENT
	def __init__(self, player_id: int, message: str):
		self.player_id = player_id
		self.message = message
	def serialize(self) -> io.BytesIO:
		b = io.BytesIO()
		b.write(self.player_id.to_bytes(1, "big", signed=True))
		b.write(utils.add_spaces(self.message))
		return b

class Disconnect(PacketSerializer):
	packet_id = 0x0e
	direction = PacketDirection.TO_CLIENT
	def __init__(self, reason: str):
		self.reason = reason
	def serialize(self) -> io.BytesIO:
		b = io.BytesIO()
		b.write(utils.add_spaces(self.reason))
		return b

class UpdateUserType(PacketSerializer):
	packet_id = 0x0f
	direction = PacketDirection.TO_CLIENT
	def __init__(self, user_type: int):
		self.user_type = user_type
	def serialize(self) -> io.BytesIO:
		b = io.BytesIO()
		b.write(self.user_type.to_bytes(1, "big", signed=False))
		return b

#List of packets:

packets = [PlayerIdentification, SetBlockToServer, PositionAndOrientationToServer, MessageToServer, 
	ServerIdentification, Ping, LevelInitialize, LevelDataChunk, 
	LevelFinalize, SetBlockToClient, SpawnPlayer, PositionAndOrientationToClient, 
	DespawnPlayer, MessageToClient, Disconnect, UpdateUserType]

#Exceptions:

class UnknownPacketError(Exception):
	pass

#Utils:

def read_packet(connection: socket.socket):
	try:
		b = connection.recv(2048)
	except socket.timeout:
		raise ConnectionAbortedError()
	except BlockingIOError:
		return None
	except TimeoutError:
		raise ConnectionAbortedError()
	if b == b'': raise ConnectionAbortedError()
	packet_id = b[0]
	for packet in packets:
		if packet.direction == PacketDirection.TO_SERVER and packet.packet_id == packet_id:
			p = packet()
			stream = io.BytesIO(b[1:])
			#p.deserialize(connection.makefile("rb"))
			p.deserialize(stream)
			return p
	raise UnknownPacketError("Unknown packet ID: 0x" + int.to_bytes(packet_id, 1, "big").hex() + \
		" (" + str(packet_id) + ")")

def read_packets(connection: socket.socket):
	try:
		b = connection.recv(2048)
		stream = io.BytesIO(b)
	except socket.timeout:
		raise ConnectionAbortedError()
	except BlockingIOError:
		return []
	except TimeoutError:
		raise ConnectionAbortedError()
	if b == b'': raise ConnectionAbortedError()
	packet_id = stream.read(1)
	ps = []
	unknown = False
	while packet_id != b'':
		packet_id = packet_id[0]
		unknown = True
		for packet in packets:
			if packet.direction == PacketDirection.TO_SERVER and packet.packet_id == packet_id:
				p = packet()
				p.deserialize(stream)
				ps.append(p)
				unknown = False
		packet_id = stream.read(1)
		if unknown:
			break
			#raise UnknownPacketError("Unknown packet ID: 0x" + int.to_bytes(packet_id, 1, "big").hex() + \
				#" (" + str(packet_id) + ")")
	return ps

def send_packet(connection: socket.socket, packet: PacketSerializer):
	if packet.direction != PacketDirection.TO_CLIENT: return
	connection.send(packet.packet_id.to_bytes(1, "big", signed=False) + \
		packet.serialize().getvalue())