# 七结构统一DFT队列核验

日期：2026-09-09。数据：`../unified_validation_20260908_133506`。

## 核验结论

七项均有BFGS收敛、最终SCF收敛、JOB DONE和有效最终分段退出码0。最终SCF精度均小于1e-8 Ry，最大原子力均小于0.001 Ry/Bohr；最终压力绝对值均小于0.5 kbar，最大应力分量绝对值不超过0.47 kbar。

输入与原任务包一致（比对允许restart_mode从from_scratch变为restart）；各任务的赝势文件哈希与统一赝势元数据一致。输出中的元素计数与输入一致。最终坐标文本与有效最终分日志严格匹配；另外用ASE的espresso-out解析器独立读取最后结构，并与提取晶胞和周期坐标交叉核对。

本机收到解压后的文件夹，未收到可比对的服务器压缩包SHA256，未宣称完成传输压缩包哈希核验。本次保存了本机输入输出SHA256清单。

## 第一项误启动后的数据完整性

`Pt-Pd-Rh-10_Pd8Pt5Rh3` 的 `output.part01.log` 已被误启动覆盖，`returncode.part01=143` 对应被终止的误运行。不能把这两个文件用于原13小时任务的第一段性能分析。

但是原成功续算的 `output.part02.log` 仍在，退出码0；包含最终BFGS与SCF收敛。保留的完整 `output.log` 以这份有效分日志结束；`final_coordinates.txt` 也与之匹配。因此本次最终结构、最终能量与力/应力有足够日志支撑，可用于结果汇总。误启动后的scratch检查点不作为成功优化终态使用；后续补算应从核验的最终坐标重新生成输入。

## 形成能口径

统一采用每项有效最终分日志最后一条 `! total energy`，而非此前的Final enthalpy。元素参考采用已核验c110组最终SCF，fcc单原子、12x12x12、偏移1 1 1：

| 元素 | 最终参考能 (Ry/原子) |
|---|---:|
| Pt | -261.18491564 |
| Pd | -270.98097218 |
| Rh | -234.57774395 |

`Delta F = (F_structure - sum(n_i F_i)) / N`，1 Ry = 13.605693122994 eV。全部110/440 Ry、MV展宽0.02 Ry、统一PseudoDojo赝势。按日志F=E-TS口径称“形成能”，未外推零展宽。不同晶胞使用各自网格，详情在CSV，不宣称每个结构的k点均已通过加密测试。

| 结构编号 | 原子数 | 形成能 (meV/原子) | 最终压力 (kbar) | 最大原子力 (eV/Å) |
|---|---:|---:|---:|---:|
| Pt-Pd-Rh-10_Pd8Pt5Rh3 | 16 | +17.604 | +0.13 | 0.016087 |
| Pt-Rh-04_Pt3Rh7 | 10 | -20.594 | -0.04 | 0.009169 |
| Pd-Rh-14_Pd2Rh6 | 8 | +53.439 | +0.37 | 0.002775 |
| Pt-Pd-01_Pd4Pt4 | 8 | -27.176 | -0.14 | 0.002424 |
| Pt-Pd-15_Pd4Pt4 | 8 | +22.848 | -0.06 | 0.010667 |
| Pd-Rh-06_PdRh3 | 4 | +107.192 | -0.06 | 0.011104 |
| Pt-Pd-Rh-12_Pd2Pt2Rh2 | 6 | +17.861 | -0.07 | 0.004587 |

这是本次有目的选择的7个结构子集，不能将7/7完成率外推为全体生成候选的成功率；也不能将2/7负形成能比例外推为材料发现成功率。

## 对论文的支持

1. 计算工作流证据：所有选定结构可完成统一赝势DFT优化并得到可追溯输出，支持流程可执行性和验证闭环。
2. 同组成比较：Pt-Pd-01与Pt-Pd-15均为Pd4Pt4，前者低约50.024 meV/原子；Pd-Rh-14与Pd-Rh-06均为Pd:Rh=1:3，前者低约53.753 meV/原子。这些可用于同组成候选筛选，仍需考虑不同网格的数值敏感性。
3. 正形成能结构是有效的筛选结果，不应删去。当前设置下相对于元素参考不占能量优势，不能直接称为稳定新相；负形成能也不等于相对所有竞争相稳定。
4. 当前数据只直接支持DFT结果与数值质量，不直接证明大模型优于传统方法。模型排序一致性、误差和相对基线优势还需结合对应的原始模型预测与基线数据。

## 后续安排

- 24核主队列无需重启或重复运行。
- 等待正在执行的4项加密k点结果，先与代表结构已有收敛扫描比较。
- 若选定新的最终参数，对已优化候选按相当倒空间密度补最终SCF；如最终力或应力不满足目标，才对对应结构短程续优化。
- 结合此前Pt11Pd7Rh2代表结构，本地已有8个统一赝势结构的结果；不同批次形成能统一采用最终SCF口径。此前代表结构更新值为-17.402 meV/原子（c110），密网格结果另列，不混作同精度数据。
- 暂不依据第一项耗时外推整个队列工期；本次其余结构实际明显更快。

## 交付文件

- `unified_results.csv`：七项数值与质量检查，可导入Origin。
- `formation_energies.png`、`formation_energies.pdf`：原始DFT计算数据绘图，正负表示相对fcc元素参考。
- `structures/`：7份CIF和对应核验的QE最终坐标，便于可视化与后续生成静态输入。
- `audit.json`、`source_SHA256SUMS.txt`：数值与来源追溯。

图建议用于论文的DFT validation部分或补充材料。英文图注：Formation energies of seven selected candidates after variable-cell DFT relaxation using a unified pseudopotential family. Energies are referenced to relaxed fcc Pt, Pd and Rh using the final converged SCF outputs at 110/440 Ry and Marzari-Vanderbilt smearing of 0.02 Ry. Structure-specific k-point meshes are listed in the accompanying data. Negative formation energy relative to elemental references does not establish stability against competing compounds. These results precede completion of the additional k-point sensitivity check.
