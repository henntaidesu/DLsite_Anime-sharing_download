using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Data;
using System.Windows.Documents;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using DASD.Core;
using DASD.Services;

namespace DASD.Views;

/// <summary>
/// 媒体库页（对应 Python 版 media_lib_UI.py）：媒体库卡片 → 社团卡片 → 作品卡片 → 作品详情 四级浏览。
/// rootGenres=true 时作为"标签页"使用：根视图为标签（标签 → 社团 → 作品）。
/// </summary>
public partial class MediaLibPage : UserControl
{
    private const int WorksPageSize = 30;   // 作品卡片懒加载：每批数量
    private const string UnknownMaker = ""; // maker_name 为空的作品归到"未知社团"
    private const double WorkCardW = 210, WorkCardH = 248;
    private const double WorkCoverW = 186, WorkCoverH = 140;

    private static readonly string[] VideoExts =
        [".mp4", ".mkv", ".avi", ".wmv", ".mov", ".flv", ".webm", ".m4v", ".ts", ".mpg", ".mpeg"];
    private static readonly string[] AudioExts =
        [".mp3", ".wav", ".flac", ".m4a", ".aac", ".ogg", ".wma", ".opus"];

    private static readonly Dictionary<string, string> AgeMap = new()
    {
        ["1"] = "全年龄", ["2"] = "R-15", ["3"] = "R-18",
    };

    // label → (db列名, 是否多值用 " / " 分割)
    private static readonly Dictionary<string, (string Col, bool Multi)> LinkCols = new()
    {
        ["社团"] = ("maker_name", false),
        ["系列"] = ("series", false),
        ["剧本"] = ("scenario", false),
        ["插画"] = ("illust", false),
        ["声优"] = ("voice_actor", true),
    };

    private readonly bool _rootGenres;
    private readonly WrapPanel _cardsPanel = new();

    private string _level = "libs";  // libs / makers / works / detail / genres / filtered_works
    private string? _currentLib;
    private string? _currentMaker;   // null=未选社团；UnknownMaker=未知社团
    private string? _currentGenre;
    private string? _currentWork;
    private string? _currentWorkFolder;
    private string? _filterCol;
    private string? _filterVal;
    private int _totalWorks;
    private double _worksScrollPos;
    private MediaLibSettingDialog? _settingDialog;

    // 作品视图数据：全部查询结果 / 搜索过滤后的结果（懒加载来源）
    private List<object?[]> _workRows = [];
    private List<object?[]> _filteredRows = [];
    private int _loadedCards;

    // 详情页右侧 信息/文件树 切换
    private Grid? _detailRightHost;
    private FrameworkElement? _detailInfoPanel;
    private FrameworkElement? _detailFileTree;
    private bool _showingFileTree;

    // 文件树视图：左侧轮播图（限高基准）/ 右侧内嵌预览
    private FrameworkElement? _detailSlider;
    private Border? _previewHost;
    private InlineMediaPlayer? _inlinePlayer;

    public MediaLibPage(bool rootGenres)
    {
        InitializeComponent();
        _rootGenres = rootGenres;
        if (rootGenres)
        {
            _level = "genres";
            GenreButton.Visibility = Visibility.Collapsed;      // 根视图就是标签页
            LibSettingButton.Visibility = Visibility.Collapsed; // 媒体库管理只保留在媒体库页
        }
        RetranslateUi();
        I18n.LanguageChanged += RetranslateUi;
    }

    private void RetranslateUi()
    {
        BackButton.Content = I18n.Tr("← 返回");
        GenreButton.Content = I18n.Tr("作品标签");
        LibSettingButton.Content = I18n.Tr("媒体库设置");
        OpenFolderButton.Content = I18n.Tr("打开文件夹");
        ViewFilesButton.Content = I18n.Tr(_showingFileTree ? "作品信息" : "查看作品");
        MoveLibButton.Content = I18n.Tr("移动媒体库");
        SearchBox.ToolTip = I18n.Tr("搜索 RJ号 / 作品名 / 社团");
        Refresh();
    }

    private void Page_IsVisibleChanged(object sender, DependencyPropertyChangedEventArgs e)
    {
        if (!(bool)e.NewValue)
            return;
        // 切换到本页时重新加载数据：先丢弃配置缓存，再重查数据库刷新当前视图
        AppConfig.Reload();
        Refresh();
    }

    // ---------- 导航 ----------

    private void BackButton_Click(object sender, RoutedEventArgs e)
    {
        switch (_level)
        {
            case "filtered_works":
                ShowDetail();
                break;
            case "detail":
                _currentWork = null;
                ShowWorks();
                RestoreWorksScroll();
                break;
            case "works":
                _currentMaker = null;
                ShowMakers();
                break;
            case "makers":
                if (_currentGenre != null)
                {
                    _currentGenre = null;
                    ShowGenres();
                }
                else
                {
                    ShowLibs();
                }
                break;
            case "genres" when !_rootGenres:
                ShowLibs();
                break;
        }
    }

    private void GenreButton_Click(object sender, RoutedEventArgs e)
    {
        _currentLib = null;
        _currentMaker = null;
        _currentGenre = null;
        _currentWork = null;
        ShowGenres();
    }

