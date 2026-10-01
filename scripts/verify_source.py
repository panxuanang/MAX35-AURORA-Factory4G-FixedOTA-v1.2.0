#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else 'xiaozhi-esp32').resolve()
OTA = 'http://124.221.112.55:8002/xiaozhi/ota/'
BOARD = ROOT / 'main/boards/sp-esp32-s3-lcd-3.5-cam-ml307'

CRITICAL = {
    'main/application.cc': '19fc795bfb726db7814e2afe0615c4845ec2c46e11c1de9de754ac084e758536',
    'main/audio/audio_service.cc': 'cbafcc5cd84834f12a4edd4ec0c8ba6d3ea1318b73346c33cbe862d913e9474a',
    'main/audio/codecs/box_audio_codec.cc': '73ff9f5003f6459f591d35342c8d3fb234f3f03e4b08f5ae4fd3b9cfdcfa15b3',
    'main/boards/common/ml307_board.cc': '8a52e53d14d1196cfa1d0d55614d89f4617e4e2cb97fe80d45695f784ad491ae',
    'main/boards/common/ml307_board.h': '018f9e81392460d816c69d883c0985ba036127b3f0f4d18a33a4b7da54b0b9dc',
    'main/boards/common/esp32_camera.cc': '88f7c62a72b92f7c5c7a3dcc85201bd09458d0f969f746844d07df18794202e6',
    'main/boards/common/esp32_camera.h': '3a110263bbeb2e3e1c76b7bf1d15a90d7766d2464d72ca0dac50e32af8945d3a',
    'main/boards/sp-esp32-s3-lcd-3.5-cam-ml307/config.h': 'f3e16b46a93dc28f642241eefbbca74d13dbac37182eac5fea8097d2f9f5a746',
    'main/boards/sp-esp32-s3-lcd-3.5-cam-ml307/power_manager.h': 'e7186ea749678d5cb433fde37d70785ad70e2fc560d4ba66728e9b04e0d0d637',
    'main/mcp_server.cc': 'f2088e08456ed9996cb8f6ae454bb8e682ccde136886f96ce940c8efb5a663f8',
    'main/protocols/websocket_protocol.cc': '5d84b742cf071e180998dcedd11d4419b3940342e28f7a54f520c5f8d642a7c9',
    'main/protocols/mqtt_protocol.cc': 'cb00beaeaeee75a25d6a013b542a3326dc323316308d123c5ff1a2f21a739f29',
    'main/display/lcd_display.cc': '26c156675944aba58e3f2f53297887bc982ed8d51c820f9871827ca3f5c41d7e',
    'main/display/lcd_display.h': '8b01694e446a0b1c90c28471713b06ea82e80fb51ec30ad02bc689e500d6eb87',
}


def fail(msg: str) -> None:
    print(f'[FAIL] {msg}', file=sys.stderr)
    raise SystemExit(1)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


if not ROOT.is_dir():
    fail(f'source root not found: {ROOT}')

print('[check] verifying factory-critical files were not changed...')
for rel, expected in CRITICAL.items():
    p = ROOT / rel
    if not p.is_file():
        fail(f'missing factory file: {rel}')
    actual = sha256(p)
    if actual != expected:
        fail(f'factory-critical file changed: {rel}\n expected {expected}\n actual   {actual}')
print(f'[OK] {len(CRITICAL)} factory-critical files are byte-for-byte unchanged')

cfg_path = BOARD / 'config.json'
cfg = json.loads(cfg_path.read_text(encoding='utf-8'))
builds = cfg.get('builds', [])
if len(builds) != 1 or builds[0].get('name') != 'sp-esp32-s3-lcd-3.5-cam-ml307':
    fail('unexpected MAX35 ML307 config.json structure')
append = builds[0].get('sdkconfig_append', [])
expected_ota = f'CONFIG_OTA_URL="{OTA}"'
if expected_ota not in append:
    fail('fixed OTA URL is not present in the MAX35 ML307 build config')
if 'CONFIG_USE_WECHAT_MESSAGE_STYLE=y' not in append:
    fail('factory display config flag unexpectedly changed')
print(f'[OK] compile-time OTA URL fixed to {OTA}')

ota = (ROOT / 'main/ota.cc').read_text(encoding='utf-8')
match = re.search(r'std::string\s+Ota::GetCheckVersionUrl\(\)\s*\{(.*?)\n\}', ota, re.S)
if not match:
    fail('cannot locate Ota::GetCheckVersionUrl()')
body = match.group(1)
if 'return CONFIG_OTA_URL;' not in body or 'GetString("ota_url")' in body:
    fail('OTA URL can still be overridden by NVS')
print('[OK] NVS ota_url override disabled for this 4G product build')

board_cc = (BOARD / 'sp-esp32-s3-lcd-3.5-cam-ml307.cc').read_text(encoding='utf-8')
if '#include "aurora_max35_display.h"' not in board_cc:
    fail('AURORA display header is not connected to the factory board')
if 'new AuroraMax35Display(' not in board_cc:
    fail('factory board does not instantiate AuroraMax35Display')
if 'new SpiLcdDisplay(' in board_cc:
    fail('factory board still instantiates the old display')
print('[OK] only the display object is swapped at the factory board integration point')

ui_h = BOARD / 'aurora_max35_display.h'
ui_cc = BOARD / 'aurora_max35_display.cc'
if not ui_h.is_file() or not ui_cc.is_file():
    fail('AURORA UI files missing')
ui = ui_cc.read_text(encoding='utf-8')
for anchor in [
    'ShowPageInternal(Page::Chat)',
    'StartReadableScrollInternal',
    'lv_anim_set_path_cb(&anim, lv_anim_path_linear)',
    'assistant_text_ +=',
    'page_before_camera_',
    'LvglDisplay::UpdateStatusBar(update_all)',
]:
    if anchor not in ui:
        fail(f'AURORA UI missing required behavior: {anchor}')
print('[OK] dialog auto-page, full answer accumulation, slow scrolling, and camera preview UI are present')

config_h = (BOARD / 'config.h').read_text(encoding='utf-8')
for anchor in [
    '#define DISPLAY_WIDTH           480',
    '#define DISPLAY_HEIGHT          320',
    '#define ML307_TX_PIN GPIO_NUM_43',
    '#define ML307_RX_PIN GPIO_NUM_44',
]:
    if anchor not in config_h:
        fail(f'factory hardware anchor changed/missing: {anchor}')
print('[OK] MAX35 480x320 + ML307 GPIO43/44 hardware definition preserved')

print('[done] MAX35 AURORA factory-4G preflight passed')
