from typing import List, Optional, Callable
from servertypes import CommandSender

class CommandExecutor:
    def run(self, sender: CommandSender, command: str, args: List[str]): pass

class Command:
    name: str
    aliases: List[str]
    executor: CommandExecutor
    permission: Optional[str]

    def __init__(self, name: str, executor: CommandExecutor, aliases: List[str] = [], permission: str = None) -> None:
        self.name = name
        self.executor = executor
        self.aliases = aliases
        self.permission = permission
    
    def has_permission(self, sender: CommandSender) -> bool:
        return sender.has_permission(self.permission) if self.permission else True

class LambdaCommandExecutor(CommandExecutor):
    def __init__(self, func: Callable[[CommandSender, str, List[str]], None]) -> None:
        self.func = func
    
    def run(self, sender: CommandSender, command: str, args: List[str]):
        self.func(sender, command, args)