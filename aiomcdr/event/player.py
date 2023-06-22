from typing import TYPE_CHECKING

from graia.broadcast.entities.dispatcher import BaseDispatcher
from graia.broadcast.entities.event import Dispatchable
from graia.broadcast.interfaces.dispatcher import DispatcherInterface

from aiomcdr.app.info_reactor.info import Info
from aiomcdr.typing import generic_issubclass

if TYPE_CHECKING:
    from aiomcdr.app.server import MinecraftServer


class PlayerEvent(Dispatchable):
    """指示有关玩家的事件."""

    server: "MinecraftServer"
    name: str
    info: Info

    def __init__(self, server: "MinecraftServer", name: str, info: Info) -> None:
        self.server = server
        self.name = name
        self.info = info

    class Dispatcher(BaseDispatcher):
        @staticmethod
        async def catch(interface: "DispatcherInterface"):
            from aiomcdr.app.server import MinecraftServer, MinecraftServerInterface

            if isinstance(interface.event, PlayerEvent):
                if generic_issubclass(MinecraftServer, interface.annotation):
                    return interface.event.server
                if generic_issubclass(MinecraftServerInterface, interface.annotation):
                    return interface.event.server.server_interface
                if generic_issubclass(str, interface.annotation):
                    return interface.event.name
                if generic_issubclass(Info, interface.annotation):
                    return interface.event.info


class PlayerJoinedEvent(PlayerEvent):
    """指示玩家加入游戏."""


class PlayerLeftEvent(PlayerEvent):
    """指示玩家离开游戏."""
