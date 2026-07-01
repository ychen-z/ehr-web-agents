"""MCP 工具网关（轻量版）：工具注册表 + 白名单校验。

生产环境的 MCP 工具网关通过 JSON-RPC 与独立 MCP Server 通信。
当前轻量版：集中声明所有工具元数据，作为单一 source of truth，
供技能绑定校验 + Agent 调用前白名单检查。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ToolSpec:
    """工具规格声明。"""
    name: str
    description: str
    version: str = "1.0.0"
    category: str = "general"
    input_schema: dict[str, Any] = field(default_factory=dict)
    owner: str = "system"
    enabled: bool = True


class ToolRegistry:
    """工具注册表：所有可用工具的集中管理。

    职责：
    - 注册 / 注销工具
    - 白名单校验（tool_name 是否合法可调用）
    - 列出所有工具（供 UI 展示 + Agent 选择）
    - description 非空强制
    """

    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}

    def register(self, spec: ToolSpec) -> None:
        if not spec.name or not spec.name.strip():
            raise ValueError("工具名称不能为空")
        if not spec.description or not spec.description.strip():
            raise ValueError(f"工具 '{spec.name}' 的 description 不能为空")
        self._tools[spec.name] = spec

    def unregister(self, name: str) -> None:
        self._tools.pop(name, None)

    def get(self, name: str) -> ToolSpec | None:
        return self._tools.get(name)

    def exists(self, name: str) -> bool:
        spec = self._tools.get(name)
        return spec is not None and spec.enabled

    def is_allowed(self, name: str) -> bool:
        """白名单校验：工具是否已注册且启用。"""
        return self.exists(name)

    def list_all(self) -> list[ToolSpec]:
        return list(self._tools.values())

    def list_enabled(self) -> list[ToolSpec]:
        return [t for t in self._tools.values() if t.enabled]

    def validate_skill_binding(self, tool_name: str) -> None:
        """技能绑定工具时校验：工具必须在注册表中且启用。"""
        if not tool_name:
            raise ValueError("技能必须绑定一个工具")
        if not self.exists(tool_name):
            available = [t.name for t in self.list_enabled()]
            raise ValueError(
                f"工具 '{tool_name}' 未在注册表中或已禁用。"
                f"可用工具: {available}"
            )


# ---------- 全局注册表实例 ----------

_registry = ToolRegistry()


def get_registry() -> ToolRegistry:
    return _registry


def _seed_builtin_tools() -> None:
    """注册所有内置工具。启动时调用。"""
    from app.tools.llm_tools import TOOL_SCHEMAS
    from app.tools.script_tools import SCRIPT_TOOLS

    # LLM 工具
    for name, schema in TOOL_SCHEMAS.items():
        _registry.register(ToolSpec(
            name=name,
            description=schema["description"],
            version="1.0.0",
            category="llm",
            input_schema={"output_fields": schema.get("output_fields", {})},
            owner="system",
        ))

    # 脚本工具
    for name in SCRIPT_TOOLS:
        if _registry.get(name):
            # 已通过 TOOL_SCHEMAS 注册（如 generate_html 既有 schema 又有 script）
            continue
        _registry.register(ToolSpec(
            name=name,
            description=f"Script tool: {name}",
            version="1.0.0",
            category="script",
            owner="system",
        ))


# 模块加载时自动注册内置工具
_seed_builtin_tools()
