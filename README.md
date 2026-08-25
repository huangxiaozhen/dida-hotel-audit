# Dida 酒店审核

`dida-hotel-audit` 是一个可复用的 Agent Skill。它直接调用 Dida Content API v2 获取酒店完整静态记录，再由当前大模型按用户的问题分析酒店身份、经纬度、房型、设施、政策、图片等内容。

本版本采用最简单的“直接凭证”方案：不使用 Audit key、不部署网关，也不需要 Cloudflare。ClientID 已在程序中固定为 ``，每位同事只需在自己的电脑上配置 LicenseKey，查询时由本机直接访问 Dida 静态接口。

```text
同事的 Agent -> 已安装的 dida-hotel-audit -> Dida Content API v2
                         ^
              本机明文 LicenseKey 配置
```

## 一条消息安装并配置

把下面整段发给 Codex、OpenClaw 或具备终端权限的 Cursor Agent，并替换 LicenseKey 占位符：

```text
帮我安装并配置 dida-hotel-audit：
GitHub 地址：https://github.com/huangxiaozhen/dida-hotel-audit
LicenseKey：<DIDA_LICENSE_KEY>

请使用当前 Agent 支持的全局 Skill 安装方式。安装完成后，运行该 Skill 自带的 scripts/configure.py，把 LicenseKey 保存到本机明文配置文件；再运行 scripts/credential_status.py 验证。最后只告诉我 Skill 是否安装成功、固定 ClientID 和配置文件路径，不要回显 LicenseKey，也不要把 LicenseKey 写入 GitHub 仓库。
```

这里的“一条消息”表示 Agent 在同一个任务里先安装、再配置。宿主产品如果弹出 GitHub Skill 安装确认或安全审核，需要用户批准一次；Skill 不能绕过宿主本身的确认机制。

## 各平台安装方式

### OpenClaw

OpenClaw 支持从 Git 仓库全局安装根目录含 `SKILL.md` 的 Skill：

```powershell
openclaw skills install git:huangxiaozhen/dida-hotel-audit@main --global
```

如果安装策略给出警告，按 OpenClaw 的提示审核并确认后继续。

### Cursor

Cursor 官方的 GitHub 导入入口是 **Customize -> Rules -> Add Rule -> Remote Rule (Github)**，输入：

```text
https://github.com/huangxiaozhen/dida-hotel-audit
```

具备终端权限的 Cursor Agent 也可以根据上面的“一条消息”把仓库安装到 Cursor 能自动发现的全局 Skill 目录，再执行配置脚本。

### Codex

向 Codex 发送上面的“一条消息”即可；Codex 应使用可用的 Skill 安装功能安装该 GitHub 仓库，然后执行配置脚本。新安装的 Skill 如果没有立即出现在列表中，请重启 Codex。

## 手动配置

如果已经安装完成，可以直接运行：

```powershell
python "<SKILL_DIR>/scripts/configure.py" --license-key "<DIDA_LICENSE_KEY>"
```

检查状态：

```powershell
python "<SKILL_DIR>/scripts/credential_status.py"
```

配置脚本不会回显 LicenseKey。默认明文文件位置为：

- Windows：`%LOCALAPPDATA%\dida-hotel-audit\credentials.json`
- macOS：`~/Library/Application Support/dida-hotel-audit/credentials.json`
- Linux：`~/.config/dida-hotel-audit/credentials.json`

也可以用 `DIDA_HOTEL_AUDIT_CREDENTIALS_FILE` 指定其他文件。运行时提供 `DIDA_LICENSE_KEY` 环境变量，会优先使用该 LicenseKey；ClientID 始终使用程序中的固定值。

## 使用示例

普通酒店身份比较：

```text
用 dida-hotel-audit 判断 Dida 酒店 1062431 和 2333428 是否为同一家酒店。
```

核验坐标：

```text
用 dida-hotel-audit 查看 Dida 酒店 3912 的经纬度是否正确，和 Google Maps 的酒店坐标比较，判断差距是否在 1000 米以内。
```

怀疑 GIATA 映射错误：

```text
有个 GIATA 可能匹配错误：Dida 的两个不同酒店被匹配到了 GIATA 的同一个酒店。请用 dida-hotel-audit 拉取两个 Dida 酒店的完整静态信息，排除 GIATA 本身作为同店证据，再判断它们是否确实为不同酒店。
```

其他静态内容问题：

```text
用 dida-hotel-audit 拉取酒店 3912 和 1062431 的完整静态信息，并根据房型、设施和政策回答我的问题。
```

## 本地脚本

比较两家酒店：

```powershell
python scripts/compare_hotels.py 1062431 2333428
```

如果正在调查 GIATA 本身是否映射错误，必须把 GIATA 从同店评分中排除：

```powershell
python scripts/compare_hotels.py 1062431 2333428 --suspect-external-provider giata
```

获取 1 至 50 家酒店的完整静态记录：

```powershell
python scripts/fetch_hotels.py 3912 1062431
```

获取单家酒店：

```powershell
python scripts/get_hotel.py 3912
```

在外部地图上核实同一家酒店的标记坐标后，计算球面距离：

```powershell
python scripts/audit_coordinate.py 3912 --reference-latitude 0 --reference-longitude 0 --reference-provider "Google Maps" --reference-url "<VERIFIED_PLACE_URL>"
```

请把示例坐标和 URL 替换为经过核实的地点数据。

## 凭证和访问边界

- `credentials.json` 只保存 LicenseKey，是明文文件，不是加密文件。
- ClientID 固定在程序中，同事不需要输入或保存 ClientID。
- 凭证文件保存在 Skill 仓库之外，并已把常见凭证文件名加入 `.gitignore`。
- 配置命令的参数和安装者发给 Agent 的消息中会包含 LicenseKey，这是本方案有意接受的简化方式。
- 所有同事使用同一个 Dida 凭证，因此无法按同事单独撤销；需要停用某人时只能更换共享 LicenseKey，并让仍获授权的同事重新配置。
- Skill 只调用 `https://static-api.didatravel.com/api/v1/hotel/details`，不实现价格、库存、下单或订单操作。
- 仓库、示例、测试、日志和最终回答中都不应出现真实 LicenseKey。

## 测试

```powershell
python -m unittest discover -s tests -v
```

测试只使用合成凭证、合成酒店记录和模拟 API，不会调用真实账号。
