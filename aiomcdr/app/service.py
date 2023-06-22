from typing import Type

from launart import Launart, Service

from aiomcdr.app.server import MinecraftServer
from aiomcdr.app.server_interface import MinecraftServerInterface


class MinecraftServerService(Service):
    id = "minecraft_server"
    supported_interface_types = {MinecraftServerInterface}

    def __init__(self) -> None:
        self.mc = MinecraftServer()
        super().__init__()

    def get_interface(self, typ: Type[MinecraftServerInterface]):
        return self.mc.server_interface

    @property
    def stages(self):
        return {"blocking"}

    @property
    def required(self):
        return set()

    async def launch(self, mgr: Launart):
        async with self.stage("blocking"):
            await self.mc.run(mgr)
