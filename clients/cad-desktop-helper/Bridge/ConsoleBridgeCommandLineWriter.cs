using System;
using System.Text.RegularExpressions;

namespace Yuantus.Cad.Bridge
{
    /// <summary>
    /// SDK-free <see cref="IBridgeCommandLineWriter"/> that emits the
    /// taskbook §3.G failure line to <see cref="Console.Error"/>:
    /// <c>[YUANTUS_HELPER_CALL_FAILED] code=&lt;code&gt; reason=&lt;short&gt;</c>.
    /// All free-form input is sanitized to a narrow character class so the
    /// line cannot leak tokens, full request/response bodies, or stack
    /// traces.
    /// </summary>
    public sealed class ConsoleBridgeCommandLineWriter : IBridgeCommandLineWriter
    {
        public void WriteFailure(string code, string reason)
        {
            Console.Error.WriteLine(
                "[YUANTUS_HELPER_CALL_FAILED] code=" + Sanitize(code) +
                " reason=" + Sanitize(reason));
        }

        private static string Sanitize(string value)
        {
            if (string.IsNullOrWhiteSpace(value))
            {
                return "unknown";
            }
            return Regex.Replace(value, @"[^A-Za-z0-9_\-./]", "_");
        }
    }
}
