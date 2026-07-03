# ZIP Skill + CodeSandbox 沙箱执行设计

## 1. 概述

支持用户上传含脚本的 Skill 包（ZIP），Agent 调用时在 CodeSandbox 云端沙箱中安全执行脚本，收集输出返回给用户。

### 目标

- 用户可上传 ZIP 格式 Skill 包（含 manifest + 脚本）
- Agent 运行时检测到 sandbox 类型工具，自动创建远程沙箱执行
- 支持 Python 和 Node.js 运行时
- 执行结果以结构化数据返回，接入现有 Agent Loop

### 不包含

- 本地容器化执行（本期不做 Docker 方案）
- 前端 Sandpack 浏览器执行
- 持久化沙箱（每次创建新沙箱）
- 沙箱间状态共享

---

## 2. 核心概念

### 2.1 Skill Package（技能包）

一个 ZIP 文件，根目录必须包含 `manifest.json`，其余为脚本文件和依赖声明。

### 2.2 manifest.json

```json
{
  "name": "data_analysis_tool",
  "version": "1.0.0",
  "runtime": "python3",
  "entry": "main.py",
  "dependencies": ["pandas==2.0.0", "matplotlib"],
  "timeout": 60,
  "input_schema": {
    "type": "object",
    "properties": {
      "data": { "type": "string", "description": "输入数据文本" }
    },
    "required": ["data"]
  },
  "output_type": "json"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | Y | 工具名，须唯一 |
| version | string | Y | 语义化版本 |
| runtime | enum | Y | `"python3"` \| `"node18"` |
| entry | string | Y | 入口脚本相对路径 |
| dependencies | string[] | N | 依赖列表（pip/npm 格式） |
| timeout | int | N | 执行超时秒数，默认 60，上限 120 |
| input_schema | object | N | JSON Schema 描述工具输入 |
| output_type | enum | N | `"json"` \| `"text"` \| `"file"`，默认 `"json"` |

### 2.3 入口脚本约定

入口脚本通过 **stdin** 接收 JSON 格式输入，通过 **stdout** 输出结果：

```python
# main.py 示例
import json
import sys

input_data = json.loads(sys.stdin.read())
# ... 业务逻辑 ...
result = {"summary": "分析完成", "chart_url": "..."}
print(json.dumps(result))
```

---

## 3. 系统架构

```
┌─────────────────────────────────────────────────┐
│                    前端                          │
│  SkillUpload 组件 (ZIP文件拖拽/选择上传)         │
└───────────────────────┬─────────────────────────┘
                        │ POST /api/skills/upload-package
                        ▼
┌─────────────────────────────────────────────────┐
│              后端 API Layer                       │
│  app/sandbox/router.py                           │
│  - 校验 ZIP 大小 / 结构                          │
│  - 解析 manifest.json                            │
│  - 注册为 sandbox_tool 类型                       │
│  - 存储到 skill_packages/{skill_id}/             │
└───────────────────────┬─────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────┐
│           Agent Loop (graph.py)                   │
│  _execute_tool 判断:                             │
│    is_script_tool? → 本地执行                     │
│    is_sandbox_tool? → sandbox executor            │
│    else → llm_tool                               │
└───────────────────────┬─────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────┐
│        Sandbox Executor                          │
│  app/sandbox/executor.py                         │
│  1. 读取 skill 文件                              │
│  2. 调 CodeSandbox API 创建沙箱                   │
│  3. 上传文件到沙箱                               │
│  4. 安装依赖 + 执行入口脚本                       │
│  5. 收集 stdout / 错误                           │
│  6. 销毁沙箱                                    │
│  7. 返回结构化结果                               │
└─────────────────────────────────────────────────┘
```

---

## 4. 模块设计

### 4.1 `app/sandbox/storage.py` — 包存储

```python
@dataclass
class PackageInfo:
    skill_id: str
    manifest: dict
    package_dir: Path          # skill_packages/{skill_id}/
    files: list[str]           # 文件列表

def validate_and_extract(zip_file: UploadFile, skill_id: str) -> PackageInfo:
    """校验 ZIP + 解压到 skill_packages/{skill_id}/"""

