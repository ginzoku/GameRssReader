import traceback
try:
    import gamer.presenter.feed_presenter as m
    print('OK imported', m)
except Exception as e:
    traceback.print_exc()
    print('ERR', repr(e))
