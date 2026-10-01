# 加密k点补充任务：4项

目的：与已完成的7x6x6合金/16x16x16元素参考组比较形成能，检查是否达到约1 meV/原子的工作精度目标。最密已有两组相差1.1876 meV/原子，目前尚不能证明该精度。

合金：已优化Pt11Pd7Rh2，固定几何SCF，8x7x7、偏移0 1 1。
元素：fcc Pt/Pd/Rh各一个原子，vc-relax，18x18x18、偏移1 1 1。
全部：110/440 Ry、MV展宽0.02 Ry、相同PseudoDojo赝势与相同SCF阈值。不改变原来比较协议。

## 在服务器使用

解压到D盘，进入含queue.py的目录。仅需要Ubuntu自带Python3和已安装的QE/MPI，无需pip安装。

```bash
cd /mnt/d/qe-kdense3-check-20260909
python3 queue.py start
python3 queue.py status
```

启动后后台运行。启动前要求已有pw.x进程不多于24、可用内存不少于24 GiB、Linux运行盘可用空间不少于15 GiB。使用12 MPI ranks、2 pools、每进程1线程。

任务数据目录固定为/home/administrator/qe-paper-runs/kdense3_check_20260909（实际跟随当前Ubuntu用户home）。输入与输出在Linux磁盘，D盘仅存放任务包与导出包。

同一个包全局加锁，重复启动会拒绝。已完成任务只有在检查实际输出与退出码后才跳过。未完成的旧目录会拒绝覆盖，需检查日志后决定恢复策略。

每项最多自动尝试两次：仅在QE正常因时间上限退出且检查点存在时自动restart。合金每次时间上限6小时，元素每次2小时；这不是预计耗时。如果未收敛或出现错误，整个队列停止并保留日志。运行时间以该机实测为准。

完成状态核验SCF、BFGS（元素参考）、退出码和JOB DONE，但不保证最终应力通过目标阈值或k点已收敛；后续数据分析还需检查。

## 导出

确认4/4后：

```bash
python3 queue.py export
```

输出到服务器D:\qe-kdense3-results-20260909.tar.gz，同时显示SHA256。排除scratch，保留输入、输出和赝势。将压缩包传回本机项目data/dft_runs中供分析。

不要重复启动原32项队列。当前24核主队列继续运行。本任务包不会主动终止或更改主队列。
