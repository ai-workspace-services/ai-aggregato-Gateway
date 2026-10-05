# AI Aggregator Home-Lab 部署包

本目录把 Home-Lab 的运行入口、验证脚本和操作文档集中到 AI Aggregator 公共仓库。它保留现有仓库边界：GitOps 管理环境声明，Ansible 管理节点服务，Vault 管理运行时秘密，CPA OAuth 只保存在 CPA 节点本地认证目录。

## 当前拓扑

```text
OpenCode / SDK / IDE
        ↓ XConnect 网络互联
    Caddy :443
        ↓ TLS
    New API :3000
        ├── CPA 订阅账号矩阵
        └── LiteLLM 官方 API
```

Home-Lab 的内网地址由 XConnect 提供，当前主机为 `10.79.0.7`，入口域名为
`ai-internal.onwalk.net`。APISIX 和 Kong 是可选网关模式，不应与直连模式同时占用公网流量；切换前必须先完成 `plan → stage → 验证 → activate`。

## 快速开始

安装只创建本地 Python 虚拟环境和 CLI，不读取或写入任何 Token：

```bash
./scripts/home-lab/install.sh
```

也可以使用固定版本的一行引导脚本：

```bash
curl -fsSL https://raw.githubusercontent.com/ai-workspace-services/ai-aggregato-Gateway/<COMMIT>/scripts/home-lab/one-shell.sh \
  | bash -s -- --ref <COMMIT>
```

它默认只安装并预检，不会自动连接主机或修改服务。需要进入 Ansible 部署时，必须显式提供 inventory、manifest 和阶段：

```bash
curl -fsSL https://raw.githubusercontent.com/ai-workspace-services/ai-aggregato-Gateway/<COMMIT>/scripts/home-lab/one-shell.sh \
  | bash -s -- --ref <COMMIT> \
    --operation plan \
    --inventory /path/to/inventory.ini \
    --manifest /path/to/ai-aggregator.yaml
```

先执行 `plan`，再人工确认 `stage`；只有 OAuth、模型推理、额度记录和回滚验证完成后，才允许显式执行 `activate`。`<COMMIT>` 必须替换为审核过的完整提交号或发布 tag。

当前 Home-Lab 直连 New API 的 `UnifiedAIGateway` 过渡不是通用 role 的输入，必须明确指定现有 playbook；该操作会备份并 reload Caddy，执行前确认 inventory 和 manifest：

```bash
curl -fsSL "https://raw.githubusercontent.com/ai-workspace-services/ai-aggregato-Gateway/${COMMIT}/scripts/home-lab/one-shell.sh" \
  | bash -s -- --ref "${COMMIT}" --operation activate \
    --inventory /path/to/inventory.ini \
    --manifest /path/to/ai-gateway-unified.yaml \
    --playbook /path/to/ai-workspace-infra/playbooks/deploy_ai_gateway_direct_new_api.yml
```

`UnifiedAIGateway` 的这个 playbook 是应用变更，不提供假 dry-run；它会先检查 New API、保存 Caddy 片段、校验候选配置，并在验证失败时恢复原配置。APISIX/Kong 统一网关模式应使用各自的显式 playbook，不能通过此入口切换。

### 任意已有 VPS/云主机的单节点目标

one-shell 支持三种网络拓扑。它先生成 inventory/manifest，只有显式 `activate` 才调用 Ansible；不负责申请云主机、修改 DNS 或生成凭据。

```text
public      ：SSH/服务公网 IP → DNS 公网 IP → Caddy 公网接口
private-nat ：SSH/服务私网 IP → DNS 公网 IP → NAT/端口转发 → Caddy 私网接口
xconnect    ：SSH/服务 XConnect IP → split-horizon DNS XConnect IP → Caddy XConnect 接口
```

公网节点：

```bash
curl -fsSL "https://raw.githubusercontent.com/ai-workspace-services/ai-aggregato-Gateway/${COMMIT}/scripts/home-lab/one-shell.sh" \
  | bash -s -- --ref "${COMMIT}" \
    --domain ai.example.com \
    --target-ip 198.51.100.20 \
    --network-mode public
```

