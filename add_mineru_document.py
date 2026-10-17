import os
import shutil
from pathlib import Path
import re
from typing import List
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 导入LangChain相关包
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

# 配置参数
PDF_OUT_DIR = "xiaomi-ESG"
FRONTEND_PUBLIC_DIR = "./agent-chat-ui/public"
VECTORSTORE_PATH = "faiss-pkl"
IMAGES_DIR = "images"

# 新的图片路径前缀（前端访问路径）
IMAGE_PREFIX = "images"

def setup_directories():
    """创建必要的目录"""
    frontend_images_dir = Path(FRONTEND_PUBLIC_DIR + f"/{IMAGE_PREFIX}")
    frontend_images_dir.mkdir(parents=True, exist_ok=True)
    print(f"创建前端图片目录: {frontend_images_dir}")
    return frontend_images_dir

def copy_images_to_frontend(source_dir: Path, target_dir: Path) -> List[str]:
    """复制图片到前端目录"""
    copied_images = []
    source_images_dir = source_dir / IMAGES_DIR
    
    if not source_images_dir.exists():
        print(f"图片目录不存在: {source_images_dir}")
        return copied_images
    
    for image_file in source_images_dir.glob("*.jpg"):
        target_file = target_dir / image_file.name
        shutil.copy2(image_file, target_file)
        copied_images.append(image_file.name)
        print(f"复制图片: {image_file.name}")
    
    print(f"总共复制了 {len(copied_images)} 张图片")
    return copied_images

def copy_all_pdf_images():
    """从pdf_out目录下的所有子目录中复制图片"""
    pdf_out_path = Path(PDF_OUT_DIR)
    target_dir = Path(FRONTEND_PUBLIC_DIR + f"/{IMAGE_PREFIX}")
    target_dir.mkdir(parents=True, exist_ok=True)
    
    copied_images_total = []
    
    # 遍历pdf_out下的所有子目录
    for subdir in pdf_out_path.iterdir():
        if subdir.is_dir():
            print(f"处理目录: {subdir.name}")
            copied_images = copy_images_to_frontend(subdir, target_dir)
            copied_images_total.extend(copied_images)
    
    print(f"总共从所有目录复制了 {len(copied_images_total)} 张图片")
    return copied_images_total

def update_image_paths_in_md(md_content: str, doc_name: str) -> str:
    """更新MD文件中的图片路径"""
    # 匹配图片引用格式: ![](images/filename.jpg)
    pattern = r'!\[\]\(images/([^)]+)\)'
    pattern2 = r'<div style="text-align: center;"><img src="images/(.*?)".*</div>'

    def replace_image_path(match):
        filename = match.group(1)
        new_path = f"/{IMAGE_PREFIX}/{filename}"
        return f"![]({new_path})"
    
    updated_content = re.sub(pattern, replace_image_path, md_content)
    updated_content = re.sub(pattern2, replace_image_path, updated_content)

    # 统计替换的图片数量
    original_count = len(re.findall(pattern, md_content)) + len(re.findall(pattern2, md_content))

    print(f"更新了 {original_count} 个图片路径引用")
    
    return updated_content

def process_markdown_files() -> List[Document]:
    """处理pdf_out目录下的所有markdown文件"""
    pdf_out_path = Path(PDF_OUT_DIR)
    all_documents = []
    
    # 遍历pdf_out下的所有子目录
    for subdir in pdf_out_path.iterdir():
        if subdir.is_dir():
            # 查找markdown文件
            md_files = list(subdir.glob("*.md"))
            for md_file in md_files:
                if "_updated" in md_file.name:
                    continue
                print(f"处理Markdown文件: {md_file}")
                with open(md_file, 'r', encoding='utf-8') as f:
                    md_content = f.read()
                
                # 更新图片路径
                updated_content = update_image_paths_in_md(md_content, subdir.name)
                
                # 保存更新后的MD文件（可选）
                updated_md_path = subdir / f"{md_file.stem}_updated.md"
                with open(updated_md_path, 'w', encoding='utf-8') as f:
                    f.write(updated_content)
                print(f"保存更新后的MD文件: {updated_md_path}")
                
                # 分割内容
                documents = split_markdown_content(updated_content, subdir.name)
                all_documents.extend(documents)
    
    print(f"总共处理了 {len(all_documents)} 个文档块")
    return all_documents

