# 接入能力、模型清单与验证边界

[返回项目首页](../../README.md)

## 接入能力一览

| 能力 / 来源 | 接入路径 | 凭据归属 | 当前状态 |
|---|---|---|---|
| Codex / GPT 订阅 | New API → CPA Codex | 每实例本地 OAuth | 已有最小推理验证 |
| Claude 订阅 | New API → CPA Claude | 每实例本地 OAuth | 已有最小推理验证 |
| Google / Antigravity | New API → CPA Google | 每实例本地 OAuth | 已有最小推理验证；不等同于 Gemini CLI 原生接口 |
| NVIDIA NIM | New API → LiteLLM → NIM | UAT Vault `providers/nvidia` | 80 项目录，5 项已验证 |
| Ollama Cloud | New API → LiteLLM → `https://ollama.com/v1` | UAT Vault `providers/ollama` | 18 项目录，成功项见下表 |
| OpenAI / Anthropic / xAI 官方 API | New API → LiteLLM → Provider | Vault Provider Key | 支持配置；当前凭据与推理需逐项验收 |
| AMD 开发者 API | New API → LiteLLM → AMD | Vault Provider Key | 当前额度 / Key 不可用，未启用 |
| 本地 Ollama | New API → LiteLLM → 本地服务 | 本地服务访问控制 | 可选；未宣称当前已部署 |

表中 Vault Provider 逻辑路径统一为 `kv/<env>/ai-aggregator/litellm/providers/<provider>`。
开发者额度受账号与平台策略约束，不承诺永久免费。客户端只持有 **New API 用户 API Key**，
不要把 Provider Key、LiteLLM master key 或网关 bootstrap key 配置到 OpenCode。

## 模型清单与验证边界

以下是 2026-10-07 的验证记录；历史最小请求成功不保证后续账号额度和上游持续可用。
标准模型名原样对外提供，不添加 `subscription/` 或 `official/` 前缀。

| 来源 | 已通过最小聊天请求的模型 ID |
|---|---|
| CPA · GPT / Codex | `gpt-5.5`、`gpt-5.6-luna`、`gpt-5.6-sol`、`gpt-5.6-terra`、`gpt-6-astra`、`gpt-6-luna`、`gpt-6-sol`、`gpt-6.1-sol`、`gpt-oss-120b-medium`、`codex-auto-review` |
| CPA · Claude | `claude-opus-4-5-20251101`、`claude-opus-4-6`、`claude-opus-4-7`、`claude-opus-4-8`、`claude-opus-5`、`claude-sonnet-4-5-20250929`、`claude-sonnet-5`、`claude-sonnet-5-5` |
| CPA · Google | `gemini-3-flash`、`gemini-3.1-flash-lite`、`gemini-3.1-pro-low`、`gemini-3.5-flash-lite`、`gemini-3.6-flash-high`、`gemini-3.7-flash-high`、`gemini-3.8-flash-high`、`gemini-pro-agent` |
| NVIDIA NIM | `openai/gpt-oss-20b`、`nvidia/nemotron-3.5-lightning-30b-a3b`、`deepseek-ai/deepseek-v4.1-flash`、`z-ai/glm-5.3`、`z-ai/glm-5.3-flash` |
| Ollama Cloud | `gpt-oss:120b`、`gpt-oss:20b`、`gemma4:31b`、`nemotron-3-super`、`nemotron-3-ultra`；5 项均通过统一 HTTPS 入口，见 [Ollama 验证记录](../home-lab/ollama-cloud-validation-20261007.md) |

已记录最小推理成功的模型共 **36 项（CPA 26 + NVIDIA 5 + Ollama 5）**。
当前运行目录返回 **52 项**，其中旧渠道仍包含未通过本轮验证的目录项；README 不将它们列为已验证能力。

Ollama 本轮其余结果：

| 状态 | 模型 ID | 处理 |
|---|---|---|
| HTTP 402 | `deepseek-v4.1-flash`、`deepseek-v4-pro:0813`、`minimax-m2.7`、`minimax-m3`、`mistral-large-3:675b`、`glm-5.2`、`glm-5.3`、`kimi-k2.6`、`kimi-k2.7-code`、`kimi-k3` | 不注册；核对账号权限与额度后重测 |
| 请求超时 | `glm-5.3-flash`、`nemotron-3-nano:30b`、`mistral-large-4` | 不注册；重测后再决定 |

`/v1/models` 是目录，不是推理验收结果。Chat、Responses、Claude Messages、SSE、工具调用和
图像接口应按模型与客户端分别验证；不要把一次 `hello` 成功当成所有协议已兼容。
完整模块声明见 [llm-modules.yaml](../../profiles/ai-gateway-v1/llm-modules.yaml)，环境启用清单由 GitOps 管理。

## Modules Hub 边界

每个模块只声明非敏感的 provider、模型 ID、协议和能力；密钥、OAuth bundle、
数据库凭据和运行状态不进入模块目录。

```text
CPA subscription modules  → New API → 本地 CPA OAuth 实例
Official API modules      → New API → LiteLLM → 官方 provider
NVIDIA/AMD modules        → New API → LiteLLM → OpenAI-compatible endpoint
Ollama Cloud modules      → New API → LiteLLM → Ollama Cloud
Local Ollama modules      → New API → LiteLLM → 本地 loopback endpoint
```

`profiles/ai-gateway-v1/llm-modules.yaml` 是模块目录示例；Home-Lab 当前只将
经过真实推理验证的 NVIDIA、Ollama Cloud 模块注册到 LiteLLM。上游 `/v1/models` 目录只是发现
结果，不会自动变成公开模型或绕过 New API 的额度、权限和消费记录。
