---
name: dida-hotel-audit
description: 直接获取并分析 Dida Content API v2 的酒店静态信息，用于判断酒店是否为同一家、调查 GIATA 等外部映射错误、核验经纬度，以及分析政策、设施、房型和图片。当请求包含 Dida 酒店 ID 或要求安装配置本 Skill 时使用；不用于价格、库存、预订或非 Dida 酒店 ID。
metadata:
  openclaw:
    requires:
      anyBins:
        - python
        - python3
---

# Dida 酒店审核

直接从安装者本机调用 Dida 静态接口。不要使用 Audit key、Audit 网关或 Cloudflare，也不要为普通静态数据问题创建新的 Skill。

## 安装后的凭证配置

ClientID 已在程序中固定为 `Huangzhen_test`。当用户明确要求配置本 Skill，并在请求中提供 LicenseKey 时：

1. 使用用户提供的原值运行第一个可用命令：

   - `python "{baseDir}/scripts/configure.py" --license-key "LICENSE_KEY"`
   - `python3 "{baseDir}/scripts/configure.py" --license-key "LICENSE_KEY"`

2. 再运行第一个可用命令验证：

   - `python "{baseDir}/scripts/credential_status.py"`
   - `python3 "{baseDir}/scripts/credential_status.py"`

3. 只报告配置是否成功、固定 ClientID 和配置文件路径。不要在工具输出摘要或最终回答中重复 LicenseKey。

配置文件是仓库外的本机明文 `credentials.json`，只保存 LicenseKey，不使用加密。不要把 LicenseKey 写入 Skill 源码、README、测试、Git 提交或其他仓库文件。如果 LicenseKey 未配置且用户没有在当前请求中提供，应说明需要先配置，不得猜测。

## 任务路由

- 两个酒店 ID，询问是否为同一家酒店或能否合并：使用 `compare_hotels`。
- 怀疑 GIATA、Vervotech 等第三方把两个 Dida 酒店错误映射到同一酒店：仍使用 `compare_hotels`，但必须将被调查的提供方标记为可疑并排除其标识符的评分。
- 一个酒店 ID，要求与外部地图坐标核验：使用 `audit_coordinate`。
- 其他任何 Dida 静态内容问题：使用 `fetch_hotels`，再把返回的完整静态记录交给当前模型按用户需求分析。

这些是本 Skill 内部的确定性辅助功能，不是不同的 Skill。除非用户明确要求开发工具，否则不要创建新 Skill 或新增命名工作流。

## 通用静态信息分析

1. 提取 1 至 50 个正整数形式的 Dida 酒店 ID。仅当完成请求所需的 ID 缺失或含义不明确时才询问。
2. 阅读[通用静态信息分析规则](references/general-static-analysis.md)。
3. 将相关 ID 代入并运行第一个可用命令：

   - `python "{baseDir}/scripts/fetch_hotels.py" HOTEL_ID [HOTEL_ID ...] --language en-US`
   - `python3 "{baseDir}/scripts/fetch_hotels.py" HOTEL_ID [HOTEL_ID ...] --language en-US`

4. 把 `hotels` 视为当前 Dida 账号为本次请求返回的完整静态记录，交给当前模型按用户的具体问题分析。
5. 外部证据必须与 Dida 数据明确区分。字段缺失时说明“当前账号未返回”，不得编造。
6. 先给结论，再展示决定性证据和 Dida trace ID、响应时间戳。除非用户明确要求，否则不要输出完整 JSON。

## 比较两家酒店

1. 准确提取两个正整数形式的 Dida 酒店 ID。
2. 阅读[酒店比较规则](references/comparison-rules.md)。
3. 普通比较运行第一个可用命令：

   - `python "{baseDir}/scripts/compare_hotels.py" HOTEL_ID_A HOTEL_ID_B --language en-US`
   - `python3 "{baseDir}/scripts/compare_hotels.py" HOTEL_ID_A HOTEL_ID_B --language en-US`

4. 如果用户正在调查某个外部提供方本身是否映射错误，增加 `--suspect-external-provider PROVIDER`。例如调查 GIATA：

   - `python "{baseDir}/scripts/compare_hotels.py" HOTEL_ID_A HOTEL_ID_B --language en-US --suspect-external-provider giata`
   - `python3 "{baseDir}/scripts/compare_hotels.py" HOTEL_ID_A HOTEL_ID_B --language en-US --suspect-external-provider giata`

5. 使用 `comparison.evidence` 作为确定性基线，并检查返回的完整原始静态字段。被标记为可疑的外部映射只能作为“正在调查的现象”，不能作为同一家酒店的正向证据。

首先输出以下结论之一：

- 同一家酒店——可以作为同一酒店处理。
- 不同酒店——不要自动合并。
- 证据不足——需要人工复核。

随后给出简洁对比，涵盖名称、地址、坐标及距离、电话、邮编、目的地、外部映射标识和其他决定性字段。名称、房型、设施或描述相似，单独都不足以证明同店。

## 核验单家酒店坐标

1. 提取一个正整数形式的 Dida 酒店 ID，并阅读[坐标核验规则](references/coordinate-audit-rules.md)。
2. 运行第一个可用命令获取 Dida 记录：

   - `python "{baseDir}/scripts/get_hotel.py" HOTEL_ID --language en-US`
   - `python3 "{baseDir}/scripts/get_hotel.py" HOTEL_ID --language en-US`

3. 使用酒店名称、地址、目的地、电话等字段，在用户指定的地图服务中定位同一家酒店。不要把同名地点或地图视窗中心当作酒店坐标。
4. 独立核实地图标记后，运行第一个可用命令：

   - `python "{baseDir}/scripts/audit_coordinate.py" HOTEL_ID --reference-latitude LAT --reference-longitude LON --reference-provider "Google Maps" --reference-name "PLACE_NAME" --reference-url "SOURCE_URL" --threshold-meters 1000`
   - `python3 "{baseDir}/scripts/audit_coordinate.py" HOTEL_ID --reference-latitude LAT --reference-longitude LON --reference-provider "Google Maps" --reference-name "PLACE_NAME" --reference-url "SOURCE_URL" --threshold-meters 1000`

5. 报告 Dida 坐标、已核实的参考坐标、Haversine 距离、阈值结论、酒店身份匹配证据、来源 URL 和 Dida 追踪元数据。无法确认地图地点身份或标记坐标时，应报告证据不足。

## 执行边界

- 只访问 Dida 静态域名 `https://static-api.didatravel.com` 的酒店详情接口。
- 每次请求最多 50 个酒店 ID。
- 不执行价格、库存、下单、付款、订单查询或取消。
- API、网络或凭证错误必须如实返回，不得用猜测数据补全。
- 不在回答、日志或异常消息中输出 LicenseKey 或 Basic Authorization 值。
