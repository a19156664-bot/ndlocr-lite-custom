import sys, os
ROOT = r"C:\Users\user\ndlocr-t31"
os.chdir(ROOT); sys.path.insert(0, ROOT)
from custom_gui.exporter import rows_to_txt_text, rows_to_csv_text

def R(img, rid, text):
    return {"image_name": img, "region_id": rid, "x1": 0, "y1": 0, "x2": 1,
            "y2": 1, "line_count": 1, "text": text}

F = []
def check(label, ok, detail=""):
    print(f"  [{'OK ' if ok else 'FAIL'}] {label}{'  '+detail if detail else ''}")
    if not ok: F.append(label)

IMG = "A案）国際寫眞新聞_028号_000009.jpg"
texts = ["印棉不買からシムラ會商まで", "南千壽",
         "―寫眞はカルナジタ・ハリソン街の綿糸布市場―", "土人娘も流行を■ふ",
         "デブの遺産四千圓", "獨木船で世界一周"]
rows = [R(IMG, i+1, t) for i, t in enumerate(texts)]
out = rows_to_txt_text(rows)
want = "｜".join(texts) + "\n"
print("=== 1. 利用者の実例 ===")
print(f"  出力: {out!r}")
check("完全一致", out == want)
check("先頭が区切りでない", not out.startswith("｜"))
check("末尾が区切りでない", not out.rstrip("\n").endswith("｜"))
check("全角｜(U+FF5C)を使用", "\uff5c" in out and "|" not in out)
check("1行である", out.count("\n") == 1)

print()
print("=== 2. 空の矩形は飛ばす ===")
out2 = rows_to_txt_text([R(IMG,1,"A"), R(IMG,2,""), R(IMG,3,"   "), R(IMG,4,"B")])
print(f"  出力: {out2!r}")
check("A｜B になる（区切りが連続しない）", out2 == "A｜B\n")

print()
print("=== 3. 矩形内の改行も区切りになる ===")
out3 = rows_to_txt_text([R(IMG,1,"第一章 序説\nこの書は"), R(IMG,2,"次\r\n行")])
print(f"  出力: {out3!r}")
check("改行が｜に変換される", out3 == "第一章 序説｜この書は｜次｜行\n")
check("1行である", out3.count("\n") == 1)

print()
print("=== 4. 複数画像：画像名＋TAB ===")
out4 = rows_to_txt_text([R("000009.jpg",1,"あ"), R("000009.jpg",2,"い"),
                         R("000010.jpg",1,"う")])
print(f"  出力: {out4!r}")
check("画像ごとに1行、TAB区切り",
      out4 == "000009.jpg\tあ｜い\n000010.jpg\tう\n")

print()
print("=== 5. 全部空の画像は行ごと出ない ===")
out5 = rows_to_txt_text([R("a.jpg",1,"あ"), R("b.jpg",1,""), R("c.jpg",1,"う")])
print(f"  出力: {out5!r}")
check("b.jpg の行が出ない", out5 == "a.jpg\tあ\nc.jpg\tう\n")

print()
print("=== 6. 空入力 ===")
check('rows=[] は "" を返す', rows_to_txt_text([]) == "")

print()
print("=== 7. CSV は無変更 ===")
csv_out = rows_to_csv_text(rows)
head = csv_out.split("\n")[0]
print(f"  ヘッダ: {head}")
check("CSVヘッダが従来どおり",
      head == "image_name,region_id,x1,y1,x2,y2,line_count,text")
check("CSVは矩形ごとに1行", len(csv_out.strip().split("\n")) == 7)

print()
print(f"=== FAILURES: {len(F)} ===")
for f in F: print("    -", f)