    private void LibSettingButton_Click(object sender, RoutedEventArgs e)
    {
        // 媒体库设置弹窗（常驻实例，扫描线程随其存活）
        if (_settingDialog == null)
        {
            _settingDialog = new MediaLibSettingDialog { Owner = Window.GetWindow(this) };
            _settingDialog.LibsChanged += Refresh;
            _settingDialog.ScanDone += Refresh;
        }
        _settingDialog.Show();
        _settingDialog.Activate();
    }

    private void OpenFolderButton_Click(object sender, RoutedEventArgs e)
    {
        if (_currentWorkFolder != null && Directory.Exists(_currentWorkFolder))
            Process.Start(new ProcessStartInfo("explorer.exe", $"\"{_currentWorkFolder}\""));
    }

    private void MoveLibButton_Click(object sender, RoutedEventArgs e)
    {
        // 把当前作品移动到另一个媒体库：移动文件夹 + 改库 + 同步元数据
        var workId = _currentWork;
        if (workId == null)
            return;
        if (_currentWorkFolder == null || !Directory.Exists(_currentWorkFolder))
        {
            MessageBox.Show(I18n.Tr("作品文件夹不存在，无法移动"), I18n.Tr("移动媒体库"),
                MessageBoxButton.OK, MessageBoxImage.Warning);
            return;
        }
        var currentLib = Db.Scalar(
            "SELECT \"library\" FROM \"works\" WHERE \"work_id\" = @w", ("@w", workId)) as string;

        var dialog = new DownTargetDialog(currentLib, moveMode: true) { Owner = Window.GetWindow(this) };
        if (dialog.ShowDialog() != true || dialog.SelectedFolder == null)
            return;
        var targetLib = dialog.SelectedLib!;
        var targetFolder = dialog.SelectedFolder;
        var answer = MessageBox.Show(
            I18n.Format(I18n.Tr("确定将 {id} 移动到媒体库“{lib}”吗？"), ("id", workId), ("lib", targetLib)),
            I18n.Tr("移动媒体库"), MessageBoxButton.YesNo, MessageBoxImage.Question, MessageBoxResult.No);
        if (answer != MessageBoxResult.Yes)
            return;

        MoveLibButton.IsEnabled = false;
        MoveLibButton.Content = I18n.Tr("移动中…");
        _ = MoveWorkAsync(workId, targetLib, targetFolder);
    }

    private async Task MoveWorkAsync(string workId, string targetLib, string targetFolder)
    {
        var (ok, message) = await Task.Run(() =>
            MediaLibraryService.MoveWorkToLibraryAsync(workId, targetLib, targetFolder));
        MoveLibButton.IsEnabled = true;
        MoveLibButton.Content = I18n.Tr("移动媒体库");
        if (ok)
        {
            MessageBox.Show(I18n.Tr("已移动到新媒体库"), I18n.Tr("移动媒体库"),
                MessageBoxButton.OK, MessageBoxImage.Information);
            Refresh();  // 重新载入详情，反映新的媒体库与文件夹
        }
        else
        {
            MessageBox.Show(message, I18n.Tr("移动媒体库"), MessageBoxButton.OK, MessageBoxImage.Warning);
        }
    }

    private void ViewFilesButton_Click(object sender, RoutedEventArgs e)
    {
        // 详情页右侧在"信息面板"与"文件树"之间切换
        if (_detailRightHost == null || _currentWorkFolder == null)
            return;
        if (!_showingFileTree)
        {
            _detailFileTree ??= BuildFileTree(_currentWorkFolder);  // 首次切换时才构建文件树
            _detailRightHost.Children.Clear();
            _detailRightHost.Children.Add(_detailFileTree);
            _showingFileTree = true;
            ViewFilesButton.Content = I18n.Tr("作品信息");
        }
        else
        {
            StopPreview();
            _detailRightHost.Children.Clear();
            if (_detailInfoPanel != null)
                _detailRightHost.Children.Add(_detailInfoPanel);
            _showingFileTree = false;
            ViewFilesButton.Content = I18n.Tr("查看作品");
        }
    }

    public void Refresh()
    {
        // 重新加载当前层级的视图
        var names = AppConfig.ReadMediaLibs().Select(l => l.Name).ToHashSet();
        if (_currentLib != null && !names.Contains(_currentLib))
            ShowRoot();  // 当前库已被删除/改名，回到根视图
        else if (_level == "filtered_works" && _filterCol != null)
            ShowFilteredWorks();
        else if (_level == "detail" && _currentWork != null)
            ShowDetail();
        else if (_level is "works" && _currentMaker != null)
            ShowWorks();
        else if (_level == "makers" && (_currentLib != null || _currentGenre != null))
            ShowMakers();
        else if (_level == "genres")
            ShowGenres();
        else
            ShowRoot();
    }

    private void ShowRoot()
    {
        if (_rootGenres)
            ShowGenres();
        else
            ShowLibs();
    }

    // ---------- 视图构建 ----------

