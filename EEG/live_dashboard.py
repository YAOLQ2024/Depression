"""
live_dashboard.py
─────────────────
实时 EEG 数据仪表盘，分类时弹出独立窗口显示:
  - 3 通道波形
  - 频段功率柱状图
  - 特征值实时曲线
  - 分类结果时间线

依赖: pip install matplotlib numpy
"""

import threading
import time
import numpy as np
from collections import deque
from typing import Optional

import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import matplotlib.gridspec as gridspec


class LiveDashboard:
    """
    独立线程运行的实时仪表盘。
    主线程通过 push_wave / push_feat / push_pred 喂数据。
    """

    def __init__(self, max_wave_sec: float = 4.0,
                 max_feat_sec: float = 120.0,
                 fs: float = 500.0):
        self.fs = fs
        self.max_wave_pts = int(max_wave_sec * fs)
        self.max_feat_pts = int(max_feat_sec)

        # ---- 波形缓冲 (3 通道) ----
        self.wave_buf = [deque(maxlen=self.max_wave_pts) for _ in range(3)]
        self.wave_seq = 0

        # ---- 特征缓冲 ----
        self.faa_buf   = deque(maxlen=self.max_feat_pts)
        self.apv_buf   = [deque(maxlen=self.max_feat_pts) for _ in range(3)]
        self.beta_buf  = [deque(maxlen=self.max_feat_pts) for _ in range(3)]
        self.hfd_buf   = [deque(maxlen=self.max_feat_pts) for _ in range(3)]
        self.alpha_buf = [deque(maxlen=self.max_feat_pts) for _ in range(3)]
        self.theta_buf = [deque(maxlen=self.max_feat_pts) for _ in range(3)]

        # ---- 最新频段功率 (柱状图用) ----
        self.latest_alpha = [0.0, 0.0, 0.0]
        self.latest_beta  = [0.0, 0.0, 0.0]
        self.latest_theta = [0.0, 0.0, 0.0]

        # ---- 分类结果缓冲 ----
        self.pred_buf  = deque(maxlen=self.max_feat_pts)
        self.prob_buf  = deque(maxlen=self.max_feat_pts)
        self.feat_time = deque(maxlen=self.max_feat_pts)

        self._feat_count = 0
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._running = False

    # ════════════════════════ 数据推入 (线程安全) ════════════════════════

    def push_wave(self, ch0: float, ch1: float, ch2: float):
        with self._lock:
            self.wave_buf[0].append(ch0)
            self.wave_buf[1].append(ch1)
            self.wave_buf[2].append(ch2)
            self.wave_seq += 1

    def push_feat(self, faa: float,
                  apv: list, beta: list, hfd: list,
                  alpha: list, theta: list):
        with self._lock:
            self._feat_count += 1
            self.feat_time.append(self._feat_count)

            self.faa_buf.append(faa)
            for c in range(3):
                self.apv_buf[c].append(apv[c])
                self.beta_buf[c].append(beta[c])
                self.hfd_buf[c].append(hfd[c])
                self.alpha_buf[c].append(alpha[c])
                self.theta_buf[c].append(theta[c])

            self.latest_alpha = list(alpha)
            self.latest_beta  = list(beta)
            self.latest_theta = list(theta)

    def push_pred(self, pred: int, prob_dep: float = 0.5):
        with self._lock:
            self.pred_buf.append(pred)
            self.prob_buf.append(prob_dep)

    # ════════════════════════ 启动/停止 ════════════════════════

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True,
                                        name='Dashboard')
        self._thread.start()

    def stop(self):
        self._running = False

    # ════════════════════════ matplotlib 主循环 ════════════════════════

    def _run(self):
        # ---- 中文字体 ----
        plt.rcParams['font.sans-serif'] = [
            'SimHei',
            'Microsoft YaHei',
            'WenQuanYi Micro Hei',
            'Arial Unicode MS',
            'Noto Sans CJK SC',
            'DejaVu Sans',
        ]
        plt.rcParams['axes.unicode_minus'] = False

        plt.ion()

        fig = plt.figure(figsize=(14, 9))
        fig.canvas.manager.set_window_title('EEG 情绪评估 - 实时仪表盘')
        fig.patch.set_facecolor('#1a1a2e')

        gs = gridspec.GridSpec(4, 3, figure=fig,
                               hspace=0.45, wspace=0.35,
                               left=0.07, right=0.97,
                               top=0.94, bottom=0.06)

        # ---- 配色 ----
        style = {
            'text':      '#e0e0e0',
            'grid':      '#333355',
            'bg':        '#16213e',
            'ch_colors': ['#00d2ff', '#00ff88', '#ffaa00'],
            'dep_color': '#ff4444',
            'nor_color': '#44ff44',
        }

        def style_ax(ax, title=''):
            ax.set_facecolor(style['bg'])
            ax.tick_params(colors=style['text'], labelsize=7)
            ax.set_title(title, color=style['text'], fontsize=9, pad=4)
            for spine in ax.spines.values():
                spine.set_color(style['grid'])
            ax.grid(True, alpha=0.2, color=style['grid'])

        # ═══════════════ 行1: 3通道波形 ═══════════════
        ax_wave = [fig.add_subplot(gs[0, c]) for c in range(3)]
        ch_names = ['F3 (左)', 'F4 (右)', 'Fpz (中)']
        wave_lines = []
        for c in range(3):
            style_ax(ax_wave[c], ch_names[c])
            ax_wave[c].set_ylabel('μV', color=style['text'], fontsize=7)
            ln, = ax_wave[c].plot([], [], color=style['ch_colors'][c],
                                   linewidth=0.5)
            wave_lines.append(ln)
            ax_wave[c].set_ylim(-100, 100)

        # ═══════════════ 行2左: 频段功率柱状图 ═══════════════
        ax_bar = fig.add_subplot(gs[1, 0])
        style_ax(ax_bar, '频段功率')

        # ═══════════════ 行2中: FAA 曲线 ═══════════════
        ax_faa = fig.add_subplot(gs[1, 1])
        style_ax(ax_faa, 'FAA (α不对称)')
        ln_faa, = ax_faa.plot([], [], color='#ff6b6b', linewidth=1.2)
        ax_faa.axhline(y=0, color=style['text'], linewidth=0.5, alpha=0.3)

        # ═══════════════ 行2右: HFD 曲线 ═══════════════
        ax_hfd = fig.add_subplot(gs[1, 2])
        style_ax(ax_hfd, 'HFD (分形维数)')
        ln_hfd = []
        for c in range(3):
            ln, = ax_hfd.plot([], [], color=style['ch_colors'][c],
                               linewidth=1, label=ch_names[c])
            ln_hfd.append(ln)
        ax_hfd.legend(fontsize=6, loc='upper right',
                      facecolor=style['bg'], edgecolor=style['grid'],
                      labelcolor=style['text'])

        # ═══════════════ 行3左: α功率 ═══════════════
        ax_alpha = fig.add_subplot(gs[2, 0])
        style_ax(ax_alpha, 'α 功率')
        ln_alpha = []
        for c in range(3):
            ln, = ax_alpha.plot([], [], color=style['ch_colors'][c],
                                 linewidth=1)
            ln_alpha.append(ln)

        # ═══════════════ 行3中: β功率 ═══════════════
        ax_beta = fig.add_subplot(gs[2, 1])
        style_ax(ax_beta, 'β 功率')
        ln_beta = []
        for c in range(3):
            ln, = ax_beta.plot([], [], color=style['ch_colors'][c],
                                linewidth=1)
            ln_beta.append(ln)

        # ═══════════════ 行3右: APV ═══════════════
        ax_apv = fig.add_subplot(gs[2, 2])
        style_ax(ax_apv, 'APV (α变异系数)')
        ln_apv = []
        for c in range(3):
            ln, = ax_apv.plot([], [], color=style['ch_colors'][c],
                               linewidth=1)
            ln_apv.append(ln)

        # ═══════════════ 行4: 分类结果 (跨3列) ═══════════════
        ax_pred = fig.add_subplot(gs[3, :])
        style_ax(ax_pred, '分类结果')
        ax_pred.set_ylabel('P(悲伤)', color=style['text'], fontsize=8)
        ax_pred.set_xlabel('时间 (s)', color=style['text'], fontsize=8)
        ln_prob, = ax_pred.plot([], [], color='#ffa502', linewidth=1.5)
        ax_pred.axhline(y=0.5, color='#ff4444', linewidth=1,
                        linestyle='--', alpha=0.5)
        ax_pred.set_ylim(-0.05, 1.05)

        # 分类结果文字
        result_text = ax_pred.text(
            0.5, 0.85, '',
            transform=ax_pred.transAxes,
            fontsize=14, ha='center',
            color=style['text'],
            fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.3',
                      facecolor=style['bg'],
                      edgecolor=style['grid'])
        )

        # ═══════════════ 更新函数 ═══════════════

        def update(frame):
            with self._lock:
                # ---- 波形 ----
                for c in range(3):
                    data = list(self.wave_buf[c])
                    if data:
                        x = np.arange(len(data)) / self.fs
                        wave_lines[c].set_data(x, data)
                        ax_wave[c].set_xlim(0, max(x[-1], 0.1))
                        if len(data) > 10:
                            recent = data[-2000:] if len(data) > 2000 else data
                            ymin = min(recent)
                            ymax = max(recent)
                            margin = max(abs(ymax - ymin) * 0.1, 5)
                            ax_wave[c].set_ylim(ymin - margin, ymax + margin)

                # ---- 频段柱状图 ----
                ax_bar.clear()
                style_ax(ax_bar, '频段功率')
                x_pos = np.arange(3)
                width = 0.25
                a_vals = self.latest_alpha
                b_vals = self.latest_beta
                t_vals = self.latest_theta

                if any(v != 0 for v in a_vals + b_vals + t_vals):
                    bars_theta = ax_bar.bar(
                        x_pos - width, t_vals, width,
                        color='#a29bfe', label='θ'
                    )
                    bars_alpha = ax_bar.bar(
                        x_pos, a_vals, width,
                        color='#00d2ff', label='α'
                    )
                    bars_beta = ax_bar.bar(
                        x_pos + width, b_vals, width,
                        color='#ff6b6b', label='β'
                    )
                    ax_bar.set_xticks(x_pos)
                    ax_bar.set_xticklabels(
                        ['F3', 'F4', 'Fpz'],
                        color=style['text'], fontsize=7
                    )
                    ax_bar.legend(
                        fontsize=6, loc='upper right',
                        facecolor=style['bg'],
                        edgecolor=style['grid'],
                        labelcolor=style['text']
                    )

                # ---- 特征曲线 ----
                t = list(self.feat_time)
                if t:
                    t_start = t[0]
                    t_end = t[-1] + 1

                    # FAA
                    faa_data = list(self.faa_buf)
                    ln_faa.set_data(t, faa_data)
                    ax_faa.set_xlim(t_start, t_end)
                    if faa_data:
                        mn = min(faa_data)
                        mx = max(faa_data)
                        mg = max(abs(mx - mn) * 0.15, 0.1)
                        ax_faa.set_ylim(mn - mg, mx + mg)

                    # HFD
                    for c in range(3):
                        d = list(self.hfd_buf[c])
                        ln_hfd[c].set_data(t[:len(d)], d)
                    ax_hfd.set_xlim(t_start, t_end)
                    all_hfd = []
                    for c in range(3):
                        all_hfd.extend(list(self.hfd_buf[c]))
                    if all_hfd:
                        hfd_min = min(all_hfd)
                        hfd_max = max(all_hfd)
                        hfd_mg = max((hfd_max - hfd_min) * 0.15, 0.01)
                        ax_hfd.set_ylim(hfd_min - hfd_mg, hfd_max + hfd_mg)

                    # α功率
                    for c in range(3):
                        d = list(self.alpha_buf[c])
                        ln_alpha[c].set_data(t[:len(d)], d)
                    ax_alpha.set_xlim(t_start, t_end)
                    all_a = []
                    for c in range(3):
                        all_a.extend(list(self.alpha_buf[c]))
                    if all_a:
                        ax_alpha.set_ylim(0, max(all_a) * 1.2 + 0.001)

                    # β功率
                    for c in range(3):
                        d = list(self.beta_buf[c])
                        ln_beta[c].set_data(t[:len(d)], d)
                    ax_beta.set_xlim(t_start, t_end)
                    all_b = []
                    for c in range(3):
                        all_b.extend(list(self.beta_buf[c]))
                    if all_b:
                        ax_beta.set_ylim(0, max(all_b) * 1.2 + 0.001)

                    # APV
                    for c in range(3):
                        d = list(self.apv_buf[c])
                        ln_apv[c].set_data(t[:len(d)], d)
                    ax_apv.set_xlim(t_start, t_end)
                    all_apv = []
                    for c in range(3):
                        all_apv.extend(list(self.apv_buf[c]))
                    if all_apv:
                        ax_apv.set_ylim(0, max(all_apv) * 1.2 + 0.01)

                # ---- 分类结果 ----
                prob_data = list(self.prob_buf)
                pred_data = list(self.pred_buf)

                if prob_data and t:
                    # 时间轴对齐 (prob 可能比 feat_time 少)
                    tp = t[-len(prob_data):]
                    ln_prob.set_data(tp, prob_data)
                    ax_pred.set_xlim(tp[0], tp[-1] + 1)

                    # 清除旧的背景色带
                    while ax_pred.collections:
                        ax_pred.collections[0].remove()

                    tp_arr = np.array(tp)
                    prob_arr = np.array(prob_data)

                    # 红色背景 = P(悲伤) > 0.5
                    ax_pred.fill_between(
                        tp_arr, 0, 1,
                        where=(prob_arr > 0.5),
                        alpha=0.1,
                        color=style['dep_color']
                    )
                    # 绿色背景 = P(悲伤) <= 0.5
                    ax_pred.fill_between(
                        tp_arr, 0, 1,
                        where=(prob_arr <= 0.5),
                        alpha=0.1,
                        color=style['nor_color']
                    )

                    # 结果文字
                    recent = pred_data[-30:] if len(pred_data) >= 30 else pred_data
                    if recent:
                        dep_pct = sum(recent) / len(recent) * 100
                        if dep_pct > 50:
                            result_text.set_text(
                                f'悲伤倾向 ({dep_pct:.0f}%)')
                            result_text.set_color(style['dep_color'])
                        else:
                            result_text.set_text(
                                f'正常 ({100-dep_pct:.0f}%)')
                            result_text.set_color(style['nor_color'])

            return []

        # ---- 启动动画 ----
        ani = FuncAnimation(
            fig, update,
            interval=500,
            blit=False,
            cache_frame_data=False
        )

        plt.show(block=True)
        self._running = False


