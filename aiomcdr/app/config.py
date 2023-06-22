from dataclasses import dataclass, field
from typing import Literal

from kayaku import config


@dataclass
class RconConfig:
    enabled: bool = False
    address: str = "127.0.0.1"
    port: int = 25575
    password: str = "password"


@config("mcdr.main")
class MCDRConfig:
    working_directory: str = "server"
    """
    The working directory of the server.
    If you use the default value server/ I will suggest you put all the files related to the server into the server/ directory
    """
    start_command: str = "java -server -Xms1G -Xmx2G -jar fabric-server-launch.jar nogui"
    """Mirai Api Http 地址"""
    handler: Literal[
        "vanilla_handler",
        "beta18_handler",
        "bukkit_handler",
        "bukkit14_handler",
        "forge_handler",
        "cat_server_handler",
        "bungeecord_handler",
        "waterfall_handler",
        "velocity_handler",
    ] = "vanilla_handler"
    """
    The handler to the specific way to parse the standard output text of the server and the correct command for server control

    vanilla_handler, for Vanilla / Carpet / Fabric server
    beta18_handler, for Vanilla server in beta1.8 versions
    bukkit_handler, For Bukkit / Spigot server with Minecraft version below 1.14, and Paper / Mohist server in all version
    bukkit14_handler, For Bukkit / Spigot server with Minecraft version 1.14 and above
    forge_handler, For Forge server
    cat_server_handler, For CatServer server
    bungeecord_handler, for Bungeecord server
    waterfall_handler,  for Waterfall server
    velocity_handler,  for Velocity server
    """
    encoding: str | None = None
    """MCDR -> Server"""
    decoding: str | None = None
    """Server -> MCDR"""
    rcon: RconConfig = field(default_factory=lambda: RconConfig())
    """
    rcon setting

    if enabled, plugins can use rcon to query commands from the server
    """
    debug: bool = False
