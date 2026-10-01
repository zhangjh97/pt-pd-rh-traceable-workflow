# Pt-Pd-Rh 统一赝势长任务队列

本任务包用于补齐方法论文最重要的 DFT 证据缺口。它按顺序对 7 个候选结构执行完整 `vc-relax`，与已完成的 `Pt-Pd-Rh-16_Pd7Pt11Rh2` 使用相同的 Quantum ESPRESSO 7.5、PseudoDojo ONCVPSP-PBE-SR v0.4.1 standard 赝势和数值参数。

## 队列内容

1. `Pt-Pd-Rh-10_Pd8Pt5Rh3`：16 原子三元代表，优先运行。
2. `Pt-Rh-04_Pt3Rh7`：10 原子 Pt-Rh 边界代表。
3. `Pd-Rh-14_Pd2Rh6`：8 原子 PdRh3 构型之一。
4. `Pt-Pd-01_Pd4Pt4`：8 原子 PdPt 构型之一。
5. `Pt-Pd-15_Pd4Pt4`：同组成 PdPt 替代构型。
6. `Pd-Rh-06_PdRh3`：同组成 PdRh3 替代构型。
7. `Pt-Pd-Rh-12_Pd2Pt2Rh2`：6 原子等原子比三元代表。

第 4/5 项和第 3/6 项形成两组同化学计量对照，可用于检验 MatterSim 与 DFT 对替代构型的相对排序。三元和三个二元边界均有完整 DFT 弛豫覆盖。

## 计算设置

- `ecutwfc = 110 Ry`，`ecutrho = 440 Ry`
- Marzari-Vanderbilt smearing，`degauss = 0.02 Ry`
- 电子收敛阈值 `1e-8 Ry`
- 力阈值 `1e-3 Ry/Bohr`，压力阈值 `0.5 kbar`
- 24 MPI ranks，4 k-point pools，OpenMP threads = 1
- 每次最长 10 小时；如有完整 QE checkpoint，脚本自动续算一次

## 启动

```bash
chmod +x launch_long_queue.sh run_long_queue.sh status.sh export_results.sh
./launch_long_queue.sh
```

查看状态：

```bash
./status.sh
```

全部完成后导出到 Windows `D:` 盘：

```bash
./export_results.sh
```

任务在 Linux 文件系统的 `~/qe-paper-runs` 中运行，避免在 `/mnt/d` 上直接进行大型临时读写。启动器会拒绝与已有 `pw.x` 或 `mpirun` 任务重叠。
