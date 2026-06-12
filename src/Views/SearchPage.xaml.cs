using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.ComponentModel;
using System.IO;
using System.Linq;
using System.Net.Http;
using System.Runtime.CompilerServices;
using System.Text.RegularExpressions;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using DASD.Core;
using DASD.Services;

namespace DASD.Views;

/// <summary>搜索结果条目。</summary>
public class SearchResultItem : INotifyPropertyChanged
{
    public string Title { get; init; } = "";
    public string Minor { get; init; } = "";
    public string Snippet { get; init; } = "";
    public string Url { get; init; } = "";
    public string ThumbUrl { get; init; } = "";

    private ImageSource? _thumb;
    public ImageSource? Thumb
    {
        get => _thumb;
        set { _thumb = value; OnPropertyChanged(); }
    }

    public event PropertyChangedEventHandler? PropertyChanged;
    private void OnPropertyChanged([CallerMemberName] string? name = null) =>
        PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(name));
}

/// <summary>下载网站卡片：host -> 链接组与检测状态。</summary>
public class HostCardItem : INotifyPropertyChanged
{
    public string Host { get; init; } = "";
    public List<string> Urls { get; init; } = [];
    public string CountText { get; init; } = "";

    /// <summary>null=检测中 / true=全部有效 / false=失效或部分 / "queued"=已加入下载。</summary>
    public object? Status { get; set; }

    private string _statusText = "";
    public string StatusText
    {
        get => _statusText;
        set { _statusText = value; OnPropertyChanged(); }
    }

    private Brush _statusBrush = Brushes.Gray;
    public Brush StatusBrush
    {
        get => _statusBrush;
        set { _statusBrush = value; OnPropertyChanged(); }
    }

    public event PropertyChangedEventHandler? PropertyChanged;
    private void OnPropertyChanged([CallerMemberName] string? name = null) =>
        PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(name));
}

/// <summary>社团作品列表条目（RG 搜索结果）。</summary>
public class MakerWorkItem : INotifyPropertyChanged
{
    public string WorkId { get; init; } = "";
    public string Title { get; init; } = "";
    public string ThumbUrl { get; init; } = "";

    private ImageSource? _thumb;
    public ImageSource? Thumb
    {
        get => _thumb;
        set { _thumb = value; OnPropertyChanged(); }
    }

    public event PropertyChangedEventHandler? PropertyChanged;
    private void OnPropertyChanged([CallerMemberName] string? name = null) =>
        PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(name));
}

/// <summary>搜索页（对应 Python 版 select_UI.py）。</summary>
public partial class SearchPage : UserControl
{
    private readonly ObservableCollection<SearchResultItem> _results = [];
    private readonly ObservableCollection<HostCardItem> _hostCards = [];
    private readonly ObservableCollection<MakerWorkItem> _makerWorks = [];

    private string? _selectId;
    private DlWork? _workData;     // 当前搜索作品的 DL API 数据，加入下载时写入 works 表
    private int _searchGeneration;  // 新一轮搜索作废旧缩略图加载（仅在重新查询时递增）
    private int _hostGeneration;    // 进入/离开详情时作废旧的网站检测，互不影响缩略图加载

    // 社团（RG）搜索状态
    private bool _fromMaker;        // 当前 AS 结果是否来自社团作品列表（决定返回去向）
    private string? _makerId;
    private int _makerPage;         // 已加载到第几页（0=未加载）
    private bool _makerHasMore;
    private bool _makerLoading;

    /// <summary>点击"← 下载列表"按钮时触发，由主窗口切回下载视图。</summary>
    public event Action? BackToDownloadRequested;

    public SearchPage()
    {
        InitializeComponent();
        ResultList.ItemsSource = _results;
        HostCardList.ItemsSource = _hostCards;
        MakerList.ItemsSource = _makerWorks;
        RetranslateUi();
        I18n.LanguageChanged += RetranslateUi;
    }

    private void RetranslateUi()
    {
        InputBox.ToolTip = I18n.Tr("输入作品号(RJ/BJ/VJ)、社团号(RG)或 DLsite 链接");
        BackToDownloadButton.Content = I18n.Tr("← 下载列表");
        SearchButton.Content = I18n.Tr("查询");
        BackButton.Content = I18n.Tr("← 返回结果");
        LoadingText.Text = I18n.Tr("正在查询…");
    }

