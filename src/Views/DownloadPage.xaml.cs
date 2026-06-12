using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Linq;
using System.Text.Json;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Threading;
using DASD.Core;
using DASD.Services;

namespace DASD.Views;

/// <summary>下载页子行：单个分卷文件。</summary>
public class DownloadFileItem : ObservableBase
{
    public string Uuid { get; init; } = "";

    private string _fileName = "";
    public string FileName { get => _fileName; set => Set(ref _fileName, value); }

    private double _pct;
    public double Pct { get => _pct; set => Set(ref _pct, value); }

    private string _speedText = "";
    public string SpeedText { get => _speedText; set => Set(ref _speedText, value); }

    private string _statusText = "";
    public string StatusText { get => _statusText; set => Set(ref _statusText, value); }

    private Brush _statusBrush = Brushes.Gray;
    public Brush StatusBrush { get => _statusBrush; set => Set(ref _statusBrush, value); }
}

/// <summary>下载页父行：番号分组。</summary>
public class DownloadGroupItem : ObservableBase
{
    public string WorkId { get; init; } = "";
    public ObservableCollection<DownloadFileItem> Children { get; } = [];

    private bool _isExpanded;
    public bool IsExpanded
    {
        get => _isExpanded;
        set
        {
            if (Set(ref _isExpanded, value))
                Raise(nameof(ChildrenVisibility));
        }
    }

    public Visibility ChildrenVisibility => IsExpanded ? Visibility.Visible : Visibility.Collapsed;

    private double _pct;
    public double Pct
    {
        get => _pct;
        set
        {
            if (Set(ref _pct, value))
                Raise(nameof(PctText));
        }
    }

    public string PctText => $"{(int)Pct}%";

    private string _speedText = "";
    public string SpeedText { get => _speedText; set => Set(ref _speedText, value); }

    private string _statusText = "";
    public string StatusText { get => _statusText; set => Set(ref _statusText, value); }

    private Brush _statusBrush = Brushes.Gray;
    public Brush StatusBrush { get => _statusBrush; set => Set(ref _statusBrush, value); }

    private Visibility _actionsVisibility = Visibility.Collapsed;
    public Visibility ActionsVisibility { get => _actionsVisibility; set => Set(ref _actionsVisibility, value); }

    public string ReparseText => I18n.Tr("重新解析");
    public string ResearchText => I18n.Tr("重新搜索");
}

/// <summary>下载页（对应 Python 版 download_UI.py）。</summary>
public partial class DownloadPage : UserControl
{
    /// <summary>解析失败的番号点击"重新搜索"时触发，由主窗口切回搜索页。</summary>
    public event Action<string>? ResearchRequested;

    /// <summary>点击"已下载"按钮时触发，由主窗口切到已下载视图。</summary>
    public event Action? ShowDownloadedRequested;

    // download_list.status -> 显示文本（中文原文，渲染时经 Tr 翻译）与颜色
    private static readonly Dictionary<string, (string Text, string Color)> StatusMap = new()
    {
        ["0"] = ("等待下载", "#facc15"),
        ["3"] = ("下载中", "#60a5fa"),
        ["1"] = ("已完成", "#4ade80"),
        ["2"] = ("解析失败", "#f87171"),
    };

    private readonly ObservableCollection<DownloadGroupItem> _groups = [];
    private readonly DispatcherTimer _refreshTimer = new() { Interval = TimeSpan.FromSeconds(1) };
    private readonly DispatcherTimer _usageTimer = new() { Interval = TimeSpan.FromSeconds(15) };
    private bool _usageLoading;

    public DownloadPage()
    {
        InitializeComponent();
        GroupList.ItemsSource = _groups;
        _refreshTimer.Tick += (_, _) => Refresh();
        _usageTimer.Tick += (_, _) => _ = FetchUsageAsync();
        RetranslateUi();
        I18n.LanguageChanged += RetranslateUi;
    }

    private void RetranslateUi()
    {
        RefreshButton.Content = I18n.Tr("刷新");
        ClearDoneButton.Content = I18n.Tr("清除已完成");
        ClearAllButton.Content = I18n.Tr("清空列表");
        ShowDownloadedButton.Content = I18n.Tr("已下载");
        UpdateStartButton();
        Refresh();
    }

    private void ShowDownloadedButton_Click(object sender, RoutedEventArgs e) =>
        ShowDownloadedRequested?.Invoke();

