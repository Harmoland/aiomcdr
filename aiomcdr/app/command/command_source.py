from abc import ABC
from contextlib import contextmanager
from typing import TYPE_CHECKING, Optional

from loguru import logger
from mcdreforged.permission.permission_level import PermissionLevel
from mcdreforged.translation.translation_text import RTextMCDRTranslation
from mcdreforged.utils import misc_util
from mcdreforged.utils.types import MessageText
from typing_extensions import TypeGuard

if TYPE_CHECKING:
    from mcdreforged.plugin.type.plugin import AbstractPlugin
    from mcdreforged.preference.preference_manager import PreferenceItem

    from aiomcdr.app.info_reactor.info import Info
    from aiomcdr.app.server import MinecraftServer
    from aiomcdr.app.server_interface import MinecraftServerInterface


class CommandSource(ABC):
    """
    :class:`CommandSource`: is an abstracted command executor model. It provides several methods for command execution

    Class inheriting tree::

            CommandSource
            ├── InfoCommandSource
            │   ├── PlayerCommandSource
            │   └── ConsoleCommandSource
            └── PluginCommandSource

    Plugins can declare a class inherited from :class:`CommandSource` to create their own command source
    """

    @property
    def is_player(self) -> TypeGuard["PlayerCommandSource"]:  # type: ignore
        """
        If the command source is a player command source

        :return: ``True`` if it's a player command source, ``False`` otherwise
        """
        return isinstance(self, PlayerCommandSource)

    @property
    def is_console(self) -> TypeGuard["ConsoleCommandSource"]:  # type: ignore
        """
        If the command source is a console command source

        :return: ``True`` if it's a console command source, ``False`` otherwise
        """
        return isinstance(self, ConsoleCommandSource)

    def get_server(self) -> "MinecraftServerInterface":
        """
        Return the server interface instance
        """
        raise NotImplementedError()

    def get_permission_level(self) -> int:
        """
        Return the permission level that the command source has

        The permission level is represented by int
        """
        raise NotImplementedError()

    def get_preference(self) -> Optional["PreferenceItem"]:
        """
        Return the preference of the command source

        Only :class:`PlayerCommandSource` and :class:`ConsoleCommandSource` are supported, otherwise None will be returned

        .. seealso::

                :class:`~mcdreforged.plugin.server_interface.ServerInterface`'s method :meth:`~mcdreforged.plugin.server_interface.ServerInterface.get_preference`

        .. versionadded:: v2.1.0
        """
        return None

    @contextmanager
    def preferred_language_context(self):
        """
        A quick helper method to use the language value in preference to create a context
        with :meth:`RTextMCDRTranslation.language_context() <mcdreforged.translation.translation_text.RTextMCDRTranslation.language_context>`

        .. seealso::

                Class :class:`~mcdreforged.translation.translation_text.RTextMCDRTranslation`

        Example usage::

                with source.preferred_language_context():
                        message = source.get_server().rtr('my_plugin.placeholder').to_plain_text()
                        text.set_click_event(RAction.suggest_command, message)

        .. versionadded:: v2.1.0
        """
        preference = self.get_preference()
        if preference is None:
            raise ValueError(f"{self} is not `PlayerCommandSource` or `ConsoleCommandSource`")
        if preference.language is None:
            raise ValueError("Prefer language is None")
        with RTextMCDRTranslation.language_context(preference.language):
            yield

    def has_permission(self, level: int) -> bool:
        """
        A helper method for testing permission requirement

        :param level: The permission level to be tested
        :return: If the command source has not less permission level than the given permission level
        """
        return self.get_permission_level() >= level

    def has_permission_higher_than(self, level: int) -> bool:
        """
        Just like the :meth:`CommandSource.has_permission`, but this time it is a greater than judgment

        :param level: The permission level to be tested
        :return: If the command source has greater permission level than the given permission level
        """
        return self.get_permission_level() > level

    async def reply(self, message: MessageText, **kwargs) -> None:
        """
        Send a message to the command source. The message can be anything including RTexts

        :param message: The message you want to send
        :keyword encoding: The encoding method for the message. It's only used in :class:`PlayerCommandSource`
        :keyword console_text: Message override when it's a :class:`ConsoleCommandSource`
        """
        raise NotImplementedError()


class InfoCommandSource(CommandSource, ABC):
    """
    Command source originated from an info created by MCDR
    """

    def __init__(self, server: "MinecraftServer", info: "Info"):
        self.server = server
        self.__info = info

    def get_info(self) -> "Info":
        """
        Return the Info instance that this command source is created from
        """
        return self.__info

    def get_server(self) -> "MinecraftServerInterface":
        return self.server.server_interface

    def get_permission_level(self) -> int:
        return self.server.permission_manager.get_permission(self)

    def __str__(self):
        raise NotImplementedError()

    def __repr__(self):
        raise NotImplementedError()


class PlayerCommandSource(InfoCommandSource):
    def __init__(self, server: "MinecraftServer", info: "Info", player: str):
        if not info.is_from_server:
            raise TypeError(f"{self.__class__.__name__} should be built from server info")
        super().__init__(server, info)

        self.player: str = player
        """The name of the player"""

    # def get_preference(self) -> Optional['PreferenceItem']:
    #     return self.get_server().get_preference(self)  # type: ignore

    async def reply(self, message: MessageText, *, encoding: Optional[str] = None, **kwargs):
        """
        :keyword encoding: encoding method to be used in :meth:`ServerInterface.tell`
        """
        await self.server.server_interface.tell(self.player, message, encoding=encoding)

    def __str__(self):
        return f"Player {self.player}"

    def __repr__(self):
        return f"{type(self).__name__}[player={self.player},info_id={self.get_info().id}]"


class ConsoleCommandSource(InfoCommandSource):
    def __init__(self, server: "MinecraftServer", info: "Info"):
        if not info.is_from_console:
            raise TypeError(f"{self.__class__.__name__} should be built from console info")
        super().__init__(server, info)

    # def get_preference(self) -> Optional['PreferenceItem']:
    #     return self.get_server().get_preference(self)  # type: ignore

    async def reply(self, message: MessageText, *, console_text: Optional[MessageText] = None, **kwargs):
        """
        :keyword console_text: If it's specified, overwrite the value of parameter ``message`` with it
        """
        from mcdreforged.minecraft.rtext.text import RTextBase

        if console_text is not None:
            message = console_text
        with self.preferred_language_context():
            for line in RTextBase.from_any(message).to_colored_text().splitlines():
                logger.info(line)

    def __str__(self):
        return "Console"

    def __repr__(self):
        return f"{type(self).__name__}[info_id={self.get_info().id}]"


class PluginCommandSource(CommandSource):
    def __init__(self, server_interface: "MinecraftServerInterface", plugin: Optional["AbstractPlugin"] = None):
        self.__server_interface = server_interface
        self.__plugin = plugin

    def get_server(self) -> "MinecraftServerInterface":
        return self.__server_interface

    def get_permission_level(self) -> int:
        return PermissionLevel.PLUGIN_LEVEL

    async def reply(self, message: MessageText, **kwargs) -> None:
        misc_util.print_text_to_console(logger, message)

    def __str__(self):
        return "Plugin" if self.__plugin is None else f"Plugin {self.__plugin}"

    def __repr__(self):
        return f"{type(self).__name__}[plugin={self.__plugin}]"
