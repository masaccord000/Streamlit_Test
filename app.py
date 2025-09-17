import streamlit as st
import pyzipper
from PyPDF2 import PdfReader, PdfWriter
import io
import tempfile
import subprocess
import os

# UI設定
st.set_page_config(page_title="PDFサイズ分割ツール", layout="wide")
st.title("📚 PDFサイズ分割・圧縮・ZIP出力")

# 入力UI
uploaded_zip = st.file_uploader("🔐 暗号化ZIPファイルをアップロード", type="zip")
zip_password = st.text_input("ZIPパスワードを入力", type="password")
target_kb = st.number_input("🎯 各PDFの最大サイズ（KB）", min_value=50, value=300)

compression_quality = st.selectbox(
    "📉 Ghostscript圧縮レベルを選択",
    ["/screen", "/ebook", "/printer", "/prepress"],
    index=1
)

compression_info = {
    "/screen": "🌐 Web表示向け（72dpi・高圧縮）",
    "/ebook": "📱 電子書籍向け（150dpi・中圧縮）",
    "/printer": "🖨️ 印刷向け（300dpi・低圧縮）",
    "/prepress": "📰 商業印刷向け（高画質・最低圧縮）"
}
st.info(f"選択中の圧縮設定：{compression_info[compression_quality]}")

# Ghostscript圧縮関数
def compress_pdf(input_bytes, quality):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as input_file:
        input_file.write(input_bytes)
        input_path = input_file.name

    output_path = input_path.replace(".pdf", "_compressed.pdf")
    gs_cmd = [
        "gs", "-sDEVICE=pdfwrite", "-dCompatibilityLevel=1.4",
        f"-dPDFSETTINGS={quality}", "-dNOPAUSE", "-dQUIET", "-dBATCH",
        f"-sOutputFile={output_path}", input_path
    ]
    subprocess.run(gs_cmd, check=True)

    with open(output_path, "rb") as f:
        compressed_bytes = f.read()

    os.remove(input_path)
    os.remove(output_path)
    return compressed_bytes

# メイン処理
if uploaded_zip and zip_password:
    try:
        with pyzipper.AESZipFile(uploaded_zip, 'r') as zf:
            zf.pwd = zip_password.encode('utf-8')
            pdf_files = [f for f in zf.namelist() if f.lower().endswith('.pdf')]

            if not pdf_files:
                st.error("ZIP内にPDFファイルが見つかりません。")
            else:
                output_zip = io.BytesIO()
                with pyzipper.AESZipFile(output_zip, 'w', compression=pyzipper.ZIP_DEFLATED, encryption=pyzipper.WZ_AES) as zipf:
                    zipf.setpassword(zip_password.encode('utf-8'))

                    for fname in pdf_files:
                        with zf.open(fname) as pdf_file:
                            reader = PdfReader(pdf_file)
                            part_index = 1
                            temp_pages = []

                            for i, page in enumerate(reader.pages):
                                temp_pages.append(page)
                                temp_writer = PdfWriter()
                                for p in temp_pages:
                                    temp_writer.add_page(p)

                                temp_pdf = io.BytesIO()
                                temp_writer.write(temp_pdf)
                                temp_pdf.seek(0)
                                compressed = compress_pdf(temp_pdf.getvalue(), compression_quality)
                                size_kb = len(compressed) / 1024

                                if size_kb > target_kb:
                                    # 最後のページを除いて保存
                                    temp_writer = PdfWriter()
                                    for p in temp_pages[:-1]:
                                        temp_writer.add_page(p)
                                    temp_pdf = io.BytesIO()
                                    temp_writer.write(temp_pdf)
                                    temp_pdf.seek(0)
                                    compressed = compress_pdf(temp_pdf.getvalue(), compression_quality)
                                    size_kb = len(compressed) / 1024
                                    out_name = f"{fname.replace('.pdf','')}_part{part_index}_{int(size_kb)}KB.pdf"
                                    zipf.writestr(out_name, compressed)

                                    part_index += 1
                                    temp_pages = [page]  # 現在のページから再スタート

                            # 最後の残りページ
                            if temp_pages:
                                temp_writer = PdfWriter()
                                for p in temp_pages:
                                    temp_writer.add_page(p)
                                temp_pdf = io.BytesIO()
                                temp_writer.write(temp_pdf)
                                temp_pdf.seek(0)
                                compressed = compress_pdf(temp_pdf.getvalue(), compression_quality)
                                size_kb = len(compressed) / 1024
                                out_name = f"{fname.replace('.pdf','')}_part{part_index}_{int(size_kb)}KB.pdf"
                                zipf.writestr(out_name, compressed)

                output_zip.seek(0)
                st.download_button(
                    label="📥 分割・圧縮済みZIPをダウンロード",
                    data=output_zip.getvalue(),
                    file_name="split_by_size.zip",
                    mime="application/zip"
                )
    except Exception as e:
        st.error(f"ZIP解凍エラー: {e}")
