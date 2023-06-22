import contextlib
from typing import TYPE_CHECKING, Optional, Union

import psutil
from launart import ExportInterface
from loguru import logger
from mcdreforged.utils import misc_util
from mcdreforged.utils.exception import IllegalCallError
from mcdreforged.utils.types import MessageText

from aiomcdr.app.command.command_source import CommandSource, PluginCommandSource
from aiomcdr.app.info_reactor.info import Info, InfoSource
from aiomcdr.app.info_reactor.server_information import ServerInformation
from aiomcdr.app.permission.permission_level import PermissionLevel, PermissionParam

if TYPE_CHECKING:
    from aiomcdr.app.handler.abstract_server_handler import AbstractServerHandler
    from aiomcdr.app.server import MinecraftServer
    from aiomcdr.app.service import MinecraftServerService  # noqa: F401

logger = logger.bind(name="Server")


class MinecraftServerInterface(ExportInterface["MinecraftServerService"]):
    def __init__(self, server: "MinecraftServer"):
        self.server = server

    # ------------------------
    #      Server Control
    # ------------------------

    def is_rcon_running(self) -> bool:
        """
        Return if MCDR's rcon is running
        """
        ...

    def get_server_pid(self) -> int | None:
        """
        Return the pid of the server process

        Notes the process with this pid is a bash process, which is the parent process of real server process
        you might be interested in

        :return: The pid of the server. None if the server is stopped
        """
        return None if self.server.proc is None else self.server.proc.pid

    def get_server_pid_all(self) -> list[int] | None:
        """
        Return a list of pid of all processes in the server's process group

        :return: A list of pid. It will be empty if the server is stopped or the pid query failed
        """
        if self.server.proc is None:
            return None
        with contextlib.suppress(psutil.NoSuchProcess):
            root = psutil.Process(self.server.proc.pid)
            processes = [root.pid]
            processes.extend(proc.pid for proc in root.children(recursive=True))
            return processes

    def get_server_information(self) -> ServerInformation:
        """
        Return a :class:`~mcdreforged.info_reactor.server_information.ServerInformation` object indicating
        the information of the current server, interred from the output of the server

        It's field(s) might be None if the server is offline, or the related information has not been parsed

        .. versionadded:: v2.1.0
        """
        return self.server.server_information.copy()

    # ------------------------
    #     Text Interaction
    # ------------------------

    async def execute(self, text: str, *, encoding: str | None = None) -> None:
        """
        Execute a server command by sending the command content to server's standard input stream

        .. seealso::

            :meth:`execute_command` if you want to execute command in MCDR's command system

        :param text: The content of the command you want to send
        :param encoding: The encoding method for the text.
            Leave it empty to use the encoding method from the configuration of MCDR
        """
        logger.debug(f'Sending command "{text}"')
        await self.server.reactor_manager.put_info(Info(InfoSource.CONSOLE, raw_content=text))
        await self.server.send(text, encoding=encoding)

    @property
    def __server_handler(self) -> "AbstractServerHandler":
        return self.server.handler

    async def tell(self, player: str, text: MessageText, *, encoding: str | None = None) -> None:
        """
        Use command like ``/tellraw`` to send the message to the specific player

        :param player: The name of the player you want to tell
        :param text: The message you want to send to the player
        :param encoding: The encoding method for the text.
            Leave it empty to use the encoding method from the configuration of MCDR
        """
        # with RTextMCDRTranslation.language_context(self.server.preference_manager.get_preferred_language(player)):
        command = self.__server_handler.get_send_message_command(player, text, self.get_server_information())
        if command is not None:
            await self.execute(command, encoding=encoding)

    async def say(self, text: MessageText, *, encoding: str | None = None) -> None:
        """
        Use command like ``/tellraw @a`` to broadcast the message in game

        :param text: The message you want to send
        :param encoding: The encoding method for the text.
            Leave it empty to use the encoding method from the configuration of MCDR
        """
        command = self.__server_handler.get_broadcast_message_command(text, self.get_server_information())
        if command is not None:
            await self.execute(command, encoding=encoding)

    async def broadcast(self, text: MessageText, *, encoding: str | None = None) -> None:
        """
        Broadcast the message in game and to the console

        :param text: The message you want to send
        :param encoding: The encoding method for the text.
            Leave it empty to use the encoding method from the configuration of MCDR
        """
        await self.say(text, encoding=encoding)
        misc_util.print_text_to_console(logger, text)

    async def reply(
        self,
        info: Info,
        text: MessageText,
        *,
        encoding: str | None = None,
        console_text: Optional[MessageText] = None,
    ):
        """
        Reply to the source of the Info

        If the Info is from a player, then use tell to reply the player;
        if the Info is from the console, then use ``server.logger.info`` to output to the console;
        In the rest of the situations, the Info is not from a user,
        a :class:`~mcdreforged.utils.exception.IllegalCallError` is raised

        :param info: the Info you want to reply to
        :param text: The message you want to send
        :param console_text: If it's specified, *console_text* will be used instead of text when replying to console
        :param encoding: The encoding method for the text
        :raise IllegalCallError: If the Info is not from a user
        """
        source = info.get_command_source()
        if source is None:
            raise IllegalCallError("Cannot reply to the given info instance")
        await source.reply(text, encoding=encoding, console_text=console_text)

    # ------------------------
    #       Permission
    # ------------------------

    def get_permission_level(self, obj: Union[str, Info, CommandSource]) -> int:
        """
        Return an int indicating permission level number the given object has

        The object could be a str indicating the name of a player,
        an :class:`~mcdreforged.info_reactor.info.Info` instance
        or a :class:`command source <mcdreforged.command.command_source.CommandSource>`

        :param obj: The object you are querying
        :raise TypeError: If the type of the given object is not supported for permission querying
        """
        if isinstance(obj, Info):
            command_source = obj.get_command_source()
            if command_source is None:
                raise TypeError("The Info instance is not from a user")
        else:
            command_source = obj
        if isinstance(command_source, CommandSource):  # Command Source
            return command_source.get_permission_level()
        elif isinstance(command_source, str):  # Player name
            return self.server.permission_manager.get_player_permission_level(command_source)
        else:
            raise TypeError(f"Unsupported permission level querying for type {type(command_source)}")

    def set_permission_level(self, player: str, value: PermissionParam) -> None:
        """
        Set the permission level of the given player

        :param player: The name of the player that you want to set his/her permission level
        :param value: The target permission level you want to set the player to. It can be an int or a str as long as
            it's related to the permission level. Available examples: ``1``, ``"1"``, ``"user"``
        :raise TypeError: If the value parameter doesn't properly represent a permission level
        """
        level = PermissionLevel.get_level(value)
        if level is None:
            raise TypeError("Parameter level needs to be a permission related value")
        self.server.permission_manager.set_permission_level(player, level)

    def reload_permission_file(self):
        """
        Reload the permission of MCDR from permission file

        It has the same effect as command ``!!MCDR reload permission``

        .. versionadded:: v2.7.0
        """
        self.server.permission_manager.load_permission_file()

    # ------------------------
    #         Command
    # ------------------------

    def get_plugin_command_source(self) -> PluginCommandSource:
        """
        Return a simple plugin command source for e.g. command execution

        It's not player or console, it has maximum permission level, it uses :attr:`logger` for replying
        """
        return PluginCommandSource(self, None)
