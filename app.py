import streamlit as st
import pandas as pd
import unicodedata
import datetime as dt
from pathlib import Path
import io

# ページ設定
st.set_page_config(
    page_title="制服申請フォーム",
    page_icon="👔",
    layout="wide"
)

# CSS スタイリング
st.markdown("""
<style>
.stButton > button {
    width: 100%;
}
.success-message {
    background-color: #d4edda;
    border: 1px solid #c3e6cb;
    color: #155724;
    padding: 12px;
    border-radius: 5px;
    margin: 10px 0;
}
.warning-message {
    background-color: #fff3cd;
    border: 1px solid #ffeaa7;
    color: #856404;
    padding: 12px;
    border-radius: 5px;
    margin: 10px 0;
}
.info-message {
    background-color: #d1ecf1;
    border: 1px solid #bee5eb;
    color: #0c5460;
    padding: 12px;
    border-radius: 5px;
    margin: 10px 0;
}
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_master_data():
    """マスタデータを読み込み"""
    try:
        applicants = pd.read_csv("files/applicant_name.csv")
        locations = pd.read_csv("files/locations.csv")
        patterns = pd.read_csv("files/pattern.csv")
        sizes = pd.read_csv("files/size.csv")
        uniforms = pd.read_csv("files/uniforms.csv")
        return applicants, locations, patterns, sizes, uniforms
    except FileNotFoundError as e:
        st.error(f"マスタファイルが見つかりません: {e}")
        st.stop()

def normalize_digits(s: str) -> str:
    """全角数字を半角数字に変換し、その他の文字はそのまま返す"""
    return "".join(
        unicodedata.normalize("NFKC", ch) if "０" <= ch <= "９" else ch
        for ch in s
    )

def create_dropdown_options(df, id_col, name_col, include_blank=True):
    """ドロップダウン用のオプションを作成"""
    if df.empty:
        return ["--- 選択 ---"] if include_blank else []
    
    options = df[[id_col, name_col]].values.tolist()
    names = [name for _, name in options]
    
    if include_blank:
        names = ["--- 選択 ---"] + names
    
    return names

def get_selected_id(df, id_col, name_col, selected_name):
    """選択された名前からIDを取得"""
    if selected_name == "--- 選択 ---" or selected_name is None:
        return None
    
    matching_rows = df[df[name_col] == selected_name]
    if not matching_rows.empty:
        return matching_rows.iloc[0][id_col]
    return None

# セッション状態の初期化
if 'entries' not in st.session_state:
    st.session_state.entries = []

if 'show_success' not in st.session_state:
    st.session_state.show_success = False

if 'reset_trigger' not in st.session_state:
    st.session_state.reset_trigger = 0

if 'current_applicant' not in st.session_state:
    st.session_state.current_applicant = None

# マスタデータ読み込み
applicants, locations, patterns, sizes, uniforms = load_master_data()

# メインUI
st.title("👔 制服申請フォーム")

# フォームを使わずに連動ドロップダウンを実現
col1, col2 = st.columns(2)

with col1:
    st.subheader("基本情報")
    
    # 申請者選択（リセット時は前回の値を保持）
    applicant_options = create_dropdown_options(applicants, "ap_id", "ap_name")
    if st.session_state.current_applicant and st.session_state.current_applicant in applicant_options:
        default_applicant_index = applicant_options.index(st.session_state.current_applicant)
    else:
        default_applicant_index = 0
    selected_applicant = st.selectbox("申請者", applicant_options, 
                                    index=default_applicant_index,
                                    key=f"applicant_{st.session_state.reset_trigger}")
    
    # 施設選択
    location_options = create_dropdown_options(locations, "location_id", "location_name")
    selected_location = st.selectbox("施設", location_options, key=f"location_{st.session_state.reset_trigger}")
    
    # 制服パターン選択
    pattern_options = create_dropdown_options(patterns, "pattern_id", "pattern_name")
    selected_pattern = st.selectbox("制服パターン", pattern_options, key=f"pattern_{st.session_state.reset_trigger}")

with col2:
    st.subheader("制服詳細")
    
    # 制服選択（パターンに応じて変更）
    selected_pattern_id = get_selected_id(patterns, "pattern_id", "pattern_name", selected_pattern)
    if selected_pattern_id is not None:
        uniform_filtered = uniforms[uniforms['pattern_id'] == selected_pattern_id]
    else:
        uniform_filtered = pd.DataFrame(columns=["uniform_id", "uniform_name"])
    
    uniform_options = create_dropdown_options(uniform_filtered, "uniform_id", "uniform_name")
    selected_uniform = st.selectbox("制服", uniform_options, key=f"uniform_{st.session_state.reset_trigger}")
    
    # サイズ選択（制服に応じて変更）
    selected_uniform_id = get_selected_id(uniform_filtered, "uniform_id", "uniform_name", selected_uniform)
    if selected_uniform_id is not None:
        size_filtered = sizes[sizes['uniform_id'] == selected_uniform_id]
    else:
        size_filtered = pd.DataFrame(columns=["size_id", "size_name"])
    
    size_options = create_dropdown_options(size_filtered, "size_id", "size_name")
    selected_size = st.selectbox("サイズ", size_options, key=f"size_{st.session_state.reset_trigger}")
    
    # 数量と使用者名
    quantity_input = st.text_input("数量", placeholder="数字のみ", key=f"quantity_{st.session_state.reset_trigger}")
    user_name_input = st.text_input("使用者名", placeholder="入力してください", key=f"user_name_{st.session_state.reset_trigger}")

# バリデーション
quantity_normalized = normalize_digits(quantity_input) if quantity_input else ""
is_quantity_valid = quantity_normalized.isdigit() and quantity_normalized != ""

all_fields_filled = (
    selected_applicant != "--- 選択 ---" and
    selected_location != "--- 選択 ---" and
    selected_pattern != "--- 選択 ---" and
    selected_uniform != "--- 選択 ---" and
    selected_size != "--- 選択 ---" and
    is_quantity_valid and
    user_name_input.strip() != ""
)

# エラーメッセージ表示
if quantity_input and not is_quantity_valid:
    st.markdown('<div class="warning-message">⚠️ 数量には数字を入力してください</div>', unsafe_allow_html=True)
elif not all_fields_filled and any([selected_applicant != "--- 選択 ---", selected_location != "--- 選択 ---", quantity_input, user_name_input]):
    st.markdown('<div class="warning-message">⚠️ 全項目を入力してください</div>', unsafe_allow_html=True)

# ボタン
button_col1, button_col2 = st.columns(2)

with button_col1:
    add_entry = st.button("続けて入力", disabled=not all_fields_filled, key="add_btn")

with button_col2:
    finish_entry = st.button("入力終了して送信", disabled=not all_fields_filled, type="primary", key="finish_btn")

# ボタン処理
if add_entry and all_fields_filled:
    # エントリを追加
    entry = {
        "applicant_id": get_selected_id(applicants, "ap_id", "ap_name", selected_applicant),
        "applicant": selected_applicant,
        "location_id": get_selected_id(locations, "location_id", "location_name", selected_location),
        "location": selected_location,
        "pattern_id": get_selected_id(patterns, "pattern_id", "pattern_name", selected_pattern),
        "pattern": selected_pattern,
        "uniform_id": get_selected_id(uniform_filtered, "uniform_id", "uniform_name", selected_uniform),
        "uniform": selected_uniform,
        "size_id": get_selected_id(size_filtered, "size_id", "size_name", selected_size),
        "size": selected_size,
        "quantity": int(quantity_normalized),
        "user_name": user_name_input.strip()
    }
    
    st.session_state.entries.append(entry)
    st.markdown(f'<div class="success-message">✅ 追加しました（現在 {len(st.session_state.entries)} 件）</div>', unsafe_allow_html=True)
    
    # 申請者を保持してフォームをリセット
    st.session_state.current_applicant = selected_applicant
    st.session_state.reset_trigger += 1
    st.rerun()

if finish_entry and all_fields_filled:
    # ① 最後のエントリを追加
    entry = {
        "applicant_id": get_selected_id(applicants, "ap_id", "ap_name", selected_applicant),
        "applicant": selected_applicant,
        "location_id": get_selected_id(locations, "location_id", "location_name", selected_location),
        "location": selected_location,
        "pattern_id": get_selected_id(patterns, "pattern_id", "pattern_name", selected_pattern),
        "pattern": selected_pattern,
        "uniform_id": get_selected_id(uniform_filtered, "uniform_id", "uniform_name", selected_uniform),
        "uniform": selected_uniform,
        "size_id": get_selected_id(size_filtered, "size_id", "size_name", selected_size),
        "size": selected_size,
        "quantity": int(quantity_normalized),
        "user_name": user_name_input.strip()
    }
    st.session_state.entries.append(entry)

    # ② 結果表示フラグを立てる
    st.session_state.show_success = True

    # ③ フォーム側は次の描画でリセット（値を消すだけ）
    st.session_state.current_applicant = None
    st.session_state.reset_trigger += 1

    # ④ ページを再実行して結果表示パートへ
    st.rerun()


# 結果表示
if st.session_state.show_success and st.session_state.entries:
    st.success("✅ 送信完了 — ありがとうございました。控えをメールに転送しています")
    
    # DataFrame作成と表示
    df = pd.DataFrame(st.session_state.entries)
    
    column_order = [
        "applicant", "location", "pattern", "uniform", "size", "quantity",
        "user_name", "applicant_id", "location_id", "pattern_id", "uniform_id", "size_id"
    ]
    
    rename_map = {
        "applicant": "起票",
        "location": "施設",
        "pattern": "制服パターン",
        "uniform": "制服名",
        "size": "サイズ",
        "quantity": "個数",
        "user_name": "使用者名"
    }
    
    df_out = df[column_order].rename(columns=rename_map)
    
    st.subheader("📋 申請内容")
    st.dataframe(df_out, use_container_width=True)
    
    # CSV ダウンロード
    ts = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    filename = f"uniform_request_{ts}.csv"
    
    csv_buffer = io.StringIO()
    df_out.to_csv(csv_buffer, index=False, encoding="utf-8")
    csv_data = csv_buffer.getvalue()
    
    st.download_button(
        label="📥 CSV ファイルをダウンロード",
        data=csv_data,
        file_name=filename,
        mime="text/csv"
    )
    
    # テキスト形式表示
    st.subheader("📝 テキスト形式")
    text_output = []
    for i, row in df_out.iterrows():
        text_line = (
            f"[{i+1}] 起票:{row['起票']} / 施設:{row['施設']} / "
            f"制服パターン:{row['制服パターン']} / 制服名:{row['制服名']} / "
            f"サイズ:{row['サイズ']} / 個数:{row['個数']} / 使用者名:{row['使用者名']}"
        )
        text_output.append(text_line)
    
    st.text_area("申請内容（テキスト）", value="\n".join(text_output), height=200)
    
    # リセットボタン
    if st.button("🔄 新しい申請を開始", type="secondary"):
        st.session_state.entries = []
        st.session_state.show_success = False
        st.session_state.current_applicant = None
        st.session_state.reset_trigger += 1
        st.rerun()

# 現在の入力状況表示
if st.session_state.entries and not st.session_state.show_success:
    st.subheader("📝 現在の入力内容")
    temp_df = pd.DataFrame(st.session_state.entries)
    display_columns = ["applicant", "location", "pattern", "uniform", "size", "quantity", "user_name"]
    rename_display = {
        "applicant": "起票", "location": "施設", "pattern": "制服パターン",
        "uniform": "制服名", "size": "サイズ", "quantity": "個数", "user_name": "使用者名"
    }
    temp_display = temp_df[display_columns].rename(columns=rename_display)
    st.dataframe(temp_display, use_container_width=True)

# フッター
st.markdown("---")
st.markdown("💡 **使い方**: 各項目を選択・入力し、「続けて入力」で複数件追加できます。最後に「入力終了して送信」で完了します。")