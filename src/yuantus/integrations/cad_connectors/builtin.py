from __future__ import annotations

from .base import build_keyvalue_connector, build_simple_connector
from .registry import CadConnectorRegistry


CAD_KEY_ALIASES = {
    "PART_NUMBER": "part_number",
    "PARTNO": "part_number",
    "PART_NO": "part_number",
    "ITEM_NUMBER": "part_number",
    "ITEMNO": "part_number",
    "ITEM_NO": "part_number",
    "DRAWING_NO": "drawing_no",
    "DRAWING_NUMBER": "drawing_no",
    "DRAWINGNO": "drawing_no",
    "DRAWINGNUM": "drawing_no",
    "图号": "drawing_no",
    "图_号": "drawing_no",
    "图纸号": "drawing_no",
    "图纸编号": "drawing_no",
    "图样号": "drawing_no",
    "图样编号": "drawing_no",
    "零件号": "part_number",
    "零件_号": "part_number",
    "零件编号": "part_number",
    "零件代号": "part_number",
    "代号": "part_number",
    "物料号": "part_number",
    "物料_号": "part_number",
    "物料编号": "part_number",
    "物料编码": "part_number",
    "DESCRIPTION": "description",
    "DESC": "description",
    "TITLE": "description",
    "NAME": "description",
    "名称": "description",
    "零件名称": "description",
    "图名": "description",
    "图纸名称": "description",
    "描述": "description",
    "REVISION": "revision",
    "REV": "revision",
    "版本": "revision",
    "版次": "revision",
    "版本号": "revision",
    "版号": "revision",
    "修订": "revision",
    "修订号": "revision",
    "更改": "revision",
    "更改号": "revision",
    "MATERIAL": "material",
    "MAT": "material",
    "材料": "material",
    "材质": "material",
    "材料牌号": "material",
    "材料名称": "material",
    "材料/牌号": "material",
    "WEIGHT": "weight",
    "MASS": "weight",
    "WEIGHTKG": "weight",
    "WEIGHTG": "weight",
    "重量": "weight",
    "重量KG": "weight",
    "重量G": "weight",
    "质量": "weight",
    "净重": "weight",
    "毛重": "weight",
}


