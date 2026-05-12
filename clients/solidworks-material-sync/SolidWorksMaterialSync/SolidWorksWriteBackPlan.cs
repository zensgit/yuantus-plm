using System;
using System.Collections.Generic;
using System.Globalization;

namespace SolidWorksMaterialSync
{
    /// <summary>
    /// Validates confirmed write_cad_fields before SolidWorks custom-property writes.
    /// </summary>
    public static class SolidWorksWriteBackPlan
    {
        private static readonly HashSet<string> ForbiddenAutoCadLabels =
            new HashSet<string>(StringComparer.OrdinalIgnoreCase)
            {
                "材料",
                "规格",
                "长",
                "宽",
                "厚",
                "图号",
                "名称"
            };

        public static IDictionary<string, string> FromWriteCadFields(
            Dictionary<string, object> writeCadFields)
        {
            var plan = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
            if (writeCadFields == null)
            {
                return plan;
            }

            foreach (var pair in writeCadFields)
            {
                if (!IsSolidWorksWriteKey(pair.Key))
                {
                    continue;
                }
                plan[pair.Key] = ValueToString(pair.Value);
            }
            return plan;
        }

        public static bool IsSolidWorksWriteKey(string key)
        {
            if (string.IsNullOrWhiteSpace(key) || ForbiddenAutoCadLabels.Contains(key))
            {
                return false;
            }
            return key.StartsWith("SW-", StringComparison.OrdinalIgnoreCase)
                && key.IndexOf('@') > 0;
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
}

