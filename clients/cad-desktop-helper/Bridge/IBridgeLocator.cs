using System;
using System.Threading;
using System.Threading.Tasks;

namespace Yuantus.Cad.Bridge
{
    /// <summary>
    /// Narrow seam for resolving the helper base URI. Production
    /// implementation (<see cref="SharedBridgeLocator"/>) delegates to S1
    /// <c>Yuantus.Cad.Shared.Discovery.HelperLocator.EnsureHelperRunningAsync</c>,
    /// which already has real-seam coverage in S1 Shared.Tests. Unit tests in
    /// the Bridge.Tests assembly inject fakes to verify the bridge's wiring
    /// shape without re-exercising the OS / network seam.
    /// </summary>
    public interface IBridgeLocator
    {
        Task<Uri> EnsureHelperRunningAsync(CancellationToken cancellationToken);
    }
}