def get_package_info(skill_id: str) -> PackageInfo | None:
    """读取已存储的包信息"""

def delete_package(skill_id: str) -> None:
    """删除包目录"""
```

**校验规则：**
- ZIP 大小 <= 10 MB
- 解压后总大小 <= 50 MB
- 必须含 `manifest.json`
- manifest 必须含 name/version/runtime/entry
- entry 文件必须存在于 ZIP 中
- runtime 必须为 `python3` 或 `node18`
- 无路径穿越（../ 检查）
- 文件数量 <= 200

### 4.2 `app/sandbox/executor.py` — 沙箱执行器

```python
@dataclass
class SandboxResult:
    stdout: str
    stderr: str
    exit_code: int
    output: dict | str | None   # 解析后的结构化输出
    duration_ms: int
    sandbox_id: str

async def execute_in_sandbox(
    package: PackageInfo,
    input_data: str,
    timeout: int = 60,
) -> SandboxResult:
    """在 CodeSandbox 中执行 skill 脚本"""
```

**执行步骤（CodeSandbox SDK）：**

1. `POST https://api.codesandbox.io/sandbox` — 创建沙箱
   - template: `python3` 或 `node18`
   - files: 从 package_dir 读取所有文件
2. 执行安装命令：
   - Python: `pip install {dependencies}`
   - Node: `npm install {dependencies}`
3. 执行入口脚本：
   - Python: `echo '{input_json}' | python {entry}`
   - Node: `echo '{input_json}' | node {entry}`
4. 读取 stdout，按 output_type 解析
5. `DELETE /sandbox/{id}` — 销毁

**错误处理：**
- 超时 → 强制终止，返回 timeout 错误
- 非零退出码 → 返回 stderr 内容
- stdout 非法 JSON（当 output_type=json）→ 返回 raw text + 警告

### 4.3 `app/sandbox/router.py` — 上传 API

```
POST /api/skills/upload-package
  - Content-Type: multipart/form-data
  - Fields: file (ZIP), skill_id (str)
  - Auth: 需要登录
  - 返回: { skill_id, manifest, files[] }

GET /api/skills/{skill_id}/package
  - 返回包元信息

DELETE /api/skills/{skill_id}/package
  - 删除包
```

### 4.4 Tool Registry 集成

在 `app/gateway/` 中新增 sandbox tool 类型：

```python
@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    version: str = "0.1.0"
    category: str = "builtin"
    enabled: bool = True
    tool_type: str = "llm"     # 新增: "llm" | "script" | "sandbox"
```

Agent Loop `_execute_tool` 分支：

```python
if is_script_tool(tool_name):
    result = invoke_script_tool(...)
elif is_sandbox_tool(tool_name):
    result = await execute_sandbox_tool(...)
else:
    result = invoke_llm_tool(...)
```

### 4.5 Skill 模型扩展

```python
class Skill(Base):
    # ... 现有字段 ...
    tool_type: Mapped[str] = mapped_column(String(20), default="llm")
    # "llm" | "script" | "sandbox"
    has_package: Mapped[bool] = mapped_column(default=False)
```

---

## 5. CodeSandbox API 集成

### 5.1 认证

- 使用 CodeSandbox API Token（存于 `.env`）
- 配置项：`CODESANDBOX_API_KEY`

### 5.2 API 调用流程

```
1. Create Sandbox
   POST https://api.codesandbox.io/v1/sandboxes
   Body: { template, files: {...} }
   → sandbox_id

2. Execute Command
   POST https://api.codesandbox.io/v1/sandboxes/{id}/exec
   Body: { command: "pip install ... && echo '{input}' | python main.py" }
   → { stdout, stderr, exit_code }

3. Delete Sandbox
   DELETE https://api.codesandbox.io/v1/sandboxes/{id}
```

### 5.3 配置

```python
# shared/config.py 新增
codesandbox_api_key: str = ""
sandbox_timeout_default: int = 60
sandbox_timeout_max: int = 120
sandbox_max_package_size_mb: int = 10
```

---

## 6. 数据流

### 6.1 上传流程

