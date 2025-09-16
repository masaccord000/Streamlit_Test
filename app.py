import base64
import time
import paramiko
import pandas as pd
import datetime


def decryptText(_ciphertext, _rm):
    """複合化 Copyright © 2023-2024 M.Fukuya

    Args:
        _ciphertext (str): 暗号化された文字列
        _rm (str): 削除文字列

    Returns:
        str: 複合化された文字列
    """
    cleartext = base64.b64decode(_ciphertext).decode()[len(_rm):]
    return cleartext

def uploadFilesToServer(_user, _password, _host, _port, _local_file_path_list, _online_file_path_list):
    """サーバにファイルをアップロード Copyright © 2023-2024 M.Fukuya

    Args:
        _user (str): サーバのユーザ名
        _password (str): サーバのパスワード
        _host (str): サーバのホスト名(IPアドレス)
        _port (int): サーバのポート番号
        _local_file_path_list (list): アップロードするファイルのパスのリスト(ローカル)
        _online_file_path_list (list): アップロードするファイルのパスのリスト(オンライン)

    Returns:
        bool: 成功時True、失敗時False
    """
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname=_host, port=_port, username=_user, password=_password)

        sftp = ssh.open_sftp()

        for j, _local_file_path in enumerate(_local_file_path_list):
            path_lists = _online_file_path_list[j].split("/")
            path_lists_len = len(path_lists) - 1

            new_path = ""
            for i, dir_name in enumerate(path_lists):
                if i != 0:
                    new_path = f"{new_path}/{dir_name}"
                    try:
                        if i != path_lists_len:
                            sftp.mkdir(new_path)
                    except: #folder exist = error
                        pass
            try:
                sftp.put(_local_file_path, _online_file_path_list[j])
            except:
                sftp.close()
                ssh.close()

                time.sleep(10)

                return False

        sftp.close()
        ssh.close()

        time.sleep(10)
    except:
        return False

    return True

def generatePHPFile(_open_file_name):
    """変電サーバ用HTMLを作成 Copyright © 2023-2024 M.Fukuya

    Args:
        _open_file_name (str): ＤＸ定点カメラ機器台帳のパス

    Returns:
        bool: 成功時True
    """
    phptext = ""
    f = open("./template/php1.txt", "r", encoding="UTF-8")
    phptext = f"{phptext}{f.read()}\n\n"
    f.close

    df = pd.read_excel(_open_file_name, sheet_name ='common')
    txt1 = f"{str(df[df['TITLE']=='BRANCH']['VALUE'].values)[2:][:-2]}"
    phptext = f"{phptext}ほくでんネットワーク　ＤＸ定点カメラシステム（重点監視用ＤＸカメラ）{txt1}\n"

    f = open("./template/php2.txt", "r", encoding="UTF-8")
    phptext = f"{phptext}{f.read()}\n\n"
    f.close

    t_delta = datetime.timedelta(hours=9)
    JST = datetime.timezone(t_delta, 'JST')
    now = datetime.datetime.now(JST)
    d = now.strftime('%Y/%m/%d %H:%M')

    phptext = f"{phptext}{d} 作成"


    f = open("./template/php3.txt", "r", encoding="UTF-8")
    phptext = f"{phptext}{f.read()}\n\n"
    f.close

    i = 0
    s = ""
    df = pd.read_excel(_open_file_name, sheet_name ='list')
    for index, row in df.iterrows():
        if row['機器種別'].find('RaspPi') == -1:
            i = i + 1
            s = s + "<tr>\n"
            s = s + "<td align=\"center\" class=\"t1\">" + str(i) + "</td>\n"
            s = s + "<td class=\"t1\">" + row['所属'] + "</td>\n"
            s = s + "<td class=\"t1\">" + row['電気所'] + "</td>\n"
            s = s + "<td class=\"t1\">" + row['監視対象'] + "</td>\n"
            s = s + "<td class=\"t1\">" + row['データ種別'] + "</td>\n"
            s = s + "<td class=\"t1\"><input type=\"button\" value=\"Push\" onclick=\"location.href='" + row['データ表示／ダウンロードURL'] + "'\"></td>\n"
            s = s + "</tr>\n\n"
        else:
            i = i + 1
            s = s + "<tr>\n"
            s = s + "<td align=\"center\" class=\"t1\">" + str(i) + "</td>\n"
            s = s + "<td class=\"t1\">" + row['所属'] + "</td>\n"
            s = s + "<td class=\"t1\">" + row['電気所'] + "</td>\n"
            s = s + "<td class=\"t1\">" + "ＤＸ定点カメラサイト" + "</td>\n"
            s = s + "<td class=\"t1\">" + "HP" + "</td>\n"
            s = s + "<td class=\"t1\"><input type=\"button\" value=\"Push\" onclick=\"location.href='" + row['URL'] + "'\"></td>\n"
            s = s + "</tr>\n\n"

    phptext = f"{phptext}{s}"

    f = open("./template/php4.txt", "r", encoding="UTF-8")
    phptext = f"{phptext}{f.read()}\n\n"
    f.close

    f = open(f"./{txt1}.php", "w", encoding="UTF-8")
    f.write(f"{phptext}")
    f.close
    return True



# サーバ接続情報（固定値）
user = "hpnadmin"
password = "YXMxMXEhZmFvKWEqMm5hc3BRfWVFMjFn"
host = "202.177.34.22"
port = 22



st.title("📤 DX定点カメラ機器台帳 ZIPアップロード")

zip_file = st.file_uploader("ZIPファイルを選択", type=["zip"])
zip_passwd = st.text_input("ZIPパスワード", type="password")

if zip_file and zip_passwd:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
        tmp.write(zip_file.read())
        zip_path = tmp.name

    flag_unzip = True
    try:
        with zipfile.ZipFile(zip_path) as zp:
            for info in zp.infolist():
                try:
                    info.filename = info.filename.encode('cp437').decode('cp932')
                    zp.extract(info, pwd=zip_passwd.encode("utf-8"))
                except:
                    flag_unzip = False
    except:
        flag_unzip = False

    os.remove(zip_path)

    if not flag_unzip:
        st.error("❌ ZIPファイルの解凍に失敗しました。パスワードを確認してください。")
    else:
        ledgers = glob.glob("./ＤＸ定点カメラ機器台帳_*.xlsx")
        for ledger in ledgers:
            generatePHPFile(ledger)

            php_file_name = os.path.basename(ledger).replace("ＤＸ定点カメラ機器台帳_", "").replace(".xlsx", ".php")
            local_file_list = [ledger, f"./{php_file_name}"]
            online_file_list = [
                f"/home/hpnadmin/public_html/dx_data/Ledger/{os.path.basename(ledger)}",
                f"/home/hpnadmin/public_html/henden/dx_cam/{php_file_name}"
            ]

            st.write("📂 アップロード対象ファイル:", local_file_list)
            #success = uploadFilesToServer(user, password, host, port, local_file_list, online_file_list)
            st.write(user, password, host, port, local_file_list, online_file_list)
            
            if success:
                st.success("✅ ファイルアップロード成功")
            else:
                st.error("❌ ファイルアップロード失敗")

            for f in local_file_list:
                os.remove(f)

