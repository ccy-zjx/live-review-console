"""
自动化插件接口

未来扩展方向:
1. 抖音开放平台 API → 直播间实时弹幕拉取 → 自动录入问题库
2. 直播间截屏 + OCR → 识别在线人数/订单数 → 自动写入场次数据
3. 主播语音转文字 (ASR) → 自动提取话术 → 录入话术库
4. WebSocket 推送 → 转化峰值自动触发场景记录

插件示例:
    class AutoCollector:
        def on_chat_message(self, user, message):
            # 自动识别问题并入库
            pass

        def on_order_spike(self, orders_before, orders_after):
            # 自动记录高转化场景
            pass

        def on_stream_end(self):
            # 汇总本场数据
            pass
"""
