# MAX35 AURORA 4G（斑梨原厂源码基准）v1.2.0

这套工程专门对应：

- SpotPear / 斑梨 ESP32S3-MAX35 3.5 寸 480×320
- 4G：ML307（GPIO43 TX / GPIO44 RX）
- 后摄像头 + 触摸 + 外壳版本
- 原厂 board：`sp-esp32-s3-lcd-3.5-cam-ml307`
- 固定 OTA/后台发现地址：`http://124.221.112.55:8002/xiaozhi/ota/`

## 这次与之前版本最大的区别

本包直接以你上传的斑梨资料中的真实 `xiaozhi-esp32` 源码快照为基准，不再在 Actions 里下载或猜测 MAX35 4G 板级代码。

为了让 GitHub 仓库保持轻量，`source/factory-aurora-source.tar.gz` 内置的是完整应用/板级源码、`dependencies.lock` 等，但不重复打包 `managed_components/`。编译时 ESP-IDF Component Manager 会按照原厂 `dependencies.lock` 中固定的版本与 hash 下载组件。

为了确认“只加 UI + 固定 OTA”，预检会对 14 个关键原厂文件做 SHA256 校验。以下逻辑保持原厂字节级不变：

- `Application`
- `AudioService`
- `BoxAudioCodec / ES8311` 路径
- `ML307Board`
- `Esp32Camera`
- MAX35 `config.h` / `power_manager.h`
- `MCP`
- WebSocket / MQTT
- 原厂通用 `LcdDisplay`

实际只改/新增 5 处：

1. 新增 `aurora_max35_display.h`
2. 新增 `aurora_max35_display.cc`
3. MAX35 4G board 的显示对象从 `SpiLcdDisplay` 换成 `AuroraMax35Display`
4. 本板 `config.json` 写入固定 `CONFIG_OTA_URL`
5. `Ota::GetCheckVersionUrl()` 固定返回 `CONFIG_OTA_URL`，禁止旧 NVS 覆盖

完整差异在 `docs/FACTORY_TO_AURORA.patch`。

## AURORA UI 行为

- 深色 AURORA 主界面，显示时间、设备状态、4G/电池/静音图标。
- 一进入聆听状态，自动切换到独立 `DIALOG` 对话页。
- 用户识别文字显示在上方卡片。
- 小智回答使用独立大面积回答区。
- 如果后台把回答分成多个 TTS sentence 发送，固件会自动累计，而不是只保留最后一句。
- 回答自动换行；超过一屏后先停留，再匀速缓慢上移，直到最后一行读完。
- 只有设备回到 Idle 且长文本滚动结束后，才延时回主页。
- 摄像头驱动/MCP 不改；`Camera::Capture()` 仍走原厂路径，只把预览显示在新的 CAMERA 页面，约 5 秒后恢复。
- 触摸初始化仍是原厂代码；AURORA UI 本身不依赖触摸。

## 上传 GitHub

本工程每个文件都控制在 GitHub 网页上传的单文件限制以内，可以直接用浏览器上传。

1. 解压本 ZIP。
2. 新建一个空 GitHub 仓库。
3. 把解压目录中的**所有内容**上传到仓库根目录，包括隐藏目录 `.github/`。
4. 确认仓库根目录能看到 `source/`、`scripts/`、`factory-recovery/`、`README_CN.md`，并且 `.github/workflows/build-max35-aurora-4g.yml` 存在。
5. 打开 `Actions`。
6. 运行：`Build MAX35 AURORA 4G - Factory Base` → `Run workflow`。
7. 成功后下载 Artifact：`MAX35-AURORA-Factory4G-Firmware`。

Artifact 中主要文件：

- `MAX35_AURORA_FACTORY4G_v1.2.0_merged-binary.bin`：AURORA 完整合并固件，烧录地址 `0x0`。
- `FACTORY_RECOVERY_ESP32S3-MAX35-4G-LCD-BCamera-Case.bin`：你上传资料里的原厂 4G 恢复固件，烧录地址 `0x0`。
- `BUILD_INFO.txt`：板型、IDF、固定 OTA 地址等信息。
- `SHA256SUMS.txt`：产物校验值。

第一次测试 AURORA 固件建议先整片擦除，再从 `0x0` 烧入 merged binary。

## GitHub Actions 的硬检查

正式编译前会确认：

- 原厂关键硬件/网络/音频/MCP 文件没有被修改；
- 板型确实是 `sp-esp32-s3-lcd-3.5-cam-ml307`；
- ML307 GPIO43/44 与 480×320 定义仍是原厂值；
- AURORA 对话页、回答累计、缓慢滚动、Camera 预览代码都存在；
- OTA 地址固定为 `http://124.221.112.55:8002/xiaozhi/ota/`；
- NVS 中旧的 `wifi/ota_url` 不再覆盖该地址。

正式编译后还会再次检查最终 `sdkconfig`。任何一项不对都会直接失败，不会生成一个“看起来成功但板型/后台不对”的 BIN。

## 编译环境

Actions 使用 `espressif/idf:release-v5.5`，并编译你上传资料中的原厂源码快照；依赖版本由该源码自带的 `dependencies.lock` 锁定。
