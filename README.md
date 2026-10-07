# AI Aggregator Gateway / Personal LLM Modules Hub

本项目面向个人工作站与团队，是统一的 LLM Modules Hub：集中管理可复用的模型模块、provider 适配、协议
契约、配置 renderer 和 Home-Lab 部署文档/脚本。
它定义与厂商无关的 AI Gateway 契约，并生成 Caddy、Kong 和 APISIX 的配置片段。

它不替代现有的 Cloudflare `edge-gateway`。现有 Worker 继续承载 Web SaaS 的 `/api/*`；本项目只描述 AI Gateway 的 `/v1/*` 链路。

## 快速使用

安装依赖后，可以直接使用模块入口：

```bash
python3 -m pip install -e .
gatewayctl validate contracts/gateway.yaml
gatewayctl render contracts/gateway.yaml --adapter caddy --output-dir build/caddy
gatewayctl render contracts/gateway.yaml --adapter kong --output-dir build/kong
gatewayctl render contracts/gateway.yaml --adapter apisix --output-dir build/apisix
```

也可以不安装 console script：

```bash
PYTHONPATH=. python3 -m gatewayctl validate contracts/gateway.yaml
```

生成物只包含非敏感配置。Provider API Key、OAuth bundle、JWT 私钥、数据库密码和客户端凭据必须由 Vault、CPA 节点本地目录或运行时凭据系统提供。

## 运行链路

```text
AI Client /v1/*
  → Caddy HTTPS
  → [可选 APISIX / Kong]
  → New API：用户、套餐、额度、模型权限、消费记录
      ├── CPA：订阅账号 OAuth 矩阵
      └── LiteLLM：官方 API / NVIDIA NIM / Ollama Cloud / 本地 Ollama
```

Home-Lab 当前使用 `Caddy → New API → CPA/LiteLLM` 直连模式，APISIX/Kong 停用。
需要入口 ACL、防滥用限流与审计时，才显式选择 APISIX Standalone（文件配置、免 etcd）
或 Kong Traditional（PostgreSQL）。两者不同时承载同一入口，也不替代 New API 用户账本。

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
| Ollama Cloud | `gpt-oss:120b`、`gpt-oss:20b`、`gemma4:31b`、`nemotron-3-super`、`nemotron-3-ultra`；5 项均通过统一 HTTPS 入口，见 [Ollama 验证记录](docs/home-lab/ollama-cloud-validation-20261007.md) |

已记录最小推理成功的模型共 **36 项（CPA 26 + NVIDIA 5 + Ollama 5）**。
当前运行目录返回 **52 项**，其中旧渠道仍包含未通过本轮验证的目录项；README 不将它们列为已验证能力。

Ollama 本轮其余结果：

| 状态 | 模型 ID | 处理 |
|---|---|---|
| HTTP 402 | `deepseek-v4.1-flash`、`deepseek-v4-pro:0813`、`minimax-m2.7`、`minimax-m3`、`mistral-large-3:675b`、`glm-5.2`、`glm-5.3`、`kimi-k2.6`、`kimi-k2.7-code`、`kimi-k3` | 不注册；核对账号权限与额度后重测 |
| 请求超时 | `glm-5.3-flash`、`nemotron-3-nano:30b`、`mistral-large-4` | 不注册；重测后再决定 |

`/v1/models` 是目录，不是推理验收结果。Chat、Responses、Claude Messages、SSE、工具调用和
图像接口应按模型与客户端分别验证；不要把一次 `hello` 成功当成所有协议已兼容。
完整模块声明见 [llm-modules.yaml](profiles/ai-gateway-v1/llm-modules.yaml)，环境启用清单由 GitOps 管理。

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

## Home-Lab 部署

Home-Lab 的部署入口、XConnect 远程连接、CPA OAuth、Vault 契约和客户端验收文档位于
`docs/home-lab/`。可执行脚本位于 `scripts/home-lab/`：

```bash
./scripts/home-lab/install.sh
AI_AGGREGATOR_INVENTORY=/path/to/inventory.ini \
AI_AGGREGATOR_MANIFEST=/path/to/ai-aggregator.yaml \
AI_AGGREGATOR_OPERATION=plan \
  ./scripts/home-lab/deploy.sh
```

