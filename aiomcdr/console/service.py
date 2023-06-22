from creart import create
from graia.broadcast import Broadcast
from graia.saya import Saya
from launart import Launart, Launchable

from ..event.lifetime import ApplicationShutdowned
from . import Console
from .saya import ConsoleBehaviour


class ConsoleService(Launchable):
    id: str = "console"

    @property
    def stages(self):
        return {"preparing", "cleanup"}

    @property
    def required(self):
        return set()

    async def launch(self, mgr: Launart):
        bcc = create(Broadcast)
        con = Console(bcc, prompt="Harmoland> ", launart=mgr, replace_logger=False)
        saya = create(Saya)
        saya.install_behaviours(ConsoleBehaviour(con))
        con.start()

        @bcc.receiver(ApplicationShutdowned)
        async def _():
            con.stop()

        async with self.stage("preparing"):
            ...

        async with self.stage("cleanup"):
            ...

        con.stop()
