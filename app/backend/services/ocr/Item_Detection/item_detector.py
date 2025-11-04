import re
import sys 

def filter_receipt_items(lines):
    
    filtered_lines = []
    stop_keywords = ["小", "計", "合"] 
    
    # ★アイデア2★ スキップしたいNGワードを定義
    skip_keywords = [
        "JAN", "SC", "ナンバー", "クレジット", "売上", "領収", 
        "担当", "レジ", "お預り", "お釣り", "控え", "点数", "税", "円"
    ]
    
    for index, line in enumerate(lines):
        
        # (ルール1: 最初の行はカット)
        if index == 0:
            continue
            
        cleaned_line = line.strip() 

        if not cleaned_line: # 空行はスキップ
            continue

        # ★アイデア2の処理★ NGワードが含まれていたら、その行はスキップ
        if any(keyword in cleaned_line for keyword in skip_keywords):
            continue 

        # stop_keywords (中断) のチェックは、NGワードチェックの後に置く
        # (5行目まではチェックしないルール)
        if index >= 5:
            if any(keyword in cleaned_line for keyword in stop_keywords):
                break # ループを中断

        # ★アイデア1の処理★
        # 日本語 (ひらがな、カタカナ、漢字) 以外をすべて削除
        japanese_only = re.sub(r'[^ぁ-んァ-ヶ一-龠]', '', cleaned_line)
        final_line = japanese_only.strip()
        
        # append (リストへの追加) は、アイデア1の結果に対して1回だけ行う
        if len(final_line) > 1:
             filtered_lines.append(final_line)
             

    return filtered_lines

# --- メインの実行部分 ---

def process_receipt_file(file_path):
    """
    指定されたテキストファイルパスからレシートを読み込み、処理を実行する。
    """
    try:
        with open("C:/Users/ryu03/Desktop/purojitsu/1/receipt-recipe/app/data/detected_texts/detected_text.txt", 'r', encoding='utf-8') as f:
            input_lines = f.read().splitlines()
        
        result = filter_receipt_items(input_lines)
        
        # --- 結果の出力 ---
        print(f"--- 処理結果 ({file_path}) ---")
        
        if not result:
            print("有効な商品名が見つかりませんでした。")
        else:
            for item in result:
                print(item)

    except FileNotFoundError:
        print(f"エラー: ファイルが見つかりません。")
        print(f"指定されたパス: {file_path}")
    except Exception as e:
        print(f"予期せぬエラーが発生しました: {e}")

# --- 実行 ---

# ▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼
# 処理したいパスを、この変数に 'r' を付けて指定します。
PATH_TO_YOUR_FILE = r"C:/Users/ryu03/Desktop/purojitsu/1/receipt-recipe/app/data/detected_texts/detected_text.txt"

# 'PATH_TO_YOUR_FILE' がダミーでないかチェックして実行
if PATH_TO_YOUR_FILE == "YOUR_FILE_PATH.txt":
    print("スクリプト内の 'PATH_TO_YOUR_FILE' を、")
    print("実際のテキストファイルのパスに変更してから実行してください。")
else:
    process_receipt_file(PATH_TO_YOUR_FILE)