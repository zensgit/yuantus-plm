// MaterialSyncDiffPreviewWindow.xaml.cs - PLM 物料字段差异确认窗口

using System;
using System.Collections.Generic;
using System.Linq;
using System.Windows;

namespace CADDedupPlugin
{
    public partial class MaterialSyncDiffPreviewWindow : Window
    {
        private readonly MaterialDiffPreviewResponse _preview;

        public Dictionary<string, object> ConfirmedWriteFields { get; private set; }

        public MaterialSyncDiffPreviewWindow(MaterialDiffPreviewResponse preview)
        {
            InitializeComponent();
            _preview = preview ?? throw new ArgumentNullException(nameof(preview));
            ConfirmedWriteFields = new Dictionary<string, object>(StringComparer.OrdinalIgnoreCase);
            LoadPreview();
        }

        private void LoadPreview()
        {
            txtContext.Text = string.Format(
                "Profile: {0}    Item: {1}",
                string.IsNullOrWhiteSpace(_preview.ProfileId) ? "-" : _preview.ProfileId,
                string.IsNullOrWhiteSpace(_preview.ItemId) ? "-" : _preview.ItemId);

            var writeCount = _preview.WriteCadFields == null ? 0 : _preview.WriteCadFields.Count;
            txtSummary.Text = string.Format("待写回 {0} 项", writeCount);

            if (_preview.Warnings != null && _preview.Warnings.Count > 0)
            {
                txtWarning.Text = string.Join(Environment.NewLine, _preview.Warnings);
            }

            var rows = (_preview.Diffs ?? new List<MaterialCadFieldDiff>())
                .Select(MaterialCadFieldDiffRow.FromDiff)
                .ToList();
            gridDiffs.ItemsSource = rows;

            btnConfirm.IsEnabled = writeCount > 0 && _preview.RequiresConfirmation;
            if (!btnConfirm.IsEnabled)
            {
                txtWarning.Text = "当前 CAD 字段与 PLM 目标字段一致，无需写回。";
            }
        }

        private void BtnConfirm_Click(object sender, RoutedEventArgs e)
        {
            ConfirmedWriteFields = _preview.WriteCadFields == null
                ? new Dictionary<string, object>(StringComparer.OrdinalIgnoreCase)
                : new Dictionary<string, object>(_preview.WriteCadFields, StringComparer.OrdinalIgnoreCase);
            DialogResult = true;
            Close();
        }

        private void BtnCancel_Click(object sender, RoutedEventArgs e)
        {
            DialogResult = false;
            Close();
        }
    }

    public class MaterialCadFieldDiffRow
    {
        public string CadKey { get; set; }
        public string Property { get; set; }
        public string CurrentText { get; set; }
        public string TargetText { get; set; }
        public string Status { get; set; }

        public static MaterialCadFieldDiffRow FromDiff(MaterialCadFieldDiff diff)
        {
            diff = diff ?? new MaterialCadFieldDiff();
            return new MaterialCadFieldDiffRow
            {
                CadKey = diff.CadKey ?? string.Empty,
                Property = diff.Property ?? string.Empty,
                CurrentText = FormatValue(diff.Current),
                TargetText = FormatValue(diff.Target),
                Status = diff.Status ?? string.Empty
            };
        }

        private static string FormatValue(object value)
        {
            if (value == null)
            {
                return string.Empty;
            }
            return Convert.ToString(value, System.Globalization.CultureInfo.InvariantCulture) ?? string.Empty;
        }
    }
}
