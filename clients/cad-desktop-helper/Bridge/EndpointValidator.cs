using System;

namespace Yuantus.Cad.Bridge
{
    /// <summary>
    /// Token-exfiltration and URI-confusion guard for the
    /// <c>endpoint</c> argument of the <c>yuantus-helper-call</c> Lisp
    /// primitive. Implements the rejection list in taskbook §3.C; the helper
    /// S4/S5/S6 gates remain the authoritative source for auth / origin /
    /// session policy.
    /// </summary>
    public static class EndpointValidator
    {
        /// <summary>
        /// Returns <c>true</c> when <paramref name="endpoint"/> is a safe
        /// helper-relative path the bridge may forward through
        /// <see cref="Yuantus.Cad.Shared.Transport.HelperTransport"/>.
        /// </summary>
        public static bool IsValid(string endpoint)
        {
            return TryValidate(endpoint, out _);
        }

        /// <summary>
        /// Same as <see cref="IsValid"/> but yields a short reason token for
        /// rejection cases, suitable for the sanitized command-line failure
        /// line described in §3.G.
        /// </summary>
        public static bool TryValidate(string endpoint, out string rejectionReason)
        {
            rejectionReason = null;

            if (string.IsNullOrEmpty(endpoint))
            {
                rejectionReason = "endpoint_missing";
                return false;
            }

            if (endpoint != endpoint.Trim())
            {
                rejectionReason = "endpoint_whitespace";
                return false;
            }

            if (string.IsNullOrWhiteSpace(endpoint))
            {
                rejectionReason = "endpoint_whitespace";
                return false;
            }

            for (var i = 0; i < endpoint.Length; i++)
            {
                var ch = endpoint[i];
                if (ch == '\r' || ch == '\n' || ch == '\t' || ch < 0x20 || ch == 0x7f)
                {
                    rejectionReason = "endpoint_control_char";
                    return false;
                }
                if (ch == '\\')
                {
                    rejectionReason = "endpoint_backslash";
                    return false;
                }
                if (ch == '%')
                {
                    rejectionReason = "endpoint_percent";
                    return false;
                }
            }

            if (endpoint[0] != '/')
            {
                rejectionReason = "endpoint_not_rooted";
                return false;
            }

            if (endpoint.Length >= 2 && endpoint[1] == '/')
            {
                rejectionReason = "endpoint_network_path";
                return false;
            }

            if (HasAbsoluteScheme(endpoint))
            {
                rejectionReason = "endpoint_absolute_scheme";
                return false;
            }

            return true;
        }

        private static bool HasAbsoluteScheme(string endpoint)
        {
            // The path already starts with '/' so an embedded scheme such as
            // "http://" can only appear inline, e.g. "/redirect/http://...".
            // .NET's Uri parser performs surprising normalization on such
            // strings; reject any inline scheme prefix to keep the guard
            // independent of Uri behavior.
            var lower = endpoint.ToLowerInvariant();
            if (lower.IndexOf("http://", StringComparison.Ordinal) >= 0) return true;
            if (lower.IndexOf("https://", StringComparison.Ordinal) >= 0) return true;
            if (lower.IndexOf("file://", StringComparison.Ordinal) >= 0) return true;
            if (lower.IndexOf("ftp://", StringComparison.Ordinal) >= 0) return true;
            if (lower.IndexOf("javascript:", StringComparison.Ordinal) >= 0) return true;
            if (lower.IndexOf("data:", StringComparison.Ordinal) >= 0) return true;
            return false;
        }
    }
}
