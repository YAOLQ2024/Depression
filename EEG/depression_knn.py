"""
depression_knn.py  (v10)
情绪 EEG 评估系统
- 7 维无量纲特征 (FAA + APV×3 + HFD×3)
- 不受硬件增益影响
"""

import os, sys, csv, time, pickle, argparse, math
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple, Optional

from sklearn.neighbors import KNeighborsClassifier
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import LeaveOneOut, StratifiedShuffleSplit
from sklearn.metrics import accuracy_score, confusion_matrix
from sklearn.base import clone as sklearn_clone

from eeg_serial import (FeaturePacket, WavePacket, NUM_CH,
                         RAW_FEAT_NAMES)

from ble_receiver import BLEEEGReceiver, scan_and_select

# ══════════════════════════════════════════════════════════
#  常量
# ══════════════════════════════════════════════════════════
SKIP_SEC = 30

GA_POP          = 60
GA_GENERATIONS  = 80
GA_CX_RATE      = 0.75
GA_MUT_RATE     = 0.08
GA_TOURNAMENT_K = 3
GA_ELITISM      = 2
KNN_K_CANDIDATES = [1, 3, 5, 7, 9]

# 7 维无量纲特征
SCALE_FREE_NAMES = [
    'FAA',
    'APV_ch0', 'APV_ch1', 'APV_ch2',
    'HFD_ch0', 'HFD_ch1', 'HFD_ch2',
]

FEAT_NAMES = []
N_FEAT     = 0


# ══════════════════════════════════════════════════════════
#  从 FeaturePacket 提取 7 维向量
# ══════════════════════════════════════════════════════════

def fp_to_vec(fp):
    """7 维无量纲特征，不受硬件增益影响"""
    return ([fp.FAA]
            + list(fp.APV)
            + list(fp.HFD))


# ══════════════════════════════════════════════════════════
#  MODE 1: BLE 采集
# ══════════════════════════════════════════════════════════

