"""
Analyzing and reacting events related to server
"""

from loguru import logger

from aiomcdr.app.info_reactor.abstract_info_reactor import AbstractInfoReactor
from aiomcdr.app.info_reactor.info import Info, InfoSource
from aiomcdr.app.info_reactor.server_information import ServerInformation
from aiomcdr.event.lifetime import ApplicationLaunched

# from mcdreforged.mcdr_state import MCDReforgedFlag
# from mcdreforged.plugin.plugin_event import MCDRPluginEvents
# from mcdreforged.utils.logger import DebugOption


class ServerReactor(AbstractInfoReactor):
    @property
    def server_info(self) -> ServerInformation:
        return self.server.server_information

    def on_server_start(self):
        self.server_info.clear()

    async def react(self, info: Info):
        if info.source != InfoSource.SERVER:
            return
        handler = self.server.handler

        if handler.test_server_startup_done(info):
            logger.debug("Server startup detected")
            # self.server.add_flag(MCDReforgedFlag.SERVER_STARTUP)
            # self.server.plugin_manager.dispatch_event(MCDRPluginEvents.SERVER_STARTUP, ())
            self.bcc.postEvent(ApplicationLaunched(self.server))

        version = handler.parse_server_version(info)
        if version is not None:
            logger.debug(f"Server version detected: {version}")
            self.server_info.version = version

        ip_and_port = handler.parse_server_address(info)
        if ip_and_port is not None:
            logger.debug("Server ip detected: {}:{}".format(*ip_and_port))
            self.server_info.ip, self.server_info.port = ip_and_port

        # if handler.test_rcon_started(info):
        #     logger.debug('Server rcon started detected')
        #     self.server.add_flag(MCDReforgedFlag.SERVER_RCON_READY)
        #     self.server.connect_rcon()

        # if handler.test_server_stopping(info):  # notes that it might happen more than once in the server lifecycle
        #     logger.debug('Server stopping detected')
        #     self.server.rcon_manager.disconnect()
