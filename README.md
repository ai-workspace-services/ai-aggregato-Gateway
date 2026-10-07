# AI Aggregator Gateway / Personal LLM Modules Hub

本项目是个人 LLM Modules Hub：它集中管理可复用的模型模块、provider 适配、协议
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
  → Kong 或 APISIX
      ├── New API → CPA
      └── LiteLLM → 官方 API
```

v1 默认使用 Kong Traditional + PostgreSQL；APISIX 作为可选 Standalone adapter，不宣称与 Kong PostgreSQL 动态配置完全等价。

## Modules Hub 边界

每个模块只声明非敏感的 provider、模型 ID、协议和能力；密钥、OAuth bundle、
数据库凭据和运行状态不进入模块目录。

```text
CPA subscription modules  → New API → 本地 CPA OAuth 实例
Official API modules      → New API → LiteLLM → 官方 provider
NVIDIA/AMD modules        → New API → LiteLLM → OpenAI-compatible endpoint
Ollama modules            → New API → LiteLLM → 本地 loopback endpoint
```

`profiles/ai-gateway-v1/llm-modules.yaml` 是模块目录示例；Home-Lab 当前只将
经过真实推理验证的 NVIDIA 模块注册到 LiteLLM。上游 `/v1/models` 目录只是发现
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

默认使用仓库的稳定通道 `main`；需要升级、回滚或复现时，再用高级参数指定已审核的 tag 或 commit：

```bash
curl -fsSL "https://raw.githubusercontent.com/ai-workspace-services/ai-aggregato-Gateway/main/scripts/home-lab/one-shell.sh" \
  | bash
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
