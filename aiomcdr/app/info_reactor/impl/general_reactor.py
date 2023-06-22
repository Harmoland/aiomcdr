"""
For reacting general info
Including on_info and !!MCDR, !!help command
"""

# from loguru import logger

from aiomcdr.app.info_reactor.abstract_info_reactor import AbstractInfoReactor
from aiomcdr.app.info_reactor.info import Info
from aiomcdr.event.info import InfoEvent, UserInfoEvent


class GeneralReactor(AbstractInfoReactor):
    async def react(self, info: Info):
        # if info.content is not None and info.is_from_console:
        #     await self.server.server_interface.execute(info.content)

        command_source = info.get_command_source()

        # TODO: bcc.postEvent('')
        # self.server.plugin_manager.dispatch_event(MCDRPluginEvents.GENERAL_INFO, (info,))
        await self.bcc.postEvent(InfoEvent(self.server, info, command_source))

        # TODO: bcc.postEvent('')
        if info.is_user:
            # self.server.plugin_manager.dispatch_event(MCDRPluginEvents.USER_INFO, (info,))
            await self.bcc.postEvent(UserInfoEvent(self.server, info, command_source))
