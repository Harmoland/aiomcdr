from graia.saya import Channel
from graiax.shortcut.saya import listen
from loguru import logger

from aiomcdr.event.info import UserInfoEvent
from aiomcdr.event.player import PlayerJoinedEvent, PlayerLeftEvent

channel = Channel.current()
channel.name("test")
logger = logger.bind(name=channel._name)


@listen(UserInfoEvent)
async def on_info(event: UserInfoEvent):
    logger.debug(event.info)
    logger.debug(event.source)


@listen(PlayerJoinedEvent)
async def on_player_join(event: PlayerJoinedEvent):
    logger.debug(event.info)
    logger.debug(event.name)


@listen(PlayerLeftEvent)
async def on_player_leave(event: PlayerLeftEvent):
    logger.debug(event.info)
    logger.debug(event.name)
