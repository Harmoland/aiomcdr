import asyncio
import contextlib
import locale
import os
import subprocess
import sys
from typing import TYPE_CHECKING

import psutil
from creart import create, it
from graia.broadcast import Broadcast
from kayaku import create as create_config
from launart import Launart
from loguru import logger
from mcdreforged.utils.exception import DecodeError

from aiomcdr.app.config import MCDRConfig
from aiomcdr.app.handler.impl import (
    Beta18Handler,
    Bukkit14Handler,
    BukkitHandler,
    BungeecordHandler,
    CatServerHandler,
    ForgeHandler,
    VanillaHandler,
    VelocityHandler,
    WaterfallHandler,
)
from aiomcdr.app.info_reactor.info_reactor_manager import InfoReactorManager
from aiomcdr.app.info_reactor.server_information import ServerInformation
from aiomcdr.app.permission.permission_manager import PermissionManager
from aiomcdr.app.server_interface import MinecraftServerInterface
from aiomcdr.event.lifetime import ApplicationLaunching, ApplicationShutdown

if TYPE_CHECKING:
    from loguru import Logger

    from aiomcdr.app.handler.abstract_server_handler import AbstractServerHandler

handlers_map = {
    "vanilla_handler": VanillaHandler,
    "beta18_handler": Beta18Handler,
    "bukkit_handler": BukkitHandler,
    "bukkit14_handler": Bukkit14Handler,
    "forge_handler": ForgeHandler,
    "cat_server_handler": CatServerHandler,
    "bungeecord_handler": BungeecordHandler,
    "waterfall_handler": WaterfallHandler,
    "velocity_handler": VelocityHandler,
}


