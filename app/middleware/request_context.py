"""
请求上下文占位模块。

TODO:
1. 后续可在这里集中管理 request_id、user_id、trace 信息。
2. 后续可考虑结合 contextvars，避免在多层调用中手动透传 request.state。
"""

