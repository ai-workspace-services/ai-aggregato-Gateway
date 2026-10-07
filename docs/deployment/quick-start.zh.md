# 部署与高级参数

[返回项目首页](../../README.md)

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

无参数时使用可变的 main 分支和内置目标配置；Home-Lab 的 `ai-internal.onwalk.net`、`10.79.0.7`、`xconnect` 只是参考默认值。任意环境可通过 `AI_AGGREGATOR_DOMAIN`、`AI_AGGREGATOR_TARGET_IP`、`AI_AGGREGATOR_NETWORK_MODE` 和 `AI_AGGREGATOR_DNS_IP` 覆盖。它不会输出凭据。使用 `--operation plan` 可先生成并检查目标文件。

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
