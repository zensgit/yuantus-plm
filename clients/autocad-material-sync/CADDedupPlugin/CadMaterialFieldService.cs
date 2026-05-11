// CadMaterialFieldService.cs - AutoCAD 标题栏/明细表字段抽取与回填
using System;
using System.Collections.Generic;
using Autodesk.AutoCAD.ApplicationServices;
using Autodesk.AutoCAD.DatabaseServices;

namespace CADDedupPlugin
{
    /// <summary>
    /// 负责从当前 DWG 的块属性和 Table 中读取/写入物料字段。
    /// </summary>
    public class CadMaterialFieldService : ICadMaterialFieldAdapter<Document>
    {
        private readonly CadMaterialFieldMapper _mapper;

        public CadMaterialFieldService()
            : this(new CadMaterialFieldMapper())
        {
        }

        public CadMaterialFieldService(CadMaterialFieldMapper mapper)
        {
            _mapper = mapper ?? new CadMaterialFieldMapper();
        }

        public Dictionary<string, object> ExtractFields(Document doc)
        {
            var fields = new Dictionary<string, object>(StringComparer.OrdinalIgnoreCase);
            if (doc == null)
            {
                return fields;
            }

            using (var tr = doc.Database.TransactionManager.StartTransaction())
            {
                foreach (var blockRecordId in GetDrawingSpaceBlockRecordIds(doc.Database, tr))
                {
                    ExtractFromBlockRecord(blockRecordId, tr, fields);
                }
                tr.Commit();
            }

            return fields;
        }

        public int ApplyFields(Document doc, Dictionary<string, object> cadFields)
        {
            if (doc == null || cadFields == null || cadFields.Count == 0)
            {
                return 0;
            }

            var normalized = _mapper.NormalizeInputFields(cadFields);
            var updated = 0;

            using (doc.LockDocument())
            using (var tr = doc.Database.TransactionManager.StartTransaction())
            {
                foreach (var blockRecordId in GetDrawingSpaceBlockRecordIds(doc.Database, tr))
                {
                    updated += ApplyToBlockRecord(blockRecordId, tr, normalized);
                }
                tr.Commit();
            }

            return updated;
        }

        private static IEnumerable<ObjectId> GetDrawingSpaceBlockRecordIds(Database db, Transaction tr)
        {
            var ids = new List<ObjectId>();
            var seen = new HashSet<ObjectId>();

            void Add(ObjectId id)
            {
                if (!id.IsNull && seen.Add(id))
                {
                    ids.Add(id);
                }
            }

            var blockTable = (BlockTable)tr.GetObject(db.BlockTableId, OpenMode.ForRead);
            Add(blockTable[BlockTableRecord.ModelSpace]);

            var layouts = (DBDictionary)tr.GetObject(db.LayoutDictionaryId, OpenMode.ForRead);
            foreach (DBDictionaryEntry entry in layouts)
            {
                var layout = tr.GetObject(entry.Value, OpenMode.ForRead, false) as Layout;
                if (layout != null)
                {
                    Add(layout.BlockTableRecordId);
                }
            }

            return ids;
        }

        private void ExtractFromBlockRecord(
            ObjectId blockRecordId,
            Transaction tr,
            Dictionary<string, object> fields)
        {
            var record = (BlockTableRecord)tr.GetObject(blockRecordId, OpenMode.ForRead);
            foreach (ObjectId id in record)
            {
                var entity = tr.GetObject(id, OpenMode.ForRead, false) as Entity;
                if (entity == null)
                {
                    continue;
                }

                var blockRef = entity as BlockReference;
                if (blockRef != null)
                {
                    ExtractBlockAttributes(blockRef, tr, fields);
                    continue;
                }

                var table = entity as Table;
                if (table != null)
                {
                    ExtractTableCells(table, fields);
                }
            }
        }

        private int ApplyToBlockRecord(
            ObjectId blockRecordId,
            Transaction tr,
            Dictionary<string, string> normalized)
        {
            var updated = 0;
            var record = (BlockTableRecord)tr.GetObject(blockRecordId, OpenMode.ForRead);
            foreach (ObjectId id in record)
            {
                var entity = tr.GetObject(id, OpenMode.ForRead, false) as Entity;
                if (entity == null)
                {
                    continue;
                }

                var blockRef = entity as BlockReference;
                if (blockRef != null)
                {
                    updated += ApplyBlockAttributes(blockRef, tr, normalized);
                    continue;
                }

                var table = entity as Table;
                if (table != null)
                {
                    updated += ApplyTableCells(table, normalized);
                }
            }
            return updated;
        }

        private void ExtractBlockAttributes(
            BlockReference blockRef,
            Transaction tr,
            Dictionary<string, object> fields)
        {
            foreach (ObjectId attrId in blockRef.AttributeCollection)
            {
                var attr = tr.GetObject(attrId, OpenMode.ForRead, false) as AttributeReference;
                if (attr == null)
                {
                    continue;
                }
                _mapper.AddField(fields, attr.Tag, attr.TextString);
            }
        }

        private int ApplyBlockAttributes(
            BlockReference blockRef,
            Transaction tr,
            Dictionary<string, string> normalized)
        {
            var updated = 0;
            foreach (ObjectId attrId in blockRef.AttributeCollection)
            {
                var attr = tr.GetObject(attrId, OpenMode.ForWrite, false) as AttributeReference;
                if (attr == null)
                {
                    continue;
                }

                if (_mapper.TryGetValue(normalized, attr.Tag, out var value))
                {
                    if ((attr.TextString ?? string.Empty) != value)
                    {
                        attr.TextString = value;
                        updated++;
                    }
                }
            }
            return updated;
        }

        private void ExtractTableCells(Table table, Dictionary<string, object> fields)
        {
            _mapper.ExtractTableCells(
                table.Rows.Count,
                table.Columns.Count,
                (row, col) => GetCellText(table, row, col),
                fields);
        }

        private int ApplyTableCells(Table table, Dictionary<string, string> normalized)
        {
            return _mapper.ApplyTableCells(
                table.Rows.Count,
                table.Columns.Count,
                (row, col) => GetCellText(table, row, col),
                (row, col, value) => SetCellText(table, row, col, value),
                normalized);
        }

        private static string GetCellText(Table table, int row, int col)
        {
            try
            {
                return table.Cells[row, col].TextString ?? string.Empty;
            }
            catch
            {
                return string.Empty;
            }
        }

        private static int SetCellText(Table table, int row, int col, string value)
        {
            try
            {
                if ((table.Cells[row, col].TextString ?? string.Empty) == value)
                {
                    return 0;
                }
                if (!table.IsWriteEnabled)
                {
                    table.UpgradeOpen();
                }
                table.Cells[row, col].TextString = value;
                return 1;
            }
            catch
            {
                return 0;
            }
        }

    }
}
