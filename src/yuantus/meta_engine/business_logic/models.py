from sqlalchemy import Column, String, Text
from yuantus.models.base import Base
import enum


class MethodType(str, enum.Enum):
    PYTHON_SCRIPT = "python_script"  # 直接存代码 (简单项目)
    PYTHON_MODULE = "python_module"  # 存模块路径 (推荐，如 plm.hooks.part_number)


class Method(Base):
    """
    服务器端方法 (Server Method)
    用于挂载到 ItemType 的事件钩子上 (onBeforeAdd, onAfterUpdate)
    """

    __tablename__ = "meta_methods"
    id = Column(String, primary_key=True)
    name = Column(String)

    type = Column(String, default=MethodType.PYTHON_MODULE)

    # if type=PYTHON_MODULE, content="plm_modules.part.hooks"
    # if type=PYTHON_SCRIPT, content="def main(item): ..."
    content = Column(Text)

    description = Column(String)
