"""wenku-fetch 子命令的 Pydantic 模型：描述百度文库搜索接口返回的文档与结果集。"""
from typing import List

from pydantic import BaseModel, Field


class WenkuDoc(BaseModel):
    """百度文库搜索结果中的一个文档"""
    doc_id: str = Field(..., description='文档唯一标识（十六进制字符串）')
    title: str = Field(..., description='文档标题（已去除 HTML 高亮标签）')
    url: str = Field(..., description='文档详情页链接')
    abstract: str = Field('', description='文档摘要（已去除 HTML 高亮标签）')
    file_type: int = Field(0, description='文档格式类型编号，如 4 为 docx、6 为 pptx')
    page_num: int = Field(0, description='文档页数')
    download_count: int = Field(0, description='下载次数')
    view_count: int = Field(0, description='阅读次数')
    author: str = Field('', description='文档作者名')
    create_time: int = Field(0, description='文档创建时间（Unix 时间戳）')
    quality_score: float = Field(0, description='文档质量评分')
    sell_type: int = Field(0, description='文档售卖类型编号')
    copyable: bool = Field(False, description='正文是否可复制')
    tag_list: List[str] = Field(default_factory=list, description='文档标签列表')


class WenkuSearchResult(BaseModel):
    """某个关键词的搜索结果"""
    keyword: str = Field(..., description='搜索关键词')
    page: int = Field(1, description='已抓取的页码数')
    total: int = Field(0, description='搜索结果总数')
    docs: List[WenkuDoc] = Field(default_factory=list, description='搜索结果文档列表')
