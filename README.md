# AI Aggregator Gateway

一个入口，聚合订阅模型、官方 API 与开源模型。面向个人工作站和团队，让 OpenCode、IDE 与自动化 Agent 共用模型与用户权限。

## 架构

```text
客户端 → Caddy TLS → [可选 APISIX / Kong] → New API
                                             ├→ CPA：订阅账号矩阵
                                             └→ LiteLLM：官方 API / NVIDIA / Ollama
```

New API 管理用户、套餐、额度和消费记录；CPA 隔离账号 OAuth；LiteLLM 适配上游、重试与统计成本。
Home-Lab 是参考环境，当前采用 Caddy → New API 直连模式。

## 聚合能力

| 来源 | 接入能力 |
|---|---|
| CPA | GPT / Codex、Claude、Google 订阅账号 |
| LiteLLM | 官方 API、NVIDIA NIM、Ollama Cloud；AMD / 本地 Ollama 可选 |
| 公共网关 | Caddy TLS；APISIX / Kong 可选认证、ACL、限流与审计 |

模型与协议按账号逐项验证；目录可见不等于可推理，开发者额度不等于永久免费。
详细清单见 [接入能力与模型](docs/models/capabilities.zh.md)。

## 快速开始

先查看帮助，确认目标与前置条件：

```bash
curl -fsSL "https://raw.githubusercontent.com/ai-workspace-services/ai-aggregato-Gateway/main/scripts/home-lab/one-shell.sh" \
  | bash -s -- --help
```

脚本不是空机安装器：需已有服务、数据库、SSH/sudo 与 Vault 运行时注入。
无参数默认操作参考 Home-Lab 并执行 `activate`；其他环境先显式指定目标并运行 `plan`。
生产部署应固定已审核的 tag / commit，而不是可变的 `main`。

## 文档导航

| 文档 | 内容 |
|---|---|
| [模块设计](docs/llm-modules-hub.zh.md) | 职责边界、模块生命周期与配置契约 |
| [能力与模型](docs/models/capabilities.zh.md) | 模型清单、验证状态与失败项 |
| [部署指南](docs/deployment/quick-start.zh.md) | 引导脚本、CLI、网络模式与高级参数 |
| [OAuth 登录](docs/home-lab/cpa-oauth-tldr.zh.md) | CPA 账号隔离与人工登录 |
| [Vault 契约](docs/home-lab/vault-contract.md) | 密钥归属与运行时注入 |
| [客户端验收](docs/home-lab/client-acceptance-tldr.zh.md) | 统一入口接入与请求验证 |
| [Ollama 验证](docs/home-lab/ollama-cloud-validation-20261007.md) | 上游与 HTTPS 实测结果 |

客户端使用 New API 用户 Key；Provider Key 与 OAuth 不进入 Git 或客户端配置。
本项目不替代 Cloudflare `edge-gateway` 的 Web SaaS `/api/*` 链路。
