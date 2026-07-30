import sys, os, io
ROOT = r"C:\Users\user\ndlocr-t34"
os.chdir(ROOT); sys.path.insert(0, ROOT)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from custom_gui.exporter import rows_to_txt_text, rows_to_csv_text

def R(img, rid, text):
    return {"image_name": img, "region_id": rid, "x1":0,"y1":0,"x2":1,"y2":1,
            "line_count":1, "text": text}
F=[]
def check(l, ok, d=""):
    print(f"  [{'OK ' if ok else 'FAIL'}] {l}{'  '+d if d else ''}")
    if not ok: F.append(l)

IMG = "A案）国際寫眞新聞_028号_000008.jpg"
texts = ["人の時","桂冠するか?押し切るか?","靜かに「非常時」を眺める沈默の人牧野内大臣",
         "(T生)","国際ヴアリエテ","フランスの國營富■","三十五年目に結婚","世界珍レコード"]
out = rows_to_txt_text([R(IMG,i+1,t) for i,t in enumerate(texts)])
want = IMG + "\t" + "｜".join(texts) + "\n"
print("=== 1. 利用者の実例（1ページ単体） ===")
print(f"  {out.rstrip()}")
check("完全一致", out == want)
check("TABは1つだけ", out.count("\t") == 1, f"{out.count(chr(9))}個")
check("TABの直前が画像名", out.split("\t")[0] == IMG)
check("1行である", out.count("\n") == 1)
check("全角｜(U+FF5C)", "\uff5c" in out and "|" not in out)

print()
print("=== 2. 複数画像（従来どおり） ===")
o2 = rows_to_txt_text([R("a.jpg",1,"あ"), R("a.jpg",2,"い"), R("b.jpg",1,"う")])
print(f"  {o2!r}")
check("画像ごとに1行", o2 == "a.jpg\tあ｜い\nb.jpg\tう\n")

print()
print("=== 3. Task 31 の規則が維持されているか ===")
o3 = rows_to_txt_text([R("x.jpg",1,"A"), R("x.jpg",2,""), R("x.jpg",3,"   "), R("x.jpg",4,"B")])
check("空・空白の矩形は飛ばす", o3 == "x.jpg\tA｜B\n", repr(o3))
o4 = rows_to_txt_text([R("x.jpg",1,"第一章\nこの書は"), R("x.jpg",2,"次\r\n行")])
check("矩形内の改行も区切りに", o4 == "x.jpg\t第一章｜この書は｜次｜行\n", repr(o4))
check("改行があってもTABは1つ", o4.count("\t") == 1)
o5 = rows_to_txt_text([R("a.jpg",1,"あ"), R("b.jpg",1,""), R("c.jpg",1,"う")])
check("全部空の画像は行ごと出ない", o5 == "a.jpg\tあ\nc.jpg\tう\n", repr(o5))
check("1画像で全部空なら空文字", rows_to_txt_text([R("z.jpg",1,"")]) == "")
check("rows=[] なら空文字", rows_to_txt_text([]) == "")

print()
print("=== 4. CSV は無変更 ===")
csv_out = rows_to_csv_text([R(IMG,i+1,t) for i,t in enumerate(texts)])
head = csv_out.split("\n")[0]
check("ヘッダが従来どおり", head == "image_name,region_id,x1,y1,x2,y2,line_count,text", head)
check("矩形ごとに1行(8件)", len(csv_out.strip().split("\n")) == 9)

print()
print(f"=== FAILURES: {len(F)} ===")
for f in F: print("    -", f)
