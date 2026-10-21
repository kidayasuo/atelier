import pickle, sys
sys.path.insert(0,'/tmp/claude-0/t/exact')
W_OVERRIDE=pickle.load(open('/tmp/claude-0/t/exact/wnew.pkl','rb'))['WN']
OUT=sys.argv[1]
exec(open('/tmp/claude-0/t/exact/exact_model.py').read())
