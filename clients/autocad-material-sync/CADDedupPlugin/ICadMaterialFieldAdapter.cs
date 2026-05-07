// ICadMaterialFieldAdapter.cs - CAD 字段适配器抽象
using System.Collections.Generic;

namespace CADDedupPlugin
{
    /// <summary>
    /// 将不同 CAD 客户端的字段读取/写回能力收口到同一接口。
    /// </summary>
    public interface ICadMaterialFieldAdapter<TCadDocument>
    {
        Dictionary<string, object> ExtractFields(TCadDocument document);

        int ApplyFields(TCadDocument document, Dictionary<string, object> cadFields);
    }
}
