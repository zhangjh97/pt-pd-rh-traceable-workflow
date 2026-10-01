# 形成能收敛并行补充队列

该任务包使用 12 MPI ranks 和 2 个 k-point pools，可与主 `24 MPI` 完整弛豫队列并行，总计占用 36 个物理核心。不要再启动第三个 QE 队列。

任务对最终弛豫的 Pt11Pd7Rh2 结构及 Pt、Pd、Rh 元素参考态计算匹配能量：

- 截断能：80、90、100、110、120 Ry，`ecutrho/ecutwfc = 4`。
- k 点：合金 4x3x3、5x4x4、6x5x5、7x6x6；元素参考态对应 10x10x10、12x12x12、14x14x14、16x16x16。
- 共 8 组设置、32 个顺序任务；每组先运行耗时较长的合金 SCF，再运行三个元素参考态。

启动：

```bash
chmod +x launch_sidecar.sh run_convergence_queue.sh status.sh
./launch_sidecar.sh
```

查看状态：

```bash
./status.sh
```

当主队列使用 24 ranks 时，本队列最多再使用 12 ranks。若系统已有超过 24 个 `pw.x` 进程，启动器会拒绝运行。
