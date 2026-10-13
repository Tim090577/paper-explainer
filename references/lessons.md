# 踩過的坑（第一篇：Joubert 2023, J Clin Med, Behçet's disease uveitis）

## 取得論文
- **MDPI、PMC 的 PDF 常擋 curl／腳本下載**。MDPI 可用 `mdpi-res.com/d_attachment/...` 直連；不行就請使用者自己下載 PDF 給你。
- PMC 開放全文可用 BioC JSON 拿乾淨的段落文字：
  `https://www.ncbi.nlm.nih.gov/research/bionlp/RESTful/pmcoa.cgi/BioC_json/<PMCID>/unicode`。
  這個 skill 不需要它（直接從 PDF 抽字），但拿來對照、找引句很方便。

## PDF 對位
- PDF 的**頁眉頁腳會插進跨頁段落中間**：預設排除頁面最上 6%、最下 6% 的字（`pdf_body.header/footer`）。出版社版面不同時要調。
- **引用括號 [13,40,41]、行尾斷字、ﬁ 連字**：兩邊都正規化成小寫英數字再比，所以引句可以省略引用括號。
- **參考文獻區**會讓短引句對到錯的地方：正文在 References 標題處停止（`stop_at_references`）；標題寫法特殊時改用 `end_page`。
- 兩欄排版 PyMuPDF 會依區塊排序，通常沒問題；若一句跨欄，用「開頭／結尾」寫法。

## 影片
- **一句＝一個狀態**，元素逐句浮現，成片才像動畫而不是翻頁；句間用 fade、換幕用 slideleft。
- 每段音訊長度**對齊影格邊界**（1/30 秒）再接，否則幾十句之後影音會累積漂移。
- **時間軸要用實際片段長度**計算，不能用「音訊長度＋停頓」推算。
- 截圖用 headless Chrome、固定 1920×1080；中文字型靠系統（PingFang TC／Noto Sans TC），換機器要確認有繁中字型。

## 配音
- macOS `say -v Meijia -r 205` 是可用的本機繁中語音；數字和百分比要寫成中文念法，否則會念成英文或怪音。
- edge-tts 的微軟端點偶爾回 403（2026-10 實測），不能當唯一方案。
- whisper 回聽的拼音比對：同音字、數字、百分比常是假警報，要人工聽。

## 播放頁與發佈
- `python3 -m http.server` **不支援 Range**，影片無法跳轉；用 `pe.py serve`。
- claude.ai Artifact：單檔上限 15 MB（影片壓 720p、CRF 30、單聲道 48k 約 10 MB／15 分鐘）；**不收 .vtt** → 存成 `.txt`，頁面再轉成 blob 給 `<track>`；頁面外層的 `<!DOCTYPE>/<html>/<head>/<body>` 由平台包，`--artifact` 會拿掉。
- 公開版要確認論文授權；CC BY 要在播放頁標示出處與授權。
