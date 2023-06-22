from typing import TYPE_CHECKING, List, Optional

from loguru import logger
from mcdreforged.utils import class_util

from aiomcdr.app.handler.abstract_server_handler import AbstractServerHandler
from aiomcdr.app.handler.impl import (
    AbstractMinecraftHandler,
    BasicHandler,
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

if TYPE_CHECKING:
    from aiomcdr.app.server import MinecraftServer

T_Handler = AbstractServerHandler | AbstractMinecraftHandler | BasicHandler | BungeecordHandler | VelocityHandler


class ServerHandlerManager:
    def __init__(self, mcdr_server: "MinecraftServer"):
        self.mcdr_server = mcdr_server
        self.handlers: dict[str, T_Handler] = {}
        self.__current_handler: T_Handler | None = None
        # the handler that should always work
        self.basic_handler: BasicHandler

        # Automation for lazy
        # self.__handler_detector = HandlerDetector(self)

    def register_handlers(self, custom_handler_class_paths: Optional[List[str]]):
        def add_handler(hdr: T_Handler):
            self.handlers[hdr.get_name()] = hdr

        self.handlers.clear()
        self.basic_handler = BasicHandler()
        add_handler(self.basic_handler)
        add_handler(VanillaHandler())
        add_handler(BukkitHandler())
        add_handler(Bukkit14Handler())
        add_handler(ForgeHandler())
        add_handler(CatServerHandler())
        add_handler(Beta18Handler())
        add_handler(BungeecordHandler())
        add_handler(WaterfallHandler())
        add_handler(VelocityHandler())
        if custom_handler_class_paths is not None:
            for class_path in custom_handler_class_paths:
                try:
                    handler_class = class_util.load_class(class_path)
                except Exception:
                    logger.exception(f'Fail to load info handler from "{class_path}"')
                else:
                    if issubclass(handler_class, AbstractServerHandler):
                        handler = handler_class()
                        if handler.get_name() not in self.handlers:
                            add_handler(handler)
                            logger.debug(f"Loaded info handler {handler_class.__name__} from {class_path}")
                        else:
                            logger.error(
                                f"Handler with name {handler.get_name()} from path {class_path} is already registered, ignored"
                            )
                    else:
                        logger.error(
                            f'Wrong handler class "{class_path}", expected {AbstractServerHandler} but found {handler_class}'
                        )

    def set_handler(self, handler_name: str):
        try:
            self.__current_handler = self.handlers[handler_name]
        except KeyError:
            logger.error(f'Fail to load handler with name "{handler_name}"')
            logger.error("Fallback basic handler is used, MCDR might not works correctly")
            self.__current_handler = self.basic_handler  # type: ignore

    def get_current_handler(self) -> T_Handler:
        return self.__current_handler or self.basic_handler

    def get_basic_handler(self) -> BasicHandler:
        return self.basic_handler

    # Automation for lazy
    # def start_handler_detection(self):
    #     self.__handler_detector.start_handler_detection()

    # def detect_text(self, text: str):
    #     self.__handler_detector.detect_text(text)


# class HandlerDetector:
#     HANDLER_DETECTION_MINIMUM_SAMPLE_COUNT = 20  # At least 20 messages
#     HANDLER_DETECTION_MINIMUM_SAMPLING_TIME = 60  # will do sample for 1 minute

#     def __init__(self, manager: 'ServerHandlerManager'):
#         self.manager = manager
#         self.mcdr_server: 'MCDReforgedServer' = manager.mcdr_server
#         self.running_flag = False
#         self.text_queue = queue.Queue()
#         self.text_count = 0
#         self.success_count = collections.defaultdict(lambda: 0)

#     def start_handler_detection(self):
#         if not self.is_detection_running():
#             self.running_flag = True
#             self.text_count = 0
#             self.success_count.clear()
#             misc_util.start_thread(self.__detection_thread, (), 'HandlerDetector')

#     def is_detection_running(self) -> bool:
#         return self.running_flag

#     def __detection_thread(self):
#         start_time = time.time()
#         while True:
#             time_elapsed = time.time() - start_time
#             if (
#                 time_elapsed >= self.HANDLER_DETECTION_MINIMUM_SAMPLING_TIME
#                 and self.text_count >= self.HANDLER_DETECTION_MINIMUM_SAMPLE_COUNT
#             ):
#                 break
#             try:
#                 text: str = self.text_queue.get(block=True, timeout=1)
#             except queue.Empty:
#                 continue

#             self.text_count += 1
#             for handler in self.manager.handlers.values():
#                 if handler is not self.manager.basic_handler:
#                     try:
#                         handler.parse_server_stdout(handler.pre_parse_server_stdout(text))
#                     except Exception:
#                         pass
#                     else:
#                         self.success_count[handler] += 1

#         self.running_flag = False
#         while True:  # clean the queue
#             try:
#                 self.text_queue.get(block=False)
#             except queue.Empty:
#                 break

#         lst = self.finalize_detection_result()  # type: List[Tuple[AbstractServerHandler, int]]
#         if len(lst) == 0:
#             return
#         total = self.text_count
#         best_count = lst[0][1]
#         end = 1
#         while end < len(lst) and lst[end][1] == best_count:
#             end += 1
#         best_handlers = set(map(lambda item: item[0], lst[:end]))
#         current_handler = self.manager.get_current_handler()
#         current_count = self.success_count[self.manager.get_current_handler()]
#         if current_handler not in best_handlers:
#             logger.warning(self.mcdr_server.tr('server_handler_manager.handler_detection.result1'))
#             logger.warning(
#                 self.mcdr_server.tr(
#                     'server_handler_manager.handler_detection.result2',
#                     current_handler.get_name(),
#                     round(100.0 * current_count / total, 2),
#                     current_count,
#                     total,
#                 )
#             )
#             for best_handler, best_count in lst[:end]:
#                 logger.warning(
#                     self.mcdr_server.tr(
#                         'server_handler_manager.handler_detection.result3',
#                         best_handler.get_name(),
#                         round(100.0 * best_count / total, 2),
#                         best_count,
#                         total,
#                     )
#                 )

#     def detect_text(self, text: str):
#         if self.is_detection_running():
#             self.text_queue.put(text)

#     def finalize_detection_result(self):
#         current_handler_set = set(self.manager.handlers.values())  # type: Set[AbstractServerHandler]
#         lst = list(
#             filter(lambda item: item[0] in current_handler_set, self.success_count.items())
#         )  # type: List[Tuple[AbstractServerHandler, int]]
#         lst.sort(key=lambda item: item[1], reverse=True)
#         return lst