私网节点通过公网 NAT：

```bash
curl -fsSL "https://raw.githubusercontent.com/ai-workspace-services/ai-aggregato-Gateway/${COMMIT}/scripts/home-lab/one-shell.sh" \
  | bash -s -- --ref "${COMMIT}" \
    --domain ai.example.com \
    --target-ip 10.0.0.10 \
    --dns-ip 198.51.100.20 \
    --network-mode private-nat
```

XConnect-One 节点：

```bash
curl -fsSL "https://raw.githubusercontent.com/ai-workspace-services/ai-aggregato-Gateway/${COMMIT}/scripts/home-lab/one-shell.sh" \
  | bash -s -- --ref "${COMMIT}" \
    --domain ai-internal.example.com \
    --target-ip 10.79.0.7 \
    --network-mode xconnect
```

三种模式都会在本地安装目录下生成 `targets/<domain>/inventory.ini` 和 `ai-gateway-unified.yaml`。公网模式默认使用 Caddy 自动 TLS；XConnect 模式默认使用已有 runtime TLS 文件。私网 NAT 仍要求公网 DNS、443 端口转发和 ACME 验证条件成立。

确认目标文件、DNS、Vault 和主机前置条件后，才加上 `--operation activate` 执行当前 bundled direct-New-API playbook：

```bash
curl -fsSL "https://raw.githubusercontent.com/ai-workspace-services/ai-aggregato-Gateway/${COMMIT}/scripts/home-lab/one-shell.sh" \
  | bash -s -- --ref "${COMMIT}" --operation activate \
    --domain ai.example.com \
    --target-ip 198.51.100.20 \
    --network-mode public
```

这不是云资源 provisioning：目标机必须已经具备 SSH/sudo、Caddy、New API、LiteLLM、CPA、Vault 运行时注入和数据库等前置条件。

部署需要显式提供 inventory、GitOps manifest 和操作阶段：

```bash
export AI_AGGREGATOR_INVENTORY=/path/to/inventory.ini
export AI_AGGREGATOR_MANIFEST=/path/to/ai-aggregator.yaml
export AI_AGGREGATOR_OPERATION=plan
./scripts/home-lab/deploy.sh
```

依次执行 `plan`、`stage` 和 `activate`。生产环境禁止用 `activate` 代替人工 OAuth、模型请求和回滚验证。

## XConnect 远程连接

XConnect-One 负责 VPN 互联，XConnect APP 负责桌面代理和后台运行，两者不是同一个职责。远程操作前先确认隧道和路由：

```bash
ifconfig utun5
route -n get 10.79.0.7
nc -vz 10.79.0.7 22
ssh -t root@10.79.0.7
```

如果 `utun5` 不存在或没有到 `10.79.0.7` 的路由，应先恢复 XConnect-One 会话，不要直接重启 AI Gateway。进入 Home-Lab 后，再按 CPA OAuth 文档使用远程桌面完成浏览器授权。

## 凭据边界

- New API 用户 API Key：由 New API 管理页面创建、撤销和轮换，客户端通过 OpenCode 的认证存储使用。
- CPA OAuth bundle：只保存于 `/var/lib/ai-aggregator/cpa/<id>/auth/`，每个实例独立 Unix 用户和目录。
- 数据库 DSN、服务密钥和官方 Provider API Key：由 Vault 在运行时注入。
- Git、配置仓库、Terraform state、CI artifact 和日志：禁止出现密钥、OAuth 文件和完整请求头。

APISIX 的旧 `bootstrap_client_key` 不等于 New API 用户 Token，不能填入 OpenCode、Claude SDK 或其他客户端。

## 验证

无 Token 请求应被拒绝；受保护变量只在本地 shell 注入：

```bash
export AI_GATEWAY_CLIENT_TOKEN='从安全凭据存储读取'
export AI_GATEWAY_BASE_URL=https://ai-internal.onwalk.net
./scripts/home-lab/verify.sh
```

需要真实推理时，再设置 `AI_GATEWAY_SMOKE_MODEL`。验证顺序为：XConnect 连通、服务状态、`/v1/models`、最小推理、streaming/tool calling，最后才激活渠道。
