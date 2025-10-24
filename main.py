from pathlib import Path

from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api.message_components import Image as AstrImage
from astrbot.api import logger
from astrbot.core import AstrBotConfig
from astrbot.core.utils.session_waiter import session_waiter, SessionController, SessionFilter
from .processor.inference import generate_mirage
from .processor.utils import save_image_as_png


class UserSessionFilter(SessionFilter):
    """确保每个用户的会话独立"""
    def __init__(self, session_id: str):
        self.session_id = session_id

    def filter(self, event: AstrMessageEvent) -> str:
        current_session_id = event.get_session_id()
        # 只接受同一个用户发来的消息
        return self.session_id if current_session_id == self.session_id else ""

@register("miragetank", "poisama", "幻影坦克生成插件", "1.2")
class MirageTankPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        self.timeout = self.config.get("timeout", 30)
        self.max_img_size = self.config.get("max_img_size", 10)

        if self.timeout <= 0 or self.timeout >= 3600:
            logger.warning("超时时间不合理，已回退为 30s。")
            self.timeout = 30
            self.config["timeout"] = 30
            self.config.save_config()

        if self.max_img_size <= 0 or self.max_img_size >= 1024:
            logger.warning("最大图片尺寸不合理，已回退为 10MB。")
            self.max_img_size = 10
            self.config["max_img_size"] = 10
            self.config.save_config()

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
                back_img_path = result_path = None
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
                    img_path = await save_image_as_png(img_msg.url, max_image_size=self.max_img_size * 1024 * 1024)
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
                        for path_label, file_path in [
                            ("front_img_path", getattr(controller, "front_img_path", None)),
                            ("back_img_path", back_img_path),
                            ("result_path", result_path),
                        ]:
                            try:
                                if file_path:
                                    p = Path(file_path)
                                    if p.exists():
                                        p.unlink()
                            except Exception as e:
                                logger.warning(f"清理文件失败: {path_label}: {file_path} ({e})")

                        controller.stop()

            try:
                session_id = event.get_session_id()
                await image_waiter(event, session_filter=UserSessionFilter(session_id))
            except TimeoutError as _:  # 当超时后，会话控制器会抛出 TimeoutError
                yield event.plain_result("已超时，幻影坦克生成已取消喵")
            finally:
                event.stop_event()

        except Exception as e:
            logger.error("handle_mirage_session error: " + str(e))
            yield event.plain_result("发生未知错误，请重试喵")

    # 普通幻影坦克命令
    @filter.command("幻影坦克")
    async def mirage_gray(self, event: AstrMessageEvent):
        """
        生成幻影坦克
        """
        async for _ in self._handle_mirage_session(event, mode="gray"):
            yield _

    # 彩色幻影坦克命令
    @filter.command("彩色幻影坦克")
    async def mirage_color(self, event: AstrMessageEvent):
        """
        生成彩色幻影坦克
        """
        async for _ in self._handle_mirage_session(event, mode="color"):
            yield _
