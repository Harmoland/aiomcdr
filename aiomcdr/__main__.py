import asyncio
import contextlib
import os
import pkgutil
import sys

import kayaku
import psutil
from creart import create
from graia.broadcast import Broadcast
from graia.saya import Saya
from launart import Launart
from loguru import logger
from prompt_toolkit.patch_stdout import StdoutProxy

from aiomcdr.app.service import MinecraftServerService
from aiomcdr.console.service import ConsoleService
from aiomcdr.static.path import plugin_path

if __name__ != "__main__":
    sys.exit(1)


kayaku.initialize({"{**}": "./config/{**}"})
kayaku.bootstrap()

from .app.config import MCDRConfig  # noqa: E402

config = kayaku.create(MCDRConfig)
logger.remove()
if config.debug:
    logger.add(
        StdoutProxy(raw=True),  # type: ignore
        level="DEBUG" if config.debug else "INFO",
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    )
else:
    logger.add(
        StdoutProxy(raw=True),  # type: ignore
        level="DEBUG" if config.debug else "INFO",
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | "
        "<cyan>{extra[name]}</cyan> - <level>{message}</level>",
    )
    logger.configure(extra={"name": "aiomcdr"})

mgr = Launart()
saya = create(Saya)
bcc = create(Broadcast)

with saya.module_context():
    for module in pkgutil.iter_modules([str(plugin_path)]):
        saya.require(f"plugins.{module.name}")

mgr.add_service(MinecraftServerService())
mgr.add_launchable(ConsoleService())

try:
    mgr.launch_blocking(loop=bcc.loop)
except (asyncio.exceptions.CancelledError, RuntimeError):
    logger.critical("Launart 非正常退出，正在杀死子进程，可能会造成服务器回档或坏档")
    with contextlib.suppress(psutil.NoSuchProcess):
        root = psutil.Process(os.getpid())
        processes = [root]
        processes.extend(root.children(recursive=True))
        for proc in reversed(processes):  # child first, parent last
            with contextlib.suppress(psutil.NoSuchProcess):
                proc_pid, proc_name = proc.pid, proc.name()  # in case we cannot get them after the process dies
                proc.kill()
                logger.info("进程 {0} (pid {1}) 已杀死", proc_name, proc_pid)

kayaku.save_all()
