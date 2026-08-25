---
name: dida-hotel-audit
description: 获取并分析当前 Dida Content API 的酒店静态信息，用于判断酒店是否为同一家、核验经纬度，以及分析政策、设施、房型、图片等静态内容。当请求包含 Dida 酒店 ID 时使用；不用于价格、库存、预订或非 Dida 酒店 ID。
metadata:
  openclaw:
    primaryEnv: DIDA_AUDIT_ACCESS_KEY
    requires:
      anyBins:
        - python
        - python3
---

# Dida 酒店审核

这是一个可复用的 Dida 静态数据分析 Skill。不要仅仅因为用户提出的静态数据问题没有专用流程，就创建新的 Skill。除非用户明确要求开发或扩展工具，否则应获取相关 Dida 酒店记录，并交给当前模型按照用户的实际需求进行分析。

绝不要自行拼接凭据来查询 Dida，也不要在聊天中索要凭据。

## 任务路由

- 提供两个酒店 ID，询问是否为同一家酒店或能否合并：使用 `compare_hotels`。
- 提供一个酒店 ID，要求与外部地图坐标进行核验：使用 `audit_coordinate`。
- 其他任何 Dida 静态内容问题：使用 `fetch_hotels`，然后直接分析返回的酒店记录。

现有专用流程是本 Skill 内部的确定性辅助功能，并非独立 Skill。处理普通审核请求时，不要搭建新的 Skill，也不要新增命名工作流。

## 通用静态信息分析

1. 从请求中提取 1 至 50 个正整数形式的 Dida 酒店 ID。仅当完成请求所需的 ID 缺失或含义不明确时，才向用户询问。
2. 阅读[通用静态信息分析规则](references/general-static-analysis.md)。
3. 将所有相关 ID 代入下列命令，并运行第一个可用的命令：

   - `python "{baseDir}/scripts/fetch_hotels.py" HOTEL_ID [HOTEL_ID ...] --language en-US`
   - `python3 "{baseDir}/scripts/fetch_hotels.py" HOTEL_ID [HOTEL_ID ...] --language en-US`

4. 将 `hotels` 视为已配置 Dida 账号针对本次请求返回的完整静态记录。把这些记录交给当前模型，根据相关字段回答用户的实际问题。
5. 如果需要外部证据，应从用户指定的服务提供方获取，并与 Dida 数据明确区分。如果记录或字段缺失，应说明这一限制，不得编造数据。
6. 先给出结论，再展示决定性证据和 Dida 追踪元数据。除非用户明确要求，否则不要输出完整 JSON。

## 比较两家酒店

1. 从请求中准确提取两个正整数形式的 Dida 酒店 ID。如果任一 ID 缺失或含义不明确，应向用户询问。
2. 在解读结果之前，阅读[酒店比较规则](references/comparison-rules.md)。
3. 将两个 ID 代入下列命令，并运行第一个可用的命令：

   - `python "{baseDir}/scripts/compare_hotels.py" HOTEL_ID_A HOTEL_ID_B --language en-US`
   - `python3 "{baseDir}/scripts/compare_hotels.py" HOTEL_ID_A HOTEL_ID_B --language en-US`

4. 将返回的 `hotels` 数组视为已配置 Dida 账号针对本次请求返回的完整静态记录。使用 `comparison.evidence` 进行确定性比较；如果其他静态字段能够实质性帮助确认酒店身份，也应一并检查。
5. 如果 `ok` 为 false、任一酒店缺失，或网关返回身份验证/API 错误，应如实说明限制。不得推测或编造酒店数据。

## 酒店比较结果

首先给出以下结论之一：

- 同一家酒店——可以作为同一酒店处理。
- 不同酒店——不要自动合并。
- 证据不足——需要人工复核。

然后提供简洁的对比表，涵盖酒店名称、地址、坐标及距离、电话、邮编、目的地、外部映射标识，以及 Dida 返回的其他决定性字段。说明字段冲突和缺失数据。如果响应中包含 Dida 追踪 ID 和响应时间戳，也应一并提供。

确定性比较结果只作为保守基线。如果原始字段存在尚未解决的矛盾，可以将结论降级为人工复核。不得仅凭名称、房型、设施或描述相似，就把人工复核升级为明确匹配。

## 核验单家酒店的坐标

1. 提取一个正整数形式的 Dida 酒店 ID，并阅读[坐标核验规则](references/coordinate-audit-rules.md)。
2. 运行下列第一个可用的命令，获取 Dida 酒店记录：

   - `python "{baseDir}/scripts/get_hotel.py" HOTEL_ID --language en-US`
   - `python3 "{baseDir}/scripts/get_hotel.py" HOTEL_ID --language en-US`

3. 使用返回的酒店名称、地址、目的地、电话及其他身份字段，在用户指定的地图服务中定位同一家酒店。不要把名称相似的地点或地图视窗中心当作酒店坐标。
4. 独立核实地图地点并提取其标记坐标后，运行下列第一个可用的命令：

   - `python "{baseDir}/scripts/audit_coordinate.py" HOTEL_ID --reference-latitude LAT --reference-longitude LON --reference-provider "Google Maps" --reference-name "PLACE_NAME" --reference-url "SOURCE_URL" --threshold-meters 1000`
   - `python3 "{baseDir}/scripts/audit_coordinate.py" HOTEL_ID --reference-latitude LAT --reference-longitude LON --reference-provider "Google Maps" --reference-name "PLACE_NAME" --reference-url "SOURCE_URL" --threshold-meters 1000`

5. 报告 Dida 坐标、已核实的参考坐标、Haversine 球面距离、阈值判断结果、酒店身份匹配证据、来源 URL 和 Dida 追踪元数据。如果无法核实地图地点身份或标记坐标，应报告证据不足，不得猜测。

## 安全要求

绝不显示、记录、复制或索要 `DIDA_AUDIT_ACCESS_KEY`、Dida ClientID、Dida LicenseKey、Basic Authorization 值或受保护存储区中的内容。不要通过命令行参数传递访问密钥。辅助程序会从受保护的本地存储区或运行时环境中读取访问密钥。
