// NotificationManager.cs - Windows通知管理
using System;
using System.Drawing;
using System.Windows.Forms;
using System.Media;

namespace CADDedupPlugin
{
    /// <summary>
    /// Windows通知管理器
    /// </summary>
    public class NotificationManager : IDisposable
    {
        private NotifyIcon _notifyIcon;
        private readonly DedupConfig _config;

        public NotificationManager()
        {
            _config = DedupConfig.Load();
            InitializeNotifyIcon();
        }

        /// <summary>
        /// 初始化系统托盘图标
        /// </summary>
        private void InitializeNotifyIcon()
        {
            _notifyIcon = new NotifyIcon
            {
                Icon = SystemIcons.Information,
                Visible = false,
                Text = "CAD图纸查重"
            };

            _notifyIcon.BalloonTipClicked += OnNotificationClicked;
        }

        /// <summary>
        /// 显示发现重复的通知
        /// </summary>
        public void ShowDuplicateNotification(string fileName, DuplicateMatch match, string checkId, int totalMatches = 1)
        {
            string title = totalMatches > 1
                ? $"⚠️ 发现 {totalMatches} 张重复图纸"
                : "⚠️ 发现重复图纸";

            string message = totalMatches > 1
                ? $"{fileName}\n" +
                  $"最相似: {match.FileName} ({match.Similarity:P0})\n" +
                  $"点击查看全部 {totalMatches} 张对比详情"
                : $"{fileName}\n" +
                  $"与 {match.FileName} 相似度 {match.Similarity:P0}\n" +
                  $"点击查看详细对比";

            ShowNotification(title, message, ToolTipIcon.Warning, checkId);

            // 播放提示音
            if (_config.PlaySoundOnDuplicate)
            {
                SystemSounds.Exclamation.Play();
            }
        }

        /// <summary>
        /// 显示未发现重复的通知
        /// </summary>
        public void ShowUniqueNotification(string fileName)
        {
            string title = "✓ 图纸检查完成";
            string message = $"{fileName}\n未发现重复，已添加到查重库";

            ShowNotification(title, message, ToolTipIcon.Info, null);
        }

        /// <summary>
        /// 显示错误通知
        /// </summary>
        public void ShowErrorNotification(string fileName, string errorMessage)
        {
            string title = "❌ 查重失败";
            string message = $"{fileName}\n{errorMessage}";

            ShowNotification(title, message, ToolTipIcon.Error, null);
        }

        /// <summary>
        /// 显示通知的核心方法
        /// </summary>
        public void ShowNotification(string title, string message, ToolTipIcon icon, string checkId)
        {
            try
            {
                _notifyIcon.Tag = checkId; // 保存checkId用于点击时打开
                _notifyIcon.Visible = true;
                _notifyIcon.ShowBalloonTip(10000, title, message, icon);

                // 10秒后自动隐藏
                var timer = new Timer { Interval = 10000 };
                timer.Tick += (s, e) =>
                {
                    _notifyIcon.Visible = false;
                    timer.Stop();
                    timer.Dispose();
                };
                timer.Start();
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"显示通知失败: {ex.Message}");
            }
        }

        /// <summary>
        /// 显示通知的重载方法（用于TrendWarningManager）
        /// </summary>
        public void ShowNotification(string title, string message, NotificationLevel level, bool playSound)
        {
            // 将NotificationLevel转换为ToolTipIcon
            ToolTipIcon icon;
            switch (level)
            {
                case NotificationLevel.Info:
                    icon = ToolTipIcon.Info;
                    break;
                case NotificationLevel.Warning:
                    icon = ToolTipIcon.Warning;
                    break;
                case NotificationLevel.Error:
                    icon = ToolTipIcon.Error;
                    break;
                default:
                    icon = ToolTipIcon.Info;
                    break;
            }

            // 调用原有的ShowNotification方法
            ShowNotification(title, message, icon, null);

            // 播放提示音
            if (playSound)
            {
                SystemSounds.Exclamation.Play();
            }
        }

        /// <summary>
        /// 通知被点击时打开详情页
        /// </summary>
        private void OnNotificationClicked(object sender, EventArgs e)
        {
            try
            {
                string checkId = _notifyIcon.Tag as string;
                if (!string.IsNullOrEmpty(checkId))
                {
                    string url = $"{_config.ServerUrl}/results/{checkId}";
                    System.Diagnostics.Process.Start(url);
                }
            }
            catch (Exception ex)
            {
                MessageBox.Show($"无法打开详情页: {ex.Message}", "错误",
                              MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }

        public void Dispose()
        {
            if (_notifyIcon != null)
            {
                _notifyIcon.Visible = false;
                _notifyIcon.Dispose();
                _notifyIcon = null;
            }
        }
    }
}
