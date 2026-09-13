import os
import re
import json
import sys

from github import Github

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stats_chart import generate_chart

BOARD_SIZE = 15
STATE_FILE = 'state.json'
STATS_FILE = 'stats.json'
README_FILE = 'README.md'
CHART_FILE = 'assets/stats.png'

SYMBOL = {'B': '●', 'W': '○', '.': '·'}
NAME = {'B': '黑方 ⚫', 'W': '白方 ⚪'}


# ---------- 工具函数 ----------

def load_json(path, default):
    if os.path.exists(path):
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    return default


def save_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def fresh_state(game_id=1):
    return {
        'board': ['.' * BOARD_SIZE for _ in range(BOARD_SIZE)],
        'turn': 'B',
        'winner': None,
        'last_move': None,
        'move_count': 0,
        'game_id': game_id,
        'recorded': False,
    }


def check_win(board, row, col, color):
    directions = [(0, 1), (1, 0), (1, 1), (1, -1)]
    for dr, dc in directions:
        count = 1
        for sign in (1, -1):
            r, c = row + dr * sign, col + dc * sign
            while 0 <= r < BOARD_SIZE and 0 <= c < BOARD_SIZE and board[r][c] == color:
                count += 1
                r += dr * sign
                c += dc * sign
        if count >= 5:
            return True
    return False


