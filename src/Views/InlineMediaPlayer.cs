using System;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Threading;
using DASD.Core;

namespace DASD.Views;

/// <summary>详情页内嵌视频播放器：MediaElement 渲染 + 播放/暂停 + 进度条（不弹窗版的 MediaPlayerDialog）。</summary>
public class InlineMediaPlayer : UserControl
{
    private readonly MediaElement _player = new()
    {
        LoadedBehavior = MediaState.Manual,
        UnloadedBehavior = MediaState.Stop,
        ScrubbingEnabled = true,
    };
    private readonly Button _playButton = new() { Width = 72 };
    private readonly Slider _slider = new() { Minimum = 0, Maximum = 0, IsMoveToPointEnabled = true };
    private readonly TextBlock _time = new()
    {
        Text = "00:00 / 00:00", VerticalAlignment = VerticalAlignment.Center,
    };
    private readonly DispatcherTimer _timer = new() { Interval = TimeSpan.FromMilliseconds(250) };
    private bool _playing;
    private bool _dragging;
    private bool _closed;

    public InlineMediaPlayer(string path)
    {
        var layout = new Grid();
        layout.RowDefinitions.Add(new RowDefinition { Height = new GridLength(1, GridUnitType.Star) });
        layout.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });

        layout.Children.Add(new Border { Background = Brushes.Black, Child = _player });

        var bar = new Grid { Margin = new Thickness(0, 6, 0, 0) };
        bar.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
        bar.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
        bar.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
        _playButton.Click += (_, _) => Toggle();
        bar.Children.Add(_playButton);
        _slider.Margin = new Thickness(8, 0, 8, 0);
        _slider.VerticalAlignment = VerticalAlignment.Center;
        _slider.PreviewMouseDown += (_, _) => _dragging = true;
        _slider.PreviewMouseUp += (_, _) =>
        {
            _player.Position = TimeSpan.FromMilliseconds(_slider.Value);
            _dragging = false;
        };
        Grid.SetColumn(_slider, 1);
        bar.Children.Add(_slider);
        Grid.SetColumn(_time, 2);
        bar.Children.Add(_time);
        Grid.SetRow(bar, 1);
        layout.Children.Add(bar);
        Content = layout;

        _player.MediaOpened += (_, _) =>
        {
            if (_player.NaturalDuration.HasTimeSpan)
                _slider.Maximum = _player.NaturalDuration.TimeSpan.TotalMilliseconds;
        };
        _player.MediaEnded += (_, _) =>
        {
            _playing = false;
            _playButton.Content = I18n.Tr("播放");
        };
        _timer.Tick += (_, _) =>
        {
            if (!_dragging)
                _slider.Value = _player.Position.TotalMilliseconds;
            var duration = _player.NaturalDuration.HasTimeSpan
                ? _player.NaturalDuration.TimeSpan
                : TimeSpan.Zero;
            _time.Text = $"{Fmt(_player.Position)} / {Fmt(duration)}";
        };

        // 被移出视觉树（切回信息面板/离开详情页）时兜底停止播放
        Unloaded += (_, _) => Shutdown();

        _player.Source = new Uri(path);
        _player.Play();
        _playing = true;
        _playButton.Content = I18n.Tr("暂停");
        _timer.Start();
    }

    /// <summary>停止播放并释放媒体资源，可重复调用。</summary>
    public void Shutdown()
    {
        if (_closed)
            return;
        _closed = true;
        _timer.Stop();
        _player.Stop();
        _player.Close();
    }

    private void Toggle()
    {
        if (_closed)
            return;
        if (_playing)
        {
            _player.Pause();
            _playing = false;
            _playButton.Content = I18n.Tr("播放");
        }
        else
        {
            _player.Play();
            _playing = true;
            _playButton.Content = I18n.Tr("暂停");
        }
    }

    private static string Fmt(TimeSpan time) =>
        $"{(int)time.TotalMinutes:D2}:{time.Seconds:D2}";
}
