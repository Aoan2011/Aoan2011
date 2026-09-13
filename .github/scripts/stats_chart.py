import json
import os
from collections import Counter

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap

plt.rcParams['font.sans-serif'] = [
    'Noto Sans CJK SC', 'WenQuanYi Zen Hei', 'DejaVu Sans'
]
plt.rcParams['axes.unicode_minus'] = False

# 霓虹色板
BG      = '#0a0e14'
PANEL   = '#0d1420'
NEON    = '#00F0FF'
MAGENTA = '#FF00AA'
GREEN   = '#39FF14'
PURPLE  = '#BD00FF'
TEXT    = '#c9d1d9'
GRID    = '#1f2937'

BOARD_SIZE = 15


def _style_ax(ax, title):
    ax.set_facecolor(PANEL)
    ax.set_title(title, color=NEON, fontsize=12, fontweight='bold', pad=10)
    ax.tick_params(colors=TEXT, labelsize=9)
    for spine in ax.spines.values():
        spine.set_color(GRID)
    ax.grid(True, color=GRID, linestyle=':', linewidth=0.6, alpha=0.5)


def _load(path):
    if os.path.exists(path):
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    return {}


def generate_chart(stats_path='stats.json',
                   state_path='state.json',
                   out_path='assets/stats.png'):
    stats = _load(stats_path) or {"games": [], "moves": []}
    games = stats.get('games', [])
    moves = stats.get('moves', [])

    black_wins = sum(1 for g in games if g.get('winner') == 'B')
    white_wins = sum(1 for g in games if g.get('winner') == 'W')

    fig, axes = plt.subplots(2, 2, figsize=(13, 9))
    fig.patch.set_facecolor(BG)
    fig.suptitle(
        f'◤ TELEMETRY ◢   GAMES: {len(games)}   MOVES: {len(moves)}',
        fontsize=16, fontweight='bold', color=NEON, y=0.98
    )

    # ---- 1. 胜负分布 ----
    ax = axes[0][0]
    _style_ax(ax, '◈ WIN RATE')
    ax.grid(False)
    if black_wins + white_wins > 0:
        labels, sizes, colors = [], [], []
        if black_wins:
            labels.append('黑方胜'); sizes.append(black_wins); colors.append(NEON)
        if white_wins:
            labels.append('白方胜'); sizes.append(white_wins); colors.append(MAGENTA)
        wedges, texts, autotexts = ax.pie(
            sizes, labels=labels, autopct='%1.0f%%',
            colors=colors, startangle=90,
            wedgeprops={'edgecolor': BG, 'linewidth': 2},
            textprops={'color': TEXT, 'fontsize': 10}
        )
        for at in autotexts:
            at.set_color(BG)
            at.set_fontweight('bold')
    else:
        ax.text(0.5, 0.5, 'NO DATA', ha='center', va='center',
                color=NEON, fontsize=14, family='monospace')
        ax.axis('off')

    # ---- 2. 每局步数 ----
    ax = axes[0][1]
    _style_ax(ax, '◈ MOVES PER GAME')
    if games:
        x = list(range(1, len(games) + 1))
        y = [g.get('moves', 0) for g in games]
        ax.bar(x, y, color=NEON, alpha=0.15, width=0.7)
        ax.bar(x, y, color=NEON, alpha=0.9, width=0.45,
               edgecolor=NEON, linewidth=1)
        ax.set_xlabel('GAME #', color=TEXT, fontsize=9)
        ax.set_ylabel('MOVES', color=TEXT, fontsize=9)
        ax.set_xticks(x)
        for xi, yi in zip(x, y):
            ax.text(xi, yi + 0.3, str(yi), ha='center', va='bottom',
                    color=GREEN, fontsize=9, family='monospace')
    else:
        ax.text(0.5, 0.5, 'NO DATA', ha='center', va='center',
                color=NEON, fontsize=14, family='monospace')
        ax.axis('off')

    # ---- 3. 玩家排行 ----
    ax = axes[1][0]
    _style_ax(ax, '◈ TOP OPERATORS')
    user_counter = Counter(m['user'] for m in moves if m.get('user'))
    if user_counter:
        top = user_counter.most_common(8)[::-1]
        names = [u for u, _ in top]
        vals = [c for _, c in top]
        colors = plt.cm.cool(np.linspace(0.3, 0.9, len(vals)))
        ax.barh(names, vals, color=colors, edgecolor=NEON, linewidth=0.8)
        ax.set_xlabel('MOVES', color=TEXT, fontsize=9)
        for i, v in enumerate(vals):
            ax.text(v + 0.1, i, str(v), va='center',
                    color=GREEN, fontsize=9, family='monospace')
    else:
        ax.text(0.5, 0.5, 'NO DATA', ha='center', va='center',
                color=NEON, fontsize=14, family='monospace')
        ax.axis('off')

    # ---- 4. 落子热力图 ----
    ax = axes[1][1]
    _style_ax(ax, '◈ MOVE HEATMAP')
    ax.grid(False)
    heat = np.zeros((BOARD_SIZE, BOARD_SIZE))
    for m in moves:
        coord = m.get('coord', '')
        if len(coord) >= 2 and coord[0].isalpha():
            col = ord(coord[0].upper()) - ord('A')
            try:
                row = int(coord[1:]) - 1
            except ValueError:
                continue
            if 0 <= row < BOARD_SIZE and 0 <= col < BOARD_SIZE:
                heat[row][col] += 1
    if heat.sum() > 0:
        cmap = LinearSegmentedColormap.from_list(
            'neon', [BG, PURPLE, NEON, '#ffffff']
        )
        im = ax.imshow(heat, cmap=cmap, origin='upper')
        ax.set_xticks(range(BOARD_SIZE))
        ax.set_xticklabels([chr(ord('A') + i) for i in range(BOARD_SIZE)],
                           fontsize=7, color=TEXT)
        ax.set_yticks(range(BOARD_SIZE))
        ax.set_yticklabels(range(1, BOARD_SIZE + 1), fontsize=7, color=TEXT)
        cbar = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        cbar.ax.yaxis.set_tick_params(color=TEXT)
        plt.setp(plt.getp(cbar.ax.axes, 'yticklabels'), color=TEXT)
        cbar.outline.set_edgecolor(GRID)
    else:
        ax.text(0.5, 0.5, 'NO DATA', ha='center', va='center',
                color=NEON, fontsize=14, family='monospace')
        ax.axis('off')

    plt.tight_layout(rect=[0, 0, 1, 0.95])
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    plt.savefig(out_path, dpi=130, bbox_inches='tight', facecolor=BG)
    plt.close(fig)
    print(f'图表已生成：{out_path}')
