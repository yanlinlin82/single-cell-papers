# 单细胞与空转测序相关文章

一个持续更新的专有领域知识库，聚焦单细胞与空转测序，通过收集和整理最新科研文献提供信息。

网址：<https://single-cell-papers.bioinfo-assist.com/>

<img src="static/images/qrcode-website.png" style=“max-width:300px">

---

## 动机

本仓库从 [what-deep-learning-does-in-biomedicine](https://github.com/yanlinlin82/what-deep-learning-does-in-biomedicine/) 拷贝和修改而来。

## 如何使用

1. 克隆本仓库：

    ```sh
    git clone https://github.com/yanlinlin82/single-cell-papers.git
    ```

2. 准备环境

    ```sh
    python -m venv .venv
    . .venv/bin/activate
    pip install -r requirements.txt
    ```

3. 配置环境参数

    ```sh
    vi .env
    ```

    ```txt
    OPENAI_BASE_URL=https://api.deepseek.com  # 若使用 openai API，则留空，或使用 https://api.openai.com/v1
    OPENAI_API_KEY=sk-XXXX                    # 填写自己账号的 API Key
    OPENAI_MODEL=deepseek-chat                # 若使用 openai API，可设置为 gpt-4o-mini
    OPENAI_PROXY_URL=socks5://x.x.x.x:xxxx    # 用于（从国内翻墙）调用 openai API，使用 DeepSeek 则可不配置此项
    ```
  
4. 初始化并运行Django

    ```sh
    python manage.py migrate
    python manage.py collectstatic
    ```

5. PubMed数据获取

    ```sh
    lftp -c "mirror -c https://ftp.ncbi.nlm.nih.gov/pubmed/" # 注意全套下载有超过50G
    ```

6. 扫描PubMed文件，提取文献信息，导入数据库

    ```sh
    python scripts/scan-pubmed.py /path/to/pubmed/updatefiles/pubmed24nXXXX.xml.gz
    python scripts/import.py output/
    ```

## 免责声明

本项目信息由手工或AI整理，信息难免存在错漏，请使用时务必注意核实。此外，由于各种原因，项目可能会不定期断档停更，还请见谅！

## 许可证

本仓库基于 [MIT协议](LICENSE) 发布，允许自由修改和传播。
