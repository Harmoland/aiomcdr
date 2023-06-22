from typing import TYPE_CHECKING, Union

from graia.broadcast.entities.dispatcher import BaseDispatcher
from graia.broadcast.entities.event import Dispatchable
from graia.broadcast.interfaces.dispatcher import DispatcherInterface

from aiomcdr.app.command.command_source import InfoCommandSource
from aiomcdr.app.info_reactor.info import Info
from aiomcdr.typing import generic_issubclass

if TYPE_CHECKING:
    from aiomcdr.app.server import MinecraftServer


class InfoEvent(Dispatchable):
    """指示有关消息（Info）的事件."""

    server: "MinecraftServer"
    info: Info
    source: Union["InfoCommandSource", None]

    def __init__(self, server: "MinecraftServer", info: "Info", source: Union["InfoCommandSource", None]) -> None:
        self.server = server
        self.info = info
        self.source = source

    class Dispatcher(BaseDispatcher):
        @staticmethod
        async def catch(interface: "DispatcherInterface"):
            from aiomcdr.app.server import MinecraftServer, MinecraftServerInterface

            if isinstance(interface.event, InfoEvent):
                if generic_issubclass(MinecraftServer, interface.annotation):
                    return interface.event.server
                if generic_issubclass(MinecraftServerInterface, interface.annotation):
                    return interface.event.server.server_interface
                if generic_issubclass(Info, interface.annotation):
                    return interface.event.info
                if generic_issubclass(InfoCommandSource, interface.annotation):
                    return interface.event.source


class UserInfoEvent(InfoEvent):
    """指示玩家发送的消息."""
