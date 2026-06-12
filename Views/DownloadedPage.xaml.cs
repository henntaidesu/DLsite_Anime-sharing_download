using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using DASD.Core;

namespace DASD.Views;

/// <summary>已下载页一行数据。</summary>
public class DownloadedRow
{
    public string WorkId { get; init; } = "";
    public string WorkName { get; init; } = "";
    public string MakerName { get; init; } = "";
    public string WorkType { get; init; } = "";
    public string State { get; init; } = "";      // 数据库原始状态值（右键菜单/着色用）
    public string StateText { get; init; } = "";  // 显示译文
    public Brush StateBrush { get; init; } = Brushes.Gray;
    public string DownTime { get; init; } = "";
}

/// <summary>已下载页（对应 Python 版 downloaded_UI.py）。</summary>
public partial class DownloadedPage : UserControl
{
    // works.state（数据库原始值）-> 显示颜色
    private static readonly Dictionary<string, string> StateColors = new()
    {
        ["已品悦"] = "#4ade80",
        ["已下载"] = "#60a5fa",
        ["下载中"] = "#facc15",
    };

    private readonly ObservableCollection<DownloadedRow> _rows = [];

    public DownloadedPage()
    {
        InitializeComponent();
        WorksGrid.ItemsSource = _rows;
        RetranslateUi();
        I18n.LanguageChanged += RetranslateUi;
    }

    private void RetranslateUi()
    {
        RefreshButton.Content = I18n.Tr("刷新");
        ColId.Header = I18n.Tr("RJ号");
        ColName.Header = I18n.Tr("作品名称");
        ColMaker.Header = I18n.Tr("社团");
        ColType.Header = I18n.Tr("类型");
        ColState.Header = I18n.Tr("状态");
        ColTime.Header = I18n.Tr("下载时间");
        MarkMenuItem.Header = I18n.Tr("标记为已品悦");
        Refresh();
    }

    private void Page_IsVisibleChanged(object sender, DependencyPropertyChangedEventArgs e)
    {
        if ((bool)e.NewValue)
            Refresh();
    }

    private void RefreshButton_Click(object sender, RoutedEventArgs e) => Refresh();

    private void Refresh()
    {
        var rows = Db.Select(
            "SELECT \"work_id\", \"work_name\", \"maker_name\", \"work_type\", \"state\", \"down_time\" " +
            "FROM \"works\" ORDER BY \"down_time\" DESC, \"work_id\" DESC");
        if (rows == null)
            return;
        _rows.Clear();
        foreach (var row in rows)
        {
            var state = row[4] as string ?? "";
            var downTime = row[5]?.ToString() ?? "";
            _rows.Add(new DownloadedRow
            {
                WorkId = row[0] as string ?? "",
                WorkName = row[1] as string ?? "",
                MakerName = row[2] as string ?? "",
                WorkType = row[3] as string ?? "",
                State = state,
                StateText = I18n.Tr(state),
                StateBrush = StateColors.TryGetValue(state, out var color)
                    ? new SolidColorBrush((Color)ColorConverter.ConvertFromString(color))
                    : Brushes.LightGray,
                DownTime = downTime.Length > 19 ? downTime[..19] : downTime,  // 不显示微秒
            });
        }
        CountLabel.Text = I18n.Format(I18n.Tr("共 {n} 个作品"), ("n", _rows.Count));
    }

    /// <summary>右键菜单仅对"已下载"状态的作品开放。</summary>
    private void WorksGrid_ContextMenuOpening(object sender, ContextMenuEventArgs e)
    {
        if (WorksGrid.SelectedItem is not DownloadedRow row || row.State != "已下载")
            e.Handled = true;
    }

    private void MarkEnjoyed_Click(object sender, RoutedEventArgs e)
    {
        if (WorksGrid.SelectedItem is not DownloadedRow row || row.State != "已下载")
            return;
        Db.Execute("UPDATE \"works\" SET \"state\" = '已品悦' WHERE \"work_id\" = @w", ("@w", row.WorkId));
        Refresh();
    }
}
