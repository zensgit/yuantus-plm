using System;
using System.Net;
using System.Net.Http;
using System.Threading;
using System.Threading.Tasks;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;

namespace Yuantus.Cad.Shared.Discovery
{
    public sealed class HelperProbe : IDisposable
    {
        public static readonly TimeSpan DefaultTimeout = TimeSpan.FromMilliseconds(500);

        private readonly HttpClient _httpClient;
        private readonly bool _disposeClient;

        public HelperProbe()
            : this(new HttpClient(), true)
        {
        }

        public HelperProbe(HttpMessageHandler handler)
            : this(new HttpClient(handler), true)
        {
        }

        public HelperProbe(HttpClient httpClient)
            : this(httpClient, false)
        {
        }

        private HelperProbe(HttpClient httpClient, bool disposeClient)
        {
            _httpClient = httpClient;
            _disposeClient = disposeClient;
        }

        public async Task<HelperProbeResult> HealthAsync(
            string host,
            int port,
            TimeSpan timeout,
            CancellationToken cancellationToken)
        {
            var uri = new Uri(string.Format("http://{0}:{1}/healthz", host, port));
            using (var timeoutSource = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken))
            {
                timeoutSource.CancelAfter(timeout);
                try
                {
                    using (var request = new HttpRequestMessage(HttpMethod.Get, uri))
                    using (var response = await _httpClient.SendAsync(request, timeoutSource.Token).ConfigureAwait(false))
                    {
                        if (response.StatusCode != HttpStatusCode.OK)
                        {
                            return HelperProbeResult.FromStatus(response.StatusCode, false);
                        }

                        var body = response.Content == null
                            ? string.Empty
                            : await response.Content.ReadAsStringAsync().ConfigureAwait(false);
                        return HelperProbeResult.FromStatus(response.StatusCode, IsExpectedHealthBody(body));
                    }
                }
                catch (OperationCanceledException)
                {
                    if (cancellationToken.IsCancellationRequested)
                    {
                        throw;
                    }
                    return HelperProbeResult.Timeout();
                }
                catch (Exception ex)
                {
                    return HelperProbeResult.Failed(ex);
                }
            }
        }

        public Task<HelperProbeResult> HealthAsync(int port, CancellationToken cancellationToken)
        {
            return HealthAsync("127.0.0.1", port, DefaultTimeout, cancellationToken);
        }

        private static bool IsExpectedHealthBody(string body)
        {
            if (string.IsNullOrWhiteSpace(body))
            {
                return false;
            }

            try
            {
                var document = JObject.Parse(body);
                var ok = document["ok"];
                if (ok != null && ok.Type == JTokenType.Boolean && ok.Value<bool>())
                {
                    return true;
                }

                var status = document["status"];
                return status != null &&
                       status.Type == JTokenType.String &&
                       string.Equals(status.Value<string>(), "ok", StringComparison.OrdinalIgnoreCase);
            }
            catch (JsonException)
            {
                return false;
            }
        }

        public void Dispose()
        {
            if (_disposeClient)
            {
                _httpClient.Dispose();
            }
        }
    }

    public sealed class HelperProbeResult
    {
        private HelperProbeResult(HttpStatusCode? statusCode, bool bodyAccepted, bool timedOut, Exception error)
        {
            StatusCode = statusCode;
            BodyAccepted = bodyAccepted;
            TimedOut = timedOut;
            Error = error;
        }

        public HttpStatusCode? StatusCode { get; private set; }
        public bool BodyAccepted { get; private set; }
        public bool TimedOut { get; private set; }
        public Exception Error { get; private set; }
        public bool IsHealthy
        {
            get { return StatusCode == HttpStatusCode.OK && BodyAccepted && !TimedOut && Error == null; }
        }

        public static HelperProbeResult FromStatus(HttpStatusCode statusCode, bool bodyAccepted)
        {
            return new HelperProbeResult(statusCode, bodyAccepted, false, null);
        }

        public static HelperProbeResult Timeout()
        {
            return new HelperProbeResult(null, false, true, null);
        }

        public static HelperProbeResult Failed(Exception error)
        {
            return new HelperProbeResult(null, false, false, error);
        }
    }
}