def generate_readme(state, repo_name):
    username = repo_name.split("/")[0]
    board = state['board']
    turn = state['turn']
    winner = state['winner']
    game_id = state.get('game_id', 1)
    move_count = state['move_count']
    last_move = state['last_move'] or '--'

    # 霓虹色板
    NEON    = '00F0FF'
    MAGENTA = 'FF00AA'
    GREEN   = '39FF14'
    PURPLE  = 'BD00FF'

    if winner:
        status_text = f'{NAME[winner]}_WIN'.replace(' ', '_')
        status_color = MAGENTA
    else:
        status_text = f'{NAME[turn]}_TURN'.replace(' ', '_')
        status_color = GREEN

    L = []

    # ========== 顶部 Banner ==========
    L += [
        '<div align="center">',
        '',
        f'<img src="https://capsule-render.vercel.app/api?type=waving'
        f'&color=0:{NEON},100:{PURPLE}&height=160&section=header'
        f'&text={username.upper()}&fontSize=48&fontColor=ffffff'
        f'&animation=fadeIn&fontAlignY=38" width="100%" />',
        '',
        f'<img src="https://readme-typing-svg.demolab.com?font=JetBrains+Mono'
        f'&size=22&duration=3000&pause=800&color={NEON}&center=true'
        f'&vCenter=true&width=700'
        f'&lines=SYSTEM+ONLINE'
        f'%3BWELCOME+TO+Aoan2011%27S+PROFILE'
        f'%3BBUILDING+One-Editor+with+Textual'
        f'%3BFIVE-IN-A-ROW+ENGINE+RUNNING" />',
        '',
        '</div>',
    ]

    # ========== 终端状态栏 ==========
    L += [
        '```',
        '╔══════════════════════════════════════════════════════════════╗',
        f'║  GOMOKU ENGINE v1.0     STATUS: {"● " + status_text:<26}║',
        f'║  GAME ID : {game_id:<6}    MOVE : {move_count:<6}   LAST : {last_move:<8}║',
        '╠══════════════════════════════════════════════════════════════╣',
        '║  FEATURED : One-Editor  [ Textual TUI Editor ]               ║',
        '╚══════════════════════════════════════════════════════════════╝',
        '```',
        '',
    ]

    # ========== 精选项目：One-Editor ==========
    PROJECT = 'One-Editor'
    proj = 'https://img.shields.io/github'
    pin_card = (
        f'https://github-readme-stats.vercel.app/api/pin/'
        f'?username={username}&repo={PROJECT}'
        f'&theme=tokyonight&hide_border=true'
        f'&bg_color=0a0e14&title_color={NEON}'
        f'&icon_color={PURPLE}&text_color=c9d1d9'
    )

    L += [
        '---',
        '',
        '## ▸ FEATURED PROJECT',
        '',
        '<div align="center">',
        '',
        f'<a href="https://github.com/{username}/{PROJECT}">',
        f'<img src="{pin_card}" height="150" />',
        '</a>',
        '',
        f'<img src="{proj}/stars/{username}/{PROJECT}'
        f'?style=for-the-badge&color={NEON}&labelColor=0a0e14&logo=github" />',
        f'<img src="{proj}/forks/{username}/{PROJECT}'
        f'?style=for-the-badge&color={PURPLE}&labelColor=0a0e14&logo=git" />',
        f'<img src="{proj}/issues/{username}/{PROJECT}'
        f'?style=for-the-badge&color={MAGENTA}&labelColor=0a0e14&logo=githubactions" />',
        f'<img src="{proj}/last-commit/{username}/{PROJECT}'
        f'?style=for-the-badge&color={GREEN}&labelColor=0a0e14&logo=git" />',
        '',
        f'<img src="{proj}/languages/top/{username}/{PROJECT}'
        f'?style=for-the-badge&color={NEON}&labelColor=0a0e14" />',
        f'<img src="{proj}/repo-size/{username}/{PROJECT}'
        f'?style=for-the-badge&color={PURPLE}&labelColor=0a0e14" />',
        f'<img src="https://img.shields.io/badge/Textual-TUI-{NEON}'
        f'?style=for-the-badge&logo=python&logoColor=white&labelColor=0a0e14" />',
        f'<img src="https://img.shields.io/badge/Python-3.10%2B-3776AB'
        f'?style=for-the-badge&logo=python&logoColor=white&labelColor=0a0e14" />',
        '',
        f'### [`{PROJECT}`](https://github.com/{username}/{PROJECT})',
        '',
        '> `TUI Editor` · Built with **Textual** · Python · 在终端里书写代码的全新方式',
        '',
        '</div>',
        '',
    ]

    # ========== 棋盘标题 ==========
    L += ['---', '', '## ▸ BOARD', '']

    if winner:
        L += [f'### 🏆 **{NAME[winner]} WINS**', '']
        reset_url = (
            f'https://github.com/{repo_name}/issues/new'
            f'?title=gomoku%7Creset&body=点击Submit重置棋盘'
        )
        L += [f'👉 [🔄 RESET BOARD]({reset_url})', '']
    else:
        L += [
            f'> 当前回合 **{NAME[turn]}** ｜ 点击棋盘 `·` 落子',
            '',
        ]

    header = '|   |' + '|'.join(
        f'**{chr(ord("A") + i)}**' for i in range(BOARD_SIZE)
    ) + '|'
    sep = '|:---:|' + ':---:|' * BOARD_SIZE
    L += [header, sep]

    for r in range(BOARD_SIZE):
        cells = [f'**{r + 1}**']
        for c in range(BOARD_SIZE):
            cell = board[r][c]
            symbol = SYMBOL[cell]
            coord = f'{chr(ord("A") + c)}{r + 1}'
            if winner or cell != '.':
                cells.append(symbol)
            else:
                url = (
                    f'https://github.com/{repo_name}/issues/new'
                    f'?title=gomoku%7Cplace%7C{coord}&body=点击Submit落子'
                )
                cells.append(f'[{symbol}]({url})')
        L.append('|' + '|'.join(cells) + '|')

    # ========== 战绩图 ==========
    L += [
        '',
        '---',
        '',
        '## ▸ TELEMETRY',
        '',
        '<div align="center">',
        '',
        f'<img src="{CHART_FILE}" width="95%" />',
        '',
        '</div>',
        '',
    ]

    # ========== GitHub 数据 ==========
    stats_base = 'https://github-readme-stats.vercel.app/api'
    theme = 'tokyonight'
    L += [
        '---',
        '',
        '## ▸ GITHUB METRICS',
        '',
        '<div align="center">',
        '',
        f'<img height="165" src="{stats_base}?username={username}'
        f'&show_icons=true&theme={theme}&hide_border=true'
        f'&bg_color=0a0e14&title_color={NEON}&icon_color={PURPLE}&text_color=c9d1d9" />',
        f'<img height="165" src="{stats_base}/top-langs/?username={username}'
        f'&layout=compact&theme={theme}&hide_border=true'
        f'&bg_color=0a0e14&title_color={NEON}&text_color=c9d1d9" />',
        '',
        f'<img src="https://streak-stats.demolab.com?user={username}'
        f'&theme={theme}&hide_border=true&background=0a0e14'
        f'&ring={NEON}&fire={MAGENTA}&currStreakLabel={NEON}" />',
        '',
        f'<img src="https://github-profile-trophy.vercel.app/?username={username}'
        f'&theme={theme}&no-frame=true&no-bg=true&row=1&column=7&margin-w=8" />',
        '',
        f'<img src="https://github-readme-activity-graph.vercel.app/graph'
        f'?username={username}&theme=tokyo-night&hide_border=true'
        f'&bg_color=0a0e14&color={NEON}&line={MAGENTA}&point={GREEN}" width="95%" />',
        '',
        '</div>',
        '',
    ]

    # ========== 页脚 ==========
    L += [
        '---',
        '',
        '<div align="center">',
        '',
        f'<img src="https://visitor-badge.laobi.icu/badge'
        f'?page_id={repo_name}&color={NEON}&label=VISITORS" />',
        '',
        '`[ SYSTEM READY ]` `[ POWERED BY GITHUB ACTIONS ]` `[ © Aoan2011 ]`',
        '',
        '</div>',
    ]

    return '\n'.join(L)