    private void ClearCards()
    {
        _cardsPanel.Children.Clear();
        ContentHost.Content = _cardsPanel;
        OpenFolderButton.Visibility = Visibility.Collapsed;
        ViewFilesButton.Visibility = Visibility.Collapsed;
        ViewFilesButton.Content = I18n.Tr("查看作品");
        MoveLibButton.Visibility = Visibility.Collapsed;
        _detailRightHost = null;
        _detailInfoPanel = null;
        _detailFileTree = null;
        _showingFileTree = false;
        _currentWorkFolder = null;
        _inlinePlayer?.Shutdown();
        _inlinePlayer = null;
        _previewHost = null;
        _detailSlider = null;
    }

    private Border MakeClickCard(string title, string caption, Action onClick)
    {
        var card = new Border
        {
            Style = (Style)FindResource("Card"),
            Width = WorkCardW,
            Height = 110,
            Margin = new Thickness(0, 0, 10, 10),
            Cursor = Cursors.Hand,
            Tag = title.ToLowerInvariant(),  // 搜索过滤用
        };
        var panel = new StackPanel();
        panel.Children.Add(new TextBlock
        {
            Text = title, FontWeight = FontWeights.SemiBold, FontSize = 15, TextWrapping = TextWrapping.Wrap,
        });
        panel.Children.Add(new TextBlock
        {
            Text = caption, Style = (Style)FindResource("CaptionText"), Margin = new Thickness(0, 6, 0, 0),
        });
        card.Child = panel;
        card.MouseLeftButtonUp += (_, _) => onClick();
        return card;
    }

    /// <summary>一级：媒体库卡片。</summary>
    private void ShowLibs()
    {
        _level = "libs";
        _currentLib = null;
        _currentMaker = null;
        BackButton.Visibility = Visibility.Collapsed;
        var counts = new Dictionary<string, long>();
        var rows = Db.Select(
            "SELECT \"library\", COUNT(*) FROM \"works\" WHERE \"state\" = '已品悦' GROUP BY \"library\"");
        if (rows != null)
            foreach (var row in rows)
                counts[row[0] as string ?? ""] = Convert.ToInt64(row[1]);
        _totalWorks = (int)counts.Values.Sum();
        ClearCards();
        foreach (var lib in AppConfig.ReadMediaLibs())
        {
            var name = lib.Name;
            var caption = I18n.Format(I18n.Tr("{works} 个作品 · {folders} 个文件夹"),
                ("works", counts.GetValueOrDefault(name)), ("folders", lib.Folders.Count));
            _cardsPanel.Children.Add(MakeClickCard(name, caption, () =>
            {
                _currentLib = name;
                _currentMaker = null;
                _currentGenre = null;
                ShowMakers();
            }));
        }
        ApplyCardFilter();
    }

    /// <summary>二级：当前媒体库（或当前标签）下的社团卡片。</summary>
    private void ShowMakers()
    {
        _level = "makers";
        _currentMaker = null;
        BackButton.Visibility = Visibility.Visible;
        List<object?[]>? rows;
        if (_currentGenre != null)
            rows = Db.Select(
                "SELECT w.\"maker_name\", COUNT(*) FROM \"works\" w " +
                "JOIN \"work_genres\" g ON g.\"work_id\" = w.\"work_id\" " +
                "WHERE w.\"state\" = '已品悦' AND g.\"genre\" = @g " +
                "GROUP BY w.\"maker_name\" ORDER BY COUNT(*) DESC",
                ("@g", _currentGenre));
        else
            rows = Db.Select(
                "SELECT \"maker_name\", COUNT(*) FROM \"works\" " +
                "WHERE \"state\" = '已品悦' AND \"library\" = @lib " +
                "GROUP BY \"maker_name\" ORDER BY COUNT(*) DESC",
                ("@lib", _currentLib ?? ""));
        if (rows == null)
            return;
        _totalWorks = (int)rows.Sum(r => Convert.ToInt64(r[1]));
        ClearCards();
        foreach (var row in rows)
        {
            var maker = row[0] as string ?? "";
            var count = Convert.ToInt64(row[1]);
            var title = maker.Length > 0 ? maker : I18n.Tr("未知社团");
            _cardsPanel.Children.Add(MakeClickCard(
                title, I18n.Format(I18n.Tr("{count} 个作品"), ("count", count)),
                () =>
                {
                    _currentMaker = maker.Length > 0 ? maker : UnknownMaker;
                    ShowWorks();
                }));
        }
        ApplyCardFilter();
    }

    /// <summary>标签视图：全部已品悦作品的ジャンル标签卡片。</summary>
    private void ShowGenres()
    {
        _level = "genres";
        BackButton.Visibility = _rootGenres ? Visibility.Collapsed : Visibility.Visible;
        var rows = Db.Select(
            "SELECT g.\"genre\", COUNT(*) FROM \"work_genres\" g " +
            "JOIN \"works\" w ON w.\"work_id\" = g.\"work_id\" " +
            "WHERE w.\"state\" = '已品悦' GROUP BY g.\"genre\" ORDER BY COUNT(*) DESC");
        if (rows == null)
            return;
        var total = Db.Scalar(
            "SELECT COUNT(DISTINCT g.\"work_id\") FROM \"work_genres\" g " +
            "JOIN \"works\" w ON w.\"work_id\" = g.\"work_id\" WHERE w.\"state\" = '已品悦'");
        _totalWorks = total != null ? (int)Convert.ToInt64(total) : 0;
        ClearCards();
        foreach (var row in rows)
        {
            var genre = row[0] as string ?? "";
            var count = Convert.ToInt64(row[1]);
            _cardsPanel.Children.Add(MakeClickCard(
                genre, I18n.Format(I18n.Tr("{count} 个作品"), ("count", count)),
                () => OpenGenre(genre)));
        }
        ApplyCardFilter();
    }

