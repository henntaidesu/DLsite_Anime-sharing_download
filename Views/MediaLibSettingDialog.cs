using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.IO;
using System.Linq;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using DASD.Core;
using DASD.Services;
using Microsoft.Win32;

namespace DASD.Views;

/// <summary>媒体库设置弹窗：新建/删除媒体库、管理文件夹、触发扫描（对应 media_lib_setting_UI.py）。</summary>
public class MediaLibSettingDialog : Window
{
    /// <summary>媒体库增删 / 文件夹增删。</summary>
    public event Action? LibsChanged;

    /// <summary>一次扫描结束（作品数据有更新）。</summary>
    public event Action? ScanDone;

    private List<MediaLib> _libs;
    private readonly TextBlock _status = new() { VerticalAlignment = VerticalAlignment.Center };
    private readonly StackPanel _cardsPanel = new();
    private readonly List<(string Lib, bool Force)> _pending = [];  // 扫描队列
    private bool _scanning;

    public MediaLibSettingDialog()
    {
        Title = I18n.Tr("媒体库设置");
        Width = 680;
        Height = 480;
        WindowStartupLocation = WindowStartupLocation.CenterOwner;
        Background = (Brush)Application.Current.Resources["WindowBrush"];

        var layout = new Grid { Margin = new Thickness(16) };
        layout.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
        layout.RowDefinitions.Add(new RowDefinition { Height = new GridLength(1, GridUnitType.Star) });

        var header = new Grid { Margin = new Thickness(0, 0, 0, 10) };
        header.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
        header.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
        _status.Foreground = (Brush)Application.Current.Resources["CaptionBrush"];
        header.Children.Add(_status);
        var createButton = new Button { Content = I18n.Tr("新建媒体库"), MinWidth = 108 };
        createButton.Click += (_, _) => CreateLib();
        Grid.SetColumn(createButton, 1);
        header.Children.Add(createButton);
        layout.Children.Add(header);

        var scroll = new ScrollViewer
        {
            VerticalScrollBarVisibility = ScrollBarVisibility.Auto,
            Content = _cardsPanel,
        };
        Grid.SetRow(scroll, 1);
        layout.Children.Add(scroll);
        Content = layout;

        _libs = AppConfig.ReadMediaLibs();
        RebuildCards();

        // 关闭时只隐藏，保持常驻实例（扫描任务随其存活）
        Closing += (_, e) =>
        {
            e.Cancel = true;
            Hide();
        };
    }

    private void SaveLibs()
    {
        AppConfig.WriteMediaLibs(_libs);
        RebuildCards();
        LibsChanged?.Invoke();
    }

    private void RebuildCards()
    {
        _cardsPanel.Children.Clear();
        if (_libs.Count == 0)
        {
            _cardsPanel.Children.Add(new TextBlock
            {
                Text = I18n.Tr("还没有媒体库，点击\"新建媒体库\"创建。"),
                Foreground = (Brush)Application.Current.Resources["CaptionBrush"],
            });
            return;
        }
        foreach (var lib in _libs)
            _cardsPanel.Children.Add(BuildLibCard(lib));
    }

