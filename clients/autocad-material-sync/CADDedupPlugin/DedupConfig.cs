// DedupConfig.cs - 插件配置管理
using System;
using System.IO;
using Newtonsoft.Json;

namespace CADDedupPlugin
{
    /// <summary>
    /// 插件配置
    /// </summary>
    public class DedupConfig
    {
        /// <summary>
        /// 查重服务器地址
        /// </summary>
        public string ServerUrl { get; set; } = "http://localhost:8000";

        /// <summary>
        /// API密钥（可选）
        /// </summary>
        public string ApiKey { get; set; } = "";

        /// <summary>
        /// 是否启用自动检查
        /// </summary>
        public bool AutoCheckEnabled { get; set; } = true;

        /// <summary>
        /// 相似度阈值（0.0-1.0）
        /// </summary>
        public double SimilarityThreshold { get; set; } = 0.85;

        /// <summary>
        /// 是否自动添加到索引库
        /// </summary>
        public bool AutoIndex { get; set; } = true;

        /// <summary>
        /// 请求超时时间（秒）
        /// </summary>
        public int TimeoutSeconds { get; set; } = 30;

        /// <summary>
        /// 高相似度时是否提示查看对比
        /// </summary>
        public bool PromptOnHighSimilarity { get; set; } = true;

        /// <summary>
        /// 未发现重复时是否显示通知
        /// </summary>
        public bool ShowNotificationOnUnique { get; set; } = false;

        /// <summary>
        /// 发现重复时是否播放声音
        /// </summary>
        public bool PlaySoundOnDuplicate { get; set; } = true;

        /// <summary>
        /// 是否在启动时检查服务器连接
        /// </summary>
        public bool CheckConnectionOnStartup { get; set; } = true;

        /// <summary>
        /// 用户名（用于统计）
        /// </summary>
        public string Username { get; set; } = Environment.UserName;

        /// <summary>
        /// 部门名称（用于统计）
        /// </summary>
        public string Department { get; set; } = "";

        /// <summary>
        /// Yuantus PLM 租户 ID（用于插件 API）
        /// </summary>
        public string TenantId { get; set; } = "tenant-1";

        /// <summary>
        /// Yuantus PLM 组织 ID（用于插件 API）
        /// </summary>
        public string OrgId { get; set; } = "org-1";

        /// <summary>
        /// CAD 物料同步默认 profile
        /// </summary>
        public string MaterialProfileId { get; set; } = "sheet";

        /// <summary>
        /// CAD 回写 PLM 默认使用 dry-run，避免误覆盖
        /// </summary>
        public bool MaterialSyncDryRunDefault { get; set; } = true;

        #region 配置文件管理

        private static readonly string ConfigFile = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
            "CADDedup",
            "config.json"
        );

        /// <summary>
        /// 加载配置
        /// </summary>
        public static DedupConfig Load()
        {
            try
            {
                if (File.Exists(ConfigFile))
                {
                    var json = File.ReadAllText(ConfigFile);
                    return JsonConvert.DeserializeObject<DedupConfig>(json);
                }
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"加载配置失败: {ex.Message}");
            }

            // 返回默认配置
            var config = new DedupConfig();
            config.Save(); // 保存默认配置
            return config;
        }

        /// <summary>
        /// 保存配置
        /// </summary>
        public void Save()
        {
            try
            {
                var dir = Path.GetDirectoryName(ConfigFile);
                if (!Directory.Exists(dir))
                    Directory.CreateDirectory(dir);

                var json = JsonConvert.SerializeObject(this, Formatting.Indented);
                File.WriteAllText(ConfigFile, json);
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"保存配置失败: {ex.Message}");
                throw;
            }
        }

        /// <summary>
        /// 验证配置
        /// </summary>
        public bool Validate(out string errorMessage)
        {
            errorMessage = null;

            // 检查服务器地址
            if (string.IsNullOrWhiteSpace(ServerUrl))
            {
                errorMessage = "服务器地址不能为空";
                return false;
            }

            if (!Uri.TryCreate(ServerUrl, UriKind.Absolute, out Uri uri))
            {
                errorMessage = "服务器地址格式无效";
                return false;
            }

            // 检查相似度阈值
            if (SimilarityThreshold < 0.0 || SimilarityThreshold > 1.0)
            {
                errorMessage = "相似度阈值必须在 0.0 到 1.0 之间";
                return false;
            }

            // 检查超时时间
            if (TimeoutSeconds < 5 || TimeoutSeconds > 300)
            {
                errorMessage = "超时时间必须在 5 到 300 秒之间";
                return false;
            }

            return true;
        }

        /// <summary>
        /// 重置为默认值
        /// </summary>
        public void ResetToDefault()
        {
            ServerUrl = "http://localhost:8000";
            ApiKey = "";
            AutoCheckEnabled = true;
            SimilarityThreshold = 0.85;
            AutoIndex = true;
            TimeoutSeconds = 30;
            PromptOnHighSimilarity = true;
            ShowNotificationOnUnique = false;
            PlaySoundOnDuplicate = true;
            CheckConnectionOnStartup = true;
            Username = Environment.UserName;
            Department = "";
            TenantId = "tenant-1";
            OrgId = "org-1";
            MaterialProfileId = "sheet";
            MaterialSyncDryRunDefault = true;
        }

        #endregion

        #region 配置预设

        /// <summary>
        /// 严格模式 - 更高的相似度阈值
        /// </summary>
        public static DedupConfig StrictMode()
        {
            var config = new DedupConfig
            {
                SimilarityThreshold = 0.95,
                PromptOnHighSimilarity = true,
                ShowNotificationOnUnique = false
            };
            return config;
        }

        /// <summary>
        /// 宽松模式 - 更低的相似度阈值
        /// </summary>
        public static DedupConfig RelaxedMode()
        {
            var config = new DedupConfig
            {
                SimilarityThreshold = 0.70,
                PromptOnHighSimilarity = false,
                ShowNotificationOnUnique = true
            };
            return config;
        }

        /// <summary>
        /// 静默模式 - 减少通知
        /// </summary>
        public static DedupConfig SilentMode()
        {
            var config = new DedupConfig
            {
                ShowNotificationOnUnique = false,
                PlaySoundOnDuplicate = false,
                PromptOnHighSimilarity = false
            };
            return config;
        }

        #endregion
    }
}
