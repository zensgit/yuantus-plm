using System;
using System.Collections.Generic;
using System.Globalization;

namespace SolidWorksMaterialSync
{
    /// <summary>
    /// SDK-free confirmation model for the future SolidWorks local diff UI.
    /// </summary>
    public sealed class SolidWorksDiffConfirmationViewModel
    {
        private readonly Dictionary<string, object> _writeCadFields;

        private SolidWorksDiffConfirmationViewModel(
            IReadOnlyList<SolidWorksDiffFieldRow> rows,
            bool requiresConfirmation,
            Dictionary<string, object> writeCadFields)
        {
            Rows = rows;
            RequiresConfirmation = requiresConfirmation;
            _writeCadFields = writeCadFields ?? new Dictionary<string, object>();
            ConfirmedWriteFields = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
        }

        public IReadOnlyList<SolidWorksDiffFieldRow> Rows { get; }

        public bool RequiresConfirmation { get; }

        public bool IsConfirmed { get; private set; }

        public bool IsCancelled { get; private set; }

        public IDictionary<string, string> ConfirmedWriteFields { get; private set; }

        public static SolidWorksDiffConfirmationViewModel FromPreview(
            IDictionary<string, object> currentCadFields,
            SolidWorksDiffPreviewResult preview)
        {
            var safePreview = preview ?? new SolidWorksDiffPreviewResult();
            var targetCadFields = safePreview.TargetCadFields ?? new Dictionary<string, object>();
            var statuses = safePreview.Statuses ?? new Dictionary<string, string>();
            var rows = new List<SolidWorksDiffFieldRow>();

            foreach (var pair in targetCadFields)
            {
                var status = statuses.TryGetValue(pair.Key, out var foundStatus)
                    ? foundStatus
                    : "unchanged";
                currentCadFields = currentCadFields ?? new Dictionary<string, object>();
                currentCadFields.TryGetValue(pair.Key, out var currentValue);
                rows.Add(new SolidWorksDiffFieldRow(
                    pair.Key,
                    ValueToString(currentValue),
                    ValueToString(pair.Value),
                    status,
                    SolidWorksWriteBackPlan.IsSolidWorksWriteKey(pair.Key)));
            }

            return new SolidWorksDiffConfirmationViewModel(
                rows,
                safePreview.RequiresConfirmation,
                safePreview.WriteCadFields ?? new Dictionary<string, object>());
        }

        public IDictionary<string, string> Confirm()
        {
            IsConfirmed = true;
            IsCancelled = false;
            ConfirmedWriteFields = RequiresConfirmation
                ? SolidWorksWriteBackPlan.FromWriteCadFields(_writeCadFields)
                : new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
            return ConfirmedWriteFields;
        }

        public IDictionary<string, string> Cancel()
        {
            IsConfirmed = false;
            IsCancelled = true;
            ConfirmedWriteFields = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
            return ConfirmedWriteFields;
        }

        private static string ValueToString(object value)
        {
            if (value == null)
            {
                return string.Empty;
            }
            if (value is IFormattable formattable)
            {
                return formattable.ToString(null, CultureInfo.InvariantCulture);
            }
            return Convert.ToString(value, CultureInfo.InvariantCulture) ?? string.Empty;
        }
    }

    public sealed class SolidWorksDiffFieldRow
    {
        public SolidWorksDiffFieldRow(
            string fieldKey,
            string currentValue,
            string targetValue,
            string status,
            bool canWrite)
        {
            FieldKey = fieldKey ?? string.Empty;
            CurrentValue = currentValue ?? string.Empty;
            TargetValue = targetValue ?? string.Empty;
            Status = status ?? "unchanged";
            CanWrite = canWrite;
        }

        public string FieldKey { get; }

        public string CurrentValue { get; }

        public string TargetValue { get; }

        public string Status { get; }

        public bool CanWrite { get; }
    }

    public sealed class SolidWorksDiffPreviewResult
    {
        public bool Ok { get; set; }

        public SolidWorksDiffSummary Summary { get; set; }

        public Dictionary<string, object> TargetCadFields { get; set; }

        public Dictionary<string, object> WriteCadFields { get; set; }

        public bool RequiresConfirmation { get; set; }

        public Dictionary<string, string> Statuses { get; set; }
    }

    public sealed class SolidWorksDiffSummary
    {
        public int Added { get; set; }

        public int Changed { get; set; }

        public int Cleared { get; set; }

        public int Unchanged { get; set; }
    }
}