    private Border BuildLibCard(MediaLib lib)
    {
        var card = new Border
        {
            Background = (Brush)Application.Current.Resources["CardBrush"],
            CornerRadius = new CornerRadius(8),
            Padding = new Thickness(12, 10, 12, 10),
            Margin = new Thickness(0, 0, 0, 8),
        };
        var panel = new StackPanel();

        var header = new StackPanel { Orientation = Orientation.Horizontal };
        header.Children.Add(new TextBlock
        {
            Text = lib.Name, FontWeight = FontWeights.SemiBold, FontSize = 14,
            VerticalAlignment = VerticalAlignment.Center,
        });
        header.Children.Add(new TextBlock
        {
            Text = I18n.Format(I18n.Tr("{n} 个文件夹"), ("n", lib.Folders.Count)),
            Foreground = (Brush)Application.Current.Resources["CaptionBrush"],
            Margin = new Thickness(8, 0, 0, 0),
            VerticalAlignment = VerticalAlignment.Center,
        });
        var addButton = new Button { Content = I18n.Tr("添加文件夹"), Margin = new Thickness(16, 0, 0, 0) };
        addButton.Click += (_, _) => AddFolder(lib.Name);
        header.Children.Add(addButton);
        var scanButton = new Button { Content = I18n.Tr("扫描元数据"), Margin = new Thickness(6, 0, 0, 0) };
        scanButton.Click += (_, _) => ScanLib(lib.Name, force: false);
        header.Children.Add(scanButton);
        var rescanButton = new Button { Content = I18n.Tr("重新扫描元数据"), Margin = new Thickness(6, 0, 0, 0) };
        rescanButton.Click += (_, _) => ScanLib(lib.Name, force: true);
        header.Children.Add(rescanButton);
        var deleteButton = new Button { Content = I18n.Tr("删除"), Margin = new Thickness(6, 0, 0, 0) };
        deleteButton.Click += (_, _) => DeleteLib(lib.Name);
        header.Children.Add(deleteButton);
        panel.Children.Add(header);

        foreach (var folder in lib.Folders)
        {
            var row = new Grid { Margin = new Thickness(0, 6, 0, 0) };
            row.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
            row.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
            row.Children.Add(new TextBlock
            {
                Text = folder,
                Foreground = (Brush)Application.Current.Resources["CaptionBrush"],
                VerticalAlignment = VerticalAlignment.Center,
                TextTrimming = TextTrimming.CharacterEllipsis,
            });
            var removeButton = new Button
            {
                Content = I18n.Tr("移除"), Width = 56, Padding = new Thickness(4, 2, 4, 2),
            };
            var libName = lib.Name;
            var captured = folder;
            removeButton.Click += (_, _) => RemoveFolder(libName, captured);
            Grid.SetColumn(removeButton, 1);
            row.Children.Add(removeButton);
            panel.Children.Add(row);
        }
        card.Child = panel;
        return card;
    }

    private MediaLib? FindLib(string name) => _libs.FirstOrDefault(l => l.Name == name);

    private void CreateLib()
    {
        var dialog = new InputDialog(I18n.Tr("新建媒体库"), I18n.Tr("媒体库名称：")) { Owner = this };
        if (dialog.ShowDialog() != true)
            return;
        var name = dialog.Value.Trim();
        if (name.Length == 0)
            return;
        if (FindLib(name) != null)
        {
            MessageBox.Show(I18n.Tr("已存在同名媒体库。"), I18n.Tr("媒体库"),
                MessageBoxButton.OK, MessageBoxImage.Information);
            return;
        }
        _libs.Add(new MediaLib { Name = name });
        SaveLibs();
    }

    private void AddFolder(string libName)
    {
        var lib = FindLib(libName);
        if (lib == null)
            return;
        var dialog = new OpenFolderDialog { Title = I18n.Tr("选择媒体库文件夹") };
        if (dialog.ShowDialog(this) != true)
            return;
        var path = Path.GetFullPath(dialog.FolderName);
        foreach (var other in _libs)
            if (other.Folders.Contains(path))
            {
                MessageBox.Show(
                    I18n.Format(I18n.Tr("该文件夹已在媒体库\"{name}\"中。"), ("name", other.Name)),
                    I18n.Tr("媒体库"), MessageBoxButton.OK, MessageBoxImage.Information);
                return;
            }
        // 只登记文件夹，扫描由"扫描元数据"按钮触发
        lib.Folders.Add(path);
        SaveLibs();
    }

    private void RemoveFolder(string libName, string folder)
    {
        var lib = FindLib(libName);
        if (lib == null || !lib.Folders.Remove(folder))
            return;
        SaveLibs();
    }

    private void DeleteLib(string libName)
    {
        var lib = FindLib(libName);
        if (lib == null)
            return;
        var answer = MessageBox.Show(
            I18n.Format(I18n.Tr("确定删除媒体库\"{name}\"吗？\n不会删除本地文件，已导入的作品记录保留。"),
                ("name", libName)),
            I18n.Tr("删除媒体库"), MessageBoxButton.YesNo, MessageBoxImage.Question);
        if (answer != MessageBoxResult.Yes)
            return;
        _libs.Remove(lib);
        _pending.RemoveAll(p => p.Lib == libName);
        SaveLibs();
        Db.Execute("UPDATE \"works\" SET \"library\" = NULL WHERE \"library\" = @l", ("@l", libName));
    }

    /// <summary>扫描媒体库下的全部文件夹；force 为 True 时强制重新获取全部元数据。</summary>
    private void ScanLib(string libName, bool force)
    {
        var lib = FindLib(libName);
        if (lib == null || lib.Folders.Count == 0)
            return;
        if (_scanning)
        {
            if (!_pending.Contains((libName, force)))
                _pending.Add((libName, force));
        }
        else
        {
            _ = RunScanAsync(libName, force);
        }
    }

