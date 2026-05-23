// CAD-host adapter for the S9 NETLOAD Lisp bridge.
//
// This file contains the AutoCAD-specific NETLOAD entry point and the
// `(yuantus-helper-call ...)` Lisp registration shim. Real AutoCAD managed
// assemblies (acmgd.dll / accoremgd.dll) are not available on the GitHub
// Windows runner, so the SDK-free CI build excludes the host-bound code via
// the `AUTOCAD_HOST` compilation symbol. The bridge's SDK-free core
// (`BridgeCallService`, `EndpointValidator`, the transport / locator seams,
// and the command-line writer interface) is fully unit-tested in
// `Bridge.Tests` without AutoCAD references.
//
// Operational NETLOAD evidence (DLL loads inside acad.exe / ZWCAD.exe /
// gscad.exe, real CAD command-line writer prints sanitized error lines, etc.)
// is deferred to native-CAD operational signoff per taskbook §3.K.

#if AUTOCAD_HOST

using System;
using Autodesk.AutoCAD.ApplicationServices;
using Autodesk.AutoCAD.DatabaseServices;
using Autodesk.AutoCAD.Runtime;

namespace Yuantus.Cad.Bridge.Adapters
{
    /// <summary>
    /// AutoCAD-host shim. Registers exactly one Lisp function,
    /// <c>yuantus-helper-call</c>, with a two-argument arity check, and
    /// delegates to <see cref="BridgeCallService.Call"/>. Returns a Lisp
    /// string on success or <c>null</c> (which AutoCAD's Lisp layer maps to
    /// <c>nil</c>) on failure. No CAD business behavior, no DWG mutation,
    /// no modal UI.
    /// </summary>
    public static class AutoCadHostAdapter
    {
        private static readonly BridgeCallService Service =
            BridgeCallService.CreateProduction();

        [LispFunction("yuantus-helper-call")]
        public static object YuantusHelperCall(ResultBuffer args)
        {
            var writer = new AutoCadCommandLineWriter();

            string endpoint;
            string jsonRequest;
            if (!TryReadStringArgs(args, out endpoint, out jsonRequest))
            {
                writer.WriteFailure("HELPER_INPUT_VALIDATION_FAILED", "arity");
                return null;
            }

            var result = Service.Call(endpoint, jsonRequest);
            if (!result.Ok)
            {
                return null;
            }
            return result.Payload;
        }

        private static bool TryReadStringArgs(ResultBuffer args, out string endpoint, out string json)
        {
            endpoint = null;
            json = null;
            if (args == null)
            {
                return false;
            }
            var values = args.AsArray();
            if (values == null || values.Length != 2)
            {
                return false;
            }
            if (values[0] == null || values[0].Value == null)
            {
                return false;
            }
            if (values[1] == null || values[1].Value == null)
            {
                return false;
            }
            endpoint = values[0].Value.ToString();
            json = values[1].Value.ToString();
            return true;
        }
    }

    /// <summary>
    /// AutoCAD editor-backed implementation of
    /// <see cref="IBridgeCommandLineWriter"/>. Production NETLOAD-only path;
    /// not exercised by the SDK-free CI build.
    /// </summary>
    public sealed class AutoCadCommandLineWriter : IBridgeCommandLineWriter
    {
        public void WriteFailure(string code, string reason)
        {
            var line = "[YUANTUS_HELPER_CALL_FAILED] code=" + Sanitize(code) +
                       " reason=" + Sanitize(reason) + "\n";
            var document = Application.DocumentManager.MdiActiveDocument;
            if (document == null || document.Editor == null)
            {
                return;
            }
            document.Editor.WriteMessage(line);
        }

        private static string Sanitize(string value)
        {
            if (string.IsNullOrWhiteSpace(value))
            {
                return "unknown";
            }
            return System.Text.RegularExpressions.Regex.Replace(
                value, @"[^A-Za-z0-9_\-./]", "_");
        }
    }
}

#endif