def cmd_collect(args):
    out_dir = Path(args.data_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    csv_path = out_dir / f'{args.subject}_label{args.label}_{ts}.csv'

    use_names = SCALE_FREE_NAMES
    header = ['timestamp', 'subject', 'label'] + use_names
    rows_written = 0

    f_csv = open(csv_path, 'w', newline='')
    writer = csv.writer(f_csv)
    writer.writerow(header)

    start_time = [None]
    done = [False]

    def on_feat(fp):
        nonlocal rows_written
        if done[0]:
            return
        if start_time[0] is None:
            start_time[0] = time.time()
            print(f'[采集] 开始, 前 {SKIP_SEC}s 为稳定期')

        elapsed = time.time() - start_time[0]

        if elapsed < SKIP_SEC:
            print(f'\r  稳定期 {elapsed:.0f}/{SKIP_SEC}s ...',
                  end='', flush=True)
            return

        if elapsed >= args.duration + SKIP_SEC:
            done[0] = True
            return

        vec = fp_to_vec(fp)

        if any(math.isnan(v) or math.isinf(v) for v in vec):
            return
        if all(v == 0.0 for v in vec):
            return

        writer.writerow([f'{fp.timestamp:.3f}', args.subject, args.label]
                        + [f'{v:.8g}' for v in vec])
        rows_written += 1
        eff = elapsed - SKIP_SEC
        print(f'\r  有效采集 {eff:.0f}/{args.duration}s  帧数={rows_written}',
              end='', flush=True)

    address = args.address
    if not address:
        address = scan_and_select()
        if not address:
            print('[采集] 未选择设备')
            f_csv.close()
            return

    rx = BLEEEGReceiver(address, on_feat=on_feat)
    rx.start()
    print(f'[采集] 被试={args.subject} 标签={args.label} 时长={args.duration}s')
    print(f'[采集] BLE={address}')
    print(f'[采集] 特征: 7维无量纲 (FAA+APV+HFD)')
    print(f'[采集] → {csv_path}')

    try:
        while not done[0]:
            time.sleep(0.5)
    except KeyboardInterrupt:
        print('\n[采集] 中断')
    finally:
        rx.stop()
        f_csv.close()

    print(f'\n[采集] 完成! {rows_written} 帧 → {csv_path}')


# ══════════════════════════════════════════════════════════
#  数据加载
# ══════════════════════════════════════════════════════════

def load_dataset(data_dir):
    data_dir = Path(data_dir)
    csvs = sorted(data_dir.glob('*.csv'))
    if not csvs:
        raise FileNotFoundError(f'在 {data_dir} 中没有找到 CSV')

    with open(csvs[0], 'r') as f:
        available_cols = list(csv.DictReader(f).fieldnames)

    feat_cols = [fn for fn in SCALE_FREE_NAMES if fn in available_cols]
    print(f'[数据集] 使用 {len(feat_cols)} 维无量纲特征: {feat_cols}')

    subjects = {}
    for csv_path in csvs:
        with open(csv_path, 'r') as f:
            for row in csv.DictReader(f):
                sid = row['subject']
                label = int(row['label'])
                vec = [float(row.get(fn, 0)) for fn in feat_cols]
                if sid not in subjects:
                    subjects[sid] = {'label': label, 'vectors': []}
                subjects[sid]['vectors'].append(vec)

    sids = sorted(subjects.keys())
    X_list, y_list = [], []
    for sid in sids:
        vecs = np.array(subjects[sid]['vectors'])
        label = subjects[sid]['label']
        med = np.median(vecs, axis=0)
        X_list.append(med)
        y_list.append(label)
        hi = feat_cols.index('HFD_ch0') if 'HFD_ch0' in feat_cols else 0
        print(f'  {sid}: label={label}, 帧={len(vecs)}, HFD_ch0={med[hi]:.4f}')

    X = np.array(X_list)
    y = np.array(y_list)
    print(f'[数据集] {len(sids)} 人 (正常={np.sum(y==0)}, '
          f'悲伤={np.sum(y==1)}), {X.shape[1]}维')
    return X, y, sids, feat_cols


# ══════════════════════════════════════════════════════════
#  GA 特征选择
# ══════════════════════════════════════════════════════════

def loocv_accuracy(X, y, clf):
    loo = LeaveOneOut()
    correct = 0
    for tri, tei in loo.split(X):
        c = sklearn_clone(clf)
        c.fit(X[tri], y[tri])
        if c.predict(X[tei]) == y[tei]:
            correct += 1
    return correct / len(y)


def _tournament_select(pop, fitness, k, rng):
    idx = rng.choice(len(pop), size=k, replace=False)
    return pop[idx[np.argmax(fitness[idx])]].copy()


def _ga_silent(Xtr, ytr, clf, n_gen=50, pop_size=50):
    nf = Xtr.shape[1]
    rng = np.random.default_rng(42)
    pop = rng.integers(0, 2, size=(pop_size, nf)).astype(np.int8)
    for i in range(pop_size):
        if pop[i].sum() == 0:
            pop[i, rng.integers(0, nf)] = 1

    best_fitness = 0.0
    best_chrom = pop[0].copy()
    fitness = np.zeros(pop_size)

    for gen in range(n_gen):
        for i in range(pop_size):
            sel = np.where(pop[i] == 1)[0]
            if len(sel) == 0:
                fitness[i] = 0
                continue
            fitness[i] = loocv_accuracy(
                StandardScaler().fit_transform(Xtr[:, sel]), ytr, clf)

        idx_best = np.argmax(fitness)
        if fitness[idx_best] > best_fitness:
            best_fitness = fitness[idx_best]
            best_chrom = pop[idx_best].copy()

        elite_idx = np.argsort(fitness)[-GA_ELITISM:]
        new_pop = [pop[i].copy() for i in elite_idx]

        while len(new_pop) < pop_size:
            p1 = _tournament_select(pop, fitness, GA_TOURNAMENT_K, rng)
            p2 = _tournament_select(pop, fitness, GA_TOURNAMENT_K, rng)
            if rng.random() < GA_CX_RATE:
                pt = rng.integers(1, nf)
                c1 = np.concatenate([p1[:pt], p2[pt:]])
                c2 = np.concatenate([p2[:pt], p1[pt:]])
            else:
                c1, c2 = p1.copy(), p2.copy()
            for c in [c1, c2]:
                mask = rng.random(nf) < GA_MUT_RATE
                c[mask] = 1 - c[mask]
                if c.sum() == 0:
                    c[rng.integers(0, nf)] = 1
            new_pop.append(c1)
            if len(new_pop) < pop_size:
                new_pop.append(c2)

        pop = np.array(new_pop[:pop_size])

    return best_chrom.astype(bool), best_fitness


# ══════════════════════════════════════════════════════════
#  MODE 2: 训练
# ══════════════════════════════════════════════════════════

def cmd_train(args):
    print('=' * 60)
    print(' 模型训练 (7维无量纲特征)')
    print('=' * 60)

    X, y, sids, fn = load_dataset(args.data_dir)
    if len(y) < 6:
        print('[错误] 被试太少')
        return

    global FEAT_NAMES, N_FEAT
    FEAT_NAMES = fn
    N_FEAT = len(fn)

    ns = 30
    print(f'\n[评估] {ns} 次划分')

    ar = {n: [] for n in ['KNN', 'LDA', 'LR']}
    sss = StratifiedShuffleSplit(n_splits=ns, test_size=1/3,
                                 random_state=args.seed)

    for si, (tri, tei) in enumerate(sss.split(X, y)):
        Xtr, ytr = X[tri], y[tri]
        Xte, yte = X[tei], y[tei]

        st = StandardScaler()
        Xts = st.fit_transform(Xtr)
        bk, ba, bw = 5, 0.0, 'distance'
        for k in KNN_K_CANDIDATES:
            if k >= len(Xtr):
                continue
            for w in ['uniform', 'distance']:
                a = loocv_accuracy(
                    Xts, ytr,
                    KNeighborsClassifier(n_neighbors=k, weights=w))
                if a > ba:
                    bk, ba, bw = k, a, w

        clfs = {
            'KNN': KNeighborsClassifier(n_neighbors=bk, weights=bw),
            'LDA': LinearDiscriminantAnalysis(),
            'LR': LogisticRegression(max_iter=1000, solver='lbfgs'),
        }

        for nm, cl in clfs.items():
            sm, ga = _ga_silent(Xtr, ytr, cl)
            si2 = np.where(sm)[0]
            if len(si2) == 0:
                si2 = np.arange(Xtr.shape[1])
            sc = StandardScaler()
            Xtrs = sc.fit_transform(Xtr[:, si2])
            Xtes = sc.transform(Xte[:, si2])
            fc = sklearn_clone(cl)
            fc.fit(Xtrs, ytr)
            yp = fc.predict(Xtes)
            ac = accuracy_score(yte, yp)
            cm = confusion_matrix(yte, yp, labels=[0, 1])
            sn = cm[1, 1] / (cm[1, 0] + cm[1, 1] + 1e-9)
            sp = cm[0, 0] / (cm[0, 0] + cm[0, 1] + 1e-9)
            ar[nm].append({
                'acc': ac, 'sens': sn, 'spec': sp,
                'sel_idx': si2, 'scaler': sc,
                'model': fc, 'cm': cm,
                'ga_loocv': ga,
            })

        print(f'\r  划分 {si+1}/{ns}  '
              f'KNN={ar["KNN"][-1]["acc"]*100:.0f}%  '
              f'LDA={ar["LDA"][-1]["acc"]*100:.0f}%  '
              f'LR={ar["LR"][-1]["acc"]*100:.0f}%',
              end='', flush=True)

    print(f'\n\n{"═" * 60}')
    print(f' 结果汇总')
    print(f'{"═" * 60}')

    bcn = None
    bma = 0.0
    for nm in ['KNN', 'LDA', 'LR']:
        ac = [r['acc'] for r in ar[nm]]
        sn = [r['sens'] for r in ar[nm]]
        sp = [r['spec'] for r in ar[nm]]
        ma = np.mean(ac)
        if ma > bma:
            bma = ma
            bcn = nm
        print(f'\n  {nm}: {ma*100:.1f}% ± {np.std(ac)*100:.1f}%  '
              f'(min={np.min(ac)*100:.0f}%, max={np.max(ac)*100:.0f}%)')
        print(f'    灵敏度: {np.mean(sn)*100:.1f}% ± {np.std(sn)*100:.1f}%')
        print(f'    特异度: {np.mean(sp)*100:.1f}% ± {np.std(sp)*100:.1f}%')

    svn = args.classifier if args.classifier else bcn
    rl = ar[svn]
    br = max(rl, key=lambda r: r['acc'])
    sfn = [fn[i] for i in br['sel_idx']]

    print(f'\n{"═" * 60}')
    print(f' 最优: {svn} 平均={np.mean([r["acc"] for r in rl])*100:.1f}%')
    print(f' 最佳单次: {br["acc"]*100:.1f}%  特征: {sfn}')

    cm = br['cm']
    print(f'  混淆矩阵:')
    print(f'              预测正常  预测悲伤')
    print(f'  实际正常:    {cm[0,0]:4d}     {cm[0,1]:4d}')
    print(f'  实际悲伤:    {cm[1,0]:4d}     {cm[1,1]:4d}')

    train_stats = {}
    for i, name in enumerate(fn):
        col = X[:, i]
        train_stats[name] = {
            'mean': float(np.mean(col)),
            'std': float(np.std(col)),
            'min': float(np.min(col)),
            'max': float(np.max(col)),
            'median': float(np.median(col)),
        }

    so = {
        'classifier_name': svn,
        'model': br['model'],
        'scaler': br['scaler'],
        'selected_features': br['sel_idx'],
        'feature_names': sfn,
        'all_feature_names': fn,
        'test_accuracy': br['acc'],
        'mean_accuracy': np.mean([r['acc'] for r in rl]),
        'std_accuracy': np.std([r['acc'] for r in rl]),
        'n_splits': ns,
        'train_stats': train_stats,
    }
    with open(args.output, 'wb') as f:
        pickle.dump(so, f)
    print(f'\n 模型已保存 → {args.output}')

    print(f'\n{"─" * 60}')
    print(f' 训练数据特征范围:')
    print(f'{"─" * 60}')
    print(f'  {"特征":<20} {"中位数":>10} {"均值":>10} {"最小":>10} {"最大":>10}')
    for name in fn:
        s = train_stats[name]
        print(f'  {name:<20} {s["median"]:>10.4f} {s["mean"]:>10.4f} '
              f'{s["min"]:>10.4f} {s["max"]:>10.4f}')
# ══════════════════════════════════════════════════════════
#  报告生成
# ══════════════════════════════════════════════════════════

def _write_single_report(path, num, addr, clf_name, mobj,
                          feat_ns, all_fn, sel_idx, window,
                          n_frames, median_vec, pred,
                          prob_nor, prob_dep, raw_log,
                          train_stats):
    result_str = '悲伤倾向' if pred == 1 else '正常'

    with open(path, 'w', encoding='utf-8') as f:
        f.write('=' * 50 + '\n')
        f.write(f'  情绪症 EEG 评估报告 #{num}\n')
        f.write('=' * 50 + '\n\n')

        f.write(f'  时间:   {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n')
        f.write(f'  设备:   {addr}\n')
        f.write(f'  模型:   {clf_name} '
                f'(准确率{mobj.get("mean_accuracy",0)*100:.1f}%'
                f'±{mobj.get("std_accuracy",0)*100:.1f}%)\n')
        f.write(f'  采集窗: {window}s\n')
        f.write(f'  有效帧: {n_frames}\n')
        f.write(f'  特征:   7维无量纲 (FAA+APV+HFD)\n\n')

        f.write('-' * 50 + '\n')
        f.write(f'  评估结果: {result_str}\n')
        f.write(f'  P(正常):  {prob_nor:.4f}\n')
        f.write(f'  P(悲伤):  {prob_dep:.4f}\n')
        f.write('-' * 50 + '\n\n')

        f.write('  分类依据 (设备值 vs 训练数据):\n')
        f.write(f'    {"特征":<20} {"设备值":>10} {"训练中位":>10} {"训练范围"}\n')
        for idx in sel_idx:
            if idx < len(all_fn) and idx < len(median_vec):
                name = all_fn[idx]
                val = median_vec[idx]
                if train_stats and name in train_stats:
                    ts = train_stats[name]
                    f.write(f'    {name:<20} {val:>10.4f} {ts["median"]:>10.4f} '
                            f'[{ts["min"]:.4f}, {ts["max"]:.4f}]\n')
                else:
                    f.write(f'    {name:<20} {val:>10.4f}\n')

        f.write(f'\n  全部特征中位数:\n')
        for i in range(min(len(all_fn), len(median_vec))):
            f.write(f'    {all_fn[i]:<20} {median_vec[i]:>12.6f}\n')

        if raw_log:
            f.write(f'\n  逐秒数据:\n')
            f.write(f'    {"秒":<6}')
            for idx in sel_idx:
                if idx < len(all_fn):
                    short = all_fn[idx][:10]
                    f.write(f' {short:>12}')
            f.write('\n')

            for entry in raw_log:
                f.write(f'    {entry["sec"]:<6}')
                for idx in sel_idx:
                    if idx < len(all_fn):
                        key = all_fn[idx]
                        val = entry['features'].get(key, '0')
                        f.write(f' {float(val):>12.4f}')
                f.write('\n')

        f.write('\n' + '=' * 50 + '\n')
        f.write('  声明: 仅供参考，不构成医学诊断。\n')
        f.write('=' * 50 + '\n')


# ══════════════════════════════════════════════════════════
#  MODE 3: 实时分类
# ══════════════════════════════════════════════════════════

def cmd_classify(args):
    with open(args.model, 'rb') as f:
        mobj = pickle.load(f)

    clf = mobj['model']
    scaler = mobj['scaler']
    sel_idx = mobj['selected_features']
    feat_ns = mobj['feature_names']
    clf_name = mobj['classifier_name']
    all_fn = mobj.get('all_feature_names', SCALE_FREE_NAMES)
    train_stats = mobj.get('train_stats', {})

    print(f'[分类] 模型: {clf_name}')
    print(f'  准确率: {mobj.get("mean_accuracy",0)*100:.1f}% '
          f'± {mobj.get("std_accuracy",0)*100:.1f}%')
    print(f'  特征: {feat_ns}')
    print(f'  7维无量纲 (FAA+APV+HFD)')
    print(f'  每 {args.window}s → 一次分类 → 一份报告')

    if train_stats:
        print(f'\n  训练数据特征范围:')
        print(f'  {"特征":<20} {"中位数":>10} {"最小":>10} {"最大":>10}')
        for name in feat_ns:
            if name in train_stats:
                s = train_stats[name]
                print(f'  {name:<20} {s["median"]:>10.4f} '
                      f'{s["min"]:>10.4f} {s["max"]:>10.4f}')
        print()

    rdir = Path('reports')
    rdir.mkdir(exist_ok=True)
    sess_ts = datetime.now().strftime('%Y%m%d_%H%M%S')

    address = args.address
    if not address:
        address = scan_and_select()
        if not address:
            print('[分类] 未选择设备')
            return

    dashboard = None
    if not args.no_gui:
        try:
            from live_dashboard import LiveDashboard
            dashboard = LiveDashboard()
            dashboard.start()
            print('[分类] 仪表盘已启动')
        except Exception as e:
            print(f'[分类] 仪表盘启动失败: {e}')
            dashboard = None

    round_feat_vecs = []
    round_raw_log = []
    start_time = [None]
    round_start = [None]
    round_sec = [0]
    debug_count = [0]

    report_count = [0]
    all_reports = []
    all_preds = []

    def on_wave(wp):
        if dashboard:
            dashboard.push_wave(wp.ch[0], wp.ch[1], wp.ch[2])

    def on_feat(fp):
        if start_time[0] is None:
            start_time[0] = time.time()

        elapsed = time.time() - start_time[0]

        if elapsed < SKIP_SEC:
            print(f'\r  稳定期 {elapsed:.0f}/{SKIP_SEC}s ...',
                  end='', flush=True)
            return

        if round_start[0] is None:
            round_start[0] = time.time()
            round_sec[0] = 0

        round_elapsed = time.time() - round_start[0]
        round_sec[0] = int(round_elapsed)

        # 7 维无量纲
        vec = fp_to_vec(fp)

        if any(math.isnan(v) or math.isinf(v) for v in vec):
            return

        if dashboard:
            dashboard.push_feat(
                faa=fp.FAA, apv=fp.APV, beta=fp.beta,
                hfd=fp.HFD, alpha=fp.alpha, theta=fp.theta)

        # 调试打印
        debug_count[0] += 1
        if debug_count[0] % 10 == 1:
            print(f'\n  [设备] '
                  f'FAA={vec[0]:+.4f}  '
                  f'APV=[{vec[1]:.3f},{vec[2]:.3f},{vec[3]:.3f}]  '
                  f'HFD=[{vec[4]:.4f},{vec[5]:.4f},{vec[6]:.4f}]')

        round_feat_vecs.append(vec)

        round_raw_log.append({
            'sec': f'{round_sec[0]}',
            'features': {all_fn[i]: f'{vec[i]:.6g}'
                         for i in range(min(len(vec), len(all_fn)))},
        })

        print(f'\r  [{round_sec[0]:3d}/{args.window}s] '
              f'采集中... {len(round_feat_vecs)} 帧'
              f' | 报告#{report_count[0]+1}进行中'
              f' | 已完成: {report_count[0]} 份    ',
              end='', flush=True)

        if round_elapsed >= args.window:
            _do_round()

    def _do_round():
        if len(round_feat_vecs) < 5:
            print(f'\n  [警告] 数据太少 ({len(round_feat_vecs)}帧), 跳过')
            round_feat_vecs.clear()
            round_raw_log.clear()
            round_start[0] = time.time()
            round_sec[0] = 0
            return

        arr = np.array(round_feat_vecs)
        median_vec = np.median(arr, axis=0)

        Xi = median_vec[sel_idx].reshape(1, -1)
        Xs = scaler.transform(Xi)

        pred = int(clf.predict(Xs)[0])

        prob_dep = 0.5
        prob_nor = 0.5
        if hasattr(clf, 'predict_proba'):
            proba = clf.predict_proba(Xs)[0]
            prob_nor = proba[0]
            prob_dep = proba[1]

        all_preds.append(pred)

        if dashboard:
            dashboard.push_pred(pred, prob_dep)

        result_str = '悲伤倾向' if pred == 1 else '正常'

        # 标准化后
        print(f'\n  [标准化后] ', end='')
        for i, idx in enumerate(sel_idx):
            if i < Xs.shape[1] and idx < len(all_fn):
                print(f'{all_fn[idx]}={Xs[0,i]:+.2f}  ', end='')
        print()

        report_count[0] += 1
        rp = rdir / f'report_{sess_ts}_{report_count[0]:03d}.txt'

        _write_single_report(
            path=str(rp),
            num=report_count[0],
            addr=address,
            clf_name=clf_name,
            mobj=mobj,
            feat_ns=feat_ns,
            all_fn=all_fn,
            sel_idx=sel_idx,
            window=args.window,
            n_frames=len(round_feat_vecs),
            median_vec=median_vec,
            pred=pred,
            prob_nor=prob_nor,
            prob_dep=prob_dep,
            raw_log=round_raw_log,
            train_stats=train_stats,
        )

        all_reports.append(str(rp))

        n_dep = all_preds.count(1)
        n_nor = all_preds.count(0)

        print(f'  ┌{"─" * 52}┐')
        print(f'  │ 报告 #{report_count[0]:03d}  结果: {result_str}'
              f'  P(悲伤)={prob_dep:.2f}'
              f'{"":>{18-len(result_str)*2}}│')
        print(f'  │ 文件: {rp.name:<44}│')
        print(f'  │ 累计: {report_count[0]} 份'
              f'  总: 正常{n_nor}/悲伤{n_dep}'
              f'{"":>{20}}│')
        print(f'  └{"─" * 52}┘')

        round_feat_vecs.clear()
        round_raw_log.clear()
        round_start[0] = time.time()
        round_sec[0] = 0

    rx = BLEEEGReceiver(address, on_wave=on_wave, on_feat=on_feat)
    rx.start()
    print(f'[分类] BLE={address}')
    print(f'[分类] 报告 → {rdir}/')
    print(f'[分类] Ctrl+C 停止\n')

    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        rx.stop()
        if dashboard:
            dashboard.stop()
        print('\n')

        if len(round_feat_vecs) >= 5:
            arr = np.array(round_feat_vecs)
            median_vec = np.median(arr, axis=0)
            Xi = median_vec[sel_idx].reshape(1, -1)
            Xs = scaler.transform(Xi)
            pred = int(clf.predict(Xs)[0])

            prob_dep = 0.5
            prob_nor = 0.5
            if hasattr(clf, 'predict_proba'):
                proba = clf.predict_proba(Xs)[0]
                prob_nor = proba[0]
                prob_dep = proba[1]

            all_preds.append(pred)

            report_count[0] += 1
            rp = rdir / f'report_{sess_ts}_{report_count[0]:03d}.txt'

            _write_single_report(
                path=str(rp),
                num=report_count[0],
                addr=address,
                clf_name=clf_name,
                mobj=mobj,
                feat_ns=feat_ns,
                all_fn=all_fn,
                sel_idx=sel_idx,
                window=args.window,
                n_frames=len(round_feat_vecs),
                median_vec=median_vec,
                pred=pred,
                prob_nor=prob_nor,
                prob_dep=prob_dep,
                raw_log=round_raw_log,
                train_stats=train_stats,
            )
            all_reports.append(str(rp))
            result_str = '悲伤倾向' if pred == 1 else '正常'
            print(f'  [报告#{report_count[0]}] → {rp} '
                  f'(最后 {len(round_feat_vecs)}帧, {result_str})')

        elif len(round_feat_vecs) > 0:
            print(f'  最后 {len(round_feat_vecs)} 帧不足5帧, 跳过')

        print(f'\n{"═" * 55}')
        print(f'  分类结束')
        print(f'{"═" * 55}')

        if all_preds:
            total = len(all_preds)
            dep = sum(all_preds)
            nor = total - dep
            final = '悲伤倾向' if dep > total / 2 else '正常'

            print(f'\n  共完成 {total} 轮 (每轮 {args.window}s)')
            print(f'  悲伤倾向: {dep} 轮')
            print(f'  正常:     {nor} 轮')
            print(f'  最终评估: {final}')
            print(f'\n  共 {report_count[0]} 份报告:')
            for rp in all_reports:
                print(f'    {rp}')
        else:
            print('  无有效数据')

        print(f'{"═" * 55}')


# ══════════════════════════════════════════════════════════
#  交互式菜单
# ══════════════════════════════════════════════════════════

def interactive_menu():
    print('=' * 60)
    print('   情绪 EEG 评估系统 (v10)')
    print('   7维无量纲特征 (FAA+APV+HFD)')
    print('=' * 60)
    print()
    print('  1 - 采集数据 (BLE)')
    print('  2 - 训练模型')
    print('  3 - 实时分类 (BLE)')
    print('  4 - 退出')
    print()

    ch = input('请选择 [1/2/3/4]: ').strip()

    if ch == '1':
        print('\n  a-自动扫描  m-手动MAC')
        md = input('  [a/m]: ').strip().lower() or 'a'
        addr = None
        if md == 'm':
            addr = input('  MAC: ').strip()

        sub = input('被试编号 (N001): ').strip() or 'S001'
        lab = input('标签 0/1: ').strip() or '0'
        dur = input('时长/秒 (120): ').strip() or '120'
        dd = input('数据目录 (dataset): ').strip() or 'dataset'

        class A:
            pass
        a = A()
        a.address = addr
        a.subject = sub
        a.label = int(lab)
        a.duration = int(dur)
        a.data_dir = dd
        cmd_collect(a)

    elif ch == '2':
        dd = input('数据目录 (dataset): ').strip() or 'dataset'
        out = input('模型文件 (model.pkl): ').strip() or 'model.pkl'
        cl = input('分类器 KNN/LDA/LR (回车自动): ').strip() or None
        sd = input('种子 (42): ').strip() or '42'

        class A:
            pass
        a = A()
        a.data_dir = dd
        a.output = out
        a.classifier = cl if cl in ('KNN', 'LDA', 'LR') else None
        a.seed = int(sd)
        cmd_train(a)

    elif ch == '3':
        print('\n  a-自动扫描  m-手动MAC')
        md = input('  [a/m]: ').strip().lower() or 'a'
        addr = None
        if md == 'm':
            addr = input('  MAC: ').strip()

        mdl = input('模型文件 (model.pkl): ').strip() or 'model.pkl'
        win = input('报告间隔/秒 (60): ').strip() or '60'
        gui = input('显示仪表盘? [Y/n]: ').strip().lower()

        class A:
            pass
        a = A()
        a.address = addr
        a.model = mdl
        a.window = int(win)
        a.no_gui = (gui == 'n')
        cmd_classify(a)

    elif ch == '4':
        return

    print()
    input('\n按回车退出...')


# ══════════════════════════════════════════════════════════
#  入口
# ══════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description='情绪 EEG 评估系统')
    sub = parser.add_subparsers(dest='mode', required=True)

    p = sub.add_parser('collect')
    p.add_argument('--address', default=None)
    p.add_argument('--subject', required=True)
    p.add_argument('--label', required=True, type=int, choices=[0, 1])
    p.add_argument('--duration', type=int, default=120)
    p.add_argument('--data-dir', default='dataset')

    p = sub.add_parser('train')
    p.add_argument('--data-dir', default='dataset')
    p.add_argument('--output', '-o', default='model.pkl')
    p.add_argument('--classifier', choices=['KNN', 'LDA', 'LR'],
                   default=None)
    p.add_argument('--seed', type=int, default=42)

    p = sub.add_parser('classify')
    p.add_argument('--address', default=None)
    p.add_argument('--model', default='model.pkl')
    p.add_argument('--window', type=int, default=60)
    p.add_argument('--no-gui', action='store_true')

    args = parser.parse_args()
    {'collect': cmd_collect, 'train': cmd_train,
     'classify': cmd_classify}[args.mode](args)


if __name__ == '__main__':
    if len(sys.argv) > 1:
        main()
    else:
        interactive_menu()
