# 範例：Behçet's Disease Uveitis（2 幕、5 句）

Joubert M, et al. *Behçet's Disease Uveitis.* J Clin Med 2023;12:3648（CC BY 4.0）。
用來確認工具裝好了、看一下產出長怎樣；約 1 分鐘跑完。

```bash
mkdir -p demo/src
cp examples/behcet-uveitis/paper.json examples/behcet-uveitis/script.json demo/
# 下載論文 PDF 存成 demo/src/paper.pdf：
#   https://www.mdpi.com/2077-0383/12/11/3648/pdf
#   （網站擋腳本下載時，用瀏覽器手動下載）
python3 scripts/pe.py crop demo 2 92 92 504 352 figs/fig1.png   # 裁論文圖一，第 2 幕會用到
python3 scripts/pe.py all demo
python3 scripts/pe.py serve demo 8790                           # http://localhost:8790/
```
