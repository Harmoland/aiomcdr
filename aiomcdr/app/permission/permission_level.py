import collections
from enum import Enum
from typing import Literal, Optional, Union

PermissionParam = Union[str, int]
T_Perm = Literal["owner", "admin", "helper", "user", "guest"]


class PermissionLevelItem:
    name: T_Perm
    level: int

    def __init__(self, name, level: int):
        self.name = name
        self.level = level

    def __str__(self):
        return f"{self.level} ({self.name})"

    def __repr__(self):
        return f"Permission[name={self.name},level={self.level}]"

    def __lt__(self, other):
        return self.level < other.level if isinstance(other, type(self)) else False


class PermissionLevel:
    class __Storage(Enum):
        GUEST_ = PermissionLevelItem("guest", 0)
        USER_ = PermissionLevelItem("user", 1)
        HELPER_ = PermissionLevelItem("helper", 2)
        ADMIN_ = PermissionLevelItem("admin", 3)
        OWNER_ = PermissionLevelItem("owner", 4)

    GUEST = __Storage.GUEST_.value.level
    USER = __Storage.USER_.value.level
    HELPER = __Storage.HELPER_.value.level
    ADMIN = __Storage.ADMIN_.value.level
    OWNER = __Storage.OWNER_.value.level

    INSTANCES: list[PermissionLevelItem] = [item.value for item in __Storage]
    LEVELS: list[int] = [inst.level for inst in INSTANCES]
    NAMES: list[str] = [inst.name for inst in INSTANCES]
    __NAME_DICT: dict[str, PermissionLevelItem] = collections.OrderedDict(zip(NAMES, INSTANCES))
    __LEVEL_DICT: dict[int, PermissionLevelItem] = collections.OrderedDict(zip(LEVELS, INSTANCES))

    MAXIMUM_LEVEL: int = LEVELS[-1]
    MINIMUM_LEVEL: int = LEVELS[0]
    MCDR_CONTROL_LEVEL: int = ADMIN
    PHYSICAL_SERVER_CONTROL_LEVEL: int = OWNER
    CONSOLE_LEVEL: int = MAXIMUM_LEVEL
    PLUGIN_LEVEL: int = MAXIMUM_LEVEL

    @classmethod
    def __check_range(cls, level: int):
        if not cls.MINIMUM_LEVEL <= level <= cls.MAXIMUM_LEVEL:
            raise ValueError(f"Value {level} out of range [{cls.MINIMUM_LEVEL}, {cls.MAXIMUM_LEVEL}]")

    @classmethod
    def from_value(cls, value: PermissionParam):
        """
        Convert any type of permission level into int value. Examples:
                'guest'	-> 0
                'admin'	-> 3
                '1'		-> 1
                2		-> 2
        If the argument is invalid return None

        :param value: a permission related object
        :type value: str or int
        :rtype: PermissionLevelItem
        """
        level = None
        if isinstance(value, str):
            if value.isdigit():
                value = int(value)
            elif value in cls.NAMES:
                level = cls.__NAME_DICT[value]
        if isinstance(value, int):
            cls.__check_range(value)
            level = cls.__LEVEL_DICT[value]
        if level is None:
            raise TypeError(f"Unsupported value for {cls.__name__}: {value}")
        return level

    @classmethod
    def get_level(cls, value: PermissionParam) -> Optional[PermissionLevelItem]:
        """
        Fail-proof version of from_value
        """
        try:
            return cls.from_value(value)
        except (TypeError, ValueError):
            return None
