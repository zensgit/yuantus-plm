using System;
using System.Threading;
using System.Threading.Tasks;
using Newtonsoft.Json.Linq;

namespace Yuantus.Cad.Bridge
{
    /// <summary>
    /// Narrow seam for posting a JSON payload to a helper endpoint and
    /// receiving the helper <c>data</c> payload back. Production
    /// implementation (<see cref="SharedBridgeTransport"/>) delegates to S1
    /// <c>Yuantus.Cad.Shared.Transport.HelperTransport.PostJsonAsync</c>,
    /// which already injects <c>X-Yuantus-Local-Token</c> and
    /// <c>X-Yuantus-Protocol</c>, parses the helper envelope, and maps
    /// non-2xx / <c>ok=false</c> envelopes to <c>HelperException</c>.
    /// </summary>
    public interface IBridgeTransport
    {
        Task<JToken> PostJsonAsync(
            Uri baseUri,
            string endpoint,
            JObject payload,
            CancellationToken cancellationToken);
    }
}
