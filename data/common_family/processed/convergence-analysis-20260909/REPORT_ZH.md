# Pt11Pd7Rh2 形成能收敛性核验

分析日期：2026-09-09。输入目录：`../formation_convergence_20260908_134907`。

## 结论和当前计算安排

32/32 项任务均通过输出核验。对于本次代表结构及固定展宽，110 Ry 的截断能有充分的数值支持；k 点还有 meV/原子级敏感性。主长队列继续完成现有结构优化，不需要因本次检查停机或重算全部结构。暂不降低截断能来提速。

本次结果尚不能证明所有候选结构的 k 点收敛，也不能证明误差小于 1 meV/原子。这里的 1 meV/原子是用于讨论下一步精度目标的工作标准，并非期刊统一要求或事先登记的阈值。

## 核验范围

- 32 项 `STATUS=DONE`、退出码 0、最终收敛总能量及其后的 SCF 收敛标志、`JOB DONE` 全部通过，日志未出现 `Error in routine`。
- 24 项元素参考计算均包含 BFGS 收敛及优化结束标志；最终 SCF 精度均小于 1e-8 Ry。
- 32 项输入文件 SHA256 与本机原任务包全部一致。
- 96 份任务内赝势文件的 SHA256 与元数据一致；服务器 `environment.txt` 中 32 份输入和 3 份赝势哈希也与本机任务包一致。
- 8 份合金输入的晶胞和坐标完全相同，均为已优化的 Pt11Pd7Rh2、20 原子固定结构 SCF。元素参考则分别做了 `vc-relax`。
- 本次收到的是解压后的文件夹。未找到所述 tar.gz，也未收到服务器压缩包 SHA256，不能宣称已核对传输压缩包哈希。另存的 `source_SHA256SUMS.txt` 是本机输入/输出等文件的后续追溯清单。

赝势为任务包记录的 PseudoDojo ONCVPSP-PBE-SR standard，commit `823b18f7701b6303e0e69114eaa645173f706600`。三个元素均使用同一系列；本次仅核对随附元数据及文件哈希，不重新认定远程库版本。

## 能量定义

采用每份 `output.log` 最后一条 `! total energy = ... Ry`，不使用更早的 `Final enthalpy`。元素参考优化结束后还有最终 SCF；例如 c110 Pt 的最终 SCF 能量为 -261.18491564 Ry，较早优化焓为 -261.1849120879 Ry。

`Delta F = [F_alloy - 11 F_Pt - 7 F_Pd - 2 F_Rh] / 20`

换算系数：1 Ry = 13.605693122994 eV。所有能量统一采用日志输出的有限展宽 `F=E-TS`，Marzari-Vanderbilt 展宽 0.02 Ry；这里沿用“形成能”简称，不等同于已经外推到零展宽的能量，也不是有限温度完整热力学自由能。

c110 得到 **-0.01740219 eV/原子**。早前 `FORMATION_ENERGY_RESULT.md` 中的 -0.01744433 eV/原子混用了较早元素优化焓，数值差约 0.0421 meV/原子。后续论文更新应以统一最终 SCF 口径重新汇总；旧报告保留供追溯。

## 截断能扫描

合金 k 点 5x4x4，偏移 0 1 1；元素 k 点 12x12x12，偏移 1 1 1。电荷密度截断始终为波函数截断的 4 倍。

| ecutwfc (Ry) | 形成能 (meV/原子) | 相对120 Ry的差值 (meV/原子) | 合金压力 (kbar) |
|---:|---:|---:|---:|
| 80 | -17.456091 | -0.053205 | -2.56 |
| 90 | -17.401852 | +0.001034 | -0.10 |
| 100 | -17.398600 | +0.004286 | -0.23 |
| 110 | -17.402192 | +0.000694 | -0.01 |
| 120 | -17.402886 | 0 | +0.03 |

110→120 Ry 的形成能变化约 **0.0007 meV/原子**，合金总能量每原子变化约 0.0894 meV，合金压力变化 0.04 kbar。因此维持 110/440 Ry 合理。本次单个结构的误差抵消不能用于承诺其他组成在 80 Ry 下同样可靠。

