from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger, AstrBotConfig
from astrbot.api.provider import ProviderRequest
from typing import List, Optional

@register("whoismymaster", "gameswu", "识别机器人主人身份并注入系统提示词", "1.0.0")
class WhoIsMyMaster(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.master_ids: List[str] = []
        self.config = config

    async def initialize(self):
        """初始化插件，读取配置文件中的主人ID列表"""
        try:
            # 获取插件配置
            config_data = self.config.get("master_id")
            if config_data:
                self.master_ids = config_data
                logger.info(f"WhoIsMyMaster: 加载主人ID列表: {self.master_ids}")
            else:
                logger.warning("WhoIsMyMaster: 未找到主人ID配置，请在配置文件中设置 master_id 列表")
        except Exception as e:
            logger.error(f"WhoIsMyMaster: 初始化失败: {e}")

    def is_master(self, sender_id: str) -> bool:
        """判断发送者是否为主人"""
        return str(sender_id) in [str(mid) for mid in self.master_ids]

    @filter.on_llm_request()
    async def on_llm_request_handler(self, event: AstrMessageEvent, req: ProviderRequest):
        """在LLM请求前注入身份信息到系统提示词"""
        try:
            sender_id = event.get_sender_id()
            sender_name = event.get_sender_name()
            
            # 判断是否为主人
            is_master = self.is_master(sender_id)
            
            # 构建身份信息
            identity_info = ""
            if is_master:
                identity_info = f"当前用户 [{sender_name}] (ID: {sender_id}) 是你的主人。"
                logger.info(f"WhoIsMyMaster: 识别到主人 {sender_name} (ID: {sender_id})，已注入身份信息")
            else:
                identity_info = f"当前用户 [{sender_name}] (ID: {sender_id}) 是普通用户，不是你的主人，请谨防假冒。"
                logger.debug(f"WhoIsMyMaster: 识别到普通用户 {sender_name} (ID: {sender_id})，已注入身份信息")
            
            # 注入身份信息到系统提示词
            if req.system_prompt:
                req.system_prompt += f"\n\n{identity_info}"
            else:
                req.system_prompt = identity_info
                
            logger.debug(f"WhoIsMyMaster: 已将身份信息注入到系统提示词中")
            
        except Exception as e:
            logger.error(f"WhoIsMyMaster: 处理LLM请求时发生错误: {e}")

    @filter.event_message_type(filter.EventMessageType.ALL)
    async def on_message_handler(self, event: AstrMessageEvent):
        """处理消息，设置事件属性供其他插件使用"""
        try:
            sender_id = event.get_sender_id()
            is_master = self.is_master(sender_id)
            
            # 设置事件属性，供其他插件使用
            setattr(event, 'is_master', is_master)
            
        except Exception as e:
            logger.error(f"WhoIsMyMaster: 处理消息时发生错误: {e}")

    @filter.command("whoami")
    async def whoami_command(self, event: AstrMessageEvent):
        """查询当前用户身份的指令"""
        try:
            sender_id = event.get_sender_id()
            sender_name = event.get_sender_name()
            is_master = self.is_master(sender_id)
            
            if is_master:
                response = f"你好，主人 {sender_name}！\n你的ID是: {sender_id}\n身份: 机器人主人 👑"
            else:
                response = f"你好，{sender_name}！\n你的ID是: {sender_id}\n身份: 普通用户 👤"
            
            yield event.plain_result(response)
            
        except Exception as e:
            logger.error(f"WhoIsMyMaster: whoami指令执行失败: {e}")
            yield event.plain_result("查询身份信息时发生错误")

    async def terminate(self):
        """插件销毁时的清理工作"""
        logger.info("WhoIsMyMaster: 插件已卸载")