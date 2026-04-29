#!/usr/bin/env python3
import os

tag          = os.environ['BT_TAG']
date         = os.environ['BT_COMMIT_DATE']
githash      = os.environ['BT_GITHASH']
githash_full = os.environ['BT_GITHASH_FULL']
title        = os.environ['BT_COMMIT_TITLE']
vulkan       = os.environ['BT_VULKAN_VERSION']
repo         = os.environ['BT_REPO']

mesa_url    = f'https://gitlab.freedesktop.org/mesa/mesa/-/commit/{githash_full}'
release_url = f'https://github.com/{repo}/releases/tag/{tag}'
new_row     = f'| [{tag}]({release_url}) | {date} | [`{githash}`]({mesa_url}) | {title} | {vulkan} |'

with open('Mesa-commit-history.md', 'r') as f:
    content = f.read()

marker       = '<!-- BUILDS_TABLE_START -->'
header       = '| Tag | Date | Mesa Commit | Commit Title | Vulkan |\n| :--- | :--- | :--- | :--- | :--- |'
insert_after = marker + '\n' + header + '\n'
content      = content.replace(insert_after, insert_after + new_row + '\n')

with open('Mesa-commit-history.md', 'w') as f:
    f.write(content)
