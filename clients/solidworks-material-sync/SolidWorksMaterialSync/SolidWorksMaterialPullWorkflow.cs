using System.Collections.Generic;
using System.Threading.Tasks;

namespace SolidWorksMaterialSync
{
    /// <summary>
    /// SDK-free orchestration for SolidWorks PLM-to-CAD pull confirmation.
    /// </summary>
    public sealed class SolidWorksMaterialPullWorkflow
    {
        private readonly ISolidWorksMaterialDocumentGateway _document;
        private readonly SolidWorksMaterialFieldAdapter _fieldAdapter;
        private readonly SolidWorksDiffPreviewClient _diffPreviewClient;

        public SolidWorksMaterialPullWorkflow(
            ISolidWorksMaterialDocumentGateway document,
            SolidWorksDiffPreviewClient diffPreviewClient)
            : this(document, diffPreviewClient, new SolidWorksMaterialFieldAdapter())
        {
        }

        public SolidWorksMaterialPullWorkflow(
            ISolidWorksMaterialDocumentGateway document,
            SolidWorksDiffPreviewClient diffPreviewClient,
            SolidWorksMaterialFieldAdapter fieldAdapter)
        {
            _document = document;
            _diffPreviewClient = diffPreviewClient;
            _fieldAdapter = fieldAdapter ?? new SolidWorksMaterialFieldAdapter();
        }

        public async Task<SolidWorksDiffConfirmationViewModel> PreviewAsync(
            string profileId,
            string itemId,
            bool includeEmpty)
        {
            var currentCadFields = _fieldAdapter.ExtractFields(_document);
            var preview = await _diffPreviewClient.PreviewAsync<SolidWorksDiffPreviewResult>(
                profileId,
                itemId,
                currentCadFields,
                includeEmpty);
            return SolidWorksDiffConfirmationViewModel.FromPreview(currentCadFields, preview);
        }

        public int ConfirmAndApply(SolidWorksDiffConfirmationViewModel confirmation)
        {
            if (confirmation == null)
            {
                return 0;
            }

            var confirmedWriteFields = confirmation.Confirm();
            if (confirmedWriteFields.Count == 0)
            {
                return 0;
            }

            return _fieldAdapter.ApplyFields(_document, ToObjectDictionary(confirmedWriteFields));
        }

        public int Cancel(SolidWorksDiffConfirmationViewModel confirmation)
        {
            confirmation?.Cancel();
            return 0;
        }

        private static Dictionary<string, object> ToObjectDictionary(
            IDictionary<string, string> fields)
        {
            var result = new Dictionary<string, object>();
            if (fields == null)
            {
                return result;
            }

            foreach (var pair in fields)
            {
                result[pair.Key] = pair.Value;
            }
            return result;
        }
    }
}

