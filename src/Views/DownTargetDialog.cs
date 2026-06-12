using System.Linq;
using System.Windows;
using System.Windows.Controls;
using DASD.Core;

namespace DASD.Views;

/// <summary>
/// 下载目标 / 移动目标选择对话框：先选媒体库，多文件夹时再选具体文件夹
/// （对应 Python 版 _DownTargetDialog / _MoveLibDialog）。
/// excludeLib 非空时排除该媒体库（移动场景排除当前所在库）。
/// </summary>
public class DownTargetDialog : Window
{
    public string? SelectedLib { get; private set; }
    public string? SelectedFolder { get; private set; }

    private readonly StackPanel _panel = new() { Margin = new Thickness(20, 16, 20, 16) };

    public DownTargetDialog(string? excludeLib = null, bool moveMode = false)
    {
        Title = I18n.Tr(moveMode ? "移动媒体库" : "选择下载位置");
        Width = 460;
        SizeToContent = SizeToContent.Height;
        MinHeight = 220;
        MaxHeight = 600;
        WindowStartupLocation = WindowStartupLocation.CenterOwner;
        Background = (System.Windows.Media.Brush)Application.Current.Resources["WindowBrush"];
        ResizeMode = ResizeMode.NoResize;
        Content = new ScrollViewer
        {
            VerticalScrollBarVisibility = ScrollBarVisibility.Auto,
            Content = _panel,
        };
        BuildLibPage(excludeLib, moveMode);
    }

    private void BuildLibPage(string? excludeLib, bool moveMode)
    {
        _panel.Children.Clear();
        _panel.Children.Add(new TextBlock
        {
            Text = I18n.Tr(moveMode ? "选择要移动到的媒体库" : "选择下载到哪个媒体库"),
            FontWeight = FontWeights.SemiBold,
            FontSize = 14,
            Margin = new Thickness(0, 0, 0, 8),
        });

        var hasTarget = false;
        foreach (var lib in AppConfig.ReadMediaLibs())
        {
            if (excludeLib != null && lib.Name == excludeLib)
                continue;  // 排除当前所在媒体库
            var folders = lib.Folders.Where(f => f.Length > 0).ToList();
            if (folders.Count == 0)
                continue;
            hasTarget = true;
            var label = folders.Count > 1
                ? $"{lib.Name}　{I18n.Format(I18n.Tr("{n} 个文件夹"), ("n", folders.Count))}"
                : lib.Name;
            var button = new Button { Content = label, MinHeight = 40, Margin = new Thickness(0, 4, 0, 0) };
            var libName = lib.Name;
            button.Click += (_, _) =>
            {
                SelectedLib = libName;
                if (folders.Count == 1)
                {
                    SelectedFolder = folders[0];
                    DialogResult = true;
                }
                else
                {
                    BuildFolderPage(folders, excludeLib, moveMode);
                }
            };
            _panel.Children.Add(button);
        }
        if (moveMode && !hasTarget)
            _panel.Children.Add(new TextBlock { Text = I18n.Tr("没有可移动到的其它媒体库") });

        var cancel = new Button { Content = I18n.Tr("取消"), Margin = new Thickness(0, 16, 0, 0) };
        cancel.Click += (_, _) => DialogResult = false;
        _panel.Children.Add(cancel);
    }

    private void BuildFolderPage(System.Collections.Generic.List<string> folders,
        string? excludeLib, bool moveMode)
    {
        _panel.Children.Clear();
        _panel.Children.Add(new TextBlock
        {
            Text = I18n.Tr(moveMode ? "选择目标文件夹" : "选择下载文件夹"),
            FontWeight = FontWeights.SemiBold,
            FontSize = 14,
            Margin = new Thickness(0, 0, 0, 8),
        });
        foreach (var folder in folders)
        {
            var button = new Button
            {
                Content = folder, MinHeight = 40, Margin = new Thickness(0, 4, 0, 0),
                ToolTip = folder,
            };
            var f = folder;
            button.Click += (_, _) =>
            {
                SelectedFolder = f;
                DialogResult = true;
            };
            _panel.Children.Add(button);
        }
        var back = new Button { Content = I18n.Tr("← 返回"), Margin = new Thickness(0, 16, 0, 0) };
        back.Click += (_, _) => BuildLibPage(excludeLib, moveMode);
        _panel.Children.Add(back);
    }
}
