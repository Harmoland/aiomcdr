from typing import TYPE_CHECKING

from graia.broadcast.entities.dispatcher import BaseDispatcher
from graia.broadcast.entities.event import Dispatchable
from graia.broadcast.interfaces.dispatcher import DispatcherInterface
from graia.saya.event import SayaModuleInstalled

from aiomcdr.typing import generic_issubclass

if TYPE_CHECKING:
    from aiomcdr.app.server import MinecraftServer


class ApplicationLifecycleEvent(Dispatchable):
    """指示有关服务器 (MinecraftServer) 的事件."""

    server: "MinecraftServer"

    def __init__(self, server: "MinecraftServer") -> None:
        self.server = server

    class Dispatcher(BaseDispatcher):
        @staticmethod
        async def catch(interface: "DispatcherInterface"):
            from aiomcdr.app.server import MinecraftServer, MinecraftServerInterface

            if isinstance(interface.event, ApplicationLifecycleEvent):
                if generic_issubclass(MinecraftServer, interface.annotation):
                    return interface.event.server
                if generic_issubclass(MinecraftServerInterface, interface.annotation):
                    return interface.event.server.server_interface


class ApplicationLaunching(ApplicationLifecycleEvent):
    """指示 MinecraftServer 正在启动."""


class ApplicationLaunched(ApplicationLifecycleEvent):
    """指示 MinecraftServer 启动完成."""


class ApplicationShutdown(ApplicationLifecycleEvent):
    """指示 MinecraftServer 关闭."""


ApplicationShutdowned = ApplicationShutdown
