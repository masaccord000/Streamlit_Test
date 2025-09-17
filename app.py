import streamlit as st
import pyzipper
from PyPDF2 import PdfReader, PdfWriter
from pdf2image import convert_from_bytes
from streamlit_sortables import sort_items
import io
import tempfile
import subprocess
import os

st.set_page_config(page_title="PDF並べ替えツール", layout="wide")
st.title("📚 PDFファイル・ページ並べ替え・圧縮・ZIP出力")

uploaded_zip = st.file_uploader("🔐 暗号化ZIPファイルをアップロード", type="zip")
zip_password = st.text_input("ZIPパスワードを入力", type="password")

compression_quality = st.selectbox(
    "📉 Ghostscript圧縮レベル",
    ["/screen", "/ebook", "/printer", "/prepress", "圧縮しない"],
    index=1
)

compression_info = {
    "/screen": "🌐 Web表示向け（72dpi・高圧縮）",
    "/ebook": "📱 電子書籍向け（150dpi・中圧縮）",
    "/printer": "🖨️ 印刷向け（300dpi・低圧縮）",
    "/prepress": "📰 商業印刷向け（高画質・最低圧縮）",
    "圧縮しない": "📄 圧縮なし（元の画質・サイズ）"
}
st.info(f"選択中の圧縮設定：{compression_info[compression_quality]}")

compress_output = st.checkbox("📦 ZIPで出力（パスワード付き）")

def compress_pdf(input_bytes, quality="/ebook"):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as input_file:
        input_file.write(input_bytes)
        input_path = input_file.name

    output_path = input_path.replace(".pdf", "_compressed.pdf")

    gs_cmd = [
        "gs",
        "-sDEVICE=pdfwrite",
        "-dCompatibilityLevel=1.4",
        f"-dPDFSETTINGS={quality}",
        "-dNOPAUSE",
        "-dQUIET",
        "-dBATCH",
        f"-sOutputFile={output_path}",
        input_path
    ]

    subprocess.run(gs_cmd, check=True)

    with open(output_path, "rb") as f:
        compressed_bytes = f.read()

    os.remove(input_path)
    os.remove(output_path)

    return compressed_bytes

if uploaded_zip and zip_password:
    try:
        with pyzipper.AESZipFile(uploaded_zip, 'r') as zf:
            zf.pwd = zip_password.encode('utf-8')
            pdf_files = [f for f in zf.namelist() if f.lower().endswith('.pdf')]

            if not pdf_files:
                st.error("ZIP内にPDFファイルが見つかりません。")
            else:
                file_pages = {}
                for fname in pdf_files:
                    with zf.open(fname) as pdf_file:
                        pdf_bytes = pdf_file.read()
                        reader = PdfReader(io.BytesIO(pdf_bytes))
                        images = convert_from_bytes(pdf_bytes, dpi=100)
                        file_pages[fname] = []
                        for i, page in enumerate(reader.pages):
                            label = f"{fname} - Page {i+1}"
                            thumbnail = images[i]
                            file_pages[fname].append((label, page, thumbnail))

                if "ordered_files" not in st.session_state:
                    st.session_state.ordered_files = pdf_files
                if "files_confirmed" not in st.session_state:
                    st.session_state.files_confirmed = False

                # ファイル順並べ替え（未確定時のみ表示）
                if not st.session_state.files_confirmed:
                    st.subheader("📁 ファイル順の並べ替え")
                    temp_sorted_files = sort_items(st.session_state.ordered_files)
                    st.session_state.temp_sorted_files = temp_sorted_files

                    if st.button("✅ ファイル順を確定"):
                        st.session_state.ordered_files = st.session_state.temp_sorted_files
                        ordered_pages = []
                        for fname in st.session_state.ordered_files:
                            ordered_pages.extend(file_pages[fname])
                        st.session_state.ordered_pages = ordered_pages
                        st.session_state.files_confirmed = True
                        st.rerun()

                # ページ順並べ替え（ファイルをまたいで）
                if st.session_state.files_confirmed:
                    st.subheader("📄 ページ順の並べ替え（サムネイル＋操作）")
                    new_ordered_pages = st.session_state.ordered_pages.copy()

                    for i, (label, page, img) in enumerate(new_ordered_pages):
                        col1, col2 = st.columns([5, 1])
                        with col1:
                            st.image(img, caption=label, use_container_width=True)
                        with col2:
                            if st.button("↑", key=f"up_{label}") and i > 0:
                                new_ordered_pages[i], new_ordered_pages[i-1] = new_ordered_pages[i-1], new_ordered_pages[i]
                                st.session_state.ordered_pages = new_ordered_pages
                                st.rerun()
                            if st.button("↓", key=f"down_{label}") and i < len(new_ordered_pages)-1:
                                new_ordered_pages[i], new_ordered_pages[i+1] = new_ordered_pages[i+1], new_ordered_pages[i]
                                st.session_state.ordered_pages = new_ordered_pages
                                st.rerun()
                            if st.button("❌", key=f"del_{label}"):
                                new_ordered_pages.pop(i)
                                st.session_state.ordered_pages = new_ordered_pages
                                st.rerun()

                    if st.button("✅ PDFを生成"):
                        try:
                            writer = PdfWriter()
                            for _, page, _ in st.session_state.ordered_pages:
                                writer.add_page(page)

                            pdf_bytes = io.BytesIO()
                            writer.write(pdf_bytes)
                            pdf_bytes.seek(0)

                            original_size_kb = len(pdf_bytes.getvalue()) / 1024

                            if compression_quality != "圧縮しない":
                                compressed_pdf = compress_pdf(pdf_bytes.getvalue(), compression_quality)
                                final_pdf = compressed_pdf
                                compressed_size_kb = len(compressed_pdf) / 1024
                                st.write(f"📊 圧縮前: {original_size_kb:.1f} KB")
                                st.write(f"📊 圧縮後: {compressed_size_kb:.1f} KB")
                                st.write(f"📉 削減率: {100 * (1 - compressed_size_kb / original_size_kb):.1f}%")
                            else:
                                final_pdf = pdf_bytes.getvalue()
                                st.write(f"📄 PDFサイズ: {original_size_kb:.1f} KB（圧縮なし）")

                            if compress_output:
                                zip_buffer = io.BytesIO()
                                with pyzipper.AESZipFile(zip_buffer, 'w', compression=pyzipper.ZIP_DEFLATED, encryption=pyzipper.WZ_AES) as zipf:
                                    zipf.setpassword(zip_password.encode('utf-8'))
                                    zipf.writestr("reordered.pdf", final_pdf)
                                zip_buffer.seek(0)
                                st.download_button(
                                    label="📥 パスワード付きZIPをダウンロード",
                                    data=zip_buffer.getvalue(),
                                    file_name="reordered_pdf.zip",
                                    mime="application/zip"
                                )
                            else:
                                st.download_button(
                                    label="📥 PDFをダウンロード",
                                    data=final_pdf,
                                    file_name="reordered.pdf",
                                    mime="application/pdf"
                                )
                        except Exception as e:
                            st.error(f"PDF生成エラー: {e}")
    except Exception as e:
        st.error(f"ZIP解凍エラー: {e}")
