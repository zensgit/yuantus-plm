using System;
using System.Threading;
using System.Threading.Tasks;
using Yuantus.Cad.Shared.Discovery;

namespace Yuantus.Cad.Bridge
{
    /// <summary>
    /// Production <see cref="IBridgeLocator"/> implementation. Delegates to
    /// S1 <see cref="HelperLocator.EnsureHelperRunningAsync"/>, which owns
    /// the helper-session-file probe, the <c>/healthz</c> poll, and
    /// helper-process spawn through S1 <c>HelperSpawner</c>. The Bridge never
    /// reads DPAPI directly, never spawns the helper directly, and never
    /// duplicates the discovery flow.
    /// </summary>
    public sealed class SharedBridgeLocator : IBridgeLocator
    {
        public async Task<Uri> EnsureHelperRunningAsync(CancellationToken cancellationToken)
        {
            using (var locator = new HelperLocator())
            {
                return await locator.EnsureHelperRunningAsync(cancellationToken).ConfigureAwait(false);
            }
        }
    }
}
