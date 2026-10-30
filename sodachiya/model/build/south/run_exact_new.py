import pickle, sys
sys.path.insert(0,'/tmp/claude-0/t/exact')
W_OVERRIDE=pickle.load(open('/tmp/claude-0/t/exact/wnew.pkl','rb'))['WN']
OUT=sys.argv[1]
_src=open('/tmp/claude-0/t/exact/exact_model.py').read()
# 西館（西館係）：北の端の架構（梁18）を足す（10-30、ユーザー：架構の表現を端まで、南の端の架構 u21.33 とそろえる。北の妻の壁は風を受けるだけの壁）。
#   架構の番号 k と u は u = 57 − 3k（k3＝u48、KE＝11.93＝u21.21）。北の妻の壁の外面 u51（k2.0）・内面 u50.75 のすぐ内側に、2 枚組の外の板の外面が u50.74
#   （南の端の架構 u21.335 の板の外面 u21.16 と同じく壁の内面から 10）になるよう芯 u50.565（k2.145）。並びの頭に入れるので、東の桁・西の桁（頭の穴を結ぶ線）が u48 から延びる。
_KN='(57.0-50.565)/3.0'
_src=_src.replace('exec(src)', 'src=src.replace("FR=[(k,)+tuple(segs[k]) for k in kint]+[(KE,)+segx(KE)]", "KN=%s\\nFR=[(KN,)+segx(KN)]+[(k,)+tuple(segs[k]) for k in kint]+[(KE,)+segx(KE)]")\nassert "KN=" in src\nexec(src)' % _KN, 1)
exec(_src)
