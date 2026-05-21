using System;
using System.Net;
using System.Net.Http;
using System.Threading;
using System.Threading.Tasks;

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
                        return HelperProbeResult.FromStatus(response.StatusCode);
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
        private HelperProbeResult(HttpStatusCode? statusCode, bool timedOut, Exception error)
        {
            StatusCode = statusCode;
            TimedOut = timedOut;
            Error = error;
        }

        public HttpStatusCode? StatusCode { get; private set; }
        public bool TimedOut { get; private set; }
        public Exception Error { get; private set; }
        public bool IsHealthy
        {
            get { return StatusCode == HttpStatusCode.OK && !TimedOut && Error == null; }
        }

        public static HelperProbeResult FromStatus(HttpStatusCode statusCode)
        {
            return new HelperProbeResult(statusCode, false, null);
        }

        public static HelperProbeResult Timeout()
        {
            return new HelperProbeResult(null, true, null);
        }

        public static HelperProbeResult Failed(Exception error)
        {
            return new HelperProbeResult(null, false, error);
        }
    }
}
