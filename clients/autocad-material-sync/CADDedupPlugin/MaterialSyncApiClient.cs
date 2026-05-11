// MaterialSyncApiClient.cs - Yuantus CAD 物料同步 API 客户端
using System;
using System.Collections.Generic;
using System.Net.Http;
using System.Net.Http.Headers;
using System.Text;
using System.Threading.Tasks;
using Newtonsoft.Json;

namespace CADDedupPlugin
{
    /// <summary>
    /// 调用 Yuantus PLM cad-material-sync 插件。
    /// </summary>
    public class MaterialSyncApiClient
    {
        private const string BasePath = "/api/v1/plugins/cad-material-sync";
        private const string CadSystem = "autocad";

        private readonly HttpClient _httpClient;
        private DedupConfig _config;

        public MaterialSyncApiClient(DedupConfig config)
        {
            _config = config;
            _httpClient = new HttpClient
            {
                BaseAddress = new Uri(_config.ServerUrl),
                Timeout = TimeSpan.FromSeconds(_config.TimeoutSeconds)
            };
            ConfigureHeaders();
        }

        public void UpdateConfig(DedupConfig config)
        {
            _config = config;
            _httpClient.BaseAddress = new Uri(_config.ServerUrl);
            _httpClient.Timeout = TimeSpan.FromSeconds(_config.TimeoutSeconds);
            ConfigureHeaders();
        }

        public async Task<MaterialProfilesResponse> GetProfilesAsync()
        {
            var request = CreateRequest(HttpMethod.Get, $"{BasePath}/profiles");
            var response = await _httpClient.SendAsync(request);
            return await ReadJsonAsync<MaterialProfilesResponse>(response);
        }

        public async Task<MaterialProfileResponse> GetProfileAsync(string profileId)
        {
            var safeProfileId = Uri.EscapeDataString(profileId ?? _config.MaterialProfileId ?? "sheet");
            var request = CreateRequest(HttpMethod.Get, $"{BasePath}/profiles/{safeProfileId}");
            var response = await _httpClient.SendAsync(request);
            return await ReadJsonAsync<MaterialProfileResponse>(response);
        }

        public async Task<MaterialSyncResponse> ComposeAsync(
            string profileId,
            Dictionary<string, object> values)
        {
            var payload = new
            {
                profile_id = profileId,
                values = values ?? new Dictionary<string, object>(),
                include_cad_fields = true,
                cad_system = CadSystem
            };
            var response = await _httpClient.SendAsync(
                CreateJsonRequest(HttpMethod.Post, $"{BasePath}/compose", payload));
            return await ReadJsonAsync<MaterialSyncResponse>(response);
        }

        public async Task<MaterialSyncResponse> ValidateAsync(
            string profileId,
            Dictionary<string, object> values,
            bool lookupExisting)
        {
            var payload = new
            {
                profile_id = profileId,
                values = values ?? new Dictionary<string, object>(),
                lookup_existing = lookupExisting,
                cad_system = CadSystem
            };
            var response = await _httpClient.SendAsync(
                CreateJsonRequest(HttpMethod.Post, $"{BasePath}/validate", payload));
            return await ReadJsonAsync<MaterialSyncResponse>(response);
        }

        public async Task<MaterialSyncResponse> SyncInboundAsync(
            string profileId,
            Dictionary<string, object> cadFields,
            bool dryRun,
            bool overwrite,
            bool createIfMissing)
        {
            var payload = new
            {
                profile_id = profileId,
                cad_fields = cadFields ?? new Dictionary<string, object>(),
                dry_run = dryRun,
                overwrite = overwrite,
                create_if_missing = createIfMissing,
                cad_system = CadSystem
            };
            var response = await _httpClient.SendAsync(
                CreateJsonRequest(HttpMethod.Post, $"{BasePath}/sync/inbound", payload));
            return await ReadJsonAsync<MaterialSyncResponse>(response);
        }

        public async Task<MaterialSyncResponse> SyncOutboundAsync(
            string profileId,
            string itemId,
            bool includeEmpty)
        {
            var payload = new
            {
                profile_id = profileId,
                item_id = itemId,
                include_empty = includeEmpty,
                cad_system = CadSystem
            };
            var response = await _httpClient.SendAsync(
                CreateJsonRequest(HttpMethod.Post, $"{BasePath}/sync/outbound", payload));
            return await ReadJsonAsync<MaterialSyncResponse>(response);
        }

        public async Task<MaterialDiffPreviewResponse> DiffPreviewAsync(
            string profileId,
            string itemId,
            Dictionary<string, object> currentCadFields,
            bool includeEmpty)
        {
            var payload = new
            {
                profile_id = profileId,
                item_id = itemId,
                current_cad_fields = currentCadFields ?? new Dictionary<string, object>(),
                include_empty = includeEmpty,
                cad_system = CadSystem
            };
            var response = await _httpClient.SendAsync(
                CreateJsonRequest(HttpMethod.Post, $"{BasePath}/diff/preview", payload));
            return await ReadJsonAsync<MaterialDiffPreviewResponse>(response);
        }

        private void ConfigureHeaders()
        {
            _httpClient.DefaultRequestHeaders.Clear();
            if (!string.IsNullOrWhiteSpace(_config.ApiKey))
            {
                _httpClient.DefaultRequestHeaders.Authorization =
                    new AuthenticationHeaderValue("Bearer", _config.ApiKey);
            }
            if (!string.IsNullOrWhiteSpace(_config.TenantId))
            {
                _httpClient.DefaultRequestHeaders.Add("x-tenant-id", _config.TenantId);
            }
            if (!string.IsNullOrWhiteSpace(_config.OrgId))
            {
                _httpClient.DefaultRequestHeaders.Add("x-org-id", _config.OrgId);
            }
        }

