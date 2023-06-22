"""
Analyzing and reacting events related to player
"""
from loguru import logger

from aiomcdr.app.info_reactor.abstract_info_reactor import AbstractInfoReactor
from aiomcdr.app.info_reactor.info import Info, InfoSource
from aiomcdr.event.player import PlayerJoinedEvent, PlayerLeftEvent

# from mcdreforged.plugin.plugin_event import MCDRPluginEvents
# from mcdreforged.utils.logger import DebugOption


class PlayerReactor(AbstractInfoReactor):
    async def react(self, info: Info):
        if info.source == InfoSource.SERVER:
            handler = self.server.handler

            # on_player_joined
            player = handler.parse_player_joined(info)
            if player is not None:
                logger.debug("Player joined detected")
                self.server.permission_manager.touch_player(player)
                # self.server.plugin_manager.dispatch_event(MCDRPluginEvents.PLAYER_JOINED, (player, info))
                await self.bcc.postEvent(PlayerJoinedEvent(self.server, player, info))

            # on_player_left
            player = handler.parse_player_left(info)
            if player is not None:
                logger.debug("Player left detected")
                # self.server.plugin_manager.dispatch_event(MCDRPluginEvents.PLAYER_LEFT, (player,))
                await self.bcc.postEvent(PlayerLeftEvent(self.server, player, info))

            # 原来就已经注释了
            # # on_death_message
            # if handler.parse_death_message(info):
            #     logger.debug('Death message detected')
            #     self.server.plugin_manager.call('on_death_message', (self.server.server_interface, info.content))
            #
            # # on_player_made_advancement
            # result = handler.parse_player_made_advancement(info)
            # if result is not None:
            #     logger.debug('Player made advancement detected')
            #     player, advancement = result
            #     self.server.plugin_manager.call('on_player_made_advancement', (self.server.server_interface, player, advancement))
