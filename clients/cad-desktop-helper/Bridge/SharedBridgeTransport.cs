using System;
using System.Threading;
using System.Threading.Tasks;
using Newtonsoft.Json.Linq;
using Yuantus.Cad.Shared.Transport;

namespace Yuantus.Cad.Bridge
{
    /// <summary>
    /// Production <see cref="IBridgeTransport"/> implementation. Each call
    /// constructs and disposes a fresh S1 <see cref="HelperTransport"/>
    /// bound to the locator-resolved base URI. The Bridge never builds its
    /// own <see cref="System.Net.Http.HttpClient"/> and never re-implements
    /// the helper envelope parser.
    /// </summary>
    public sealed class SharedBridgeTransport : IBridgeTransport
    {
        public async Task<JToken> PostJsonAsync(
            Uri baseUri,
            string endpoint,
            JObject payload,
            CancellationToken cancellationToken)
        {
            using (var transport = new HelperTransport(baseUri))
            {
                return await transport
                    .PostJsonAsync<JToken>(endpoint, payload, cancellationToken)
                    .ConfigureAwait(false);
            }
        }
    }
}
