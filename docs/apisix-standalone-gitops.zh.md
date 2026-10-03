# APISIX Standalone GitOps 选型

Home-Lab 默认候选链路为 Caddy TLS → APISIX Standalone → New API → CPA/LiteLLM。New API 统一用户、套餐、额度、模型权限和消费记录；APISIX 负责协议头归一、路由、来源限流和请求元数据。IP 白名单和管理入口保护须由环境配置单独声明。

## 生成候选配置

```bash
python3 -m gatewayctl validate contracts/ai-internal-new-api.yaml
python3 -m gatewayctl render contracts/ai-internal-new-api.yaml --adapter apisix --output-dir build/apisix
python3 -m gatewayctl render contracts/ai-internal-new-api.yaml --adapter caddy --output-dir build/caddy
```

使用环境 GitOps 域名替换示例域名。模型请求进入 New API；LiteLLM 作为其内部官方 API 渠道。不要以旧 AI 插件演示替换单账本路由。APISIX 使用 YAML 文件后端，无 etcd，监听 loopback 9080，关闭 Admin/Control API；完整路由文件以 `#END` 结尾。

## 用户 Token

`bootstrap_client_key` 是旧 APISIX Consumer Key，不是 New API 用户 API Key。客户端使用 New API 用户 Token；`auth.mode: new-api-token` 将 OpenAI Bearer、Anthropic `x-api-key` 和 `apikey` 归一后原样发送给 New API。

该模式不要求第二个 APISIX client key，也不生成 Key Auth/Consumer ACL 替代 New API 用户身份。通用 Key Auth/JWT 路由仍保留 Consumer ACL。New API 做最终认证、模型授权与记账；本 renderer 不实现远程 Token 预检或独立用户额度账本。

## 直连与 Kong

`gateway.entry_mode: direct-new-api` 将 Caddy 指向 New API；既有 APISIX/Kong 服务可作为回滚备用。

Kong renderer 使用 pre-function 归一相同 Token，并保留 `/v1` 原始路径。Kong Traditional/PostgreSQL 配置通过 decK/Admin API 发布。Kong 的安装、PostgreSQL、插件加载和节点切换需独立验收，不能以 APISIX 测试代替。

## 发布与验收

先生成候选文件，使用目标版本校验，保存上一版配置，再切换。验证无凭据和错误 Token 拒绝、有效用户 Token 可列模型并推理、New API 产生对应用户记录。验证 CPA 与 LiteLLM 故障隔离；失败时恢复原路由配置。切换过程中不得用共享网关密钥替换用户 Token。

Home-Lab 当前直连 New API；APISIX 运行但不承载 Caddy 当前流量。2026-10-03 两个路径的无凭据模型请求均返回 401；这是拒绝路径证据，仍需有效用户 Token 正向验收。Kong 当前未运行。

所有服务端敏感信息通过 Vault 运行时注入；CPA OAuth 留在节点本地加密目录。旧 bootstrap 值的移除不由本轮部署自动执行。