`deploy.sh` 默认使用仓库内的 Ansible 入口，也可通过
`AI_AGGREGATOR_PLAYBOOK_ROOT` 指向现有 `ai-workspace-infra/playbooks`。凭据仍由
Vault 和客户端本地安全存储提供，脚本不会接收或打印密钥。

### 一行引导安装

脚本默认引用 `main`（可变分支，不是不可变发行版本）；需要升级、回滚或复现时，指定已审核的 tag 或 commit。
先确认目标地址和前置条件：无参数会使用 Home-Lab 示例地址，并默认执行 `activate`。
首次使用建议先查看帮助：

```bash
curl -fsSL "https://raw.githubusercontent.com/ai-workspace-services/ai-aggregato-Gateway/main/scripts/home-lab/one-shell.sh" \
  | bash -s -- --help
```

无参数时使用稳定通道和内置目标配置；Home-Lab 的 `ai-internal.onwalk.net`、`10.79.0.7`、`xconnect` 只是参考默认值。任意环境可通过 `AI_AGGREGATOR_DOMAIN`、`AI_AGGREGATOR_TARGET_IP`、`AI_AGGREGATOR_NETWORK_MODE` 和 `AI_AGGREGATOR_DNS_IP` 覆盖。它不会输出凭据。使用 `--operation plan` 可先生成并检查目标文件。

指定具体 tag 或 commit：

```bash
curl -fsSL "https://raw.githubusercontent.com/ai-workspace-services/ai-aggregato-Gateway/<TAG_OR_COMMIT>/scripts/home-lab/one-shell.sh" \
  | bash -s -- --ref <TAG_OR_COMMIT>
```

当前 Home-Lab 的 `UnifiedAIGateway` 直连过渡需要显式传入
`deploy_ai_gateway_direct_new_api.yml`，并使用 `activate` 表示这是会修改 Caddy
路由的应用操作；脚本不会把这个清单误交给通用 aggregator role。

当前 Home-Lab 运行主路径是 `Caddy → New API → CPA/LiteLLM`；APISIX/Kong 仅作为
显式选择的可选网关模式，不能与直连模式并行占用同一公网入口。

### 单节点网络模式

one-shell 可以为已有 Linux 主机生成非敏感的 inventory 和单节点 manifest；它不创建云资源、不修改 DNS，也不写入凭据：

| 模式 | SSH/服务地址 | DNS 地址 | Caddy 绑定 |
|---|---|---|---|
| `public` | 公网 IP | 公网 IP | 公网接口 |
| `private-nat` | 私网 IP | 公网 IP | 私网 IP |
| `xconnect` | XConnect-One IP | split-horizon 的 XConnect IP | XConnect IP |

示例：

```bash
curl -fsSL "https://raw.githubusercontent.com/ai-workspace-services/ai-aggregato-Gateway/main/scripts/home-lab/one-shell.sh" \
  | bash -s -- \
    --domain ai.example.com \
    --target-ip 198.51.100.20 \
    --network-mode public
```

`private-nat` 必须额外提供 `--dns-ip`；`xconnect` 默认使用 runtime TLS 文件，因为公网 ACME 不能假定能够访问 VPN 地址。生成的清单只描述地址和 TLS 模式，真实部署仍需主机已安装服务、Vault 访问和人工 OAuth。

确认目标文件、DNS、Vault 和主机前置条件后，才加上 `--operation activate` 执行当前 bundled direct-New-API playbook：

```bash
curl -fsSL "https://raw.githubusercontent.com/ai-workspace-services/ai-aggregato-Gateway/${REF}/scripts/home-lab/one-shell.sh" \
  | bash -s -- --ref "$REF" --operation activate \
    --domain ai.example.com \
    --target-ip 198.51.100.20 \
    --network-mode public
```

这不是云资源 provisioning：目标机必须已经具备 SSH/sudo、Caddy、New API、LiteLLM、CPA、Vault 运行时注入和数据库等前置条件。