def register_builtin_connectors(registry: CadConnectorRegistry) -> None:
    registry.register(
        build_simple_connector(
            connector_id="autocad",
            label="AutoCAD",
            cad_format="AUTOCAD",
            document_type="2d",
            extensions=["dwg", "dxf"],
            aliases=["ACAD"],
            priority=50,
            description="AutoCAD DWG/DXF (default for 2D)",
        )
    )
    registry.register(
        build_keyvalue_connector(
            connector_id="gstarcad",
            label="GStarCAD",
            cad_format="GSTARCAD",
            document_type="2d",
            extensions=["dwg", "dxf"],
            aliases=["GSTAR", "GSTAR_CAD"],
            priority=20,
            description="GStarCAD DWG/DXF (key-value extractor)",
            key_aliases=CAD_KEY_ALIASES,
            signature_tokens=["GSTARCAD", "GSTAR"],
        )
    )
    registry.register(
        build_keyvalue_connector(
            connector_id="zwcad",
            label="ZWCAD",
            cad_format="ZWCAD",
            document_type="2d",
            extensions=["dwg", "dxf"],
            aliases=["ZW", "ZWCAD+", "ZWSOFT"],
            priority=20,
            description="ZWCAD DWG/DXF (key-value extractor)",
            key_aliases=CAD_KEY_ALIASES,
            signature_tokens=["ZWCAD", "ZWSOFT"],
        )
    )
    registry.register(
        build_keyvalue_connector(
            connector_id="haochencad",
            label="Haochen CAD",
            cad_format="HAOCHEN",
            document_type="2d",
            extensions=["dwg", "dxf"],
            aliases=["HAOCHEN_CAD", "HAOCHENCAD"],
            priority=20,
            description="Haochen CAD DWG/DXF (key-value extractor)",
            key_aliases=CAD_KEY_ALIASES,
            signature_tokens=["HAOCHEN", "HAOCHENCAD", "浩辰", "浩辰CAD"],
        )
    )
    registry.register(
        build_keyvalue_connector(
            connector_id="zhongwangcad",
            label="Zhongwang CAD",
            cad_format="ZHONGWANG",
            document_type="2d",
            extensions=["dwg", "dxf"],
            aliases=["ZHONGWANG_CAD", "ZWCAD_CN"],
            priority=20,
            description="Zhongwang CAD DWG/DXF (key-value extractor)",
            key_aliases=CAD_KEY_ALIASES,
            signature_tokens=["ZHONGWANG", "中望", "中望CAD"],
        )
    )
    registry.register(
        build_simple_connector(
            connector_id="step",
            label="STEP",
            cad_format="STEP",
            document_type="3d",
            extensions=["step", "stp"],
            priority=10,
        )
    )
    registry.register(
        build_simple_connector(
            connector_id="iges",
            label="IGES",
            cad_format="IGES",
            document_type="3d",
            extensions=["iges", "igs"],
            priority=10,
        )
    )
    registry.register(
        build_simple_connector(
            connector_id="solidworks",
            label="SolidWorks",
            cad_format="SOLIDWORKS",
            document_type="3d",
            extensions=["sldprt", "sldasm"],
            priority=20,
            description="SolidWorks part/assembly",
            signature_tokens=["SOLIDWORKS", "SLD"],
        )
    )
    registry.register(
        build_simple_connector(
            connector_id="inventor",
            label="Inventor",
            cad_format="INVENTOR",
            document_type="3d",
            extensions=["ipt", "iam"],
            priority=10,
            description="Autodesk Inventor part/assembly",
            signature_tokens=["INVENTOR"],
        )
    )
    registry.register(
        build_simple_connector(
            connector_id="nx",
            label="Siemens NX",
            cad_format="NX",
            document_type="3d",
            extensions=["prt", "asm"],
            aliases=["UG", "UGS", "SIEMENS_NX"],
            priority=18,
            description="Siemens NX part/assembly (default for .prt/.asm)",
            signature_tokens=["SIEMENS NX", "NX", "UG"],
        )
    )
    registry.register(
        build_simple_connector(
            connector_id="creo",
            label="Creo",
            cad_format="CREO",
            document_type="3d",
            extensions=["prt", "asm"],
            aliases=["PROE", "PRO/E", "PROENGINEER"],
            priority=17,
            description="PTC Creo/ProE part/assembly",
            signature_tokens=["CREO", "PRO/ENGINEER", "PROE"],
        )
    )
    registry.register(
        build_simple_connector(
            connector_id="nx_or_proe",
            label="NX/ProE (Legacy)",
            cad_format="NX_OR_PROE",
            document_type="3d",
            extensions=["prt", "asm"],
            priority=5,
            description="Legacy NX/ProE alias (deprecated)",
        )
    )
    registry.register(
        build_simple_connector(
            connector_id="catia",
            label="CATIA",
            cad_format="CATIA",
            document_type="3d",
            extensions=["catpart", "catproduct"],
            priority=16,
            description="Dassault CATIA part/assembly",
            signature_tokens=["CATIA"],
        )
    )
    registry.register(
        build_simple_connector(
            connector_id="solid_edge",
            label="Solid Edge",
            cad_format="SOLID_EDGE",
            document_type="3d",
            extensions=["par", "psm"],
            priority=10,
            description="Siemens Solid Edge part/sheetmetal",
            signature_tokens=["SOLID EDGE", "SOLID_EDGE"],
        )
    )
    registry.register(
        build_simple_connector(
            connector_id="rhino",
            label="Rhino",
            cad_format="RHINO",
            document_type="3d",
            extensions=["3dm"],
            priority=10,
            description="Rhino 3DM",
            signature_tokens=["RHINO"],
        )
    )
    registry.register(
        build_simple_connector(
            connector_id="stl",
            label="STL",
            cad_format="STL",
            document_type="3d",
            extensions=["stl"],
            priority=10,
        )
    )
    registry.register(
        build_simple_connector(
            connector_id="obj",
            label="OBJ",
            cad_format="OBJ",
            document_type="3d",
            extensions=["obj"],
            priority=10,
        )
    )
    registry.register(
        build_simple_connector(
            connector_id="gltf",
            label="glTF",
            cad_format="GLTF",
            document_type="3d",
            extensions=["gltf", "glb"],
            priority=10,
        )
    )
    registry.register(
        build_simple_connector(
            connector_id="pdf",
            label="PDF",
            cad_format="PDF",
            document_type="2d",
            extensions=["pdf"],
            priority=5,
        )
    )