低截断参考态的最终压力需要单独记录：c080 Pt/Pd/Rh 分别为 1.71/1.22/2.64 kbar，c090 Rh 为 0.51 kbar，超过输入 0.5 kbar 的压力阈值。虽然有 BFGS 收敛标志，最终重新计算的应力并非全部通过该阈值。不能把32项全标成“最终压力均收敛”。

## k点扫描

本扫描固定 110/440 Ry，合金与元素参考网格同时加密，因此反映成对网格协议的敏感性，不能单独归因于合金网格。

| 合金网格 | 元素参考网格 | 形成能 (meV/原子) | 相对最密组差值 (meV/原子) |
|---|---|---:|---:|
| 4x3x3 | 10x10x10 | -14.771021 | +4.142002 |
| 5x4x4 | 12x12x12 | -17.402192 | +1.510831 |
| 6x5x5 | 14x14x14 | -20.100582 | -1.187559 |
| 7x6x6 | 16x16x16 | -18.913022 | 0 |

最密组只是当前比较基准，尚不能视作无限密度极限。6x5x5→7x6x6 仍变化 1.1876 meV/原子，且序列非单调；基础组与6x5x5差2.6984 meV/原子。所有已测设置下形成能符号保持为负，但这一事实不能证明相对竞争相稳定或发现新相。

在固定合金几何上，6x5x5、7x6x6 的压力分别为 -1.07、-0.60 kbar，最大原子力分别约 0.000819、0.000860 Ry/Bohr。此为加密参数下的几何敏感性，不是 SCF 失败。若最终采用更密参数且要求0.5 kbar，应重新检查并视需要短程优化晶胞，不能预先承诺所有结构只做静态SCF即可。

## 下一步优先级

1. 当前24核长队列继续。先备份已完成第一项的 `output.log`、`output.part02.log`、最终坐标和摘要；它此前被误启动过，保存状态不能代替原始文件核验。
2. 可利用空余资源补一组成对k点检查：代表合金8x7x7与元素18x18x18，保持110/440 Ry、同一结构、相同展宽及偏移约定。此为建议任务，尚未在服务器启动。与7x6x6/16x16x16比较后再选择最终参数。
3. 如果仍有明显振荡，再做更密网格或展宽0.01 Ry的联合检查；展宽与k点要共同评估。额外计算时间需以新任务实测更新，前次数日工期估计不能视作保证。
4. 主队列完成后，对其他候选采用相当的倒空间网格密度验证最终能量、力和应力；晶胞不同，不能机械套用相同网格数字。必要时补最终静态SCF或短程弛豫。
5. 汇总统一参考形成能、模型与DFT排序及误差，再更新论文。无需为证明此方法可行而自动增加声子/能带；若论文声称动力学稳定或相关物性，则需相应证据。

## 图表及论文用途

- `formation_convergence.csv`：8组形成能、组成能量及网格，适合导入 Origin；所有原始数值保留在CSV。
- `job_audit.csv`：32项最终能量、精度、力、压力与输入匹配状态。
- `formation_convergence.png` / `.pdf`：收敛曲线；左右纵轴范围不同，左图显示很小的差异，不应按视觉起伏比较误差大小。
- `audit.json`：完整机器可读结果。

图可放入补充材料的“Numerical convergence tests”，方法段引用。英文图注草稿：

Numerical sensitivity of the formation energy of Pt11Pd7Rh2 relative to fcc Pt, Pd and Rh. (a) Wavefunction cutoff scan at fixed alloy/reference meshes of 5x4x4/12x12x12; the charge-density cutoff is four times the wavefunction cutoff. (b) Paired alloy/reference k-point mesh scan at 110/440 Ry. The alloy geometry is held fixed, whereas the elemental references are relaxed for each setting. Energies are taken from the final converged SCF output using Marzari-Vanderbilt smearing of 0.02 Ry. Lines guide the eye; panel scales differ. The densest mesh is a tested reference, not an established converged limit.

关于 `conv_thr`、压力收敛阈值、截断能及 k 点偏移的定义，参见 [Quantum ESPRESSO 7.5 输入说明](https://www.quantum-espresso.org/Doc/INPUT_PW.html)。本报告的数值结论来自本地计算日志。