def write_output(should_commit, message=''):
    out_path = os.environ.get('GITHUB_OUTPUT')
    if not out_path:
        return
    with open(out_path, 'a', encoding='utf-8') as f:
        f.write(f'commit={"true" if should_commit else "false"}\n')
        if message:
            clean = message.replace('\n', ' ').replace('%', '')
            f.write(f'message={clean}\n')


# ---------- 主流程 ----------

def main():
    repo_name = os.environ['GITHUB_REPOSITORY']
    issue_title = os.environ.get('ISSUE_TITLE', '').strip()
    issue_number = os.environ.get('ISSUE_NUMBER')
    issue_user = os.environ.get('ISSUE_USER', 'unknown')

    state = load_json(STATE_FILE, fresh_state())
    stats = load_json(STATS_FILE, {'games': [], 'moves': []})

    # 手动触发：只重新生成 README 和图表
    if not issue_title:
        readme = generate_readme(state, repo_name)
        with open(README_FILE, 'w', encoding='utf-8') as f:
            f.write(readme)
        generate_chart(STATS_FILE, STATE_FILE, CHART_FILE)
        write_output(True, 'Regenerate README and chart [skip ci]')
        return

    g = Github(os.environ['GITHUB_TOKEN'])
    repo = g.get_repo(repo_name)
    issue = repo.get_issue(int(issue_number))

    should_commit = False
    commit_msg = ''

    # ---- 重置 ----
    if issue_title.startswith('gomoku|reset'):
        old_id = state.get('game_id', 1)
        state = fresh_state(game_id=old_id + 1)
        comment = '🔄 棋盘已重置，黑方先行。'
        should_commit = True
        commit_msg = f'Reset board to game #{state["game_id"]} [skip ci]'

    # ---- 落子 ----
    else:
        match = re.match(r'gomoku\|place\|([A-O])(\d{1,2})$', issue_title)
        if not match:
            issue.create_comment('❌ 无效指令。请通过点击棋盘落子。')
            issue.edit(state='closed')
            write_output(False)
            return

        col = ord(match.group(1)) - ord('A')
        row = int(match.group(2)) - 1
        coord = f'{match.group(1)}{match.group(2)}'

        if not (0 <= row < BOARD_SIZE and 0 <= col < BOARD_SIZE):
            issue.create_comment('❌ 坐标超出棋盘范围。')
            issue.edit(state='closed')
            write_output(False)
            return

        if state['winner']:
            issue.create_comment('❌ 游戏已结束，请先重置棋盘。')
            issue.edit(state='closed')
            write_output(False)
            return

        if state['board'][row][col] != '.':
            issue.create_comment(f'❌ 位置 {coord} 已有棋子。')
            issue.edit(state='closed')
            write_output(False)
            return

        color = state['turn']
        board = [list(r) for r in state['board']]
        board[row][col] = color
        state['board'] = [''.join(r) for r in board]
        state['last_move'] = coord
        state['move_count'] += 1

        stats['moves'].append({
            'game': state.get('game_id', 1),
            'coord': coord,
            'color': color,
            'user': issue_user,
        })

        if check_win(board, row, col, color):
            state['winner'] = color
            comment = f'🏆 {NAME[color]} 落子 {coord}，五子连珠获胜！'
            if not state.get('recorded'):
                stats['games'].append({
                    'id': state.get('game_id', 1),
                    'winner': color,
                    'moves': state['move_count'],
                    'players': sorted({
                        m['user'] for m in stats['moves']
                        if m.get('game') == state.get('game_id', 1)
                    }),
                })
                state['recorded'] = True
        else:
            state['turn'] = 'W' if color == 'B' else 'B'
            comment = f'✅ {NAME[color]} 落子 {coord}，轮到 {NAME[state["turn"]]}。'

        should_commit = True
        commit_msg = f'Move {coord} by {issue_user} [skip ci]'

    # ---- 写回本地文件 ----
    save_json(STATE_FILE, state)
    save_json(STATS_FILE, stats)

    with open(README_FILE, 'w', encoding='utf-8') as f:
        f.write(generate_readme(state, repo_name))

    generate_chart(STATS_FILE, STATE_FILE, CHART_FILE)

    issue.create_comment(comment)
    issue.edit(state='closed')

    write_output(should_commit, commit_msg)


if __name__ == '__main__':
    main()