        private HttpRequestMessage CreateRequest(HttpMethod method, string path)
        {
            return new HttpRequestMessage(method, path);
        }

        private HttpRequestMessage CreateJsonRequest(HttpMethod method, string path, object payload)
        {
            var request = CreateRequest(method, path);
            var json = JsonConvert.SerializeObject(payload);
            request.Content = new StringContent(json, Encoding.UTF8, "application/json");
            return request;
        }

        private static async Task<T> ReadJsonAsync<T>(HttpResponseMessage response)
        {
            var body = await response.Content.ReadAsStringAsync();
            if (!response.IsSuccessStatusCode)
            {
                throw new Exception($"PLM 物料同步 API 失败: {(int)response.StatusCode} {body}");
            }
            return JsonConvert.DeserializeObject<T>(body);
        }
    }

    public class MaterialProfilesResponse
    {
        [JsonProperty("ok")]
        public bool Ok { get; set; }

        [JsonProperty("profiles")]
        public List<MaterialProfile> Profiles { get; set; } = new List<MaterialProfile>();
    }

    public class MaterialProfileResponse
    {
        [JsonProperty("ok")]
        public bool Ok { get; set; }

        [JsonProperty("profile")]
        public MaterialProfile Profile { get; set; }
    }

    public class MaterialProfile
    {
        [JsonProperty("profile_id")]
        public string ProfileId { get; set; }

        [JsonProperty("label")]
        public string Label { get; set; }

        [JsonProperty("fields")]
        public List<MaterialFieldDefinition> Fields { get; set; } = new List<MaterialFieldDefinition>();
    }

    public class MaterialFieldDefinition
    {
        [JsonProperty("name")]
        public string Name { get; set; }

        [JsonProperty("label")]
        public string Label { get; set; }

        [JsonProperty("type")]
        public string Type { get; set; }

        [JsonProperty("required")]
        public bool Required { get; set; }

        [JsonProperty("default")]
        public object DefaultValue { get; set; }

        [JsonProperty("unit")]
        public string Unit { get; set; }

        [JsonProperty("cad_key")]
        public string CadKey { get; set; }
    }

    public class MaterialSyncResponse
    {
        [JsonProperty("ok")]
        public bool Ok { get; set; }

        [JsonProperty("valid")]
        public bool Valid { get; set; }

        [JsonProperty("action")]
        public string Action { get; set; }

        [JsonProperty("profile_id")]
        public string ProfileId { get; set; }

        [JsonProperty("item_id")]
        public string ItemId { get; set; }

        [JsonProperty("dry_run")]
        public bool DryRun { get; set; }

        [JsonProperty("properties")]
        public Dictionary<string, object> Properties { get; set; } = new Dictionary<string, object>();

        [JsonProperty("cad_fields")]
        public Dictionary<string, object> CadFields { get; set; } = new Dictionary<string, object>();

        [JsonProperty("matched_items")]
        public List<Dictionary<string, object>> MatchedItems { get; set; } = new List<Dictionary<string, object>>();

        [JsonProperty("errors")]
        public List<MaterialSyncIssue> Errors { get; set; } = new List<MaterialSyncIssue>();

        [JsonProperty("warnings")]
        public List<string> Warnings { get; set; } = new List<string>();

        [JsonProperty("conflicts")]
        public List<MaterialSyncIssue> Conflicts { get; set; } = new List<MaterialSyncIssue>();
    }

    public class MaterialSyncIssue
    {
        [JsonProperty("field")]
        public string Field { get; set; }

        [JsonProperty("code")]
        public string Code { get; set; }

        [JsonProperty("message")]
        public string Message { get; set; }

        [JsonProperty("current")]
        public object Current { get; set; }

        [JsonProperty("incoming")]
        public object Incoming { get; set; }
    }

    public class MaterialDiffPreviewResponse
    {
        [JsonProperty("ok")]
        public bool Ok { get; set; }

        [JsonProperty("profile_id")]
        public string ProfileId { get; set; }

        [JsonProperty("item_id")]
        public string ItemId { get; set; }

        [JsonProperty("properties")]
        public Dictionary<string, object> Properties { get; set; } = new Dictionary<string, object>();

        [JsonProperty("current_cad_fields")]
        public Dictionary<string, object> CurrentCadFields { get; set; } = new Dictionary<string, object>();

        [JsonProperty("target_cad_fields")]
        public Dictionary<string, object> TargetCadFields { get; set; } = new Dictionary<string, object>();

        [JsonProperty("write_cad_fields")]
        public Dictionary<string, object> WriteCadFields { get; set; } = new Dictionary<string, object>();

        [JsonProperty("requires_confirmation")]
        public bool RequiresConfirmation { get; set; }

        [JsonProperty("diffs")]
        public List<MaterialCadFieldDiff> Diffs { get; set; } = new List<MaterialCadFieldDiff>();

        [JsonProperty("summary")]
        public Dictionary<string, int> Summary { get; set; } = new Dictionary<string, int>();

        [JsonProperty("errors")]
        public List<MaterialSyncIssue> Errors { get; set; } = new List<MaterialSyncIssue>();

        [JsonProperty("warnings")]
        public List<string> Warnings { get; set; } = new List<string>();
    }

    public class MaterialCadFieldDiff
    {
        [JsonProperty("cad_key")]
        public string CadKey { get; set; }

        [JsonProperty("property")]
        public string Property { get; set; }

        [JsonProperty("current")]
        public object Current { get; set; }

        [JsonProperty("target")]
        public object Target { get; set; }

        [JsonProperty("status")]
        public string Status { get; set; }
    }
}