    private void OpenGenre(string genre)
    {
        _currentGenre = genre;
        ShowMakers();
    }

    /// <summary>三级：当前社团的作品卡片（标签流程下为 标签+社团）。</summary>
    private void ShowWorks()
    {
        _level = "works";
        BackButton.Visibility = Visibility.Visible;
        List<object?[]>? rows;
        var makerCond = _currentMaker == UnknownMaker
            ? "(\"maker_name\" IS NULL OR \"maker_name\" = '')"
            : "\"maker_name\" = @maker";
        if (_currentGenre != null)
            rows = Db.Select(
                "SELECT w.\"work_id\", w.\"work_name\", w.\"maker_name\", w.\"work_type\", " +
                "w.\"age_category\", w.\"cover\" FROM \"works\" w " +
                "JOIN \"work_genres\" g ON g.\"work_id\" = w.\"work_id\" " +
                $"WHERE w.\"state\" = '已品悦' AND g.\"genre\" = @g AND {makerCond.Replace("\"maker_name\"", "w.\"maker_name\"")} " +
                "ORDER BY w.\"work_id\" DESC",
                ("@g", _currentGenre), ("@maker", _currentMaker ?? ""));
        else
            rows = Db.Select(
                "SELECT \"work_id\", \"work_name\", \"maker_name\", \"work_type\", \"age_category\", \"cover\" " +
                $"FROM \"works\" WHERE \"state\" = '已品悦' AND \"library\" = @lib AND {makerCond} " +
                "ORDER BY \"work_id\" DESC",
                ("@lib", _currentLib ?? ""), ("@maker", _currentMaker ?? ""));
        if (rows == null)
            return;
        _workRows = rows;
        ApplyCardFilter();
    }

    /// <summary>按单列值过滤的作品视图（跨所有媒体库），由详情页可点击字段触发。</summary>
    private void ShowFilteredWorks()
    {
        _level = "filtered_works";
        BackButton.Visibility = Visibility.Visible;
        var cond = _filterCol == "voice_actor"
            ? "\"voice_actor\" LIKE @val"
            : $"\"{_filterCol}\" = @val";
        var value = _filterCol == "voice_actor" ? $"%{_filterVal}%" : _filterVal;
        var rows = Db.Select(
            "SELECT \"work_id\", \"work_name\", \"maker_name\", \"work_type\", \"age_category\", \"cover\" " +
            $"FROM \"works\" WHERE \"state\" = '已品悦' AND {cond} ORDER BY \"work_id\" DESC",
            ("@val", value));
        if (rows == null)
            return;
        _workRows = rows;
        ApplyCardFilter();
    }

    private void OpenFilter(string column, string value)
    {
        _filterCol = column;
        _filterVal = value;
        ShowFilteredWorks();
    }

    // ---------- 过滤与懒加载 ----------

    private void SearchBox_TextChanged(object sender, TextChangedEventArgs e) => ApplyCardFilter();

    private void ApplyCardFilter()
    {
        if (_level == "detail")
            return;
        var keyword = SearchBox.Text.Trim().ToLowerInvariant();
        if (_level is "works" or "filtered_works")
        {
            // 作品视图：在全量查询结果上过滤，再懒加载
            _filteredRows = keyword.Length == 0
                ? _workRows.ToList()
                : _workRows.Where(r =>
                    $"{r[0]} {r[1]} {r[2]}".ToLowerInvariant().Contains(keyword)).ToList();
            ClearCards();
            BackButton.Visibility = Visibility.Visible;
            _loadedCards = 0;
            LoadMoreWorks();
            return;
        }
        var shown = 0;
        var totalCards = 0;
        foreach (var child in _cardsPanel.Children.OfType<Border>())
        {
            totalCards++;
            var visible = keyword.Length == 0 ||
                          (child.Tag as string ?? "").Contains(keyword);
            child.Visibility = visible ? Visibility.Visible : Visibility.Collapsed;
            if (visible)
                shown++;
        }
        var unit = I18n.Tr(_level switch
        {
            "makers" => "个社团",
            "genres" => "个标签",
            _ => "个媒体库",
        });
        CountLabel.Text = keyword.Length > 0
            ? I18n.Format(I18n.Tr("共 {total} {unit}，匹配 {shown} 个"),
                ("total", totalCards), ("unit", unit), ("shown", shown))
            : I18n.Format(I18n.Tr("共 {total} {unit}，{works} 个作品"),
                ("total", totalCards), ("unit", unit), ("works", _totalWorks));
    }

    /// <summary>作品视图：追加加载下一批卡片。</summary>
    private void LoadMoreWorks()
    {
        var batch = _filteredRows.Skip(_loadedCards).Take(WorksPageSize).ToList();
        foreach (var row in batch)
            _cardsPanel.Children.Add(MakeWorkCard(row));
        _loadedCards += batch.Count;

        var keyword = SearchBox.Text.Trim();
        var total = _workRows.Count;
        var matched = _filteredRows.Count;
        var text = keyword.Length > 0
            ? I18n.Format(I18n.Tr("共 {total} 个作品，匹配 {matched} 个"), ("total", total), ("matched", matched))
            : I18n.Format(I18n.Tr("共 {total} 个作品"), ("total", total));
        if (_loadedCards < matched)
            text += I18n.Format(I18n.Tr("（已加载 {loaded}）"), ("loaded", _loadedCards));
        CountLabel.Text = text;
    }

    private void CardsScroll_ScrollChanged(object sender, ScrollChangedEventArgs e)
    {
        // 滚动接近底部时加载下一批作品卡片
        if (_level is not ("works" or "filtered_works") || _loadedCards >= _filteredRows.Count)
            return;
        if (e.VerticalOffset >= CardsScroll.ScrollableHeight - 300)
            LoadMoreWorks();
    }

    private void RestoreWorksScroll()
    {
        var target = _worksScrollPos;
        if (target <= 0)
            return;
        // 预加载直到内容高度能容纳目标滚动位置
        while (_loadedCards < _filteredRows.Count &&
               _cardsPanel.ActualHeight < target + CardsScroll.ViewportHeight)
        {
            LoadMoreWorks();
            _cardsPanel.UpdateLayout();
        }
        Dispatcher.BeginInvoke(() => CardsScroll.ScrollToVerticalOffset(target));
    }

    /// <summary>单个作品卡片：封面 + 角标（RJ号/形式）+ 标题。</summary>
    private Border MakeWorkCard(object?[] row)
    {
        var workId = row[0] as string ?? "";
        var workName = row[1] as string ?? "";
        var makerName = row[2] as string ?? "";
        var workType = row[3] as string ?? "";
        var cover = row[5] as string;

        var card = new Border
        {
            Style = (Style)FindResource("Card"),
            Width = WorkCardW,
            Height = WorkCardH,
            Margin = new Thickness(0, 0, 10, 10),
            Cursor = Cursors.Hand,
            ToolTip = workName.Length > 0 ? workName : workId,
        };
        var panel = new StackPanel();

        // 封面区固定大小：图片按比例铺满裁切，无封面时显示纯色底
        var coverGrid = new Grid { Width = WorkCoverW, Height = WorkCoverH, ClipToBounds = true };
        coverGrid.Children.Add(new Border
        {
            Background = new SolidColorBrush(Color.FromArgb(12, 255, 255, 255)),
            CornerRadius = new CornerRadius(4),
        });
        if (cover != null && File.Exists(cover))
        {
            var image = new Image { Stretch = Stretch.UniformToFill };
            try
            {
                var bmp = new BitmapImage();
                bmp.BeginInit();
                bmp.CacheOption = BitmapCacheOption.OnLoad;
                bmp.UriSource = new Uri(cover);
                bmp.DecodePixelWidth = (int)WorkCoverW * 2;  // 控制解码尺寸防内存膨胀
                bmp.EndInit();
                bmp.Freeze();
                image.Source = bmp;
                coverGrid.Children.Add(image);
            }
            catch (Exception)
            {
                // 单张封面读取失败不影响整页
            }
        }
        // RJ 号：封面左上角；作品形式：右上角
        var badgeStyleBg = new SolidColorBrush(Color.FromArgb(170, 0, 0, 0));
        var rjBadge = new Border
        {
            Background = badgeStyleBg, CornerRadius = new CornerRadius(4),
            Padding = new Thickness(6, 1, 6, 1),
            HorizontalAlignment = HorizontalAlignment.Left, VerticalAlignment = VerticalAlignment.Top,
            Margin = new Thickness(4),
            Child = new TextBlock { Text = workId, FontSize = 11, Foreground = Brushes.WhiteSmoke },
        };
        coverGrid.Children.Add(rjBadge);
        if (workType.Length > 0)
            coverGrid.Children.Add(new Border
            {
                Background = badgeStyleBg, CornerRadius = new CornerRadius(4),
                Padding = new Thickness(6, 1, 6, 1),
                HorizontalAlignment = HorizontalAlignment.Right, VerticalAlignment = VerticalAlignment.Top,
                Margin = new Thickness(4),
                MaxWidth = WorkCoverW - 80,
                Child = new TextBlock
                {
                    Text = workType, FontSize = 11, Foreground = Brushes.WhiteSmoke,
                    TextTrimming = TextTrimming.CharacterEllipsis,
                },
            });
        panel.Children.Add(coverGrid);

        panel.Children.Add(new TextBlock
        {
            Text = workName.Length > 0 ? workName : workId,
            FontWeight = FontWeights.SemiBold,
            TextWrapping = TextWrapping.Wrap,
            TextTrimming = TextTrimming.CharacterEllipsis,
            MaxHeight = 80,
            Margin = new Thickness(0, 6, 0, 0),
        });
        card.Child = panel;
        card.MouseLeftButtonUp += (_, _) =>
        {
            _worksScrollPos = CardsScroll.VerticalOffset;
            _currentWork = workId;
            ShowDetail();
        };
        return card;
    }

    // ---------- 作品详情 ----------

    private void ShowDetail()
    {
        var rows = Db.Select(
            "SELECT \"work_id\", \"work_name\", \"maker_name\", \"sell_date\", \"series\", " +
            "\"scenario\", \"illust\", \"voice_actor\", \"age_category\", \"work_type\", " +
            "\"genre\", \"file_size\", \"intro_s\", \"folder\" FROM \"works\" WHERE \"work_id\" = @w",
            ("@w", _currentWork));
        if (rows is not { Count: > 0 })
            return;
        var r = rows[0];
        var workId = r[0] as string ?? "";
        var workName = r[1] as string ?? "";
        var workFolder = r[13] as string;

        _level = "detail";
        BackButton.Visibility = Visibility.Visible;
        CountLabel.Text = workId;
        ClearCards();
        if (workFolder != null && Directory.Exists(workFolder))
        {
            _currentWorkFolder = workFolder;
            OpenFolderButton.Visibility = Visibility.Visible;
            ViewFilesButton.Visibility = Visibility.Visible;
            MoveLibButton.Visibility = Visibility.Visible;
        }

        var root = new Border
        {
            Style = (Style)FindResource("Card"),
            Padding = new Thickness(20, 16, 20, 16),
        };
        var layout = new StackPanel();
        root.Child = layout;

        layout.Children.Add(new TextBlock
        {
            Text = workName.Length > 0 ? workName : workId,
            FontWeight = FontWeights.SemiBold, FontSize = 18, TextWrapping = TextWrapping.Wrap,
        });

        var folder = workFolder != null ? Path.Combine(workFolder, DlsitePage.DataSourceDir) : "";
        if (!Directory.Exists(folder))
            folder = Path.Combine(DlsitePage.ImagesDir, workId);

        // 正文：按 [img:文件名] 占位标记拆成 文本/图片 块
        var bodyBlocks = new List<(string Kind, string Value)>();
        var bodyFiles = new HashSet<string>();
        var txtPath = Path.Combine(folder, DlsitePage.DescriptionTxt);
        if (File.Exists(txtPath))
        {
            string bodyText;
            try
            {
                bodyText = File.ReadAllText(txtPath).Trim();
            }
            catch (IOException)
            {
                bodyText = "";
            }
            var buf = new List<string>();
            foreach (var line in bodyText.Split('\n'))
            {
                var match = DlsitePage.BodyImageRe.Match(line.Trim());
                if (match.Success)
                {
                    if (buf.Count > 0)
                    {
                        bodyBlocks.Add(("text", string.Join('\n', buf)));
                        buf.Clear();
                    }
                    bodyBlocks.Add(("image", match.Groups[1].Value));
                    bodyFiles.Add(match.Groups[1].Value);
                }
                else
                {
                    buf.Add(line);
                }
            }
            if (buf.Count > 0)
                bodyBlocks.Add(("text", string.Join('\n', buf)));
        }

        // 轮播图：数据源中除正文图片外的图片，主图排最前
        var sliderPaths = new List<string>();
        if (Directory.Exists(folder))
        {
            var names = Directory.GetFiles(folder)
                .Select(Path.GetFileName)
                .Where(f => f != null &&
                            DlsitePage.ImageExts.Contains(Path.GetExtension(f).ToLowerInvariant()) &&
                            !bodyFiles.Contains(f))
                .Select(f => f!)
                .OrderBy(f => f.Contains("img_main", StringComparison.OrdinalIgnoreCase) ? 0 : 1)
                .ThenBy(f => f, StringComparer.OrdinalIgnoreCase)
                .ToList();
            sliderPaths = names.Select(f => Path.Combine(folder, f)).ToList();
        }

        // 字段网格（带可点击链接）
        var infoPanel = BuildDetailFields(workId, r);
        _detailInfoPanel = infoPanel;

        // 上半部分：左边轮播图（1/3），右边字段详情（2/3）
        var content = new Grid { Margin = new Thickness(0, 10, 0, 0) };
        content.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
        content.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(2, GridUnitType.Star) });
        if (sliderPaths.Count > 0)
        {
            var slider = new ImageSliderControl(sliderPaths) { VerticalAlignment = VerticalAlignment.Top };
            Grid.SetColumn(slider, 0);
            content.Children.Add(slider);
            _detailSlider = slider;
        }
        var rightHost = new Grid { Margin = new Thickness(20, 0, 0, 0) };
        rightHost.Children.Add(infoPanel);
        Grid.SetColumn(rightHost, 1);
        content.Children.Add(rightHost);
        _detailRightHost = rightHost;
        layout.Children.Add(content);

        // 正文：文本与图片按原文顺序嵌入
        var maxWidth = Math.Max(360, CardsScroll.ViewportWidth - 100);
        foreach (var (kind, value) in bodyBlocks)
        {
            if (kind == "text")
            {
                if (value.Trim().Length == 0)
                    continue;
                layout.Children.Add(new TextBox
                {
                    Text = value,
                    IsReadOnly = true,
                    TextWrapping = TextWrapping.Wrap,
                    BorderThickness = new Thickness(0),
                    Background = Brushes.Transparent,
                    Margin = new Thickness(0, 10, 0, 0),
                });
            }
            else
            {
                var path = Path.Combine(folder, value);
                if (!File.Exists(path))
                    continue;
                try
                {
                    var bmp = new BitmapImage();
                    bmp.BeginInit();
                    bmp.CacheOption = BitmapCacheOption.OnLoad;
                    bmp.UriSource = new Uri(path);
                    bmp.EndInit();
                    bmp.Freeze();
                    layout.Children.Add(new Image
                    {
                        Source = bmp,
                        MaxWidth = maxWidth,
                        Stretch = Stretch.Uniform,
                        HorizontalAlignment = HorizontalAlignment.Left,
                        Margin = new Thickness(0, 10, 0, 0),
                    });
                }
                catch (Exception)
                {
                    // 单张正文图加载失败跳过
                }
            }
        }

        ContentHost.Content = root;
        CardsScroll.ScrollToVerticalOffset(0);
    }

    /// <summary>详情字段网格：社团/声优等渲染为可点击链接，标签来自 work_genres 表。</summary>
    private FrameworkElement BuildDetailFields(string workId, object?[] r)
    {
        var fields = new (string Label, string? Value)[]
        {
            ("社团", r[2] as string), ("販売日", r[3] as string),
            ("系列", r[4] as string), ("剧本", r[5] as string), ("插画", r[6] as string),
            ("声优", r[7] as string), ("年龄分级", r[8]?.ToString()), ("作品形式", r[9] as string),
            ("类型", r[10] as string), ("文件容量", r[11] as string), ("简介", r[12] as string),
        };
        var tags = Db.Select(
            "SELECT \"genre\" FROM \"work_genres\" WHERE \"work_id\" = @w", ("@w", workId));

        var grid = new Grid();
        grid.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
        grid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
        var row = 0;
        foreach (var (label, value) in fields)
        {
            FrameworkElement valueElement;
            if (label == "类型" && tags is { Count: > 0 })
            {
                // 标签渲染为可点击链接
                var tb = new TextBlock { TextWrapping = TextWrapping.Wrap };
                foreach (var tagRow in tags)
                {
                    var tag = tagRow[0] as string ?? "";
                    var link = new Hyperlink(new Run(tag))
                    {
                        Foreground = (Brush)FindResource("AccentLightBrush"),
                        TextDecorations = null,
                    };
                    var captured = tag;
                    link.Click += (_, _) =>
                    {
                        _currentGenre = captured;
                        _currentLib = null;
                        _currentMaker = null;
                        ShowMakers();
                    };
                    tb.Inlines.Add(link);
                    tb.Inlines.Add(new Run("　"));
                }
                valueElement = tb;
            }
            else if (string.IsNullOrEmpty(value))
            {
                continue;
            }
            else if (label == "年龄分级")
            {
                var display = I18n.Tr(AgeMap.GetValueOrDefault(value, value));
                valueElement = MakeLinkBlock(display, () => OpenFilter("age_category", value));
            }
            else if (LinkCols.TryGetValue(label, out var linkInfo))
            {
                var parts = linkInfo.Multi
                    ? value.Split(" / ").Select(p => p.Trim()).Where(p => p.Length > 0).ToList()
                    : [value.Trim()];
                var tb = new TextBlock { TextWrapping = TextWrapping.Wrap };
                for (var i = 0; i < parts.Count; i++)
                {
                    var part = parts[i];
                    var link = new Hyperlink(new Run(part))
                    {
                        Foreground = (Brush)FindResource("AccentLightBrush"),
                        TextDecorations = null,
                    };
                    link.Click += (_, _) => OpenFilter(linkInfo.Col, part);
                    tb.Inlines.Add(link);
                    if (i < parts.Count - 1)
                        tb.Inlines.Add(new Run(" / "));
                }
                valueElement = tb;
            }
            else
            {
                valueElement = new TextBox
                {
                    Text = value, IsReadOnly = true, TextWrapping = TextWrapping.Wrap,
                    BorderThickness = new Thickness(0), Background = Brushes.Transparent,
                    Padding = new Thickness(0),
                };
            }

            grid.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
            var keyLabel = new TextBlock
            {
                Text = I18n.Tr(label),
                Style = (Style)FindResource("CaptionText"),
                Margin = new Thickness(0, 3, 16, 3),
                VerticalAlignment = VerticalAlignment.Top,
            };
            Grid.SetRow(keyLabel, row);
            Grid.SetColumn(keyLabel, 0);
            grid.Children.Add(keyLabel);
            valueElement.Margin = new Thickness(0, 3, 0, 3);
            Grid.SetRow(valueElement, row);
            Grid.SetColumn(valueElement, 1);
            grid.Children.Add(valueElement);
            row++;
        }
        return grid;
    }

    private TextBlock MakeLinkBlock(string text, Action onClick)
    {
        var link = new Hyperlink(new Run(text))
        {
            Foreground = (Brush)FindResource("AccentLightBrush"),
            TextDecorations = null,
        };
        link.Click += (_, _) => onClick();
        var tb = new TextBlock { TextWrapping = TextWrapping.Wrap };
        tb.Inlines.Add(link);
        return tb;
    }

    // ---------- 文件树 ----------

    /// <summary>文件树面板：左列目录树 + 右列内嵌预览（图片/视频），整体高度不超过左侧轮播图。</summary>
    private FrameworkElement BuildFileTree(string root)
    {
        var panel = new Grid();
        panel.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
        panel.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
        // 限高：跟随左侧轮播图实际高度，树内容超出时自行滚动
        if (_detailSlider != null)
            panel.SetBinding(MaxHeightProperty,
                new Binding(nameof(ActualHeight)) { Source = _detailSlider });
        else
            panel.MaxHeight = 480;

        var tree = new TreeView
        {
            Background = Brushes.Transparent,
            BorderThickness = new Thickness(0),
        };
        PopulateTree(tree.Items, root, depth: 0);
        tree.SelectedItemChanged += (_, e) =>
        {
            if (e.NewValue is TreeViewItem { Tag: string path } && File.Exists(path))
                ShowPreview(path);
        };
        panel.Children.Add(tree);

        var previewHost = new Border
        {
            Background = new SolidColorBrush(Color.FromRgb(0x11, 0x11, 0x11)),
            CornerRadius = new CornerRadius(4),
            Margin = new Thickness(12, 0, 0, 0),
            Child = MakePreviewPlaceholder(),
        };
        Grid.SetColumn(previewHost, 1);
        panel.Children.Add(previewHost);
        _previewHost = previewHost;
        return panel;
    }

    /// <summary>递归填充：文件夹在前、文件在后，各自按名称排序；根层级默认展开。</summary>
    private void PopulateTree(ItemCollection items, string path, int depth)
    {
        string[] entries;
        try
        {
            entries = Directory.GetFileSystemEntries(path);
        }
        catch (Exception e) when (e is IOException or UnauthorizedAccessException)
        {
            return;
        }
        foreach (var entry in entries
                     .OrderBy(p => Directory.Exists(p) ? 0 : 1)
                     .ThenBy(Path.GetFileName, StringComparer.OrdinalIgnoreCase))
        {
            var item = new TreeViewItem
            {
                Header = Path.GetFileName(entry),
                Tag = entry,
                Foreground = (Brush)FindResource("TextBrush"),
                IsExpanded = depth == 0,
            };
            if (Directory.Exists(entry))
                PopulateTree(item.Items, entry, depth + 1);
            else
                item.MouseDoubleClick += (_, e2) =>
                {
                    e2.Handled = true;
                    OpenTreeFile(entry);
                };
            items.Add(item);
        }
    }

    private TextBlock MakePreviewPlaceholder() => new()
    {
        Text = I18n.Tr("单击图片或视频文件预览"),
        Style = (Style)FindResource("CaptionText"),
        HorizontalAlignment = HorizontalAlignment.Center,
        VerticalAlignment = VerticalAlignment.Center,
        Margin = new Thickness(12),
        TextWrapping = TextWrapping.Wrap,
    };

    /// <summary>停止内嵌播放并把预览区恢复为占位提示。</summary>
    private void StopPreview()
    {
        _inlinePlayer?.Shutdown();
        _inlinePlayer = null;
        if (_previewHost != null)
            _previewHost.Child = MakePreviewPlaceholder();
    }

    /// <summary>单击选中文件：图片/视频直接在详情页右侧预览区显示，其它类型不改变预览。</summary>
    private void ShowPreview(string path)
    {
        if (_previewHost == null)
            return;
        var ext = Path.GetExtension(path).ToLowerInvariant();
        if (DlsitePage.ImageExts.Contains(ext))
        {
            _inlinePlayer?.Shutdown();
            _inlinePlayer = null;
            try
            {
                var bmp = new BitmapImage();
                bmp.BeginInit();
                bmp.CacheOption = BitmapCacheOption.OnLoad;
                bmp.UriSource = new Uri(path);
                bmp.EndInit();
                bmp.Freeze();
                _previewHost.Child = new Image { Source = bmp, Stretch = Stretch.Uniform };
            }
            catch (Exception)
            {
                // 单张预览图加载失败保持原内容
            }
        }
        else if (VideoExts.Contains(ext))
        {
            _inlinePlayer?.Shutdown();
            _inlinePlayer = new InlineMediaPlayer(path);
            _previewHost.Child = _inlinePlayer;
        }
    }

    /// <summary>双击文件：图片/视频已由单击内嵌预览；音频→播放器弹窗；其它→系统默认程序。</summary>
    private void OpenTreeFile(string path)
    {
        var ext = Path.GetExtension(path).ToLowerInvariant();
        if (DlsitePage.ImageExts.Contains(ext) || VideoExts.Contains(ext))
            return;
        if (AudioExts.Contains(ext))
            new MediaPlayerDialog(path, isVideo: false) { Owner = Window.GetWindow(this) }
                .ShowDialog();
        else
            Process.Start(new ProcessStartInfo(path) { UseShellExecute = true });
    }
}