    private void Page_IsVisibleChanged(object sender, DependencyPropertyChangedEventArgs e)
    {
        if ((bool)e.NewValue)
        {
            Refresh();
            _refreshTimer.Start();
            _ = FetchUsageAsync();
            _usageTimer.Start();
        }
        else
        {
            _refreshTimer.Stop();
            _usageTimer.Stop();
        }
    }

    private void StartButton_Click(object sender, RoutedEventArgs e)
    {
        // 开始/暂停切换
        if (DownloadEngine.IsRunning)
            DownloadEngine.Stop();
        else
            DownloadEngine.Start();
        UpdateStartButton();
    }

    private void UpdateStartButton()
    {
        if (DownloadEngine.IsRunning)
        {
            if (DownloadEngine.StopRequested)
            {
                // 已请求暂停，等待当前文件停到断点
                StartButton.Content = I18n.Tr("暂停中…");
                StartButton.IsEnabled = false;
            }
            else
            {
                StartButton.Content = I18n.Tr("暂停下载");
                StartButton.IsEnabled = true;
            }
        }
        else
        {
            StartButton.Content = I18n.Tr("开始下载");
            StartButton.IsEnabled = true;
        }
    }

    private void RefreshButton_Click(object sender, RoutedEventArgs e) => Refresh();

    // ---------- debrid-link 用量 ----------

    private async Task FetchUsageAsync()
    {
        if (_usageLoading)
            return;
        _usageLoading = true;
        try
        {
            JsonElement? value;
            using (var client = new DebridLinkClient())
                value = await client.DownloadLimitsAsync();
            UpdateUsage(value);
        }
        catch (Exception)
        {
            UpdateUsage(null);
        }
        finally
        {
            _usageLoading = false;
        }
    }

    private void UpdateUsage(JsonElement? value)
    {
        double? current = null;
        double resetSeconds = 0;
        if (value is { } v && v.ValueKind == JsonValueKind.Object)
        {
            if (v.TryGetProperty("usagePercent", out var usage) &&
                usage.ValueKind == JsonValueKind.Object &&
                usage.TryGetProperty("current", out var cur) &&
                cur.ValueKind == JsonValueKind.Number)
                current = cur.GetDouble();
            if (v.TryGetProperty("nextResetSeconds", out var reset) &&
                reset.ValueKind == JsonValueKind.Object &&
                reset.TryGetProperty("value", out var rv) &&
                rv.ValueKind == JsonValueKind.Number)
                resetSeconds = rv.GetDouble();
        }
        if (current is null)
        {
            UsageLabel.Text = I18n.Tr("debrid-link 使用量 --");
            UsageBar.Value = 0;
            return;
        }
        UsageBar.Value = Math.Min(100, Math.Round(current.Value));
        var text = I18n.Tr("debrid-link 使用量");
        var reset2 = FormatReset(resetSeconds);
        if (reset2.Length > 0)
            text += I18n.Format(I18n.Tr(" · {reset} 后重置"), ("reset", reset2));
        UsageLabel.Text = text;
    }

    /// <summary>把距离流量重置的秒数格式化为 Xh Ym（不足 1 分钟显示 &lt;1m）。</summary>
    private static string FormatReset(double seconds)
    {
        var s = (long)seconds;
        if (s <= 0)
            return "";
        var hours = s / 3600;
        var minutes = s % 3600 / 60;
        if (hours > 0)
            return $"{hours}h{minutes}m";
        return minutes > 0 ? $"{minutes}m" : "<1m";
    }

    // ---------- 列表刷新 ----------

    private static string FormatSpeed(double speed)
    {
        if (speed >= 1024 * 1024)
            return $"{speed / 1024 / 1024:F1} MB/s";
        if (speed >= 1024)
            return $"{speed / 1024:F0} KB/s";
        return $"{speed:F0} B/s";
    }

    /// <summary>从下载链接提取文件名（前台不直接显示链接）。</summary>
    private static string FileNameOf(string url) =>
        url.TrimEnd('/').Split('/')[^1].Split('?')[0];

