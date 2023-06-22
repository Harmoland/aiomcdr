#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import locale
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from uuid import UUID

import aiohttp
import orjson
from graiax.shortcut import listen
from kayaku import config, create, save
from loguru import logger

from aiomcdr.app.config import MCDRConfig
from aiomcdr.app.info_reactor.info import Info
from aiomcdr.app.server_interface import MinecraftServerInterface
from aiomcdr.event.info import InfoEvent
from aiomcdr.event.lifetime import ApplicationLaunched
from aiomcdr.event.player import PlayerJoinedEvent


@dataclass
class FirstJoinMessage:
    toEnderChest: str = "Hello, &c<player_name>!\n&b看起来你是第一次加入服务器，那就送你一个头吧，已经放到你的末影箱里了，要好好珍惜噢"
    toHand: str = "Hello, &c<player_name>!\n&b看起来你是第一次加入服务器，送你一个头吧，要好好珍惜噢"

    def __getitem__(self, _name: str):
        return self.__getattribute__(_name)


@dataclass
class Message:
    firstJoin: FirstJoinMessage = field(default_factory=lambda: FirstJoinMessage())
    JoinEvery100h: str = "&9wow，&6今天是你在服务器游玩的第{hours}个小时噢，送你一个头吧，要好好珍惜噢"
    apiError: str = "无法从 Mojang API 获取你的 UUID 因此无法给你发送头颅，请联系服务器管理员"


@config("redlnn.head_on_join")
class Config:
    message: Message = field(default_factory=lambda: Message())
    sendToEnderChestWhenFirstJoin: bool = True
    giveAnotherHeadEvery100h: bool = True
    players: dict[str, int] = field(default_factory=lambda: {})


@dataclass
class Static:
    players: dict[str, UUID] = field(default_factory=lambda: {})
    serve_folder: str = ""
    save_folder: str = ""


static = Static()


async def read_online_hour_from_save(server: MinecraftServerInterface, player_uuid: str, player_name: str) -> int:
    try:
        player_stats = Path(
            os.path.join(os.getcwd(), static.serve_folder, static.save_folder, "stats", f"{player_uuid}.json")
        ).read_text()
    except FileNotFoundError:
        await first_join_give_gead(server, player_uuid, player_name)
        return 0
    player_stats = orjson.loads(player_stats)
    online_ticks = player_stats["stats"]["minecraft:custom"]["minecraft:play_time"]
    online_total_sec = int(online_ticks / 20)
    online_minute, online_sec = divmod(online_total_sec, 60)
    return online_minute // 60


async def first_join_give_gead(server: MinecraftServerInterface, player_uuid: str, player_name: str):
    config = create(Config)
    config.players[player_uuid] = 1
    save(config)
    if config.sendToEnderChestWhenFirstJoin:
        await get_and_send_message_when_first_join("toEnderChest", player_name, server)
        await server.execute(
            f"item replace entity {player_name} enderchest.0 with "
            + 'minecraft:player_head{SkullOwner:"'
            + player_name
            + '"}'
        )
    else:
        await get_and_send_message_when_first_join("toHand", player_name, server)
        await server.execute(f"give {player_name} minecraft:player_head" + '{SkullOwner:"' + player_name + '"}')


async def get_and_send_message_when_first_join(arg0, player_name, server):
    config = create(Config)
    msg = config.message.firstJoin[arg0]
    for i in re.findall("&[0-9a-gk-r]", msg):
        msg = msg.replace(i, f"§{i[1]}")
    msg = msg.replace("<player_name>", player_name)
    await server.tell(player_name, msg)


async def give_head(server: MinecraftServerInterface, player_uuid: str, player_name: str):
    config = create(Config, flush=True)
    if player_uuid not in config.players.keys():
        await first_join_give_gead(server, player_uuid, player_name)
    elif config.giveAnotherHeadEvery100h:
        online_hour: int = await read_online_hour_from_save(server, player_uuid, player_name)
        if online_hour // 100 >= 1:
            await give_and_send_message_every_100h(player_uuid, server, player_name, online_hour)


async def give_and_send_message_every_100h(
    player_uuid: str, server: MinecraftServerInterface, player_name: str, hours: int
):
    config = create(Config)
    config.players[player_uuid] += 1
    save(config)
    msg = config.message.JoinEvery100h
    for i in re.findall("&[0-9a-gk-r]", msg):
        msg = msg.replace(i, f"§{i[1]}")
    await server.tell(player_name, msg.format(hours=hours))
    await server.execute(f"give {player_name}" + ' minecraft:player_head{SkullOwner:"' + player_name + '"}')


async def get_player_uuid(player_name: str) -> dict | int:
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://api.mojang.com/users/profiles/minecraft/{player_name}") as resp:
            if resp.status == 204:
                return 204
            elif resp.status == 200:
                return await resp.json()
            else:
                raise ValueError(f"Fail to get uuid for {player_name}")


@listen(InfoEvent)
async def on_info(info: Info):
    if info.content is None or not info.is_from_server:
        return
    if info.content.startswith("UUID of player"):
        return
    re_result = re.match(
        r"(UUID\ of\ player\ )(\S+)(\ is\ )([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})", info.content
    )
    if not re_result:
        return
    player_name = str(re_result[2])
    player_uuid = re_result[4]
    static.players[player_name] = UUID(player_uuid)


@listen(PlayerJoinedEvent)
async def on_player_joined(server: MinecraftServerInterface, player_name: str):
    if player_name in static.players:
        await give_head(server, static.players[player_name].hex, player_name)
        return

    try:
        res = await get_player_uuid(player_name)
        if isinstance(res, dict):
            await give_head(server, UUID(res["id"]).hex, player_name)
        if res == 204:
            return
    except Exception:
        config = create(Config)
        await server.tell(player_name, config.message.apiError)
        logger.error(f"无法获取玩家 {player_name} 的 UUID，因此无法给予头颅")


@listen(ApplicationLaunched)
async def on_load():
    create(Config)
    mcdr_conf = create(MCDRConfig)
    static.serve_folder = mcdr_conf.working_directory

    if os.name == "nt":
        try:
            server_properties = Path(os.path.join(os.getcwd(), static.serve_folder, "server.properties")).read_text(
                encoding="utf8"
            )
        except UnicodeDecodeError:
            server_properties = Path(os.path.join(os.getcwd(), static.serve_folder, "server.properties")).read_text(
                encoding=locale.getpreferredencoding()
            )
    else:
        server_properties = Path(os.path.join(os.getcwd(), static.serve_folder, "server.properties")).read_text()

    if res := re.search(r"(level-name=)(\S+)", server_properties):
        save_folder = res[2]
    else:
        save_folder = "world"
    static.save_folder = save_folder
