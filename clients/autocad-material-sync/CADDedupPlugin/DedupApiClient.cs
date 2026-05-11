// DedupApiClient.cs - 查重服务器API客户端
using System;
using System.Collections.Generic;
using System.IO;
using System.Net.Http;
using System.Net.Http.Headers;
using System.Threading.Tasks;
using Newtonsoft.Json;

namespace CADDedupPlugin
{
    /// <summary>
    /// 查重API客户端
    /// </summary>
    public class DedupApiClient
    {
        private readonly HttpClient _httpClient;
        private readonly DedupConfig _config;
        private DedupResult _lastResult;
        private readonly UsageStatistics _stats;

        public DedupApiClient(DedupConfig config)
        {
            _config = config;
            _stats = UsageStatistics.Load();

            _httpClient = new HttpClient
            {
                BaseAddress = new Uri(_config.ServerUrl),
                Timeout = TimeSpan.FromSeconds(_config.TimeoutSeconds)
            };

            if (!string.IsNullOrEmpty(_config.ApiKey))
            {
                _httpClient.DefaultRequestHeaders.Authorization =
                    new AuthenticationHeaderValue("Bearer", _config.ApiKey);
            }
        }

        /// <summary>
        /// 检查文件是否重复
        /// </summary>
        public async Task<DedupResult> CheckDuplicateAsync(string filePath)
        {
            if (!File.Exists(filePath))
                throw new FileNotFoundException("文件不存在", filePath);

            try
            {
                using (var form = new MultipartFormDataContent())
                // 使用共享读取模式，允许其他进程（如AutoCAD）同时访问文件
                using (var fileStream = new FileStream(filePath, FileMode.Open, FileAccess.Read, FileShare.ReadWrite))
                {
                    var fileContent = new StreamContent(fileStream);
                    fileContent.Headers.ContentType =
                        new MediaTypeHeaderValue("application/octet-stream");

                    form.Add(fileContent, "file", Path.GetFileName(filePath));
                    form.Add(new StringContent(_config.SimilarityThreshold.ToString()),
                            "threshold");
                    form.Add(new StringContent(_config.AutoIndex.ToString().ToLower()),
                            "auto_index");
                    // 添加文件完整路径，用于识别是否是同一文件
                    form.Add(new StringContent(filePath), "file_path");

                    var response = await _httpClient.PostAsync("/api/dedup/check", form);
                    response.EnsureSuccessStatusCode();

                    var json = await response.Content.ReadAsStringAsync();
                    var result = JsonConvert.DeserializeObject<DedupResult>(json);

                    // 保存结果
                    _lastResult = result;

                    // 更新统计
                    _stats.TotalChecks++;
                    if (result.IsDuplicate)
                    {
                        _stats.DuplicatesFound++;
                        // 假设发现重复可以节省2天工时
                        _stats.EstimatedTimeSaved += 16; // 2天 * 8小时
                    }
                    else
                    {
                        _stats.UniqueDrawings++;
                    }
                    _stats.Save();

                    return result;
                }
            }
            catch (HttpRequestException ex)
            {
                throw new Exception($"无法连接到查重服务器: {ex.Message}", ex);
            }
            catch (TaskCanceledException)
            {
                throw new Exception("请求超时，请检查网络连接或增加超时时间");
            }
        }

        /// <summary>
        /// 获取上次检查结果
        /// </summary>
        public DedupResult GetLastResult()
        {
            return _lastResult;
        }

        /// <summary>
        /// 更新配置
        /// </summary>
        public void UpdateConfig(DedupConfig config)
        {
            _httpClient.BaseAddress = new Uri(config.ServerUrl);
            _httpClient.Timeout = TimeSpan.FromSeconds(config.TimeoutSeconds);

            if (!string.IsNullOrEmpty(config.ApiKey))
            {
                _httpClient.DefaultRequestHeaders.Authorization =
                    new AuthenticationHeaderValue("Bearer", config.ApiKey);
            }
            else
            {
                _httpClient.DefaultRequestHeaders.Authorization = null;
            }
        }

        /// <summary>
        /// 获取使用统计
        /// </summary>
        public UsageStatistics GetStatistics()
        {
            return _stats;
        }

        /// <summary>
        /// 测试服务器连接
        /// </summary>
        public async Task<bool> TestConnectionAsync()
        {
            try
            {
                foreach (var path in new[] { "/api/health", "/api/v1/health", "/health" })
                {
                    var response = await _httpClient.GetAsync(path);
                    if (response.IsSuccessStatusCode)
                    {
                        return true;
                    }
                }
                return false;
            }
            catch
            {
                return false;
            }
        }
    }

    /// <summary>
    /// 查重结果
    /// </summary>
    public class DedupResult
    {
        [JsonProperty("is_duplicate")]
        public bool IsDuplicate { get; set; }

        [JsonProperty("check_id")]
        public string CheckId { get; set; }

        [JsonProperty("duplicates")]
        public List<DuplicateMatch> Duplicates { get; set; }

        [JsonProperty("message")]
        public string Message { get; set; }

        public DedupResult()
        {
            Duplicates = new List<DuplicateMatch>();
        }
    }

    /// <summary>
    /// 重复匹配项
    /// </summary>
    public class DuplicateMatch
    {
        [JsonProperty("filename")]
        public string FileName { get; set; }

        [JsonProperty("similarity")]
        public double Similarity { get; set; }

        [JsonProperty("preview_url")]
        public string PreviewUrl { get; set; }

        [JsonProperty("file_path")]
        public string FilePath { get; set; }

        [JsonProperty("created_at")]
        public DateTime CreatedAt { get; set; }

        [JsonProperty("created_by")]
        public string CreatedBy { get; set; }
    }

    /// <summary>
    /// 使用统计
    /// </summary>
    public class UsageStatistics
    {
        public int TotalChecks { get; set; }
        public int DuplicatesFound { get; set; }
        public int UniqueDrawings { get; set; }
        public double EstimatedTimeSaved { get; set; } // 小时

        [JsonIgnore]
        public double DuplicateRate =>
            TotalChecks > 0 ? (double)DuplicatesFound / TotalChecks : 0;

        private static readonly string StatsFile = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
            "CADDedup",
            "statistics.json"
        );

        public static UsageStatistics Load()
        {
            try
            {
                if (File.Exists(StatsFile))
                {
                    var json = File.ReadAllText(StatsFile);
                    return JsonConvert.DeserializeObject<UsageStatistics>(json);
                }
            }
            catch
            {
                // 加载失败，返回新实例
            }

            return new UsageStatistics();
        }

        public void Save()
        {
            try
            {
                var dir = Path.GetDirectoryName(StatsFile);
                if (!Directory.Exists(dir))
                    Directory.CreateDirectory(dir);

                var json = JsonConvert.SerializeObject(this, Formatting.Indented);
                File.WriteAllText(StatsFile, json);
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"保存统计失败: {ex.Message}");
            }
        }
    }
}
