from abc import ABC
from typing import TYPE_CHECKING

from .info import Info

if TYPE_CHECKING:
    from graia.broadcast import Broadcast

    from ..server import MinecraftServer


class AbstractInfoReactor(ABC):
    """
    The abstract base class for info reactors
    """

    bcc: "Broadcast"
    server: "MinecraftServer"

    def __init__(self, bcc: "Broadcast", server: "MinecraftServer"):
        self.bcc: "Broadcast" = bcc
        self.server = server
        """The MCDR server object"""

    async def react(self, info: Info):
        """
        React to an :class:`~mcdreforged.info_reactor.info.Info` object

        It will be invoked on the task executor thread

        :param info: The info to be reacted to
        """
        raise NotImplementedError()

    def on_server_start(self):
        """
        Gets invoked when the server starts
        """
        pass

    def on_server_stop(self):
        """
        Gets invoked when the server stops
        """
        pass
