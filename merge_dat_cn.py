#!/usr/bin/env python3
"""
合成脚本: 将 No-Intro DAT (ClrMamePro 格式) 与中文名 CSV 合并为带 cnname 字段的 XML DAT。

输入:
  gba_no_intro.dat  — No-Intro ClrMamePro 格式, 含 name/serial/crc/size
  gba_names_cn.csv  — 英文名到中文名的映射表

输出:
  gba_cn.dat        — XML 格式, game 标签含 name(英文) 和 cnname(中文) 属性,
                      rom 标签含 name/size/crc/serial 属性
"""

import re
import csv
import sys
import os
from html import escape


def load_cn_names(csv_path):
    """加载 CSV 中英文映射表"""
    en_to_cn = {}
    with open(csv_path, 'r', encoding='utf-8-sig', errors='ignore') as f:
        reader = csv.reader(f)
        header = next(reader, None)
        for row in reader:
            if len(row) >= 2 and row[1].strip():
                en_to_cn[row[0].strip()] = row[1].strip()
    return en_to_cn


def parse_cmp_dat(dat_path):
    """解析 ClrMamePro 格式 DAT, 返回 game 列表

    每个 game 是 dict: {name, serial, roms: [{name, size, crc, serial}]}
    """
    with open(dat_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    games = []

    # 定位每个 'game ( name "..."' 的位置, 提取游戏名
    game_matches = list(re.finditer(
        r'game\s*\(\s*name\s+"((?:[^"\\]|\\.)*)"', content, re.IGNORECASE
    ))

    for i, gm in enumerate(game_matches):
        start = gm.start()
        end = game_matches[i + 1].start() if i + 1 < len(game_matches) else len(content)
        block = content[start:end]

        game_name = gm.group(1)

        # 游戏级 serial
        serial_m = re.search(r'serial\s+"([^"]+)"', block)
        game_serial = serial_m.group(1) if serial_m else ''

        # 直接从整个 block 中提取 rom 信息 (避免嵌套括号问题)
        # 一个 block 可能有多个 rom 条目
        roms = []
        # 找到所有 rom 关键字的位置
        rom_starts = [m.start() for m in re.finditer(r'rom\s*\(', block)]

        for j, rs in enumerate(rom_starts):
            # rom 内容范围: 从当前 rom ( 到下一个 rom ( 或 block 结尾
            rom_end = rom_starts[j + 1] if j + 1 < len(rom_starts) else len(block)
            rom_text = block[rs:rom_end]

            rom_name_m = re.search(r'name\s+"((?:[^"\\]|\\.)*)"', rom_text)
            size_m = re.search(r'size\s+(\d+)', rom_text)
            crc_m = re.search(r'crc\s+([0-9A-Fa-f]+)', rom_text)
            rom_serial_m = re.search(r'serial\s+"([^"]+)"', rom_text)

            roms.append({
                'name': rom_name_m.group(1) if rom_name_m else '',
                'size': size_m.group(1) if size_m else '',
                'crc': crc_m.group(1).upper() if crc_m else '',
                'serial': rom_serial_m.group(1) if rom_serial_m else game_serial,
            })

        if roms:
            games.append({
                'name': game_name,
                'serial': game_serial,
                'roms': roms,
            })

    return games


def build_xml(games, en_to_cn):
    """生成 XML DAT 字符串"""
    lines = []
    lines.append('<?xml version="1.0" encoding="UTF-8"?>')
    lines.append('<datafile>')
    lines.append('\t<header>')
    lines.append('\t\t<name>Nintendo - Game Boy Advance (CN)</name>')
    lines.append('\t\t<description>Nintendo - Game Boy Advance with Chinese names</description>')
    lines.append('\t</header>')

    matched = 0
    total = len(games)

    for game in games:
        en_name = game['name']
        cn_name = en_to_cn.get(en_name, '')

        if cn_name:
            matched += 1

        # XML 属性转义
        en_esc = escape(en_name)
        cn_attr = f' cnname="{escape(cn_name)}"' if cn_name else ''

        lines.append(f'\t<game name="{en_esc}"{cn_attr}>')

        for rom in game['roms']:
            rom_name_esc = escape(rom['name'])
            serial_attr = f' serial="{rom["serial"]}"' if rom['serial'] else ''
            lines.append(
                f'\t\t<rom name="{rom_name_esc}" '
                f'size="{rom["size"]}" '
                f'crc="{rom["crc"]}"'
                f'{serial_attr} />'
            )

        lines.append('\t</game>')

    lines.append('</datafile>')

    print(f"共 {total} 条游戏, {matched} 条匹配到中文名")
    return '\n'.join(lines)


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    dat_path = os.path.join(script_dir, 'gba_no_intro.dat')
    csv_path = os.path.join(script_dir, 'gba_names_cn.csv')
    out_path = os.path.join(script_dir, 'data', 'gba.dat')

    if not os.path.exists(dat_path):
        print(f"错误: 找不到 DAT 文件: {dat_path}")
        sys.exit(1)
    if not os.path.exists(csv_path):
        print(f"错误: 找不到 CSV 文件: {csv_path}")
        sys.exit(1)

    print("加载中文名映射表...")
    en_to_cn = load_cn_names(csv_path)
    print(f"  CSV 共 {len(en_to_cn)} 条中文名")

    print("解析 No-Intro DAT...")
    games = parse_cmp_dat(dat_path)
    print(f"  DAT 共 {len(games)} 条游戏")

    print("合成 XML DAT...")
    xml = build_xml(games, en_to_cn)

    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(xml)
    print(f"已生成: {out_path} ({os.path.getsize(out_path)} bytes)")


if __name__ == '__main__':
    main()
