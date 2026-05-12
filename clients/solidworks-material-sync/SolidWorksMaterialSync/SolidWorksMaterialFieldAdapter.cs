using System.Collections.Generic;

namespace SolidWorksMaterialSync
{
    /// <summary>
    /// Extracts and writes SolidWorks material fields through an SDK-free gateway.
    /// </summary>
    public sealed class SolidWorksMaterialFieldAdapter
        : ICadMaterialFieldAdapter<ISolidWorksMaterialDocumentGateway>
    {
        private readonly SolidWorksMaterialFieldMapper _mapper;

        public SolidWorksMaterialFieldAdapter()
            : this(new SolidWorksMaterialFieldMapper())
        {
        }

        public SolidWorksMaterialFieldAdapter(SolidWorksMaterialFieldMapper mapper)
        {
            _mapper = mapper ?? new SolidWorksMaterialFieldMapper();
        }

        public Dictionary<string, object> ExtractFields(ISolidWorksMaterialDocumentGateway document)
        {
            var fields = new Dictionary<string, object>();
            if (document == null)
            {
                return fields;
            }

            AddProperties(fields, document.ReadCustomProperties());
            foreach (var bag in document.ReadCutListProperties() ?? new List<SolidWorksPropertyBag>())
            {
                AddProperties(fields, bag.Properties);
            }
            foreach (var row in document.ReadTableRows() ?? new List<IReadOnlyList<string>>())
            {
                _mapper.ExtractTableCells(row, fields);
            }

            return fields;
        }

        public int ApplyFields(
            ISolidWorksMaterialDocumentGateway document,
            Dictionary<string, object> cadFields)
        {
            if (document == null)
            {
                return 0;
            }

            var writeBackPlan = SolidWorksWriteBackPlan.FromWriteCadFields(cadFields);
            if (writeBackPlan.Count == 0)
            {
                return 0;
            }
            return document.ApplyCustomProperties(writeBackPlan);
        }

        private void AddProperties(
            Dictionary<string, object> fields,
            IDictionary<string, string> properties)
        {
            if (properties == null)
            {
                return;
            }
            foreach (var pair in properties)
            {
                _mapper.AddField(fields, pair.Key, pair.Value);
            }
        }
    }
}

