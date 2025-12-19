from sqlalchemy import Column, String, Integer, ForeignKey, Text
from sqlalchemy.orm import relationship
from yuantus.models.base import Base


class Form(Base):
    """
    表单定义 (Form Definition)
    定义一个 ItemType 在前端 "Form View" 中长什么样
    """

    __tablename__ = "meta_forms"
    id = Column(String, primary_key=True)
    name = Column(String)
    description = Column(String)

    # CSS/HTML 模板 (可选，用于高级自定义)
    # Aras 允许完全自定义 HTML，这里存一段 HTML 字符串
    html_content = Column(Text)

    fields = relationship(
        "FormField", back_populates="form", cascade="all, delete-orphan"
    )


class FormField(Base):
    """
    表单字段 (Form Field)
    定义某个具体字段在表单上的位置、类型、样式
    """

    __tablename__ = "meta_form_fields"
    id = Column(String, primary_key=True)
    form_id = Column(String, ForeignKey("meta_forms.id"))

    # 绑定到哪个 Property?
    property_name = Column(String)

    label = Column(String)

    # 布局坐标 (Grid Layout or Absolute)
    # x, y, width, height
    x_pos = Column(Integer, default=0)
    y_pos = Column(Integer, default=0)
    width = Column(Integer, default=100)

    # 控件类型: "text", "date", "item_picker", "dropdown"
    control_type = Column(String, default="text")

    # 交互逻辑: "return confirm('...')" (Javascript Hook)
    on_change_handler = Column(String)

    form = relationship("Form", back_populates="fields")


class GridView(Base):
    """
    网格视图定义 (Grid View / Search Result View)
    定义 ItemType 在列表页显示的列
    """

    __tablename__ = "meta_grid_views"
    id = Column(String, primary_key=True)
    name = Column(String)

    columns = relationship(
        "GridColumn", back_populates="grid_view", cascade="all, delete-orphan"
    )


class GridColumn(Base):
    __tablename__ = "meta_grid_columns"
    id = Column(String, primary_key=True)
    grid_view_id = Column(String, ForeignKey("meta_grid_views.id"))

    property_name = Column(String)
    label = Column(String)
    width = Column(Integer, default=100)
    sort_order = Column(Integer, default=0)

    grid_view = relationship("GridView", back_populates="columns")
