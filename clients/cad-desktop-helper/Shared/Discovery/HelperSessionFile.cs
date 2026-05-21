using System;
using System.IO;
using Newtonsoft.Json;
using Yuantus.Cad.Shared.Identity;

namespace Yuantus.Cad.Shared.Discovery
{
    public sealed class HelperSessionFile
    {
        [JsonProperty("schema_version")]
        public string SchemaVersion { get; set; }

        [JsonProperty("session_id")]
        public int SessionId { get; set; }

        [JsonProperty("port")]
        public int Port { get; set; }

        [JsonProperty("pid")]
        public int Pid { get; set; }

        [JsonProperty("image_path")]
        public string ImagePath { get; set; }

        [JsonProperty("started_at")]
        public DateTimeOffset StartedAt { get; set; }

        [JsonProperty("protocol_version")]
        public string ProtocolVersion { get; set; }

        [JsonProperty("helper_version")]
        public string HelperVersion { get; set; }

        [JsonProperty("endpoints_base")]
        public string EndpointsBase { get; set; }

        public static string Path
        {
            get { return Paths.HelperSessionFilePath; }
        }

        public static HelperSessionFile Read()
        {
            var path = Path;
            if (!File.Exists(path))
            {
                return null;
            }
            var json = File.ReadAllText(path);
            return JsonConvert.DeserializeObject<HelperSessionFile>(json);
        }

        public Uri ToBaseUri()
        {
            if (!string.IsNullOrWhiteSpace(EndpointsBase))
            {
                return new Uri(EndpointsBase, UriKind.Absolute);
            }
            return new Uri(string.Format("http://127.0.0.1:{0}", Port));
        }
    }
}
