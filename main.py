import os

from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api.message_components import Image as AstrImage
from astrbot.api import logger
from astrbot.core import AstrBotConfig
from astrbot.core.utils.session_waiter import session_waiter, SessionController
from .processor.inference import generate_mirage
from .processor.utils import save_image_as_png


@register("miragetank", "poisama", "幻影坦克生成插件", "1.1")
class MirageTankPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        self.timeout = self.config.get("TIMEOUT_SEC", "30")

    async def _handle_mirage_session(self, event: AstrMessageEvent, mode: str):
        """
        通用会话：接收两张图 -> 生成 -> 发送 -> 清理
        """
        try:
            yield event.plain_result(f"请发送表图，{self.timeout}s 内有效喵")

            @session_waiter(timeout=self.timeout, record_history_chains=False)
            async def image_waiter(controller: SessionController, event: AstrMessageEvent):
                """
                等待发送图片作为表图/里图
                """
                controller.state = getattr(controller, "state", "waiting_front")
                msg_str = event.message_str
                if msg_str == "取消":
                    await event.send(event.plain_result("已取消幻影坦克生成喵~"))
                    controller.stop()  # 停止会话控制器，会立即结束。
                    return

                img_msg = event.message_obj.message[0]

                # 如果用户发送的不是图片，则要求用户重新发送
                if not isinstance(img_msg, AstrImage):
                    await event.send(event.plain_result("这不是一张图片，请重新发送喵"))
                    return

                # 获取用户发送的图片
                try:
                    img_path = await save_image_as_png(img_msg.url)
                except Exception as e:
                    logger.error(f"下载图片失败: " + str(e))
                    await event.send(event.plain_result("图片下载失败，请稍后再试喵"))
                    controller.stop()
                    return

                try:
                    # 如果还没收到过图片，等待发送第一张图片作为表图
                    if controller.state == "waiting_front":
                        controller.front_img_path = img_path
                        controller.state = "waiting_back"
                        await event.send(event.plain_result("收到表图喵！请发送里图～"))
                        controller.keep(timeout=self.timeout, reset_timeout=True)
                        return

                    # 等待发送第二张图片作为里图
                    elif controller.state == "waiting_back":
                        back_img_path = img_path
                        await event.send(event.plain_result("收到里图喵！请等待幻影坦克生成喵～"))

                        result_path = await generate_mirage(controller.front_img_path, back_img_path, mode=mode)

                        await event.send(event.plain_result("幻影坦克生成完毕！请签收喵～"))
                        await event.send(event.chain_result([AstrImage.fromFileSystem(result_path)]))
                        controller.state = "finished"

                except Exception as e:
                    logger.error("处理图片失败: " + str(e))
                    await event.send(event.plain_result("图片处理失败，请稍后再试喵"))
                    controller.stop()
                    return

                # 清理资源
                finally:
                    if controller.state == "finished":
                        if hasattr(controller, "front_img_path"):
                            os.unlink(controller.front_img_path)
                        if back_img_path and os.path.exists(back_img_path):
                            os.unlink(back_img_path)
                        if result_path and os.path.exists(result_path):
                            os.unlink(result_path)
                        controller.stop()

            try:
                await image_waiter(event)
            except TimeoutError as _:  # 当超时后，会话控制器会抛出 TimeoutError
                yield event.plain_result("已超时，幻影坦克生成已取消喵")
            finally:
                event.stop_event()

        except Exception as e:
            logger.error("handle_empty_mention error: " + str(e))
            yield event.plain_result("发生未知错误，请重试喵")

    # 普通幻影坦克命令
    @filter.command("幻影坦克")
    async def mirage_gray(self, event: AstrMessageEvent):
        async for _ in self._handle_mirage_session(event, mode="gray"):
            yield _

    # 彩色幻影坦克命令
    @filter.command("彩色幻影坦克")
    async def mirage_color(self, event: AstrMessageEvent):
        async for _ in self._handle_mirage_session(event, mode="color"):
            yield _