    /// <summary>由下载页"重新搜索"触发：填入番号并自动搜索。</summary>
    public async void SearchFor(string workId)
    {
        InputBox.Text = workId;
        await RunSearchAsync();
    }

    private async void SearchButton_Click(object sender, RoutedEventArgs e) => await RunSearchAsync();

    private async void InputBox_KeyDown(object sender, KeyEventArgs e)
    {
        if (e.Key == Key.Enter)
            await RunSearchAsync();
    }

    private void BackButton_Click(object sender, RoutedEventArgs e)
    {
        // 网盘卡片 → 结果列表；结果列表（来自社团）→ 社团作品列表
        if (HostCardList.Visibility == Visibility.Visible)
            ShowResultsPage();
        else if (ResultList.Visibility == Visibility.Visible && _fromMaker)
            ShowMakerPage();
    }

    private void BackToDownloadButton_Click(object sender, RoutedEventArgs e) =>
        BackToDownloadRequested?.Invoke();

    private void ShowResultsPage()
    {
        ResultList.Visibility = Visibility.Visible;
        HostCardList.Visibility = Visibility.Collapsed;
        MakerList.Visibility = Visibility.Collapsed;
        BackButton.Visibility = _fromMaker ? Visibility.Visible : Visibility.Collapsed;
    }

    private void ShowDetailPage()
    {
        ResultList.Visibility = Visibility.Collapsed;
        HostCardList.Visibility = Visibility.Visible;
        MakerList.Visibility = Visibility.Collapsed;
        BackButton.Visibility = Visibility.Visible;
    }

    private void ShowMakerPage()
    {
        ResultList.Visibility = Visibility.Collapsed;
        HostCardList.Visibility = Visibility.Collapsed;
        MakerList.Visibility = Visibility.Visible;
        BackButton.Visibility = Visibility.Collapsed;
    }

    /// <summary>搜索入口：识别输入是作品号还是社团号，分流到对应流程。</summary>
    private async Task RunSearchAsync()
    {
        var (kind, id) = DlsiteApi.ParseSearchInput(InputBox.Text);
        switch (kind)
        {
            case SearchKind.Maker:
                await RunMakerSearchAsync(id);
                break;
            case SearchKind.Work:
                _fromMaker = false;
                await RunWorkSearchAsync(id);
                break;
            default:
                InAppDialog.Warn(this,
                    I18n.Tr("请输入有效的作品号（RJ/BJ/VJ + 数字）、社团号（RG + 数字）或 DLsite 链接"),
                    I18n.Tr("输入错误"));
                break;
        }
    }

    // ---------- 作品搜索（AS 论坛）----------

    /// <summary>按作品号搜索 Anime-sharing 论坛并展示结果。</summary>
    private async Task RunWorkSearchAsync(string workId)
    {
        _searchGeneration++;   // 作废旧缩略图加载
        _hostGeneration++;     // 作废旧网站检测
        _results.Clear();
        _hostCards.Clear();
        _selectId = workId;

        // 已下载过的作品提示用户
        var existed = Db.Select(
            "SELECT \"work_name\", \"down_time\" FROM \"works\" WHERE \"work_id\" = @w", ("@w", _selectId));
        if (existed is { Count: > 0 })
        {
            var workName = existed[0][0] as string ?? "";
            var downTime = existed[0][1]?.ToString() ?? "";
            if (!InAppDialog.Confirm(this,
                    I18n.Format(I18n.Tr("{id} {name}\n该作品已于 {time} 加入过下载，是否继续搜索？"),
                        ("id", _selectId), ("name", workName),
                        ("time", downTime.Length > 19 ? downTime[..19] : downTime)),
                    I18n.Tr("已下载")))
            {
                if (_fromMaker) ShowMakerPage();
                return;
            }
        }

        // 查询期间显示加载遮罩，网络请求在后台执行
        LoadingOverlay.Visibility = Visibility.Visible;
        List<AsSearchResult> results;
        try
        {
            var workTask = DlsiteApi.GetWorkDataAsync(_selectId);
            var searchTask = AnimeSharing.SearchWorkAsync(_selectId);
            await Task.WhenAll(workTask, searchTask);
            _workData = workTask.Result;
            results = searchTask.Result;
        }
        finally
        {
            LoadingOverlay.Visibility = Visibility.Collapsed;
        }
        if (results.Count == 0)
        {
            InAppDialog.Info(this, I18n.Tr("无匹配数据"), I18n.Tr("提示"));
            if (_fromMaker) ShowMakerPage();
            return;
        }

        foreach (var res in results)
            _results.Add(new SearchResultItem
            {
                Title = res.Title,
                Minor = res.Minor,
                Snippet = TrimSnippet(res.Snippet),
                Url = res.Url,
                ThumbUrl = res.Thumb,
            });
        ShowResultsPage();
        _ = LoadThumbnailsAsync(_searchGeneration);
    }

