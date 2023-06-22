from graia.saya import Channel
from graia.saya.event import SayaModuleInstalled
from graiax.shortcut.saya import listen
from loguru import logger

from aiomcdr.event.lifetime import (
    ApplicationLaunched,
    ApplicationLaunching,
    ApplicationShutdowned,
)

cur_channel = Channel.current()
cur_channel.name("test copy")
logger = logger.bind(name=cur_channel._name)


@listen(SayaModuleInstalled)
async def test1(channel: Channel):
    if channel._name == cur_channel._name:
        logger.info(f"{cur_channel._name}: Hi!")


@listen(ApplicationLaunching)
async def test2():
    logger.debug("ApplicationLaunching")


@listen(ApplicationLaunched)
async def test3():
    logger.debug("ApplicationLaunched")


@listen(ApplicationShutdowned)
async def test4():
    logger.debug("ApplicationShutdowned")