    /// <summary>返回 (进度百分比, 实时速度 B/s 或 null)。</summary>
    private static (int Pct, double? Speed) FileProgress(string uuid, string status, string dbLong)
    {
        if (status == "1")
            return (100, null);
        if (status == "3" && DownloadEngine.DownloadProgress.TryGetValue(uuid, out var info) &&
            info.Total > 0)
            return ((int)(info.Downloaded * 100 / info.Total), info.Speed);
        // 等待/失败/无实时数据时，退回数据库中记录的进度（断点续传的已完成部分）
        var pct = int.TryParse(dbLong, out var p) ? p : 0;
        return (Math.Min(pct, 100), null);
    }

    private (string Text, string Color) AggregateStatus(string workId, List<string> statuses)
    {
        var done = statuses.Count(s => s == "1");
        if (statuses.Contains("3"))
            return (I18n.Format(I18n.Tr("下载中 {done}/{total}"),
                ("done", done), ("total", statuses.Count)), "#60a5fa");
        if (statuses.Contains("0"))
            return (I18n.Format(I18n.Tr("等待下载 {done}/{total}"),
                ("done", done), ("total", statuses.Count)), "#facc15");
        if (statuses.Contains("2"))
            return (I18n.Format(I18n.Tr("{n} 个解析失败"),
                ("n", statuses.Count(s => s == "2"))), "#f87171");
        // 全部分卷已下载完成：解压前/解压中/移动中显示对应状态
        if (DownloadEngine.UnzipProgress.TryGetValue(workId, out var unzip))
        {
            if (unzip.State == "pending")
                return (I18n.Tr("待解压"), "#facc15");
            if (unzip.State == "moving")
                return (I18n.Format(I18n.Tr("移动中 {pct}%"), ("pct", unzip.Pct)), "#a78bfa");
            return (I18n.Format(I18n.Tr("解压中 {pct}%"), ("pct", unzip.Pct)), "#60a5fa");
        }
        return (I18n.Tr("已完成"), "#4ade80");
    }

    private static Brush BrushOf(string hex) =>
        new SolidColorBrush((Color)ColorConverter.ConvertFromString(hex));

    private void Refresh()
    {
        UpdateStartButton();
        var rows = Db.Select(
            "SELECT \"UUID\", \"work_id\", \"url\", \"status\", \"long\" FROM \"download_list\" ORDER BY rowid");
        if (rows == null)
            return;

        // 按番号分组，同一番号合并为一个父条目
        var groups = new Dictionary<string, List<(string Uuid, string Url, string Status, string Long)>>();
        var order = new List<string>();
        foreach (var row in rows)
        {
            var workId = row[1] as string ?? "";
            if (!groups.TryGetValue(workId, out var list))
            {
                groups[workId] = list = [];
                order.Add(workId);
            }
            list.Add((row[0] as string ?? "", row[2] as string ?? "",
                row[3] as string ?? "", row[4]?.ToString() ?? ""));
        }

        // 同步到现有集合（保留展开状态与滚动位置）
        var existing = _groups.ToDictionary(g => g.WorkId);
        for (var i = _groups.Count - 1; i >= 0; i--)
            if (!groups.ContainsKey(_groups[i].WorkId))
                _groups.RemoveAt(i);

        foreach (var workId in order)
        {
            var items = groups[workId];
            if (!existing.TryGetValue(workId, out var group))
            {
                group = new DownloadGroupItem { WorkId = workId };
                _groups.Add(group);
            }

            var statuses = items.Select(it => it.Status).ToList();
            var (aggText, aggColor) = AggregateStatus(workId, statuses);
            group.StatusText = aggText;
            group.StatusBrush = BrushOf(aggColor);
            // 该番号有分卷解析失败时显示"重新解析/重新搜索"按钮
            group.ActionsVisibility = statuses.Contains("2") && workId.Length > 0
                ? Visibility.Visible
                : Visibility.Collapsed;

            var totalPct = 0;
            var totalSpeed = 0.0;
            var children = group.Children;
            var existingChildren = children.ToDictionary(c => c.Uuid);
            for (var i = children.Count - 1; i >= 0; i--)
                if (!items.Any(it => it.Uuid == children[i].Uuid))
                    children.RemoveAt(i);
            foreach (var it in items)
            {
                var (pct, speed) = FileProgress(it.Uuid, it.Status, it.Long);
                totalPct += pct;
                if (speed is { } s)
                    totalSpeed += s;

                var (rawText, color) = StatusMap.TryGetValue(it.Status, out var mapped)
                    ? mapped
                    : ((string?)null, "#cdd3de");
                var text = rawText != null
                    ? I18n.Tr(rawText)
                    : I18n.Format(I18n.Tr("未知({status})"), ("status", it.Status));

                if (!existingChildren.TryGetValue(it.Uuid, out var child))
                {
                    child = new DownloadFileItem { Uuid = it.Uuid };
                    children.Add(child);
                }
                child.FileName = FileNameOf(it.Url);
                child.Pct = pct;
                child.SpeedText = speed is { } sp ? FormatSpeed(sp) : "";
                child.StatusText = text;
                child.StatusBrush = BrushOf(color);
            }

            group.SpeedText = totalSpeed > 0 ? FormatSpeed(totalSpeed) : "";
            // 解压中时父进度条改为显示解压进度，否则显示分卷下载进度均值
            group.Pct = DownloadEngine.UnzipProgress.TryGetValue(workId, out var unzip)
                ? unzip.Pct
                : (double)totalPct / Math.Max(1, items.Count);
        }
    }