    // ---------- 社团搜索（DLsite 作品列表）----------

    /// <summary>按社团号（RG）拉取该社团作品列表，展示供用户点选。</summary>
    private async Task RunMakerSearchAsync(string makerId)
    {
        _searchGeneration++;
        _hostGeneration++;
        _results.Clear();
        _hostCards.Clear();
        _makerWorks.Clear();
        _makerId = makerId;
        _makerPage = 0;
        _makerHasMore = true;
        _fromMaker = false;
        ShowMakerPage();
        await LoadMakerPageAsync();
    }

    /// <summary>加载社团作品的下一页（首页显示遮罩，后续页静默追加）。</summary>
    private async Task LoadMakerPageAsync()
    {
        if (_makerId == null || _makerLoading || !_makerHasMore)
            return;
        _makerLoading = true;
        var gen = _searchGeneration;
        var firstPage = _makerPage == 0;
        if (firstPage)
            LoadingOverlay.Visibility = Visibility.Visible;
        (List<DlMakerWork> Works, bool HasMore) page;
        try
        {
            page = await DlsiteApi.GetMakerWorksAsync(_makerId, _makerPage + 1);
        }
        finally
        {
            if (firstPage)
                LoadingOverlay.Visibility = Visibility.Collapsed;
        }
        if (gen != _searchGeneration)   // 期间发起了新搜索，丢弃本次结果
        {
            _makerLoading = false;
            return;
        }
        if (page.Works.Count == 0)
        {
            if (firstPage)
                InAppDialog.Info(this, I18n.Tr("未找到该社团的作品"), I18n.Tr("提示"));
            _makerHasMore = false;
            _makerLoading = false;
            return;
        }
        _makerPage++;
        _makerHasMore = page.HasMore;
        var added = new List<MakerWorkItem>();
        foreach (var w in page.Works)
        {
            var item = new MakerWorkItem { WorkId = w.WorkId, Title = w.Title, ThumbUrl = w.Thumb };
            _makerWorks.Add(item);
            added.Add(item);
        }
        _makerLoading = false;
        _ = LoadMakerThumbnailsAsync(added, gen);
    }

    private void MakerList_ScrollChanged(object sender, ScrollChangedEventArgs e)
    {
        // 下拉接近底部时自动加载下一页
        if (!_makerHasMore || _makerLoading || e.ExtentHeight <= 0)
            return;
        if (e.VerticalOffset >= e.ExtentHeight - e.ViewportHeight - 300)
            _ = LoadMakerPageAsync();
    }

