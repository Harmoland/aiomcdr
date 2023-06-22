# (WIP) aiomcdr

一个**随时弃坑**的部分移植到 Aysncio 的 MCDR（[MCDReforged](https://github.com/Fallen-Breath/MCDReforged)）

MCDR 为了不阻塞主线程，部分操作只能开新线程，对于新手来说很容易出现线程不安全的操作，并且
MCDR 的 `new_thread.get_return_value` 方法类型提示非常不友好，导致 IDE 一片红，有点难受，所以有了这个随便写写的
**aiomcdr**。

目前包含部分插件一起传，仅供测试用，`plugins` 文件夹不属于开源部分

## 已实现

- 服务器的启动与关闭
- 事件广播
- 插件加载与卸载（含接口）
- 执行控制台命令
- 更多...

## 未实现

- 服务器退出时不退出 aiomcdr
- 服务器重启
- i18n
- 更多...

## 可能有问题

- 权限相关
- 更多...

## 不会/暂时不会实现

- 控制台命令补全
- 偏好（preference）相关
- 命令注册
- `!!MCDR` 命令
- 更多...

## Breaking Change

- `MCDReforgedServer.logger` 和 `MCDReforgedServerInterface.logger` 不存在了
- 更多...

## 事件对应

[MCDR 原事件列表](https://mcdreforged.readthedocs.io/zh_CN/latest/plugin_dev/event.html)

- 插件被加载 on_load -> `graia.saya.event.SayaModuleInstalled`（需做特殊判断）
- 插件被卸载 on_unload -> 无
- 标准信息 on_info -> `aiomcdr.event.info.InfoEvent`
- 用户信息 on_user_info `aiomcdr.event.info.UserInfoEvent`
- 服务端刚被启动 on_server_start -> `aiomcdr.event.lifetime.ApplicationLaunching`
- 服务端启动完成 on_server_startup -> `aiomcdr.event.lifetime.ApplicationLaunched`
- 服务端终止 on_server_stop -> `aiomcdr.event.lifetime.ApplicationShutdowned`
- MCDR 正在启动 on_mcdr_start -> 暂无
- MCDR 正在关闭 on_mcdr_stop -> 暂无
- 玩家加入 on_player_joined -> `aiomcdr.event.player.PlayerJoinedEvent`
- 玩家离开 on_player_left -> `aiomcdr.event.player.PlayerLeftEvent`
