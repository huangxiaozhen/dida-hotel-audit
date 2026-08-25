# 安全说明

## 仓库边界

本仓库不得包含真实 Dida LicenseKey、Basic Authorization 值、`.env` 文件或本机 `credentials.json`。Issue、Pull Request、截图、测试和日志中也不得提交真实 LicenseKey。ClientID 是程序中的固定公开配置，不作为秘密处理。

## 本机明文配置

本项目按团队选择，把凭证保存在安装者本机、仓库之外的明文 `credentials.json`。这不是加密存储。配置脚本只在结果中显示 ClientID 和文件路径，不回显 LicenseKey。

如果凭证被发到 Agent 对话或作为配置命令参数使用，它可能存在于相应产品的对话记录、终端记录或审计日志中；这是直接凭证方案的已知特性。

## 凭证更换

所有同事共享同一组 Dida 凭证，项目本身无法按人员单独撤销。需要终止某位同事的访问，或认为 LicenseKey 已泄露时，应在 Dida 端更换 LicenseKey，并让仍获授权的同事重新配置。

## API 范围

本 Skill 固定访问 Dida 静态接口，不实现价格、库存、下单、支付或订单管理功能。
