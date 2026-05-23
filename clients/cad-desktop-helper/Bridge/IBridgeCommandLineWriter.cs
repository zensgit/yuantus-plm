namespace Yuantus.Cad.Bridge
{
    /// <summary>
    /// Narrow seam for emitting one sanitized bridge failure line to the CAD
    /// command line. The SDK-free <see cref="ConsoleBridgeCommandLineWriter"/>
    /// targets <see cref="System.Console.Error"/> for unit-testable coverage of
    /// the formatting rules in taskbook §3.G. The production CAD host adapter
    /// (see <c>Adapters/AutoCadHostAdapter.cs</c>) supplies an implementation
    /// that writes through the AutoCAD editor / command-line API, and that
    /// production path is deferred to native-CAD operational signoff per §3.K.
    /// </summary>
    public interface IBridgeCommandLineWriter
    {
        void WriteFailure(string code, string reason);
    }
}
