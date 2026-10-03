# AI Gateway 公共组件边界与 Home-Lab 拓扑

Home-Lab 使用单入口 `ai-internal.onwalk.net`，New API 是用户、套餐、额度、模型权限和消费记录的唯一账本。现有 Cloudflare `edge-gateway` 继续提供 Web SaaS `/api/*`。

```text
客户端 / IDE / SDK
  → Caddy：TLS
  → 可选 APISIX Standalone 或 Kong Traditional/PostgreSQL
  → New API：用户认证、模型权限、套餐与消费账本
      ├→ CPA：节点本地 OAuth 订阅账号矩阵
      └→ LiteLLM：官方 API 适配、重试与上游成本统计
```

默认单入口契约为 `contracts/ai-internal-new-api.yaml`。所有客户端模型请求经过 New API；LiteLLM 配置为 New API 渠道，使用内部凭据。控制台与管理 API 继续使用 New API 自身登录、RBAC 和独立网络访问策略。公共 renderer 的模型 API 配置不能代替管理入口保护。

`contracts/gateway.yaml` 保留通用双主机示例，其中 LiteLLM 直连路由使用独立网关凭据；它不能使用 New API 用户 Token，也不属于上述单账本部署方案。`contracts/ai-internal-apisix.yaml` 保留独立 AI 插件演示，供适配器测试，不作为 Home-Lab 的新默认入口。

## Token 契约

客户端使用 New API 为对应用户签发的 API Token。旧 `bootstrap_client_key` 属于 APISIX Consumer 凭据，不能作为 New API 用户 Token 或渠道 Token。

`auth.mode: new-api-token` 表示 APISIX/Kong 将 `Authorization`、`x-api-key` 或 `apikey` 归一为 `Authorization: Bearer <原用户 Token>`。网关不替换 Token，New API 执行最终认证、授权和用量处理。该模式不生成网关 Key Auth 或 Consumer ACL 来冒充 New API 用户身份；其他使用网关凭据的通用路由仍保留租户 ACL。

网关来源 IP 限流用于防滥用，用户额度与模型权限由 New API 管理。请求元数据不是可信租户身份。CPA 与官方 API 之间不自动 fallback，以免订阅请求转为付费调用。

## 可选入口模式

```text
direct-new-api: Caddy → New API
gateway + apisix: Caddy → APISIX → New API
gateway + kong: Caddy → Kong → New API
```

`gateway.entry_mode` 选择直连或代理。代理模式下 `gateway.adapter` 选择 APISIX/Kong。APISIX 使用 Standalone 文件配置，无 etcd；Kong 使用 Traditional 与 PostgreSQL，由 decK/Admin API 同步配置。

直连切换只改变请求路径，既有网关进程可保留用于回滚。Playbook 的直连分支要求 New API 已健康运行，先 stage 候选 Caddy 片段，activate 时校验、reload，并在失败时恢复旧片段。Kong renderer 可生成候选配置；现有 Playbook 的 Kong 任务仍有旧部署契约，运行切换须先完成迁移和节点验收。

## 配置与凭据归属

GitOps 保存环境、域名、节点、adapter、模型与 Vault 引用。Vault 保存数据库、网关服务端密钥及官方 Provider Key。CPA OAuth 仅留在实例本地加密目录。客户端凭据、OAuth、数据库密码不进入公共 YAML、Git、日志或 CI artifact。

CPA 若采用订阅免计费，New API 对对应模型配置零价格并保留使用记录。官方 API 渠道按用户套餐策略在 New API 记账；LiteLLM 的 Provider 成本统计不替代用户账本。

## 本次验收边界

2026-10-03 的只读检查：Home-Lab Caddy 实际直连 `127.0.0.1:3000`；APISIX active，监听 `127.0.0.1:9080`；Kong inactive、没有 8000 监听。Caddy 直连和 APISIX loopback 的无凭据模型请求均返回 401。

契约、renderer 与语法检查验证的是候选配置。上述 401 只验证拒绝路径；有效普通用户 Token 的模型请求、消费记录、APISIX 新配置切换和 Kong 运行验收仍需分别完成。旧 Vault 凭据保留到迁移与回滚窗口结束再清理。
