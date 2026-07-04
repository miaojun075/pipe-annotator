# -*- coding: utf-8 -*-
"""
管件名称重命名工具
用法:
  python rename_pipe.py  旧名称  新名称
  python rename_pipe.py  旧名称  新名称  --dry-run   (预览不执行)

一次更新所有存储位置:
  1. templates.db  → templates.category
  2. corrections.db → manual_corrections (old_category / new_category)
  3. learned_rois.json → category
  4. manual_boxes.json → category
  5. session_items → category_code
"""

import sqlite3
import json
import os
import sys
import argparse

PROJ_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DB = os.path.join(PROJ_DIR, 'templates.db')
CORRECTIONS_DB = os.path.join(PROJ_DIR, 'corrections.db')
LEARNED_ROIS = os.path.join(PROJ_DIR, 'learned_rois.json')
MANUAL_BOXES = os.path.join(PROJ_DIR, 'manual_boxes.json')


def rename_templates_db(old, new, dry=False):
    """更新 templates 表的 category 字段"""
    db = sqlite3.connect(TEMPLATES_DB)
    cur = db.cursor()
    cur.execute('SELECT COUNT(*) FROM templates WHERE category = ?', (old,))
    cnt = cur.fetchone()[0]
    if cnt == 0:
        print(f'  templates: 未找到 "{old}"')
        cur.execute(
            "SELECT DISTINCT category FROM templates WHERE category LIKE ?",
            (f'%{old.split("_")[0]}%',)
        )
        similar = cur.fetchall()
        if similar:
            print(f'  相似条目: {[s[0] for s in similar]}')
    else:
        print(f'  templates: {cnt} 条 → "{new}"')
        if not dry:
            cur.execute('UPDATE templates SET category = ? WHERE category = ?', (new, old))
            db.commit()
    db.close()
    return cnt


def rename_corrections_db(old, new, dry=False):
    """更新 corrections.db 的 old_category 和 new_category"""
    if not os.path.exists(CORRECTIONS_DB):
        print('  corrections.db: 不存在')
        return 0
    db = sqlite3.connect(CORRECTIONS_DB)
    cur = db.cursor()

    cur.execute('SELECT COUNT(*) FROM manual_corrections WHERE old_category = ?', (old,))
    cnt_old = cur.fetchone()[0]

    cur.execute('SELECT COUNT(*) FROM manual_corrections WHERE new_category = ?', (old,))
    cnt_new = cur.fetchone()[0]

    total = cnt_old + cnt_new
    if total == 0:
        print(f'  corrections: 未找到 "{old}"')
    else:
        print(f'  corrections: {cnt_old} old_category + {cnt_new} new_category = {total} 条')
        if not dry:
            if cnt_old:
                cur.execute('UPDATE manual_corrections SET old_category = ? WHERE old_category = ?',
                            (new, old))
            if cnt_new:
                cur.execute('UPDATE manual_corrections SET new_category = ? WHERE new_category = ?',
                            (new, old))
            db.commit()
    db.close()
    return total


def rename_json_file(filepath, old, new, dry=False):
    """更新 JSON 文件中的 category 字段"""
    if not os.path.exists(filepath):
        print(f'  {os.path.basename(filepath)}: 不存在')
        return 0

    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    changed = 0
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict) and item.get('category') == old:
                item['category'] = new
                changed += 1
    elif isinstance(data, dict):
        for key, val in data.items():
            if isinstance(val, list):
                for item in val:
                    if isinstance(item, dict) and item.get('category') == old:
                        item['category'] = new
                        changed += 1

    print(f'  {os.path.basename(filepath)}: {changed} 条')
    if not dry and changed:
        bak = filepath + '.bak'
        if not os.path.exists(bak):
            import shutil
            shutil.copy2(filepath, bak)
            print(f'    备份: {bak}')
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    return changed


def rename_session_items(old, new, dry=False):
    """更新 session_items 表的 category_code 字段"""
    db = sqlite3.connect(TEMPLATES_DB)
    cur = db.cursor()
    try:
        cur.execute('SELECT COUNT(*) FROM session_items WHERE category_code = ?', (old,))
        cnt = cur.fetchone()[0]
        if cnt == 0:
            print(f'  session_items: 未找到 "{old}"')
        else:
            print(f'  session_items: {cnt} 条')
            if not dry:
                cur.execute('UPDATE session_items SET category_code = ? WHERE category_code = ?',
                            (new, old))
                db.commit()
    except sqlite3.OperationalError:
        print('  session_items: 表不存在')
        cnt = 0
    db.close()
    return cnt


def main():
    parser = argparse.ArgumentParser(description='管件名称重命名工具')
    parser.add_argument('old_name', help='当前名称')
    parser.add_argument('new_name', help='新名称')
    parser.add_argument('--dry-run', action='store_true', help='预览模式，不实际修改')
    args = parser.parse_args()

    old = args.old_name
    new = args.new_name

    print(f'重命名: "{old}" → "{new}"')
    print(f'模式: {"预览 (不修改)" if args.dry_run else "执行"}\n')

    total = 0
    total += rename_templates_db(old, new, args.dry_run)
    total += rename_corrections_db(old, new, args.dry_run)
    total += rename_json_file(LEARNED_ROIS, old, new, args.dry_run)
    total += rename_json_file(MANUAL_BOXES, old, new, args.dry_run)
    total += rename_session_items(old, new, args.dry_run)

    print(f'\n{"[预览] " if args.dry_run else ""}总计 {total} 条需要更新')
    if args.dry_run:
        print('去掉 --dry-run 执行实际修改')
    else:
        print('完成。重启程序生效。')


if __name__ == '__main__':
    main()
