# GitHub 与数据发布操作说明

## 推荐的分阶段公开方式

1. 投稿审查阶段：将本文件夹作为仅支撑当前论文的复现包。代码可以建立公开 GitHub 仓库；如暂不希望数据在论文接收前公开，可把完整 ZIP 作为投稿系统的补充审稿文件，或存入支持私密审稿链接/延迟公开的数据仓库。
2. 接收后：确认公司与全部作者同意，再公开数据目录，创建 GitHub Release，并将该 Release 归档至 Zenodo 取得 DOI。
3. 校样阶段：把正式 DOI 写入论文 Data availability 和 Code availability，不要预先编造 DOI。

## GitHub 建议操作

1. 在 GitHub 新建仓库，建议名称：`pt-pd-rh-traceable-workflow`。
2. 投稿前仍需保密时，先设为 Private；代码可单独建立 Public 仓库，数据 ZIP 通过投稿系统提供给编辑和审稿人。
3. 将本文件夹内容上传到仓库根目录，不要上传整个原项目。
4. 检查仓库中没有服务器 IP、账号、邮箱、密钥、Tailscale 信息或后续研究目录。
5. 经权利人确认后，代码建议 MIT License，作者生成的数据建议 CC BY 4.0。第三方软件、模型和赝势仍遵循其原许可。
6. 创建版本标签，例如 `v1.0.0-submission`。论文接收后可创建 `v1.0.0-accepted`。

## 论文接收前是否会“泄露”

公开 GitHub 仓库会立即被任何人看到，因此确实属于提前公开。若存在专利、商业秘密或后续申请安排，不应在权利人确认前公开完整数据。编辑部要求的是支撑论文的数据与代码可供核验；可以先向编辑提供非公开审稿附件或私密仓库访问方式，并书面说明接收后公开的计划。最终是否接受延迟公开由期刊编辑决定。

## 不应上传

- Pt-W、氧化锆弥散强化、Pt-Pd-Rh-Ru 四元合金及后续催化项目；
- 尚未形成论文结论的服务器任务；
- QE `scratch`、波函数、密度和检查点大文件；
- 登录凭据、远程桌面/Tailscale 地址、个人邮箱和服务器清单；
- 无权再分发的第三方模型权重或材料数据库副本。

## 发布前必须完成

- 由通讯作者和单位确认公开范围与许可；
- 在 `LICENSE_SELECTION_REQUIRED.md` 所列许可中作出选择；
- 执行 `python code/verify_release.py`；
- 检查 `metadata/MANIFEST.csv` 与 `metadata/SHA256SUMS.txt`；
- 获得 DOI 后更新论文中的 Data availability 与 Code availability。
