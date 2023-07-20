from dataclasses import dataclass
from types import FunctionType
from typing import Type, List
from servertypes import Player
from packets import PacketSerializer
import socket

class Event:
    pass

class PlayerEvent(Event):
    def __init__(self, player: Player):
        self.__player = player
    def get_player(self):
        return self.__player


#Player events:

class PreLoginEvent(Event):
    __reason = None
    def __init__(self, connection: socket.socket, client_address: tuple, identify_packet: PacketSerializer):
        self.connection = connection
        self.client_address = client_address
        self.identify_packet = identify_packet
    def allow(self):
        self.__reason = None
    def disallow(self, reason: str):
        self.__reason = reason
    def is_allowed(self):
        return not self.__reason
    def get_reason(self):
        return self.__reason
    

#Event options:

class Cancellable:
    __is_cancelled = False
    def set_cancelled(self, b: bool):
        self.__is_cancelled = b
    def is_cancelled(self):
        return self.__is_cancelled


@dataclass
class EventHandler:
    func: Type[FunctionType]
    events: List[Event]
    filter: Type[FunctionType]