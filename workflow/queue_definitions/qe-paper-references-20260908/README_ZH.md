# Pt/Pd/Rh 统一赝势元素参考态队列

本队列依次计算 Pt、Pd、Rh 的 fcc 元素参考态 `vc-relax`。所有任务使用与三元代表结构相同的 PseudoDojo ONCVPSP PBE v0.4.1 standard 赝势、`ecutwfc=110 Ry`、`ecutrho=440 Ry`、`degauss=0.02 Ry` 和电子收敛阈值 `1e-8 Ry`。

每项采用 24 MPI 进程、4 个 k 点池和 `12x12x12` k 网格。单项最长 4 小时；一项完成后自动运行下一项。如果任一项未完整 BFGS 收敛，队列会停止，不会掩盖失败。

在 Ubuntu 中执行：

```bash
chmod +x launch_references.sh run_reference_queue.sh status.sh
./launch_references.sh
```

查看状态：

```bash
./status.sh
```