    private async void MakerList_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        // 点击社团作品 → 自动用其 RJ 号搜索 AS
        if (MakerList.SelectedItem is not MakerWorkItem item)
            return;
        MakerList.SelectedItem = null;
        InputBox.Text = item.WorkId;
        _fromMaker = true;
        await RunWorkSearchAsync(item.WorkId);
    }

    /// <summary>后台加载社团作品缩略图。</summary>
    private async Task LoadMakerThumbnailsAsync(List<MakerWorkItem> items, int generation)
    {
        using var client = Http.CreateClient(TimeSpan.FromSeconds(15));
        foreach (var item in items)
        {
            if (generation != _searchGeneration)
                return;
            if (string.IsNullOrEmpty(item.ThumbUrl))
                continue;
            try
            {
                var bytes = await client.GetByteArrayAsync(item.ThumbUrl);
                if (generation != _searchGeneration)
                    return;
                var image = new BitmapImage();
                using (var ms = new MemoryStream(bytes))
                {
                    image.BeginInit();
                    image.CacheOption = BitmapCacheOption.OnLoad;
                    image.StreamSource = ms;
                    image.EndInit();
                }
                image.Freeze();
                item.Thumb = image;
            }
            catch (Exception ex) when (ex is HttpRequestException or TaskCanceledException or NotSupportedException)
            {
                // 单张缩略图失败不影响其它
            }
        }
    }

    /// <summary>整理帖子摘要：去掉空行和多余空白，最多保留 6 行。</summary>
    private static string TrimSnippet(string snippet)
    {
        var lines = snippet.Split('\n')
            .Select(l => string.Join(' ', l.Split(' ', StringSplitOptions.RemoveEmptyEntries)))
            .Where(l => l.Length > 0)
            .Take(6);
        return string.Join('\n', lines);
    }

    /// <summary>后台下载搜索结果缩略图（对应 Python 版 ThumbLoader 线程）。</summary>
    private async Task LoadThumbnailsAsync(int generation)
    {
        using var client = Http.CreateClient(TimeSpan.FromSeconds(15));
        foreach (var item in _results.ToList())
        {
            if (generation != _searchGeneration)
                return;  // 新一轮搜索已开始，停止旧缩略图加载
            if (string.IsNullOrEmpty(item.ThumbUrl))
                continue;
            try
            {
                var bytes = await client.GetByteArrayAsync(item.ThumbUrl);
                if (generation != _searchGeneration)
                    return;
                var image = new BitmapImage();
                using (var ms = new MemoryStream(bytes))
                {
                    image.BeginInit();
                    image.CacheOption = BitmapCacheOption.OnLoad;
                    image.StreamSource = ms;
                    image.EndInit();
                }
                image.Freeze();
                item.Thumb = image;
            }
            catch (Exception e) when (e is HttpRequestException or TaskCanceledException or NotSupportedException)
            {
                // 单张缩略图失败不影响其它
            }
        }
    }

    private async void ResultList_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (ResultList.SelectedItem is not SearchResultItem item)
            return;
        ResultList.SelectedItem = null;

        LoadingOverlay.Visibility = Visibility.Visible;
        List<string> urls;
        try
        {
            (urls, _) = await AnimeSharing.GetWorkDownUrlsAsync(item.Url);
        }
        finally
        {
            LoadingOverlay.Visibility = Visibility.Collapsed;
        }
        if (urls.Count == 0)
        {
            // 帖子里没有解析出任何网盘下载链接（如 Request 求档帖），明确提示而不是无反应
            InAppDialog.Info(this, I18n.Tr("该帖子中没有找到下载链接"), I18n.Tr("提示"));
            return;
        }
        BuildHostCards(urls);
        ShowDetailPage();
    }

    private static string HostOf(string url)
    {
        try
        {
            var host = new Uri(url).Host.ToLowerInvariant();
            return host.StartsWith("www.") ? host[4..] : host;
        }
        catch (UriFormatException)
        {
            return url;
        }
    }

    /// <summary>按下载网站分组生成卡片，并为每个网站启动检测任务。</summary>
    private void BuildHostCards(List<string> urlList)
    {
        _hostCards.Clear();
        var generation = ++_hostGeneration;

        // 按域名分组，保持链接出现顺序
        var groups = new Dictionary<string, List<string>>();
        foreach (var url in urlList)
        {
            var host = HostOf(url);
            if (!groups.TryGetValue(host, out var list))
                groups[host] = list = [];
            list.Add(url);
        }

        foreach (var (host, urls) in groups)
        {
            var card = new HostCardItem
            {
                Host = host,
                Urls = urls,
                CountText = I18n.Format(I18n.Tr("{count} 个文件"), ("count", urls.Count)),
                StatusText = I18n.Tr("检测中…"),
                StatusBrush = (Brush)FindResource("CaptionBrush"),
            };
            _hostCards.Add(card);
            _ = CheckHostAsync(card, generation);
        }
    }

    /// <summary>每个网站一个任务，直连检测该网站下所有链接是否有效（不经过中转站）。</summary>
    private async Task CheckHostAsync(HostCardItem card, int generation)
    {
        using var client = LinkChecker.MakeClient();
        int valid = 0, checkedCount = 0;
        foreach (var url in card.Urls)
        {
            var ok = await LinkChecker.CheckUrlAsync(url, client);
            checkedCount++;
            if (ok)
                valid++;
            if (generation != _hostGeneration)
                return;
            if (checkedCount < card.Urls.Count)
                card.StatusText = I18n.Format(I18n.Tr("检测中… {checked}/{total}"),
                    ("checked", checkedCount), ("total", card.Urls.Count));
        }
        if (generation != _hostGeneration)
            return;
        if (valid == card.Urls.Count)
        {
            card.Status = true;
            card.StatusText = I18n.Tr("有效");
            card.StatusBrush = (Brush)FindResource("GreenBrush");
        }
        else if (valid == 0)
        {
            card.Status = false;
            card.StatusText = I18n.Tr("失效");
            card.StatusBrush = (Brush)FindResource("RedBrush");
        }
        else
        {
            // 分卷不全等于不可用，不允许加入下载
            card.Status = false;
            card.StatusText = I18n.Format(I18n.Tr("部分有效 {valid}/{total}"),
                ("valid", valid), ("total", card.Urls.Count));
            card.StatusBrush = (Brush)FindResource("YellowBrush");
        }
    }

    /// <summary>点击检测通过的网站卡片，该网站全部链接通过 debrid-link 中转站下载。</summary>
    private void HostCardList_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (HostCardList.SelectedItem is not HostCardItem card)
            return;
        HostCardList.SelectedItem = null;
        if (card.Status is not true)
            return;  // 失效、分卷不全或还在检测中的网站不加入下载

        // 有媒体库配置时弹窗选择下载目标
        string? targetFolder = null, targetLib = null;
        if (AppConfig.ReadMediaLibs().Count > 0)
        {
            var dialog = new DownTargetDialog();
            if (!dialog.Show(this))
                return;
            targetFolder = dialog.SelectedFolder;
            targetLib = dialog.SelectedLib;
        }

        foreach (var downUrl in card.Urls)
            // url 为主键：重复加入同一作品时覆盖旧记录并重置为待下载（用户已在搜索时确认过）
            Db.Execute(
                "INSERT OR REPLACE INTO \"download_list\" (\"UUID\", \"work_id\", \"url\", \"status\", \"long\", \"delete\") " +
                "VALUES (@uuid, @w, @url, '0', '0', '1')",
                ("@uuid", Guid.NewGuid().ToString()), ("@w", _selectId), ("@url", downUrl));
        RecordWork();
        // 须在 RecordWork 建好 works 行之后落库目标目录，重启后仍可恢复
        if (!string.IsNullOrEmpty(targetFolder))
            DownloadEngine.SetWorkTargetPath(_selectId!, targetFolder, targetLib);
        DownloadEngine.Start();

        card.Status = "queued";
        card.StatusText = I18n.Tr("已加入下载");
        card.StatusBrush = (Brush)FindResource("AccentLightBrush");
    }

    /// <summary>
    /// 把 DL API 返回的作品数据写入 works 表，状态为下载中。
    /// UPSERT：重复入队时只刷新本次下载相关的列，保留已有元数据；
    /// folder/target/target_lib/cover/meta_scanned 重置，重新下载后重新获取。
    /// </summary>
    private void RecordWork()
    {
        var work = _workData;
        Db.Execute(
            "INSERT INTO \"works\" (\"work_id\", \"work_name\", \"maker_id\", \"maker_name\", \"work_type\", " +
            "\"intro_s\", \"age_category\", \"is_ana\", \"state\", \"down_time\") VALUES " +
            "(@w, @n, @mi, @mn, @t, @s, @a, @ana, '下载中', @time) " +
            "ON CONFLICT(\"work_id\") DO UPDATE SET " +
            "\"work_name\" = excluded.\"work_name\", \"maker_id\" = excluded.\"maker_id\", " +
            "\"maker_name\" = excluded.\"maker_name\", \"work_type\" = excluded.\"work_type\", " +
            "\"intro_s\" = excluded.\"intro_s\", \"age_category\" = excluded.\"age_category\", " +
            "\"is_ana\" = excluded.\"is_ana\", \"state\" = excluded.\"state\", \"down_time\" = excluded.\"down_time\", " +
            "\"folder\" = NULL, \"target\" = NULL, \"target_lib\" = NULL, " +
            "\"cover\" = NULL, \"meta_scanned\" = NULL",
            ("@w", _selectId), ("@n", work?.WorkName ?? ""), ("@mi", work?.MakerId ?? ""),
            ("@mn", work?.MakerName ?? ""), ("@t", work?.WorkType ?? ""), ("@s", work?.IntroS ?? ""),
            ("@a", work?.AgeCategory ?? ""), ("@ana", work?.IsAna ?? ""),
            ("@time", DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss.ffffff")));
    }
}
