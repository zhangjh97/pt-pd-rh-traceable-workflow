# QE 7.5 论文整夜任务

该任务对论文代表性三元结构 `Pt-Pd-Rh-16_Pd7Pt11Rh2`（20 原子）执行完整 `vc-relax`，同时统一使用 PseudoDojo NC-SR ONCVPSP PBE v0.4.1 standard 赝势。任务使用 24 MPI 进程、4 个 k 点池、每进程 1 个 OpenMP 线程，最长运行 11 小时，收敛时自动提前结束。

物理设置：`ecutwfc=110 Ry`、`ecutrho=440 Ry`、Marzari-Vanderbilt smearing、`degauss=0.02 Ry`、电子收敛阈值 `1e-8 Ry`、力阈值 `1e-3 Ry/Bohr`、压力阈值 `0.5 kbar`。`ecutrho=440 Ry` 对应统一 NC 赝势的 4 倍波函数截断；正式结论仍需结合后续截断能和 k 点收敛测试。

在 Ubuntu 中进入解压目录后运行：

```bash
chmod +x launch_overnight.sh status.sh resume_latest.sh
./launch_overnight.sh
```

检查状态：

```bash
./status.sh
```

计算目录位于 `~/qe-paper-runs/overnight_日期_时间`。关闭终端不影响 `nohup` 后台任务，但 Windows 不能休眠、关机或重启。

如果任务达到 11 小时上限但尚未完成，可从原检查点继续：

```bash
./resume_latest.sh
```

赝势来源固定到 PseudoDojo `ONCVPSP-PBE-SR` 提交 `823b18f7701b6303e0e69114eaa645173f706600`，并由 `SHA256SUMS` 校验。
