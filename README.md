# AI Aggregator Gateway

本项目是 AI Aggregator 的公共契约、配置 renderer 和 Home-Lab 部署文档/脚本仓库。
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

生产环境应固定已审核的 tag 或 commit，不要直接执行未固定的 `main`：

```bash
curl -fsSL https://raw.githubusercontent.com/ai-workspace-services/ai-aggregato-Gateway/<COMMIT>/scripts/home-lab/one-shell.sh \
  | bash -s -- --ref <COMMIT>
```

该命令只安装工具并执行预检。真正部署必须显式提供 inventory、GitOps manifest
和 `plan`/`stage`/`activate` 阶段；Token 不作为命令参数传递。

当前 Home-Lab 的 `UnifiedAIGateway` 直连过渡需要显式传入
`deploy_ai_gateway_direct_new_api.yml`，并使用 `activate` 表示这是会修改 Caddy
路由的应用操作；脚本不会把这个清单误交给通用 aggregator role。

当前 Home-Lab 运行主路径是 `Caddy → New API → CPA/LiteLLM`；APISIX/Kong 仅作为
显式选择的可选网关模式，不能与直连模式并行占用同一公网入口。
