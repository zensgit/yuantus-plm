namespace Yuantus.Cad.Bridge
{
    /// <summary>
    /// Outcome of a single <c>yuantus-helper-call</c> Lisp invocation.
    /// Lisp callers see <c>Payload</c> as a JSON string on success, or
    /// <c>null</c> on failure with a sanitized command-line error already
    /// written by the bridge.
    /// </summary>
    public sealed class BridgeResult
    {
        private BridgeResult(bool ok, string payload, string code, string reason)
        {
            Ok = ok;
            Payload = payload;
            Code = code;
            Reason = reason;
        }

        public bool Ok { get; private set; }
        public string Payload { get; private set; }
        public string Code { get; private set; }
        public string Reason { get; private set; }

        public static BridgeResult Success(string payload)
        {
            return new BridgeResult(true, payload, null, null);
        }

        public static BridgeResult Failure(string code, string reason)
        {
            return new BridgeResult(false, null, code, reason);
        }
    }
}