    // ---------- 操作 ----------

    /// <summary>重新解析：把该作品解析失败的分卷重新排队（已完成的保留不动）。</summary>
    private void Reparse_Click(object sender, RoutedEventArgs e)
    {
        if ((sender as FrameworkElement)?.DataContext is not DownloadGroupItem group)
            return;
        Db.Execute(
            "UPDATE \"download_list\" SET \"status\" = '0' WHERE \"work_id\" = @w AND \"status\" = '2'",
            ("@w", group.WorkId));
        DownloadEngine.Start();
        Refresh();
    }

    /// <summary>重新搜索：先确认并删除已下载的分卷与文件夹，再切回搜索页重新搜索。</summary>
    private void Research_Click(object sender, RoutedEventArgs e)
    {
        if ((sender as FrameworkElement)?.DataContext is not DownloadGroupItem group)
            return;
        var answer = MessageBox.Show(
            I18n.Format(I18n.Tr("将删除 {id} 已下载的分卷与文件夹，并重新搜索。是否继续？"),
                ("id", group.WorkId)),
            I18n.Tr("重新搜索"), MessageBoxButton.YesNo, MessageBoxImage.Question,
            MessageBoxResult.No);
        if (answer != MessageBoxResult.Yes)
            return;
        DownloadEngine.PurgeWorkDownload(group.WorkId);
        Refresh();
        ResearchRequested?.Invoke(group.WorkId);
    }

    private void ClearDoneButton_Click(object sender, RoutedEventArgs e)
    {
        // 正在解压（待解压/解压中）的番号其分卷虽已是 '1'，但还未真正完成，保留不清除
        var unzipping = DownloadEngine.UnzipProgress.Keys.ToList();
        if (unzipping.Count > 0)
        {
            var names = new List<string>();
            var args = new List<(string, object?)>();
            for (var i = 0; i < unzipping.Count; i++)
            {
                names.Add($"@u{i}");
                args.Add(($"@u{i}", unzipping[i]));
            }
            Db.Execute(
                $"DELETE FROM \"download_list\" WHERE \"status\" = '1' AND \"work_id\" NOT IN ({string.Join(",", names)})",
                args.ToArray());
        }
        else
        {
            Db.Execute("DELETE FROM \"download_list\" WHERE \"status\" = '1'");
        }
        Refresh();
    }

    private void ClearAllButton_Click(object sender, RoutedEventArgs e)
    {
        if (_groups.Count == 0)
            return;
        var answer = MessageBox.Show(
            I18n.Tr("确定要清空整个下载列表吗？等待中的任务也会被删除。"),
            I18n.Tr("清空下载列表"), MessageBoxButton.YesNo, MessageBoxImage.Question,
            MessageBoxResult.No);
        if (answer != MessageBoxResult.Yes)
            return;
        // 没有下载完成就被删除的番号，从已下载（works 表）中移除
        var rows = Db.Select(
            "SELECT DISTINCT \"work_id\" FROM \"download_list\" WHERE \"status\" != '1'");
        if (rows != null)
            foreach (var row in rows)
                Db.Execute(
                    "DELETE FROM \"works\" WHERE \"work_id\" = @w AND \"state\" = '下载中'",
                    ("@w", row[0] as string ?? ""));
        Db.Execute("DELETE FROM \"download_list\"");
        Refresh();
    }
}
