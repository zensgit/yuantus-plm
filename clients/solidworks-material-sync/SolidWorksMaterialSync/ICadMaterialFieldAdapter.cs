using System.Collections.Generic;

namespace SolidWorksMaterialSync
{
    /// <summary>
    /// CAD field extraction/write-back seam shared by CAD client adapters.
    /// </summary>
    public interface ICadMaterialFieldAdapter<TCadDocument>
    {
        Dictionary<string, object> ExtractFields(TCadDocument document);

        int ApplyFields(TCadDocument document, Dictionary<string, object> cadFields);
    }
}

