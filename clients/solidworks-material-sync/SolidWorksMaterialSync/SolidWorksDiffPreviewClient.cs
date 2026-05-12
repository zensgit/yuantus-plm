using System.Collections.Generic;
using System.Threading.Tasks;

namespace SolidWorksMaterialSync
{
    /// <summary>
    /// Diff-preview request seam for the local confirmation UI.
    /// </summary>
    public sealed class SolidWorksDiffPreviewClient
    {
        public const string DiffPreviewPath = "/api/v1/plugins/cad-material-sync/diff/preview";
        public const string CadSystem = "solidworks";

        private readonly IJsonTransport _transport;

        public SolidWorksDiffPreviewClient(IJsonTransport transport)
        {
            _transport = transport;
        }

        public Task<TResponse> PreviewAsync<TResponse>(
            string profileId,
            string itemId,
            Dictionary<string, object> currentCadFields,
            bool includeEmpty)
        {
            var request = new Dictionary<string, object>
            {
                { "profile_id", profileId },
                { "item_id", itemId },
                { "current_cad_fields", currentCadFields ?? new Dictionary<string, object>() },
                { "include_empty", includeEmpty },
                { "cad_system", CadSystem }
            };
            return _transport.PostJsonAsync<Dictionary<string, object>, TResponse>(
                DiffPreviewPath,
                request);
        }
    }

    public interface IJsonTransport
    {
        Task<TResponse> PostJsonAsync<TRequest, TResponse>(string path, TRequest request);
    }

}
