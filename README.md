# Dida 酒店审核

`dida-hotel-audit` 是一个可复用的 Agent Skill，用于获取当前 Dida Content API 的酒店静态记录，并由当前模型分析与用户请求相关的字段。它包含用于比较酒店身份和核验坐标距离的确定性辅助功能，以及处理其他静态内容问题的通用工作流。

本 Skill 不会为每个新问题创建新的 Skill。它会获取用户指定的酒店记录，并把返回的静态数据交给当前模型分析。

## 安装后包含和不包含的内容

安装这个 GitHub 仓库只会安装 Skill 指令和客户端代码。仓库中**不包含** Dida ClientID、Dida LicenseKey、Audit 访问密钥或本地加密凭据文件；仅完成安装并不会获得 Dida 访问权限。

团队使用时，各组件按以下方式分离：

```text
同事的 Agent -> 已安装的 Skill -> HTTPS Audit 网关 -> Dida Content API
                                   ^
                                   个人 Audit key
```

- Dida ClientID 和 LicenseKey 仅保存在受信任的网关机器上。
- 每位同事获得一个可单独撤销的 Audit key，而不是 Dida 凭据。
- 仓库和 Agent 提示词中均不包含这些敏感信息。
- 当前内置服务器默认只监听 `127.0.0.1`。其他机器上的同事必须先获得可信的 HTTPS 隧道地址或已部署的网关 URL，才能使用本 Skill。

## 从 GitHub 安装

仓库根目录中必须保留 `SKILL.md`。

### Codex

向 Codex 输入：

```text
使用 $skill-installer 安装以下仓库根目录中的 Skill：
https://github.com/huangxiaozhen/dida-hotel-audit
安装名称设为 dida-hotel-audit。
```

如果新 Skill 没有立即显示，请重启 Codex。

### OpenClaw

全局安装：

```powershell
openclaw skills install git:huangxiaozhen/dida-hotel-audit@main --global
```

如果只想安装到当前工作区，请省略 `--global`。

### Cursor

打开 **Customize -> Rules -> Add Rule -> Remote Rule (Github)**，然后输入：

```text
https://github.com/huangxiaozhen/dida-hotel-audit
```

## 在 Windows 上配置同事的 Audit key

只有在负责人提供了可访问的网关 URL 和个人 Audit key 后，才能进行此配置。请在已安装的 Skill 目录中运行命令。

最安全的配置方式是使用隐藏输入：

```powershell
python -m dida_hotel_audit client configure --gateway-url https://audit.example.com
```

如果终端的隐藏输入模式无法粘贴，请仅复制 Audit key，然后使用剪贴板模式。程序会使用 Windows DPAPI 加密该密钥，随后清空剪贴板：

```powershell
python -m dida_hotel_audit client configure --gateway-url https://audit.example.com --from-clipboard
```

在不显示密钥的情况下检查配置：

```powershell
python -m dida_hotel_audit client status
```

在非 Windows 机器上，请使用操作系统或平台提供的密钥管理器，在运行时注入 `DIDA_AUDIT_ACCESS_KEY` 和 `DIDA_AUDIT_GATEWAY_URL`。不要把它们保存在本仓库或 Agent 提示词中。

## 示例提示词

```text
用 dida-hotel-audit 的 compare_hotels 判断 Dida 酒店 1062431 和 2333428 是否为同一家酒店。
```

```text
用 dida-hotel-audit 查看 Dida 酒店 3912 的经纬度是否正确，和 Google Maps 的酒店坐标比较，判断差距是否在 1000 米以内。
```

```text
用 dida-hotel-audit 拉取这些酒店的完整静态信息，并根据房型、设施和政策回答我的问题：3912、1062431。
```

## 网关负责人在 Windows 上的配置步骤

需要 Python 3.10 或更高版本，不依赖第三方软件包。

1. 通过终端隐藏输入保存 Dida 凭据：

   ```powershell
   python -m dida_hotel_audit credentials set --client-id <your-client-id>
   ```

   如果隐藏输入模式无法粘贴，请仅复制 LicenseKey，然后使用剪贴板模式：

   ```powershell
   python -m dida_hotel_audit credentials set --client-id <your-client-id> --from-clipboard
   ```

2. 为每位同事创建独立的访问密钥：

   ```powershell
   python -m dida_hotel_audit access-key create --label <teammate-name> --no-save-client
   ```

   每个密钥只显示一次。请通过获准使用的密钥共享渠道传递，不要通过聊天、电子邮件、Issue 或 Git 提交发送。

3. 启动用于开发的本地网关：

   ```powershell
   python -m dida_hotel_audit serve
   ```

   不要把内置的明文 HTTP 监听服务直接暴露到互联网。团队需要远程访问时，应在其前面配置可信的 HTTPS 隧道或反向代理。

4. 网关负责人需要在本机使用时，创建一个密钥，并同时保存一份由 DPAPI 保护的本地客户端副本：

   ```powershell
   python -m dida_hotel_audit access-key create --label local-owner
   ```

## 直接进行开发测试

网关运行后，可以比较两家酒店：

```powershell
python scripts/compare_hotels.py 1 2
```

获取 1 至 50 家酒店的完整静态记录，交给模型分析：

```powershell
python scripts/fetch_hotels.py 3912 1062431
```

在可信地图上定位酒店之前，先获取一家酒店的静态记录：

```powershell
python scripts/get_hotel.py 3912
```

核实地图标记对应同一家酒店后，计算坐标距离：

```powershell
python scripts/audit_coordinate.py 3912 --reference-latitude 0 --reference-longitude 0 --reference-provider "Google Maps" --reference-url "<verified-place-url>"
```

请把示例中的参考坐标和 URL 替换为经过核实的地点标记数据。

## 安全模型

- Dida 凭据和本地 Audit 客户端密钥使用 Windows DPAPI 加密，存放在本仓库之外、当前用户的本地应用数据目录中。
- 网关访问密钥是由 32 个字母和数字组成的随机字符串，服务器只保存其 SHA-256 摘要。
- 访问密钥不能通过命令行参数传入。
- 网关不会记录凭据或请求正文。
- 无需修改 Dida 凭据，即可单独撤销某位同事的密钥：

  ```powershell
  python -m dida_hotel_audit access-key list
  python -m dida_hotel_audit access-key revoke <key-id>
  ```

绝不要把凭据添加到本仓库、`.env` 文件、截图、提示词、Issue 报告或 Pull Request 中。发布项目前或报告安全问题前，请先阅读 [SECURITY.md](SECURITY.md)。

## 测试

```powershell
python -m unittest discover -s tests -v
```

测试使用合成的酒店记录和模拟 API 响应，不需要也不会输出真实凭据。