def split_markdown_content(content: str, source_name: str) -> List[Document]:
    """分割markdown内容为文档块"""
    # 配置文本分割器
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=300,
        chunk_overlap=100,
        separators=[
            "\n# ",      # 一级标题
            "\n## ",     # 二级标题  
            "\n### ",    # 三级标题
            "\n\n",      # 段落
            "\n",        # 行
            " ",         # 词
            ""           # 字符
        ]
    )
    
    # 分割文本
    texts = text_splitter.split_text(content)
    
    # 创建Document对象
    documents = []
    for i, text in enumerate(texts):
        doc = Document(
            page_content=text,
            metadata={
                "source": source_name,
                "chunk_id": i,
                "document_type": "course_material",
                "processed_by": "MinerU"
            }
        )
        # print(i,"############",text)
        documents.append(doc)
    
    print(f"文档分割为 {len(documents)} 个块")
    return documents

def add_to_vectorstore(documents: List[Document]):
    """将文档添加到向量库"""
    try:
        # 初始化本地embeddings
        embeddings = HuggingFaceEmbeddings(
            model_name=os.getenv("EMBEDDING_MODEL", "E:/demo/minerU-rag-agent/models/bge-base-zh-v1.5"),
            model_kwargs={'device': os.getenv("EMBEDDING_DEVICE", "cpu")}
        )
        
        # 检查是否存在现有向量库
        vectorstore_path = Path(VECTORSTORE_PATH)

        if vectorstore_path.exists():
            print("加载现有向量库...")
            # 加载现有向量库
            vectorstore = FAISS.load_local(
                folder_path=VECTORSTORE_PATH,
                embeddings=embeddings,
                allow_dangerous_deserialization=True,
            )
            
            # 添加新文档
            vectorstore.add_documents(documents)
            print("新文档已添加到现有向量库")
            
        else:
            print("创建新的向量库...")
            # 创建新的向量库
            vectorstore = FAISS.from_documents(documents, embeddings)
            print("新向量库创建成功")
        
        # 保存向量库
        vectorstore.save_local(VECTORSTORE_PATH)
        print(f"向量库已保存到: {VECTORSTORE_PATH}")
        
        # 显示向量库信息
        print(f"向量库总文档数: {vectorstore.index.ntotal}")
        
    except Exception as e:
        print(f"向量库操作失败: {str(e)}")
        raise

def validate_environment():
    """验证环境配置"""
    # 本地embedding不需要API key，直接返回True
    print("使用本地embedding模型，无需验证API key")
    return True

def main():
    """主函数"""
    print("开始处理MinerU文档...")
    
    # 验证环境
    if not validate_environment():
        return
    
    try:
        # 1. 设置目录并复制所有图片
        frontend_images_dir = setup_directories()
        
        # 2. 从pdf_out所有子目录复制图片到前端
        copied_images = copy_all_pdf_images()
        
        # 3. 处理所有markdown文件
        documents = process_markdown_files()
        
        # 4. 添加到向量库
        add_to_vectorstore(documents)
        
        print("处理完成！")
        print(f"总结:")
        print(f"   - 复制图片: {len(copied_images)} 张")
        print(f"   - 文档分块: {len(documents)} 个")
        print(f"   - 向量库路径: {VECTORSTORE_PATH}")
        print(f"   - 前端图片路径: {frontend_images_dir}")
        
    except Exception as e:
        print(f"处理失败: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()