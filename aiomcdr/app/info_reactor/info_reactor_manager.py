"""
The place to reacting information from the server
"""
from typing import TYPE_CHECKING, List, Optional

from graia.broadcast import Broadcast
from loguru import logger
from mcdreforged.utils import class_util

from aiomcdr.app.info_reactor.impl import GeneralReactor, PlayerReactor, ServerReactor

from .abstract_info_reactor import AbstractInfoReactor
from .info import Info

if TYPE_CHECKING:
    from ..server import MinecraftServer


class InfoReactorManager:
    def __init__(self, bcc: "Broadcast", server: "MinecraftServer"):
        self.bcc = bcc
        self.server = server
        self.last_queue_full_warn_time = None
        self.reactors = []  # type: List[AbstractInfoReactor]

    def register_reactors(self, custom_reactor_class_paths: Optional[List[str]] = None):
        self.reactors.clear()
        self.reactors.extend(
            [
                GeneralReactor(self.bcc, self.server),
                ServerReactor(self.bcc, self.server),
                PlayerReactor(self.bcc, self.server),
            ]
        )
        if custom_reactor_class_paths is not None:
            for class_path in custom_reactor_class_paths:
                try:
                    reactor_class = class_util.load_class(class_path)
                except Exception:
                    logger.exception(f'Fail to load info reactor from "{class_path}"')
                else:
                    if issubclass(reactor_class, AbstractInfoReactor):
                        self.reactors.append(reactor_class(self.bcc, self.server))
                        logger.debug(f"Loaded info reactor {reactor_class.__name__} from {class_path}")
                    else:
                        logger.error(
                            f'Wrong reactor class "{class_path}", '
                            f"expected {AbstractInfoReactor} but found {reactor_class}"
                        )

    async def process_info(self, info: Info):
        for reactor in self.reactors:
            try:
                await reactor.react(info)
            except Exception:
                logger.exception("info_reactor_manager.react.error", type(reactor).__name__)

        # send command input from the console to the server's stdin
        if info.is_from_console and info.should_send_to_server() and info.content:
            await self.server.send(info.content)

    async def put_info(self, info: Info):
        info.attach_server(self.server)
        # echo info from the server to the console
        # if info.is_from_server:
        #     logger.debug(info.raw_content)
        await self.process_info(info)
        # try:
        #     self.server.task_executor.enqueue_info_task(lambda: self.process_info(info), info.is_user)
        # except queue.Full:
        #     current_time = time.monotonic()
        #     logging_method = logger.debug
        #     kwargs = {'option': DebugOption.REACTOR}
        #     if (
        #         self.last_queue_full_warn_time is None
        #         or current_time - self.last_queue_full_warn_time >= core_constant.REACTOR_QUEUE_FULL_WARN_INTERVAL_SEC
        #     ):
        #         logging_method = logger.warning
        #         kwargs = {}
        #         self.last_queue_full_warn_time = current_time
        #     logging_method(self.server.tr('info_reactor_manager.info_queue.full'), **kwargs)

    def on_server_start(self):
        for reactor in self.reactors:
            reactor.on_server_start()

    def on_server_stop(self):
        for reactor in self.reactors:
            reactor.on_server_stop()
