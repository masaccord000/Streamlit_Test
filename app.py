import streamlit as st
import pyzipper
from PyPDF2 import PdfReader, PdfWriter
from pdf2image import convert_from_bytes
from streamlit_sortable import sortable
import zipfile
import io
import subprocess
import tempfile
import os

st.set_page_config(page_title="PDF結合・圧縮・並び替え", layout="wide")
st.title("📚 サムネイル付きPDF結合・並び替え・圧縮ツール")

uploaded_zip = st.file_uploader("🔐 暗号化ZIPファイルをアップロード", type="zip")
zip_password = st.text_input("ZIPパスワードを入力", type="password")

compression_quality = st.selectbox(
    "📉 Ghostscript圧縮レベル",
    ["/screen", "/ebook", "/printer", "/prepress", "圧縮しない"],
    index=1
)

compress_output = st.checkbox("📦 ZIPで出力（パスワード付き）")

def compress_pdf_with_ghostscript(input_bytes, quality="/ebook"):
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
            pdf_files = [name for name in zf.namelist() if name.lower().endswith('.pdf')]

            if not pdf_files:
                st.error("ZIP内にPDFファイルが見つかりません。")
            else:
                st.subheader("📁 PDFファイルの並び順を指定")
                ordered_files = sortable("ファイル順", pdf_files)

                page_pool = []  # [(label, page_obj, image)]
                for fname in ordered_files:
                    with zf.open(fname) as pdf_file:
                        pdf_bytes = pdf_file.read()
                        reader = PdfReader(io.BytesIO(pdf_bytes))
                        images = convert_from_bytes(pdf_bytes, dpi=100, fmt='PNG')
                        for i, page in enumerate(reader.pages):
                            label = f"{fname} - Page {i+1}"
                            thumbnail = images[i]
                            page_pool.append((label, page, thumbnail))

                st.subheader("🧹 結合対象ページを選択（サムネイル付き）")
                selected_labels = []
                for label, _, img in page_pool:
                    col1, col2 = st.columns([1, 4])
                    with col1:
                        include = st.checkbox(label, value=True, key=label)
                    with col2:
                        st.image(img, caption=label, use_column_width=True)
                    if include:
                        selected_labels.append(label)

                st.subheader("📄 ページ順の並び替え")
                ordered_labels = sortable("ページ順", selected_labels)

                try:
                    reordered_writer = PdfWriter()
                    for label in ordered_labels:
                        page = next(p for l, p, _ in page_pool if l == label)
                        reordered_writer.add_page(page)

                    pdf_bytes = io.BytesIO()
                    reordered_writer.write(pdf_bytes)
                    pdf_bytes.seek(0)

                    original_size_kb = len(pdf_bytes.getvalue()) / 1024

                    if compression_quality != "圧縮しない":
                        compressed_pdf = compress_pdf_with_ghostscript(pdf_bytes.getvalue(), compression_quality)
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
                    st.error(f"並び替えエラー: {e}")
    except Exception as e:
        st.error(f"ZIP解凍エラー: {e}")