class MinecraftServer:
    mgr: Launart | None = None
    tasks: list[asyncio.Task] = []
    proc: asyncio.subprocess.Process | None
    server_runnning: bool = False
    broadcast: Broadcast
    config: MCDRConfig
    handler: "AbstractServerHandler"
    encoding: str
    decoding: str
    server_information: ServerInformation
    server_interface: MinecraftServerInterface
    reactor_manager: InfoReactorManager
    console_logger: "Logger"
    server_logger: "Logger"

    # --------------------------
    #      Server Controls
    # --------------------------
    def __init__(self) -> None:
        self.broadcast = it(Broadcast)
        self.config = create_config(MCDRConfig)
        self.handler: "AbstractServerHandler" = handlers_map[self.config.handler]()
        self.encoding = self.config.encoding or sys.getdefaultencoding()
        self.decoding = self.config.decoding or locale.getpreferredencoding()
        self.server_information = ServerInformation()
        self.permission_manager = PermissionManager(self)
        self.server_interface = MinecraftServerInterface(self)
        self.reactor_manager = InfoReactorManager(self.broadcast, self)
        self.reactor_manager.register_reactors()
        self.console_logger = logger.bind(name="Console")
        self.server_logger = logger.bind(name="Server")

    async def start_server(self):
        self.proc = await asyncio.create_subprocess_shell(
            self.config.start_command,
            cwd=self.config.working_directory,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            shell=True,
            creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == "nt" else 0,
        )

    async def __kill_server(self):
        if self.proc is not None and self.proc.returncode is not None:
            logger.info("正在杀死服务端进程组")
            with contextlib.suppress(psutil.NoSuchProcess):
                root = psutil.Process(self.proc.pid)
                processes = [root]
                processes.extend(root.children(recursive=True))
                for proc in reversed(processes):  # child first, parent last
                    with contextlib.suppress(psutil.NoSuchProcess):
                        proc_pid, proc_name = proc.pid, proc.name()  # in case we cannot get them after the process dies
                        proc.kill()
                        logger.info("进程 {0} (pid {1}) 已杀死", proc_name, proc_pid)
        else:
            logger.warning("当服务器进程已经终止时，尝试终止服务器")

    async def check_stop(self, mgr: Launart):
        await asyncio.sleep(0.1)  # 等待服务器先启动，否则不生效
        while self.server_runnning and self.proc is not None:
            if mgr.status.exiting and self.proc.stdin is not None:
                logger.warning("服务器正在关闭，再次按下 Ctrl-C 会强制结束服务器进程，但可能会造成回档或坏档")
                await self.send("stop")
                break
            await asyncio.sleep(0.5)
        total_wait_seconds = 360
        for _ in range(total_wait_seconds):
            if self.proc is None:
                break
            try:
                if self.proc.returncode is not None:
                    break
                await asyncio.sleep(1)
            except asyncio.TimeoutError:
                if _ % 30 == 0:
                    logger.info(f"已等待服务端进程停止 {_}s，若 {total_wait_seconds - _}s 后服务器进程仍未退出，则杀死他")
            else:
                break
        else:
            logger.error("服务器进程在{total_wait_seconds}s内未退出，杀死他")
            await self.__kill_server()
        return

    # --------------------------
    #      Server Logics
    # --------------------------

    async def send(self, text: str | bytes, ending: str = "\n", encoding: str | None = None):
        """
        Send a text to server's stdin if the server is running

        :param text: A str or a bytes you want to send. if text is a str then it will attach the ending parameter to its
        back
        :param str ending: The suffix of a command with a default value
        """
        if isinstance(text, str):
            if text == "stop" and self.mgr:
                self.mgr.status.exiting = True
            encoded_text = (text + ending).encode(encoding or self.encoding)
        elif isinstance(text, bytes):
            encoded_text = text
        else:
            raise TypeError()

        if self.proc is None:
            raise ValueError("Minecraft Server has not been initialized yet.")
        if self.server_runnning and self.proc.stdin is not None:
            self.proc.stdin.write(encoded_text)
        else:
            logger.warning("服务端已关闭，不能向其标准输入流输入指令")
            logger.warning("被输入的指令: {0}", text if len(text) <= 32 else f"{text[:32]}...")

    async def __receive(self):
        if self.proc is None:
            raise ValueError("Minecraft Server has not been initialized yet.")
        if self.proc.stdout is None:
            return None
        try:
            text = await anext(self.proc.stdout)
        except StopAsyncIteration:
            for _ in range(60):
                try:
                    if self.proc.returncode is not None:
                        break
                    await asyncio.sleep(1)
                except asyncio.TimeoutError:
                    logger.info("等待服务端进程停止")
                else:
                    break
            else:
                logger.warning("服务器在其stdout关闭60秒后仍未停止，杀死他")
                await self.__kill_server()
            return
        else:
            if os.name == "nt":
                try:
                    decoded_text: str = text.decode("utf8")
                except UnicodeDecodeError:
                    decoded_text: str = text.decode(self.decoding)
                except Exception as e:
                    logger.error("解析文本 {0} 出错: {1}", text, e)
                    raise DecodeError(e) from e
            else:
                try:
                    decoded_text: str = text.decode(self.decoding)
                except Exception as e:
                    logger.error("解析文本 {0} 出错: {1}", text, e)
                    raise DecodeError(e) from e
            return decoded_text.rstrip("\n\r").lstrip("\n\r")

    async def __parse_log(self, decoded_text: str):
        try:
            decoded_text = self.handler.pre_parse_server_stdout(text=decoded_text)
        except Exception as e:
            logger.warning(f"预解析服务端标准输出流失败，使用源文本: {e}")

        try:
            parsed_result = self.handler.parse_server_stdout(decoded_text)
            if parsed_result.is_from_console:
                self.console_logger.info(f"{parsed_result.content}")
            if parsed_result.is_from_server:
                if parsed_result.is_player:
                    self.server_logger.info(f"<{parsed_result.player}> {parsed_result.content}")
                else:
                    self.server_logger.info(f"{parsed_result.content}")
        except Exception:
            logger.info(decoded_text)
        else:
            # self.handler.detect_text(text)
            await self.reactor_manager.put_info(parsed_result)

    async def loop(self):
        await self.start_server()
        self.server_runnning = True
        self.broadcast.postEvent(ApplicationLaunching(self))
        if self.proc is None:
            raise ValueError("Minecraft Server 还未初始化.")
        while True:
            if self.proc.returncode is not None:
                logger.info(f"return code: {self.proc.returncode}")
                break

            try:
                decoded_text = await self.__receive()
            except DecodeError as e:
                logger.exception(e)
                continue

            if decoded_text is None:
                break

            await self.__parse_log(decoded_text)

            await asyncio.sleep(0.001)
        self.server_runnning = False
        with contextlib.suppress(Exception):
            self.proc.kill()
        self.proc = None

    async def run(self, mgr: Launart):
        self.mgr = mgr
        while not mgr.status.exiting:
            self.tasks.append(asyncio.create_task(self.loop()))
            self.tasks.append(asyncio.create_task(self.check_stop(mgr)))
            await asyncio.wait(self.tasks)
            bcc = create(Broadcast)
            bcc.postEvent(ApplicationShutdown(self))
            for task in self.tasks:
                task.cancel()

    # TODO: connect RCON
