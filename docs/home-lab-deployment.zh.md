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