    /// <summary>后台扫描媒体库：导入 RJ 号并调用 DL API + 作品页补全（文件夹列表在启动时快照）。</summary>
    private async Task RunScanAsync(string libName, bool force)
    {
        var lib = FindLib(libName);
        if (lib == null || lib.Folders.Count == 0)
        {
            DequeueNext();
            return;
        }
        _scanning = true;
        _status.Text = I18n.Format(I18n.Tr("正在扫描媒体库\"{name}\"…"), ("name", libName));
        var folders = lib.Folders.ToList();
        try
        {
            var (added, total) = await Task.Run(() =>
            {
                int addedSum = 0, totalSum = 0;
                foreach (var folder in folders)
                {
                    var (a, t) = MediaLibraryService.ImportMediaLib(folder, libName);
                    addedSum += a;
                    totalSum += t;
                }
                return (addedSum, totalSum);
            });
            SetStatus(I18n.Format(I18n.Tr("已导入 {total} 个作品（新增 {added}），正在从 DL API 补全数据…"),
                ("total", total), ("added", added)));

            var (filled, _, _) = await MediaLibraryService.BackfillWorksFromApiAsync(
                delaySeconds: 0.5,
                progress: (i, totalCount, _, _) =>
                {
                    if (i % 10 == 0 || i == totalCount)
                        SetStatus(I18n.Format(I18n.Tr("DL API 数据补全中… {i}/{total}"),
                            ("i", i), ("total", totalCount)));
                },
                library: libName, force: force);

            SetStatus(I18n.Tr("正在抓取 DLsite 作品页元数据与图片…"));
            var (pageFilled, pageMissed, _) = await MediaLibraryService.BackfillWorkPagesAsync(
                delaySeconds: 1.0,
                progress: (i, totalCount, rj, _) =>
                    SetStatus(I18n.Format(I18n.Tr("作品页抓取中… {i}/{total}（{rj}）"),
                        ("i", i), ("total", totalCount), ("rj", rj))),
                library: libName, force: force);

            SetStatus(I18n.Format(
                I18n.Tr("扫描完成：导入 {total} 个，API 补全 {filled} 个，作品页补全 {page_filled} 个（失败 {page_missed}）"),
                ("total", total), ("filled", filled),
                ("page_filled", pageFilled), ("page_missed", pageMissed)));
        }
        catch (Exception e)
        {
            Logger.Error(e, "媒体库扫描");
            SetStatus(e.Message);
        }
        finally
        {
            _scanning = false;
            ScanDone?.Invoke();
            DequeueNext();
        }
    }

    private void DequeueNext()
    {
        if (_pending.Count == 0)
            return;
        var (lib, force) = _pending[0];
        _pending.RemoveAt(0);
        _ = RunScanAsync(lib, force);
    }

    private void SetStatus(string text) => Dispatcher.Invoke(() => _status.Text = text);
}

/// <summary>简单文本输入对话框（对应 QInputDialog.getText）。</summary>
public class InputDialog : Window
{
    public string Value { get; private set; } = "";

    public InputDialog(string title, string prompt)
    {
        Title = title;
        Width = 380;
        SizeToContent = SizeToContent.Height;
        WindowStartupLocation = WindowStartupLocation.CenterOwner;
        Background = (Brush)Application.Current.Resources["WindowBrush"];
        ResizeMode = ResizeMode.NoResize;

        var panel = new StackPanel { Margin = new Thickness(20, 16, 20, 16) };
        panel.Children.Add(new TextBlock { Text = prompt, Margin = new Thickness(0, 0, 0, 8) });
        var input = new TextBox();
        panel.Children.Add(input);
        var buttons = new StackPanel
        {
            Orientation = Orientation.Horizontal,
            HorizontalAlignment = HorizontalAlignment.Right,
            Margin = new Thickness(0, 14, 0, 0),
        };
        var ok = new Button { Content = "OK", MinWidth = 80, IsDefault = true };
        ok.Click += (_, _) =>
        {
            Value = input.Text;
            DialogResult = true;
        };
        var cancel = new Button
        {
            Content = I18n.Tr("取消"), MinWidth = 80, Margin = new Thickness(8, 0, 0, 0), IsCancel = true,
        };
        buttons.Children.Add(ok);
        buttons.Children.Add(cancel);
        panel.Children.Add(buttons);
        Content = panel;
        Loaded += (_, _) => input.Focus();
    }
}
