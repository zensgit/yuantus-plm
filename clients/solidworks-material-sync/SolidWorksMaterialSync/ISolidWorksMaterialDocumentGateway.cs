using System.Collections.Generic;

namespace SolidWorksMaterialSync
{
    /// <summary>
    /// SDK-free gateway for the future SolidWorks Add-in/COM implementation.
    /// </summary>
    public interface ISolidWorksMaterialDocumentGateway
    {
        /// <summary>
        /// Future Windows backing must use CustomPropertyManager.GetAll3 for
        /// key enumeration and CustomPropertyManager.Get6 for resolved value reads.
        /// </summary>
        IDictionary<string, string> ReadCustomProperties();

        /// <summary>
        /// Returns cut-list property bags from the active SolidWorks part.
        /// </summary>
        IEnumerable<SolidWorksPropertyBag> ReadCutListProperties();

        /// <summary>
        /// Returns table rows as raw SolidWorks key/value cells.
        /// </summary>
        IEnumerable<IReadOnlyList<string>> ReadTableRows();

        /// <summary>
        /// Applies confirmed SolidWorks custom-property writes.
        /// </summary>
        int ApplyCustomProperties(IDictionary<string, string> properties);
    }

    public sealed class SolidWorksPropertyBag
    {
        public SolidWorksPropertyBag(string name, IDictionary<string, string> properties)
        {
            Name = name ?? string.Empty;
            Properties = properties ?? new Dictionary<string, string>();
        }

        public string Name { get; }

        public IDictionary<string, string> Properties { get; }
    }
}

