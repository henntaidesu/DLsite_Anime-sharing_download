"""界面多语言支持。

以简体中文原文作为翻译键（key），运行时按当前语言返回对应译文：
- 当前语言为 zh_CN 时，tr() 直接返回原文；
- 其他语言在 TRANSLATIONS 中查表，缺失时回退到原文。

含占位符的文案（如 '共 {n} 个作品'）由调用方自行 .format()，
各语言译文需保留相同的占位符名称。

注意：仅用于“显示”的中文才走 tr()。数据库中存取的中文值
（works.state 的 '已品悦' / '已下载' / '下载中' 等）必须保持原样，不要翻译。
"""

from PyQt5.QtCore import QObject, pyqtSignal


# 语言代码 -> 该语言自我标注的名称（用于设置页下拉框）
LANGUAGES = [
    ('zh_CN', '简体中文'),
    ('zh_TW', '繁體中文'),
    ('ja', '日本語'),
    ('en', 'English'),
]

_VALID = {code for code, _ in LANGUAGES}

# 简体中文原文 -> {语言代码: 译文}
TRANSLATIONS = {
    # ---------- 导航 / 通用 ----------
    'DLsite 下载器': {'zh_TW': 'DLsite 下載器', 'ja': 'DLsite ダウンローダー', 'en': 'DLsite Downloader'},
    '搜索': {'zh_TW': '搜尋', 'ja': '検索', 'en': 'Search'},
    '下载': {'zh_TW': '下載', 'ja': 'ダウンロード', 'en': 'Download'},
    '已下载': {'zh_TW': '已下載', 'ja': 'ダウンロード済み', 'en': 'Downloaded'},
    '媒体库': {'zh_TW': '媒體庫', 'ja': 'ライブラリ', 'en': 'Library'},
    '标签': {'zh_TW': '標籤', 'ja': 'タグ', 'en': 'Tags'},
    '设置': {'zh_TW': '設定', 'ja': '設定', 'en': 'Settings'},
    '保存': {'zh_TW': '儲存', 'ja': '保存', 'en': 'Save'},
    '取消': {'zh_TW': '取消', 'ja': 'キャンセル', 'en': 'Cancel'},
    '删除': {'zh_TW': '刪除', 'ja': '削除', 'en': 'Delete'},
    '移除': {'zh_TW': '移除', 'ja': '削除', 'en': 'Remove'},
    '刷新': {'zh_TW': '重新整理', 'ja': '更新', 'en': 'Refresh'},
    '测试': {'zh_TW': '測試', 'ja': 'テスト', 'en': 'Test'},
    '提示': {'zh_TW': '提示', 'ja': 'お知らせ', 'en': 'Notice'},
    '← 返回': {'zh_TW': '← 返回', 'ja': '← 戻る', 'en': '← Back'},

    # ---------- 搜索页 ----------
    '输入作品番号，例如 RJ01234567': {
        'zh_TW': '輸入作品番號，例如 RJ01234567',
        'ja': '作品番号を入力（例：RJ01234567）',
        'en': 'Enter work ID, e.g. RJ01234567'},
    '查询': {'zh_TW': '查詢', 'ja': '検索', 'en': 'Search'},
    '← 返回结果': {'zh_TW': '← 返回結果', 'ja': '← 結果に戻る', 'en': '← Back to results'},
    '选择下载位置': {'zh_TW': '選擇下載位置', 'ja': 'ダウンロード先を選択', 'en': 'Choose download location'},
    '选择下载到哪个媒体库': {
        'zh_TW': '選擇下載到哪個媒體庫',
        'ja': 'ダウンロードするライブラリを選択',
        'en': 'Choose which library to download to'},
    '选择下载文件夹': {'zh_TW': '選擇下載資料夾', 'ja': 'ダウンロードフォルダを選択', 'en': 'Choose download folder'},
    '正在查询…': {'zh_TW': '正在查詢…', 'ja': '検索中…', 'en': 'Searching…'},
    '{count} 个文件': {'zh_TW': '{count} 個檔案', 'ja': '{count} 個のファイル', 'en': '{count} files'},
    '检测中…': {'zh_TW': '檢測中…', 'ja': '確認中…', 'en': 'Checking…'},
    '检测中… {checked}/{total}': {
        'zh_TW': '檢測中… {checked}/{total}',
        'ja': '確認中… {checked}/{total}',
        'en': 'Checking… {checked}/{total}'},
    '有效': {'zh_TW': '有效', 'ja': '有効', 'en': 'Valid'},
    '失效': {'zh_TW': '失效', 'ja': '無効', 'en': 'Invalid'},
    '部分有效 {valid}/{total}': {
        'zh_TW': '部分有效 {valid}/{total}',
        'ja': '一部有効 {valid}/{total}',
        'en': 'Partly valid {valid}/{total}'},
    '已加入下载': {'zh_TW': '已加入下載', 'ja': 'ダウンロードに追加', 'en': 'Added to downloads'},
    'RJ号错误': {'zh_TW': 'RJ號錯誤', 'ja': 'RJ番号エラー', 'en': 'Invalid RJ number'},
    '{id} 不是有效的RJ号（格式：RJ + 数字）': {
        'zh_TW': '{id} 不是有效的RJ號（格式：RJ + 數字）',
        'ja': '{id} は有効な RJ 番号ではありません（形式：RJ + 数字）',
        'en': '{id} is not a valid RJ number (format: RJ + digits)'},
    '{id} {name}\n该作品已于 {time} 加入过下载，是否继续搜索？': {
        'zh_TW': '{id} {name}\n該作品已於 {time} 加入過下載，是否繼續搜尋？',
        'ja': '{id} {name}\nこの作品は {time} にダウンロードへ追加済みです。検索を続けますか？',
        'en': '{id} {name}\nThis work was added to downloads on {time}. Continue searching?'},
    '无匹配数据': {'zh_TW': '無相符資料', 'ja': '一致するデータがありません', 'en': 'No matching data'},
    '该帖子中没有找到下载链接': {
        'zh_TW': '該帖子中沒有找到下載連結',
        'ja': 'このスレッドにダウンロードリンクが見つかりません',
        'en': 'No download links found in this thread'},

    # ---------- 下载页 ----------
    'debrid-link 使用量': {'zh_TW': 'debrid-link 使用量', 'ja': 'debrid-link 使用量', 'en': 'debrid-link usage'},
    'debrid-link 使用量 --': {'zh_TW': 'debrid-link 使用量 --', 'ja': 'debrid-link 使用量 --', 'en': 'debrid-link usage --'},
    ' · {reset} 后重置': {'zh_TW': ' · {reset} 後重置', 'ja': ' · {reset} 後にリセット', 'en': ' · resets in {reset}'},
    '开始下载': {'zh_TW': '開始下載', 'ja': 'ダウンロード開始', 'en': 'Start'},
    '暂停下载': {'zh_TW': '暫停下載', 'ja': 'ダウンロード停止', 'en': 'Pause'},
    '暂停中…': {'zh_TW': '暫停中…', 'ja': '停止中…', 'en': 'Pausing…'},
    '清除已完成': {'zh_TW': '清除已完成', 'ja': '完了分を消去', 'en': 'Clear completed'},
    '清空列表': {'zh_TW': '清空列表', 'ja': 'リストをクリア', 'en': 'Clear all'},
    '等待下载': {'zh_TW': '等待下載', 'ja': '待機中', 'en': 'Waiting'},
    '下载中': {'zh_TW': '下載中', 'ja': 'ダウンロード中', 'en': 'Downloading'},
    '已完成': {'zh_TW': '已完成', 'ja': '完了', 'en': 'Completed'},
    '待解压': {'zh_TW': '待解壓', 'ja': '解凍待ち', 'en': 'Pending extract'},
    '解压中 {pct}%': {'zh_TW': '解壓中 {pct}%', 'ja': '解凍中 {pct}%', 'en': 'Extracting {pct}%'},
    '移动中 {pct}%': {'zh_TW': '移動中 {pct}%', 'ja': '移動中 {pct}%', 'en': 'Moving {pct}%'},
    '解析失败': {'zh_TW': '解析失敗', 'ja': '解析失敗', 'en': 'Parse failed'},
    '下载中 {done}/{total}': {
        'zh_TW': '下載中 {done}/{total}', 'ja': 'ダウンロード中 {done}/{total}', 'en': 'Downloading {done}/{total}'},
    '等待下载 {done}/{total}': {
        'zh_TW': '等待下載 {done}/{total}', 'ja': '待機中 {done}/{total}', 'en': 'Waiting {done}/{total}'},
    '{n} 个解析失败': {'zh_TW': '{n} 個解析失敗', 'ja': '{n} 件解析失敗', 'en': '{n} parse failed'},
    '未知({status})': {'zh_TW': '未知({status})', 'ja': '不明({status})', 'en': 'Unknown({status})'},
    '番号 / 文件': {'zh_TW': '番號 / 檔案', 'ja': '番号 / ファイル', 'en': 'ID / File'},
    '下载进度': {'zh_TW': '下載進度', 'ja': '進捗', 'en': 'Progress'},
    '速度': {'zh_TW': '速度', 'ja': '速度', 'en': 'Speed'},
    '状态': {'zh_TW': '狀態', 'ja': '状態', 'en': 'Status'},
    '清空下载列表': {'zh_TW': '清空下載列表', 'ja': 'ダウンロードリストをクリア', 'en': 'Clear download list'},
    '确定要清空整个下载列表吗？等待中的任务也会被删除。': {
        'zh_TW': '確定要清空整個下載列表嗎？等待中的任務也會被刪除。',
        'ja': 'ダウンロードリスト全体をクリアしますか？待機中のタスクも削除されます。',
        'en': 'Clear the entire download list? Pending tasks will also be removed.'},

    # ---------- 已下载页 ----------
    'RJ号': {'zh_TW': 'RJ號', 'ja': 'RJ番号', 'en': 'RJ number'},
    '作品名称': {'zh_TW': '作品名稱', 'ja': '作品名', 'en': 'Title'},
    '类型': {'zh_TW': '類型', 'ja': 'ジャンル', 'en': 'Genre'},
    '下载时间': {'zh_TW': '下載時間', 'ja': 'ダウンロード日時', 'en': 'Download time'},
    '标记为已品悦': {'zh_TW': '標記為已品悦', 'ja': '鑑賞済みにする', 'en': 'Mark as enjoyed'},
    '已品悦': {'zh_TW': '已品悦', 'ja': '鑑賞済み', 'en': 'Enjoyed'},
    '共 {n} 个作品': {'zh_TW': '共 {n} 個作品', 'ja': '作品 {n} 件', 'en': '{n} works total'},

    # ---------- 媒体库页 ----------
    '搜索 RJ号 / 作品名 / 社团': {
        'zh_TW': '搜尋 RJ號 / 作品名 / 社團',
        'ja': 'RJ番号 / 作品名 / サークルで検索',
        'en': 'Search RJ / title / maker'},
    '作品标签': {'zh_TW': '作品標籤', 'ja': '作品タグ', 'en': 'Tags'},
    '媒体库设置': {'zh_TW': '媒體庫設定', 'ja': 'ライブラリ設定', 'en': 'Library settings'},
    '打开文件夹': {'zh_TW': '開啟資料夾', 'ja': 'フォルダを開く', 'en': 'Open folder'},
    '移动媒体库': {'zh_TW': '移動媒體庫', 'ja': 'ライブラリを移動', 'en': 'Move library'},
    '移动中…': {'zh_TW': '移動中…', 'ja': '移動中…', 'en': 'Moving…'},
    '选择要移动到的媒体库': {
        'zh_TW': '選擇要移動到的媒體庫',
        'ja': '移動先のライブラリを選択',
        'en': 'Choose the library to move to'},
    '选择目标文件夹': {'zh_TW': '選擇目標資料夾', 'ja': '移動先フォルダを選択', 'en': 'Choose target folder'},
    '没有可移动到的其它媒体库': {
        'zh_TW': '沒有可移動到的其它媒體庫',
        'ja': '移動できる他のライブラリがありません',
        'en': 'No other library to move to'},
    '确定将 {id} 移动到媒体库“{lib}”吗？': {
        'zh_TW': '確定將 {id} 移動到媒體庫「{lib}」嗎？',
        'ja': '{id} をライブラリ「{lib}」へ移動しますか？',
        'en': 'Move {id} to library "{lib}"?'},
    '已移动到新媒体库': {'zh_TW': '已移動到新媒體庫', 'ja': '新しいライブラリへ移動しました', 'en': 'Moved to the new library'},
    '作品文件夹不存在，无法移动': {
        'zh_TW': '作品資料夾不存在，無法移動',
        'ja': '作品フォルダが存在しないため移動できません',
        'en': 'Work folder does not exist; cannot move'},
    '全年龄': {'zh_TW': '全年齡', 'ja': '全年齢', 'en': 'All ages'},
    '社团': {'zh_TW': '社團', 'ja': 'サークル', 'en': 'Maker'},
    '系列': {'zh_TW': '系列', 'ja': 'シリーズ', 'en': 'Series'},
    '剧本': {'zh_TW': '劇本', 'ja': 'シナリオ', 'en': 'Scenario'},
    '插画': {'zh_TW': '插畫', 'ja': 'イラスト', 'en': 'Illustration'},
    '声优': {'zh_TW': '聲優', 'ja': '声優', 'en': 'Voice actor'},
    '販売日': {'zh_TW': '販售日', 'ja': '販売日', 'en': 'Release date'},
    '年龄分级': {'zh_TW': '年齡分級', 'ja': '年齢区分', 'en': 'Age rating'},
    '作品形式': {'zh_TW': '作品形式', 'ja': '作品形式', 'en': 'Work type'},
    '文件容量': {'zh_TW': '檔案容量', 'ja': 'ファイル容量', 'en': 'File size'},
    '简介': {'zh_TW': '簡介', 'ja': '紹介', 'en': 'Description'},
    '未知社团': {'zh_TW': '未知社團', 'ja': '不明なサークル', 'en': 'Unknown maker'},
    '{count} 个作品': {'zh_TW': '{count} 個作品', 'ja': '作品 {count} 件', 'en': '{count} works'},
    '{works} 个作品 · {folders} 个文件夹': {
        'zh_TW': '{works} 個作品 · {folders} 個資料夾',
        'ja': '作品 {works} 件 · フォルダ {folders} 個',
        'en': '{works} works · {folders} folders'},
    '个媒体库': {'zh_TW': '個媒體庫', 'ja': 'ライブラリ', 'en': 'libraries'},
    '个社团': {'zh_TW': '個社團', 'ja': 'サークル', 'en': 'makers'},
    '个标签': {'zh_TW': '個標籤', 'ja': 'タグ', 'en': 'tags'},
    '共 {total} {unit}，匹配 {shown} 个': {
        'zh_TW': '共 {total} {unit}，相符 {shown} 個',
        'ja': '{unit} {total} 件、一致 {shown} 件',
        'en': '{total} {unit}, {shown} matched'},
    '共 {total} {unit}，{works} 个作品': {
        'zh_TW': '共 {total} {unit}，{works} 個作品',
        'ja': '{unit} {total} 件、作品 {works} 件',
        'en': '{total} {unit}, {works} works'},
    '共 {total} 个作品，匹配 {matched} 个': {
        'zh_TW': '共 {total} 個作品，相符 {matched} 個',
        'ja': '作品 {total} 件、一致 {matched} 件',
        'en': '{total} works, {matched} matched'},
    '共 {total} 个作品': {'zh_TW': '共 {total} 個作品', 'ja': '作品 {total} 件', 'en': '{total} works'},
    '（已加载 {loaded}）': {'zh_TW': '（已載入 {loaded}）', 'ja': '（読み込み済み {loaded}）', 'en': ' (loaded {loaded})'},

    # ---------- 媒体库设置弹窗 ----------
    '新建媒体库': {'zh_TW': '新增媒體庫', 'ja': 'ライブラリを新規作成', 'en': 'New library'},
    '还没有媒体库，点击"新建媒体库"创建。': {
        'zh_TW': '還沒有媒體庫，點擊「新增媒體庫」建立。',
        'ja': 'ライブラリがまだありません。「ライブラリを新規作成」をクリックしてください。',
        'en': 'No libraries yet. Click "New library" to create one.'},
    '{n} 个文件夹': {'zh_TW': '{n} 個資料夾', 'ja': '{n} 個のフォルダ', 'en': '{n} folders'},
    '添加文件夹': {'zh_TW': '新增資料夾', 'ja': 'フォルダを追加', 'en': 'Add folder'},
    '扫描元数据': {'zh_TW': '掃描中繼資料', 'ja': 'メタデータをスキャン', 'en': 'Scan metadata'},
    '重新扫描元数据': {'zh_TW': '重新掃描中繼資料', 'ja': 'メタデータを再スキャン', 'en': 'Rescan metadata'},
    '媒体库名称：': {'zh_TW': '媒體庫名稱：', 'ja': 'ライブラリ名：', 'en': 'Library name:'},
    '已存在同名媒体库。': {'zh_TW': '已存在同名媒體庫。', 'ja': '同じ名前のライブラリが既に存在します。', 'en': 'A library with this name already exists.'},
    '选择媒体库文件夹': {'zh_TW': '選擇媒體庫資料夾', 'ja': 'ライブラリフォルダを選択', 'en': 'Choose library folder'},
    '该文件夹已在媒体库"{name}"中。': {
        'zh_TW': '該資料夾已在媒體庫「{name}」中。',
        'ja': 'このフォルダは既にライブラリ「{name}」に含まれています。',
        'en': 'This folder is already in library "{name}".'},
    '删除媒体库': {'zh_TW': '刪除媒體庫', 'ja': 'ライブラリを削除', 'en': 'Delete library'},
    '确定删除媒体库"{name}"吗？\n不会删除本地文件，已导入的作品记录保留。': {
        'zh_TW': '確定刪除媒體庫「{name}」嗎？\n不會刪除本機檔案，已匯入的作品記錄會保留。',
        'ja': 'ライブラリ「{name}」を削除しますか？\nローカルファイルは削除されず、取り込み済みの作品記録は保持されます。',
        'en': 'Delete library "{name}"?\nLocal files will not be deleted; imported work records are kept.'},
    '正在扫描媒体库"{name}"…': {
        'zh_TW': '正在掃描媒體庫「{name}」…',
        'ja': 'ライブラリ「{name}」をスキャン中…',
        'en': 'Scanning library "{name}"…'},
    '已导入 {total} 个作品（新增 {added}），正在从 DL API 补全数据…': {
        'zh_TW': '已匯入 {total} 個作品（新增 {added}），正在從 DL API 補全資料…',
        'ja': '{total} 件の作品を取り込みました（新規 {added}）。DL API からデータを補完中…',
        'en': 'Imported {total} works ({added} new), filling data from DL API…'},
    '正在抓取 DLsite 作品页元数据与图片…': {
        'zh_TW': '正在抓取 DLsite 作品頁中繼資料與圖片…',
        'ja': 'DLsite 作品ページのメタデータと画像を取得中…',
        'en': 'Fetching DLsite work page metadata and images…'},
    '扫描完成：导入 {total} 个，API 补全 {filled} 个，作品页补全 {page_filled} 个（失败 {page_missed}）': {
        'zh_TW': '掃描完成：匯入 {total} 個，API 補全 {filled} 個，作品頁補全 {page_filled} 個（失敗 {page_missed}）',
        'ja': 'スキャン完了：取り込み {total} 件、API 補完 {filled} 件、作品ページ補完 {page_filled} 件（失敗 {page_missed}）',
        'en': 'Scan complete: imported {total}, API filled {filled}, page filled {page_filled} ({page_missed} failed)'},
    'DL API 数据补全中… {i}/{total}': {
        'zh_TW': 'DL API 資料補全中… {i}/{total}',
        'ja': 'DL API データ補完中… {i}/{total}',
        'en': 'Filling data from DL API… {i}/{total}'},
    '作品页抓取中… {i}/{total}（{rj}）': {
        'zh_TW': '作品頁抓取中… {i}/{total}（{rj}）',
        'ja': '作品ページ取得中… {i}/{total}（{rj}）',
        'en': 'Fetching work pages… {i}/{total} ({rj})'},

    # ---------- 设置页 ----------
    '下载路径': {'zh_TW': '下載路徑', 'ja': 'ダウンロード先', 'en': 'Download path'},
    '缓存路径': {'zh_TW': '快取路徑', 'ja': 'キャッシュ先', 'en': 'Cache path'},
    '代理': {'zh_TW': '代理', 'ja': 'プロキシ', 'en': 'Proxy'},
    'Debrid-Link 下载中转站': {'zh_TW': 'Debrid-Link 下載中轉站', 'ja': 'Debrid-Link 中継', 'en': 'Debrid-Link relay'},
    '下载选项': {'zh_TW': '下載選項', 'ja': 'ダウンロード設定', 'en': 'Download options'},
    '自动下载': {'zh_TW': '自動下載', 'ja': '自動ダウンロード', 'en': 'Auto download'},
    '自动解压': {'zh_TW': '自動解壓', 'ja': '自動解凍', 'en': 'Auto extract'},
    '文件夹命名': {'zh_TW': '資料夾命名', 'ja': 'フォルダ命名', 'en': 'Folder naming'},
    '单文件线程数': {'zh_TW': '單檔執行緒數', 'ja': 'ファイルごとのスレッド数', 'en': 'Threads per file'},
    '单个文件分成多少段并发下载（多线程下载），1 为不分段': {
        'zh_TW': '單個檔案分成多少段並發下載（多執行緒下載），1 為不分段',
        'ja': '1 つのファイルを何分割して並列ダウンロードするか（マルチスレッド）。1 で分割なし',
        'en': 'How many segments to split each file into for concurrent download; 1 means no split'},
    '单个文件分成多少段并发下载（多线程下载），1 为不分段，最大 16': {
        'zh_TW': '單個檔案分成多少段並發下載（多執行緒下載），1 為不分段，最大 16',
        'ja': '1 つのファイルを何分割して並列ダウンロードするか（マルチスレッド）。1 で分割なし、最大 16',
        'en': 'How many segments to split each file into for concurrent download; 1 means no split, max 16'},
    '查询线程数': {'zh_TW': '查詢執行緒數', 'ja': '検索スレッド数', 'en': 'Query threads'},
    '最低速度 (KB/s)': {'zh_TW': '最低速度 (KB/s)', 'ja': '最低速度 (KB/s)', 'en': 'Min speed (KB/s)'},
    '持续低于该速度 30 秒后自动重试，0 表示不限制': {
        'zh_TW': '持續低於該速度 30 秒後自動重試，0 表示不限制',
        'ja': 'この速度を 30 秒下回ると自動で再試行。0 は無制限',
        'en': 'Auto-retry after staying below this speed for 30s; 0 means no limit'},
    '速度限制 (KB/s)': {'zh_TW': '速度限制 (KB/s)', 'ja': '速度制限 (KB/s)', 'en': 'Speed limit (KB/s)'},
    '下载总速度上限，0 表示不限速': {
        'zh_TW': '下載總速度上限，0 表示不限速',
        'ja': 'ダウンロード総速度の上限。0 は無制限',
        'en': 'Total download speed cap; 0 means unlimited'},
    '系统': {'zh_TW': '系統', 'ja': 'システム', 'en': 'System'},
    '日志级别': {'zh_TW': '日誌等級', 'ja': 'ログレベル', 'en': 'Log level'},
    '解压编码': {'zh_TW': '解壓編碼', 'ja': '解凍エンコード', 'en': 'Extract encoding'},
    'API 地址': {'zh_TW': 'API 位址', 'ja': 'API アドレス', 'en': 'API address'},
    '语言': {'zh_TW': '語言', 'ja': '言語', 'en': 'Language'},
    '开启': {'zh_TW': '開啟', 'ja': 'オン', 'en': 'On'},
    '关闭': {'zh_TW': '關閉', 'ja': 'オフ', 'en': 'Off'},
    '测试成功': {'zh_TW': '測試成功', 'ja': 'テスト成功', 'en': 'Test succeeded'},
    '测试失败': {'zh_TW': '測試失敗', 'ja': 'テスト失敗', 'en': 'Test failed'},
    '已连接 debrid-link\n账户: {account}': {
        'zh_TW': '已連接 debrid-link\n帳戶: {account}',
        'ja': 'debrid-link に接続しました\nアカウント: {account}',
        'en': 'Connected to debrid-link\nAccount: {account}'},
    'API Key 无效或网络不可用': {
        'zh_TW': 'API Key 無效或網路不可用',
        'ja': 'API Key が無効か、ネットワークが利用できません',
        'en': 'Invalid API Key or network unavailable'},
    '选择下载路径': {'zh_TW': '選擇下載路徑', 'ja': 'ダウンロード先を選択', 'en': 'Choose download path'},
    '选择缓存路径': {'zh_TW': '選擇快取路徑', 'ja': 'キャッシュ先を選択', 'en': 'Choose cache path'},
}


class _Notifier(QObject):
    """语言切换广播：各窗口在初始化时连接 language_changed，收到信号后重译界面。"""
    language_changed = pyqtSignal()


notifier = _Notifier()

_current = 'zh_CN'


def current_language():
    return _current


def set_language(lang):
    """仅更新内存中的当前语言（不写库、不发信号）。"""
    global _current
    _current = lang if lang in _VALID else 'zh_CN'


def init_language():
    """从配置读取已保存的语言；在创建任何窗口之前调用。"""
    from src.module.conf_operate import Config
    set_language(Config().read_value('language', 'lang', 'zh_CN'))


def apply_language(lang):
    """切换语言：写入配置、更新当前语言并广播给所有窗口实时重译。"""
    from src.module.conf_operate import Config
    set_language(lang)
    Config().write_value('language', 'lang', _current)
    notifier.language_changed.emit()


def tr(text):
    """按当前语言返回译文；zh_CN 或查不到时返回原文。"""
    if _current == 'zh_CN':
        return text
    entry = TRANSLATIONS.get(text)
    if not entry:
        return text
    return entry.get(_current, text)