```
User → POST /api/skills/upload-package (ZIP + skill_id)
     → validate ZIP size/structure
     → extract manifest.json, validate fields
     → save to skill_packages/{skill_id}/
     → update Skill record: tool_type="sandbox", has_package=True
     → register in ToolRegistry with category="sandbox"
     → return PackageInfo
```

### 6.2 执行流程

```
Agent Loop → _plan_next_step: LLM decides call_tool "data_analysis_tool"
           → _execute_tool: detect tool_type == "sandbox"
           → load PackageInfo for skill
           → execute_in_sandbox(package, user_input, timeout)
             → create CodeSandbox → upload files → install deps → run entry
             → collect stdout → parse output → destroy sandbox
           → return structured result to Agent Loop
           → Agent Loop decides: respond with result or call another tool
```

---

## 7. 安全设计

| 威胁 | 缓解 |
|------|------|
| 恶意脚本（网络攻击/挖矿） | CodeSandbox 自带网络隔离 + 超时强制终止 |
| ZIP 炸弹 | 10MB 压缩上限 + 50MB 解压上限 + 200 文件上限 |
| 路径穿越 | 解压前检查所有路径无 `../` |
| API Key 泄漏 | 仅服务端持有，不传入沙箱 |
| 无限循环 | timeout 强制终止（默认 60s，上限 120s） |
| 大输出攻击 | stdout 截断 1MB |
| 并发滥用 | 单用户同时最多 2 个沙箱 |

---

## 8. 文件结构

```
apps/api/
├── app/
│   ├── sandbox/
│   │   ├── __init__.py
│   │   ├── storage.py       # ZIP 校验 + 解压 + 存储
│   │   ├── executor.py      # CodeSandbox API 封装
│   │   ├── router.py        # HTTP 接口
│   │   └── schemas.py       # Pydantic 模型
│   ├── tools/
│   │   └── sandbox_tools.py # is_sandbox_tool / invoke_sandbox_tool 桥接
│   ├── gateway/
│   │   └── __init__.py      # ToolSpec 新增 tool_type 字段
│   └── agents/
│       └── graph.py         # _execute_tool 新增 sandbox 分支
├── skill_packages/           # 解压后的 skill 包存储目录
│   └── {skill_id}/
│       ├── manifest.json
│       └── main.py
└── tests/
    ├── test_sandbox_storage.py
    └── test_sandbox_executor.py
```

---

## 9. 测试策略

- **storage 单测**：ZIP 校验（大小/结构/路径穿越/manifest 缺失）
- **executor 单测**：mock CodeSandbox API，验证创建→执行→销毁流程
- **集成测试**：上传 ZIP → 创建 run → 验证沙箱执行输出正确返回
- **FakeSandboxExecutor**：测试环境替换 executor，返回预设输出

---

## 10. 实施计划（建议顺序）

1. 添加 `app/sandbox/storage.py` — ZIP 校验 + 解压
2. 添加 `app/sandbox/schemas.py` — Pydantic 模型
3. 添加 `app/sandbox/router.py` — 上传/查询/删除 API
4. 添加 `app/sandbox/executor.py` — CodeSandbox SDK 封装
5. 扩展 `ToolSpec` + `Skill` 模型（`tool_type` 字段）
6. 修改 `graph.py` `_execute_tool` 增加 sandbox 分支
7. 前端：Skill 创建时支持 ZIP 上传
8. 测试 + 文档更新

---

## 11. 配置项汇总

| 配置键 | 默认值 | 说明 |
|--------|--------|------|
| `codesandbox_api_key` | `""` | CodeSandbox API Token |
| `sandbox_timeout_default` | `60` | 默认执行超时（秒） |
| `sandbox_timeout_max` | `120` | 最大执行超时（秒） |
| `sandbox_max_package_size_mb` | `10` | ZIP 包大小上限 |
| `sandbox_max_concurrent` | `2` | 单用户并发沙箱数 |

---

## 12. 已知限制

- CodeSandbox API 免费层有并发和调用频率限制
- 冷启动延迟（创建沙箱 + 安装依赖）约 10-30 秒
- 暂不支持 GPU 运行时
- 输出文件暂不支持（仅 stdout），后续可扩展为文件下载