# ════════════════════════ 快速测试 ════════════════════════
if __name__ == '__main__':
    print('仪表盘测试模式 — 模拟数据')
    print('按 Ctrl+C 退出\n')

    dash = LiveDashboard()
    dash.start()

    t = 0
    feat_t = 0

    try:
        while True:
            # 模拟波形 (每 0.1s 推 50 个点 = 500 Hz)
            for _ in range(50):
                dash.push_wave(
                    np.sin(t * 10) * 30 + np.random.randn() * 5,
                    np.sin(t * 10 + 1) * 25 + np.random.randn() * 5,
                    np.sin(t * 10 + 2) * 20 + np.random.randn() * 5,
                )
                t += 1 / 500

            # 每秒推一次特征
            feat_t += 0.1
            if feat_t >= 1.0:
                feat_t = 0

                dash.push_feat(
                    faa=np.sin(t * 0.1) * 0.3 + np.random.randn() * 0.05,
                    apv=[0.2 + np.random.rand() * 0.1 for _ in range(3)],
                    beta=[np.random.rand() * 5 + 1 for _ in range(3)],
                    hfd=[1.05 + np.random.rand() * 0.1 for _ in range(3)],
                    alpha=[np.random.rand() * 10 + 2 for _ in range(3)],
                    theta=[np.random.rand() * 8 + 1 for _ in range(3)],
                )

                # 模拟分类
                pred = 1 if np.random.rand() > 0.7 else 0
                prob = 0.3 + np.random.rand() * 0.5
                dash.push_pred(pred, prob)

            time.sleep(0.1)

    except KeyboardInterrupt:
        dash.stop()
        print('\n测试结束')
