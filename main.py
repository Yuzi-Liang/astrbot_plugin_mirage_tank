import re
import time

from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api.message_components import Image as AstrImage, Plain as AstrPlain
from astrbot.api import logger
from astrbot.core.utils.session_waiter import session_waiter, SessionController
from .config import TIMEOUT_SEC, TEMP_DIR
from .processor.utils import save_image


@register("miragetank", "poisama", "幻影坦克生成插件", "1.0")
class MirageTankPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    # 注册指令的装饰器。指令名为 幻影坦克。注册成功后，发送 `/幻影坦克` 就会触发这个指令，接受图片输入并生成幻影坦克`
    @filter.command("幻影坦克")
    async def generate_mirage_tank(self, event: AstrMessageEvent):
        """生成幻影坦克指令"""
        try:
            yield event.plain_result(f"请发送表图,{TIMEOUT_SEC}s 内有效：")

            @session_waiter(timeout=TIMEOUT_SEC, record_history_chains=False)
            async def image_waiter(controller: SessionController, event: AstrMessageEvent):
                # img = event.message_obj
                # img_path = save_image(img, TEMP_DIR)
                img_path = "E:\\qqbot\\dev\\AstrBot\\data\\temp\\test.jpg"
                logger.info(img_path)
                await event.send(event.chain_result([AstrImage.fromFileSystem(img_path)]))
                controller.stop()  # 停止会话控制器，会立即结束。
                return

            try:
                await image_waiter(event)
            except TimeoutError as _:  # 当超时后，会话控制器会抛出 TimeoutError
                yield event.plain_result("已超时，幻影坦克生成已取消喵")
            finally:
                event.stop_event()

        except Exception as e:
            logger.error("handle_empty_mention error: " + str(e))