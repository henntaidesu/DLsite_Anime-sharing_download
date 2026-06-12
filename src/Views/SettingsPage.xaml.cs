using System;
using System.IO;
using System.Linq;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using DASD.Core;
using DASD.Services;
using Microsoft.Win32;

namespace DASD.Views;

/// <summary>设置页（对应 Python 版 setting_UI.py）：输入框失焦即保存，下拉框选择即保存。</summary>
public partial class SettingsPage : UserControl
{
    private bool _loading;  // 回填控件时不触发保存

    public SettingsPage()
    {
        InitializeComponent();
        BuildCombos();
        RetranslateUi();
        ReadConf();
        I18n.LanguageChanged += RetranslateUi;
    }

    private void BuildCombos()
    {
        _loading = true;
        ProxyStatusCombo.Items.Add(I18n.Tr("开启"));
        ProxyStatusCombo.Items.Add(I18n.Tr("关闭"));
        foreach (var type in new[] { "http", "https", "Socks5" })
            ProxyTypeCombo.Items.Add(type);
        AutoDownloadCombo.Items.Add(I18n.Tr("开启"));
        AutoDownloadCombo.Items.Add(I18n.Tr("关闭"));
        AutoUnzipCombo.Items.Add(I18n.Tr("开启"));
        AutoUnzipCombo.Items.Add(I18n.Tr("关闭"));
        WebEnableCombo.Items.Add(I18n.Tr("开启"));
        WebEnableCombo.Items.Add(I18n.Tr("关闭"));
        foreach (var level in new[] { "info", "error", "debug" })
            LogLevelCombo.Items.Add(level);
        foreach (var (_, name) in I18n.Languages)
            LanguageCombo.Items.Add(name);
        _loading = false;
    }

    private void RetranslateUi()
    {
        _loading = true;
        DownloadGroup.Header = I18n.Tr("下载");
        ProxyGroup.Header = I18n.Tr("代理");
        DebridGroup.Header = I18n.Tr("Debrid-Link 下载中转站");
        OtherGroup.Header = I18n.Tr("下载选项");
        SystemGroup.Header = I18n.Tr("系统");
        PathLabel.Text = I18n.Tr("缓存路径");
        PathChooseButton.Content = I18n.Tr("保存");
        AutoDownloadLabel.Text = I18n.Tr("自动下载");
        AutoUnzipLabel.Text = I18n.Tr("自动解压");
        ProxyStatusLabel.Text = I18n.Tr("代理");
        DebridTestButton.Content = I18n.Tr("测试");
        DownProcLabel.Text = I18n.Tr("单文件线程数");
        DownProcLabel.ToolTip = I18n.Tr("单个文件分成多少段并发下载（多线程下载），1 为不分段");
        DownProcBox.ToolTip = I18n.Tr("单个文件分成多少段并发下载（多线程下载），1 为不分段，最大 16");
        MinSpeedLabel.Text = I18n.Tr("最低速度 (KB/s)");
        MinSpeedBox.ToolTip = I18n.Tr("持续低于该速度 30 秒后自动重试，0 表示不限制");
        SpeedLimitLabel.Text = I18n.Tr("速度限制 (KB/s)");
        SpeedLimitBox.ToolTip = I18n.Tr("下载总速度上限，0 表示不限速");
        LanguageLabel.Text = I18n.Tr("语言");
        LogLevelLabel.Text = I18n.Tr("日志级别");
        EncodingLabel.Text = I18n.Tr("解压编码");
        WebGroup.Header = I18n.Tr("外部访问");
        WebEnableLabel.Text = I18n.Tr("外部访问");
        WebPortLabel.Text = I18n.Tr("端口");
        WebPasswordLabel.Text = I18n.Tr("访问密码");
        WebPasswordBox.ToolTip = I18n.Tr("留空则不需要密码；手机/电脑浏览器访问时输入此密码");
        // 下拉框选项文案（保持索引语义不变，仅更新显示文本）
        ProxyStatusCombo.Items[0] = I18n.Tr("开启");
        ProxyStatusCombo.Items[1] = I18n.Tr("关闭");
        AutoDownloadCombo.Items[0] = I18n.Tr("开启");
        AutoDownloadCombo.Items[1] = I18n.Tr("关闭");
        AutoUnzipCombo.Items[0] = I18n.Tr("开启");
        AutoUnzipCombo.Items[1] = I18n.Tr("关闭");
        WebEnableCombo.Items[0] = I18n.Tr("开启");
        WebEnableCombo.Items[1] = I18n.Tr("关闭");
        _loading = false;
        UpdateWebStatus();
    }

