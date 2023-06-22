"""
Permission control things
"""
from dataclasses import field
from typing import TYPE_CHECKING, Literal, Optional, Set

from kayaku import config, create, save
from loguru import logger

from aiomcdr.app.command.command_source import (
    CommandSource,
    ConsoleCommandSource,
    PlayerCommandSource,
)
from aiomcdr.app.permission.permission_level import (
    PermissionLevel,
    PermissionLevelItem,
    PermissionParam,
)

if TYPE_CHECKING:
    from aiomcdr.app.server import MinecraftServer


@config("mcdr.permission")
class PermissionStorage:
    default_level: Literal["owner", "admin", "helper", "user", "guest"] = "user"
    owner: list[str] = field(default_factory=lambda: ["Fallen_Breath"])
    admin: list[str] = field(default_factory=lambda: [])
    helper: list[str] = field(default_factory=lambda: [])
    user: list[str] = field(default_factory=lambda: [])
    guest: list[str] = field(default_factory=lambda: [])

    def __getitem__(self, key):
        return self.__getattribute__(key)

    def __setitem__(self, key, value):
        return self.__setattr__(key, value)


class PermissionManager:
    def __init__(self, server: "MinecraftServer"):
        self.server = server
        self.storage = create(PermissionStorage)

    # --------------
    # File Operating
    # --------------

    def load_permission_file(self, *, allowed_missing_file: bool = True):
        """
        Load the permission file from disk
        """
        self.storage = create(PermissionStorage, flush=True)

    # def file_presents(self) -> bool:
    #     return self.storage.file_presents()

    # def save_default(self):
    #     self.storage.save_default()

    # ---------------------
    # Permission processing
    # ---------------------

    def get_default_permission_level(self) -> str:
        """
        Return the default permission level
        """
        return self.storage.default_level

    def set_default_permission_level(self, level: PermissionLevelItem):
        """
        Set default permission level
        A message will be informed using server logger
        """
        self.storage.default_level = level.name
        save(self.storage)
        logger.info("permission_manager.set_default_permission_level.done", level.name)

    def get_permission_group_list(self, value: PermissionParam):
        """
        Return the list of the player who has permission level <level>
        Example return value: ['Steve', 'Alex']

        :param value: a permission related object
        :rtype: list[str]
        """
        level_name = PermissionLevel.from_value(value).name
        if self.storage[level_name] is None:
            self.storage[level_name] = []
        return self.storage[level_name]

    def add_player(self, player: str, level_name: Optional[str] = None) -> int:
        """
        Add a new player with permission level level_name
        If level_name is not set use default level
        Then save the permission data to file

        :param player: the name of the player
        :param level_name: the permission level name
        :return: the permission of the player after operation done
        """
        if level_name is None:
            level_name = self.get_default_permission_level()
        PermissionLevel.from_value(level_name)  # validity check
        self.get_permission_group_list(level_name).append(player)
        logger.debug(f"Added player {player} with permission level {level_name}")
        save(self.storage)
        return PermissionLevel.from_value(level_name).level

    def remove_player(self, player: str):
        """
        Remove a player from data, then save the permission data to file
        If the player has multiple permission level, remove them all
        And then save the permission data to file

        :param player: the name of the player
        """
        while True:
            level = self.get_player_permission_level(player, auto_add=False)
            if level is None:
                break
            self.get_permission_group_list(level).remove(player)
        logger.debug(f"Removed player {player}")
        save(self.storage)

    def set_permission_level(self, player: str, new_level: PermissionLevelItem):
        """
        Set new permission level of the player
        Basically it will remove the player first, then add the player with given permission level
        Then save the permission data to file

        :param player: the name of the player
        :param new_level: the permission level name
        """
        self.remove_player(player)
        self.add_player(player, new_level.name)
        logger.info("permission_manager.set_permission_level.done", player, new_level.name)

    def touch_player(self, player: str):
        """
        Add player if it's not in permission data

        :param player: the name of the player
        """
        self.get_player_permission_level(player)

    def get_player_permission_level(self, player: str, *, auto_add: bool = True) -> int:
        """
        If the player is not in the permission data set its level to default_level,
        unless parameter auto_add is set to False, then it will return 0
        If the player is in multiple permission level group it will return the highest one

        :param player: the name of the player
        :param auto_add: if it's True when player is invalid he will receive the default permission level
        :return the permission level from a player's name. If auto_add is False and player invalid return None
        """
        for level_value in PermissionLevel.LEVELS[::-1]:  # high -> low
            if player in self.get_permission_group_list(level_value):
                return level_value
        return self.add_player(player) if auto_add else 0

    def get_permission(self, source: CommandSource) -> int:
        """
        Gets called in CommandSource implementation
        """
        if isinstance(source, ConsoleCommandSource):
            return PermissionLevel.CONSOLE_LEVEL
        elif isinstance(source, PlayerCommandSource):
            return self.get_player_permission_level(source.player)
        else:
            raise TypeError(f"Unknown type {type(source)} in get_permission")

    def get_players(self) -> Set[str]:
        players = set()
        for level_value in PermissionLevel.LEVELS:
            players.update(self.get_permission_group_list(level_value))
        return players