    private void Page_IsVisibleChanged(object sender, DependencyPropertyChangedEventArgs e)
    {
        if (!(bool)e.NewValue)
            return;
        // 切换到本页时重新加载配置：先丢弃缓存从数据库重读，再回填控件
        AppConfig.Reload();
        ReadConf();
    }

    /// <summary>用户的"下载"文件夹。</summary>
    private static string DefaultDownPath() =>
        Path.GetFullPath(Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), "Downloads"));

    private void ReadConf()
    {
        _loading = true;
        var path = AppConfig.DownloadPath.Replace(@"\\", @"\");
        // 校验下载路径：不存在时回退到用户的下载文件夹并保存
        if (path.Length == 0 || !Directory.Exists(path))
        {
            path = DefaultDownPath();
            AppConfig.Write("downpath", "downpath", path);
        }
        PathBox.Text = path;

        var (enabled, host, port, proxyType) = AppConfig.ReadProxySetting();
        ProxyHostBox.Text = host;
        ProxyPortBox.Text = port;
        ProxyStatusCombo.SelectedIndex = enabled == "True" ? 0 : 1;
        ProxyTypeCombo.SelectedIndex = proxyType switch
        {
            "http" => 0,
            "https" => 1,
            _ => 2,
        };

        DebridKeyBox.Text = AppConfig.DebridApiKey;
        AutoDownloadCombo.SelectedIndex = AppConfig.AutoDownload ? 0 : 1;
        AutoUnzipCombo.SelectedIndex = AppConfig.AutoUnzip ? 0 : 1;
        DownProcBox.Text = AppConfig.DownloadProcesses.ToString();
        MinSpeedBox.Text = AppConfig.MinSpeedKb.ToString();
        SpeedLimitBox.Text = AppConfig.SpeedLimitKb.ToString();
        LogLevelCombo.SelectedIndex = AppConfig.Read("loglevel", "level") switch
        {
            "error" => 1,
            "debug" => 2,
            _ => 0,
        };
        EncodingBox.Text = AppConfig.SysEncoding;
        var codes = I18n.Languages.Select(l => l.Code).ToList();
        var langIndex = codes.IndexOf(I18n.CurrentLanguage);
        LanguageCombo.SelectedIndex = langIndex >= 0 ? langIndex : 0;

        WebEnableCombo.SelectedIndex = AppConfig.WebEnabled ? 0 : 1;
        WebPortBox.Text = AppConfig.WebPort.ToString();
        WebPasswordBox.Text = AppConfig.WebPassword;
        _loading = false;
        UpdateWebStatus();
    }

    // ---------- 保存 ----------

    private void PathBox_LostFocus(object sender, RoutedEventArgs e)
    {
        if (_loading)
            return;
        // 手动输入下载路径：输入的是有效目录时才保存
        var path = PathBox.Text.Trim();
        if (path.Length > 0 && Directory.Exists(path))
            AppConfig.Write("downpath", "downpath", Path.GetFullPath(path));
    }

    private void PathChooseButton_Click(object sender, RoutedEventArgs e)
    {
        var current = PathBox.Text;
        var dialog = new OpenFolderDialog
        {
            Title = I18n.Tr("选择缓存路径"),
            InitialDirectory = Directory.Exists(current) ? current : DefaultDownPath(),
        };
        if (dialog.ShowDialog(Window.GetWindow(this)) != true)
            return;
        var path = Path.GetFullPath(dialog.FolderName);
        PathBox.Text = path;
        AppConfig.Write("downpath", "downpath", path);
    }

    private void Proxy_LostFocus(object sender, RoutedEventArgs e)
    {
        if (_loading)
            return;
        AppConfig.Write("proxy", "host", ProxyHostBox.Text);
        AppConfig.Write("proxy", "port", ProxyPortBox.Text);
    }

    private void ProxyStatusCombo_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (_loading)
            return;
        AppConfig.Write("proxy", "openproxy", ProxyStatusCombo.SelectedIndex == 0 ? "True" : "False");
    }

    private void ProxyTypeCombo_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (_loading)
            return;
        AppConfig.Write("proxy", "type", new[] { "http", "https", "Socks5" }[ProxyTypeCombo.SelectedIndex]);
    }

    private void DebridKeyBox_LostFocus(object sender, RoutedEventArgs e)
    {
        if (_loading)
            return;
        AppConfig.Write("debrid", "api_key", DebridKeyBox.Text.Trim());
    }

    private async void DebridTestButton_Click(object sender, RoutedEventArgs e)
    {
        string? account = null;
        try
        {
            using var client = new DebridLinkClient(DebridKeyBox.Text.Trim());
            var info = await client.AccountInfosAsync();
            if (info is { } v)
            {
                account = DlsiteApi.JStr(v, "email");
                if (account.Length == 0)
                    account = DlsiteApi.JStr(v, "username");
            }
        }
        catch (Exception)
        {
            account = null;
        }
        if (account != null)
            MessageBox.Show(
                I18n.Format(I18n.Tr("已连接 debrid-link\n账户: {account}"), ("account", account)),
                I18n.Tr("测试成功"), MessageBoxButton.OK, MessageBoxImage.Information);
        else
            MessageBox.Show(I18n.Tr("API Key 无效或网络不可用"), I18n.Tr("测试失败"),
                MessageBoxButton.OK, MessageBoxImage.Warning);
    }

    private void AutoDownloadCombo_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (_loading)
            return;
        AppConfig.Write("down_list", "auto_download", AutoDownloadCombo.SelectedIndex == 0 ? "True" : "False");
    }

    private void AutoUnzipCombo_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (_loading)
            return;
        AppConfig.Write("down_list", "auto_unzip", AutoUnzipCombo.SelectedIndex == 0 ? "True" : "False");
    }

    private void DownProcBox_LostFocus(object sender, RoutedEventArgs e)
    {
        if (_loading)
            return;
        AppConfig.Write("down_list", "download_processes", DownProcBox.Text.Trim());
    }

    private void MinSpeedBox_LostFocus(object sender, RoutedEventArgs e)
    {
        if (_loading)
            return;
        var value = MinSpeedBox.Text.Trim();
        AppConfig.Write("down_list", "min_speed", int.TryParse(value, out _) ? value : "0");
    }

    private void SpeedLimitBox_LostFocus(object sender, RoutedEventArgs e)
    {
        if (_loading)
            return;
        var value = SpeedLimitBox.Text.Trim();
        AppConfig.Write("down_list", "speed_limit", int.TryParse(value, out _) ? value : "0");
    }

    private void LanguageCombo_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (_loading || LanguageCombo.SelectedIndex < 0)
            return;
        I18n.ApplyLanguage(I18n.Languages[LanguageCombo.SelectedIndex].Code);
    }

    private void LogLevelCombo_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (_loading || LogLevelCombo.SelectedIndex < 0)
            return;
        AppConfig.Write("loglevel", "level",
            new[] { "info", "error", "debug" }[LogLevelCombo.SelectedIndex]);
    }

    private void EncodingBox_LostFocus(object sender, RoutedEventArgs e)
    {
        if (_loading)
            return;
        AppConfig.Write("encoding", "encoding", EncodingBox.Text.Trim());
    }

    // ---------- 外部访问 ----------

    private void WebEnableCombo_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (_loading)
            return;
        AppConfig.Write("web_server", "enabled", WebEnableCombo.SelectedIndex == 0 ? "True" : "False");
        ApplyWebServer();
    }

    private void WebPortBox_LostFocus(object sender, RoutedEventArgs e)
    {
        if (_loading)
            return;
        // 端口校验：非法值回退 8080
        var port = int.TryParse(WebPortBox.Text.Trim(), out var v) && v is >= 1 and <= 65535 ? v : 8080;
        WebPortBox.Text = port.ToString();
        AppConfig.Write("web_server", "port", port.ToString());
        ApplyWebServer();
    }

    private void WebPasswordBox_LostFocus(object sender, RoutedEventArgs e)
    {
        if (_loading)
            return;
        AppConfig.Write("web_server", "password", WebPasswordBox.Text.Trim());
        ApplyWebServer();
    }

    /// <summary>按当前配置启动/停止内嵌 Web 服务（开启时改端口/密码会重启），并刷新状态文案。</summary>
    private void ApplyWebServer()
    {
        if (AppConfig.WebEnabled)
            WebServer.StartFromConfig();
        else
            WebServer.Stop();
        UpdateWebStatus();
    }

    private void UpdateWebStatus()
    {
        if (WebStatusLabel == null)
            return;
        if (!AppConfig.WebEnabled)
        {
            WebStatusLabel.Text = I18n.Tr("外部访问已关闭");
            return;
        }
        if (WebServer.IsRunning)
        {
            var url = $"http://{WebServer.LocalIPv4()}:{WebServer.RunningPort}";
            var text = I18n.Format(I18n.Tr("已开启 · 在手机/电脑浏览器打开 {url}"), ("url", url));
            if (AppConfig.WebPassword.Length > 0)
                text += I18n.Tr("（需输入访问密码）");
            WebStatusLabel.Text = text;
        }
        else
        {
            WebStatusLabel.Text = I18n.Tr("启动失败：端口可能被占用，请更换端口");
        }
    }
}
